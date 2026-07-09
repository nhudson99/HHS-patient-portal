"""
Authentication routes for HHS Patient Portal
Handles user registration, login, logout, and password management
"""

from flask import Blueprint, request, jsonify
from flask import current_app
from datetime import datetime, timedelta, timezone
import os
import bcrypt
from psycopg2 import errors as pg_errors

from api.db.connection import execute_query
from api.utils.security import (
    verify_password, validate_password_strength
)
from api.utils.session_manager import (
    create_session, invalidate_session, invalidate_all_user_sessions
)
from api.utils.audit_log import (
    log_login, log_logout, log_password_change,
    log_account_lockout, get_client_ip
)
from api.middleware.auth import authenticate, check_account_lock

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
BCRYPT_ROUNDS = int(os.getenv('BCRYPT_ROUNDS', 12))
IS_PRODUCTION = os.getenv('NODE_ENV') == 'production'


def _is_bcrypt_salt(value):
    """Return True when value looks like a bcrypt salt prefix."""
    return (
        isinstance(value, str) and
        len(value) >= 29 and
        (value.startswith('$2a$') or value.startswith('$2b$') or value.startswith('$2y$'))
    )


def _is_undefined_column_error(exc):
    return isinstance(exc, pg_errors.UndefinedColumn)


def _fetch_login_user(username):
    query = """
        SELECT id, username, email, role, password_hash, salt,
               failed_login_attempts, account_locked_until, is_active,
               password_last_changed, must_change_password
        FROM users
        WHERE username = %s
    """
    try:
        user = execute_query(query, (username,), fetch_one=True)
        if user:
            user = dict(user)
            user['_supports_lockout_columns'] = True
        return user
    except Exception as exc:
        if not _is_undefined_column_error(exc):
            raise
        current_app.logger.warning(
            "Users table missing one or more auth columns during login; using compatibility query"
        )
        fallback_query = """
            SELECT id, username, email, role, password_hash, salt
            FROM users
            WHERE username = %s
        """
        user = execute_query(fallback_query, (username,), fetch_one=True)
        if not user:
            return None
        user = dict(user)
        user['failed_login_attempts'] = 0
        user['account_locked_until'] = None
        user['is_active'] = True
        user['password_last_changed'] = None
        user['must_change_password'] = False
        user['_supports_lockout_columns'] = False
        return user


def _verify_login_password(submitted_password, user):
    stored_hash = user.get('password_hash')
    if not stored_hash:
        return False

    try:
        if bcrypt.checkpw(submitted_password.encode('utf-8'), stored_hash.encode('utf-8')):
            return True
    except ValueError:
        current_app.logger.warning("Invalid stored bcrypt hash format for user %s", user.get('username'))

    stored_salt = user.get('salt')
    if stored_salt and not _is_bcrypt_salt(stored_salt):
        try:
            return verify_password(submitted_password, stored_hash, stored_salt)
        except ValueError:
            return False

    return False


def _comparison_now(reference_dt):
    if reference_dt and reference_dt.tzinfo and reference_dt.tzinfo.utcoffset(reference_dt) is not None:
        return datetime.now(timezone.utc)
    return datetime.now()

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    POST /api/auth/register
    Register a new user (patient)
    """
    try:
        data = request.get_json(silent=True) or {}
        
        # Validate required fields
        required = ['username', 'email', 'password', 'firstName', 'lastName', 'dateOfBirth']
        if not all(field in data for field in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        username = data['username']
        email = data['email']
        password = data['password']
        first_name = data['firstName']
        last_name = data['lastName']
        date_of_birth = data['dateOfBirth']
        phone = data.get('phone')
        
        # Validate password strength
        password_validation = validate_password_strength(password)
        if not password_validation['valid']:
            return jsonify({
                'error': 'Password does not meet security requirements',
                'details': password_validation['errors']
            }), 400
        
        # Check if username or email already exists
        check_query = "SELECT id FROM users WHERE username = %s OR email = %s"
        existing = execute_query(check_query, (username, email), fetch_one=True)
        
        if existing:
            return jsonify({'error': 'Username or email already exists'}), 409
        
        # Hash password on backend using bcrypt
        salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        
        # Keep salt prefix for legacy compatibility with existing records.
        # Format: $2a$10$XXXXXXXXXXXXXXXX (29 characters)
        salt_str = password_hash[:29]
        
        # Create user
        user_query = """
            INSERT INTO users (username, email, password_hash, salt, role)
            VALUES (%s, %s, %s, %s, 'patient')
            RETURNING id, username, email, role
        """
        user = execute_query(
            user_query,
            (username, email, password_hash, salt_str),
            fetch_one=True
        )
        
        # Create patient profile
        patient_query = """
            INSERT INTO patients (user_id, first_name, last_name, date_of_birth, phone)
            VALUES (%s, %s, %s, %s, %s)
        """
        execute_query(
            patient_query,
            (user['id'], first_name, last_name, date_of_birth, phone)
        )
        
        return jsonify({
            'message': 'User registered successfully',
            'user': {
                'id': str(user['id']),
                'username': user['username'],
                'email': user['email'],
                'role': user['role']
            }
        }), 201
        
    except Exception as e:
        current_app.logger.exception("Registration error")
        return jsonify({'error': 'Registration failed'}), 500

@auth_bp.route('/salt', methods=['POST'])
def get_salt():
    """
    POST /api/auth/salt
    Deprecated endpoint retained for backwards compatibility.
    """
    return jsonify({
        'error': 'Salt endpoint is deprecated. Submit plaintext password over TLS to /api/auth/login.'
    }), 410

@auth_bp.route('/login', methods=['POST'])
@check_account_lock
def login():
    """
    POST /api/auth/login
    Authenticate user and create session
    """
    try:
        data = request.get_json(silent=True) or {}
        
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({'error': 'Username and password required'}), 400
        
        username = data['username']
        password = data['password']
        
        # Get user
        user = _fetch_login_user(username)
        
        if not user:
            log_login(None, username, False, request)
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Check if account is active
        if not user['is_active']:
            log_login(user['id'], username, False, request)
            return jsonify({'error': 'Account is inactive'}), 403
        
        # Verify password server-side (industry-standard pattern over TLS).
        valid_password = _verify_login_password(password, user)
        
        if not valid_password:
            if user.get('_supports_lockout_columns'):
                # Increment failed login attempts
                max_attempts = int(os.getenv('MAX_LOGIN_ATTEMPTS', 5))
                lockout_minutes = int(os.getenv('ACCOUNT_LOCKOUT_MINUTES', 30))
                new_attempts = (user['failed_login_attempts'] or 0) + 1

                if new_attempts >= max_attempts:
                    lockout_until = datetime.now() + timedelta(minutes=lockout_minutes)

                    update_query = """
                        UPDATE users
                        SET failed_login_attempts = %s,
                            account_locked_until = %s,
                            last_failed_login = NOW()
                        WHERE id = %s
                    """
                    execute_query(update_query, (new_attempts, lockout_until, user['id']))

                    log_account_lockout(user['id'], 'Too many failed login attempts', request)

                    return jsonify({
                        'error': 'Account locked due to too many failed login attempts',
                        'minutesLocked': lockout_minutes
                    }), 423

                update_query = """
                    UPDATE users
                    SET failed_login_attempts = %s,
                        last_failed_login = NOW()
                    WHERE id = %s
                """
                execute_query(update_query, (new_attempts, user['id']))

                log_login(user['id'], username, False, request)

                return jsonify({
                    'error': 'Invalid credentials',
                    'attemptsRemaining': max_attempts - new_attempts
                }), 401

            log_login(user['id'], username, False, request)
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Reset failed login attempts
        if user.get('_supports_lockout_columns'):
            reset_query = """
                UPDATE users
                SET failed_login_attempts = 0, account_locked_until = NULL, last_login = NOW()
                WHERE id = %s
            """
            execute_query(reset_query, (user['id'],))
        
        # Check if password has expired
        password_expiry_days = int(os.getenv('PASSWORD_EXPIRY_DAYS', 90))
        password_expired = False
        if user['password_last_changed']:
            expiry_date = user['password_last_changed'] + timedelta(days=password_expiry_days)
            password_expired = _comparison_now(expiry_date) > expiry_date
        
        # Create session
        session_token = create_session(
            user['id'],
            get_client_ip(request),
            request.headers.get('User-Agent', 'unknown')
        )
        
        log_login(user['id'], username, True, request)
        
        response = jsonify({
            'message': 'Login successful',
            'sessionToken': session_token,
            'user': {
                'id': str(user['id']),
                'username': user['username'],
                'email': user['email'],
                'role': user['role']
            },
            'requirePasswordChange': user['must_change_password'] or password_expired
        })
        timeout_minutes = int(os.getenv('SESSION_TIMEOUT_MINUTES', 15))
        response.set_cookie(
            'sessionToken',
            session_token,
            max_age=timeout_minutes * 60,
            httponly=True,
            secure=IS_PRODUCTION,
            samesite='Lax',
            path='/'
        )
        return response, 200
        
    except pg_errors.UndefinedTable:
        current_app.logger.exception("Login failed because users table is missing")
        return jsonify({
            'error': 'Authentication database schema is not initialized. Run database setup and try again.'
        }), 503
    except Exception as e:
        current_app.logger.exception("Login error")
        return jsonify({'error': 'Login failed'}), 500

@auth_bp.route('/logout', methods=['POST'])
@authenticate
def logout():
    """
    POST /api/auth/logout
    Invalidate current session
    """
    try:
        if hasattr(request, 'session_token'):
            invalidate_session(request.session_token)
        
        if hasattr(request, 'user'):
            log_logout(request.user['id'], request)
        
        response = jsonify({'message': 'Logout successful'})
        response.delete_cookie('sessionToken', path='/')
        return response, 200
        
    except Exception as e:
        current_app.logger.exception("Logout error")
        return jsonify({'error': 'Logout failed'}), 500

@auth_bp.route('/change-password', methods=['POST'])
@authenticate
def change_password():
    """
    POST /api/auth/change-password
    Change user password
    """
    try:
        data = request.get_json(silent=True) or {}
        
        if not data or 'currentPassword' not in data or 'newPassword' not in data:
            return jsonify({'error': 'Current and new password required'}), 400
        
        current_password = data['currentPassword']
        new_password = data['newPassword']
        
        password_validation = validate_password_strength(new_password)
        if not password_validation['valid']:
            return jsonify({
                'error': 'Password does not meet security requirements',
                'details': password_validation['errors']
            }), 400
        
        # Get user's current password hash and salt
        user_query = "SELECT password_hash, salt FROM users WHERE id = %s"
        user = execute_query(user_query, (request.user['id'],), fetch_one=True)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Verify current password server-side to support current and legacy hashes.
        valid_password = _verify_login_password(current_password, dict(user))
        
        if not valid_password:
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Hash new password on backend
        new_salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
        new_password_hash = bcrypt.hashpw(new_password.encode('utf-8'), new_salt).decode('utf-8')
        new_salt_str = new_password_hash[:29]
        
        # Update password
        update_query = """
            UPDATE users 
            SET password_hash = %s, 
                salt = %s, 
                password_last_changed = NOW(), 
                must_change_password = false
            WHERE id = %s
        """
        execute_query(update_query, (new_password_hash, new_salt_str, request.user['id']))
        
        # Invalidate all other sessions (force re-login on other devices)
        invalidate_all_user_sessions(request.user['id'])
        
        log_password_change(request.user['id'], False, request)
        
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except Exception as e:
        current_app.logger.exception("Password change error")
        return jsonify({'error': 'Password change failed'}), 500

@auth_bp.route('/my-salt', methods=['GET'])
@authenticate
def get_my_salt():
    """
    GET /api/auth/my-salt
    Get current user's salt for password verification
    Used during password change to hash the current password
    """
    try:
        user_query = "SELECT salt FROM users WHERE id = %s"
        user = execute_query(user_query, (request.user['id'],), fetch_one=True)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'salt': user['salt']}), 200
        
    except Exception as e:
        current_app.logger.exception("Salt retrieval error")
        return jsonify({'error': 'Salt retrieval failed'}), 500

@auth_bp.route('/me', methods=['GET'])
@authenticate
def get_current_user():
    """
    GET /api/auth/me
    Get current user information
    """
    try:
        return jsonify({'user': request.user}), 200
    except Exception as e:
        current_app.logger.exception("Get user error")
        return jsonify({'error': 'Failed to get user information'}), 500

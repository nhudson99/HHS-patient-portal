"""
Authentication routes for HHS Patient Portal
Handles user registration, login, logout, and password management
"""

from flask import Blueprint, request, jsonify
from flask import current_app
from datetime import datetime, timedelta
import os
import bcrypt

from api.db.connection import execute_query
from api.utils.security import (
    generate_salt, hash_password, verify_password,
    verify_client_hashed_password, validate_password_strength
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
        
        # Store the salt as a string (the full bcrypt salt prefix needed for client-side hashing during login)
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
    Get the salt for a username (for client-side password hashing)
    This endpoint is intentionally public to allow login-time salt retrieval
    """
    try:
        data = request.get_json(silent=True) or {}
        
        if not data or 'username' not in data:
            return jsonify({'error': 'Username required'}), 400
        
        username = data['username']
        
        # Get user's salt
        user_query = "SELECT salt FROM users WHERE username = %s AND is_active = true"
        user = execute_query(user_query, (username,), fetch_one=True)
        
        if not user or not user.get('salt'):
            dummy_salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS).decode('utf-8')
            return jsonify({'salt': dummy_salt}), 200

        return jsonify({'salt': user['salt']}), 200
        
    except Exception as e:
        current_app.logger.exception("Salt retrieval error")
        return jsonify({'error': 'Salt retrieval failed'}), 500

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
        user_query = """
            SELECT id, username, email, role, password_hash, salt, 
                   failed_login_attempts, account_locked_until, is_active,
                   password_last_changed, must_change_password
            FROM users 
            WHERE username = %s
        """
        user = execute_query(user_query, (username,), fetch_one=True)
        
        if not user:
            log_login(None, username, False, request)
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Check if account is active
        if not user['is_active']:
            log_login(user['id'], username, False, request)
            return jsonify({'error': 'Account is inactive'}), 403
        
        # Verify password - since client sends pre-hashed password, compare directly
        # Client sends bcryptjs hash, we stored it directly, so they should match
        valid_password = verify_client_hashed_password(password, user['password_hash'])
        
        if not valid_password:
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
            else:
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
        
        # Reset failed login attempts
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
            password_expired = datetime.now() > expiry_date
        
        # Create session
        session_token = create_session(
            user['id'],
            get_client_ip(request),
            request.headers.get('User-Agent', 'unknown')
        )
        
        log_login(user['id'], username, True, request)
        
        return jsonify({
            'message': 'Login successful',
            'sessionToken': session_token,
            'user': {
                'id': str(user['id']),
                'username': user['username'],
                'email': user['email'],
                'role': user['role']
            },
            'requirePasswordChange': user['must_change_password'] or password_expired
        }), 200
        
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
        
        return jsonify({'message': 'Logout successful'}), 200
        
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
        
        # Verify current password using bcrypt
        valid_password = bcrypt.checkpw(current_password.encode('utf-8'), user['password_hash'].encode('utf-8'))
        
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

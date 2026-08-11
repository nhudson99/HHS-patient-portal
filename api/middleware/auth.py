"""
Authentication middleware for Flask
HIPAA Compliance: Ensures only authenticated users can access PHI
"""

from functools import wraps
from flask import request, jsonify
import os
from datetime import datetime, timezone, timedelta
from psycopg2 import errors as pg_errors
from api.utils.session_manager import validate_session
from api.db.connection import execute_query

# Endpoints allowed while a password change is required.
_PASSWORD_CHANGE_ALLOWED_PATHS = {
    '/api/auth/change-password',
    '/api/auth/logout',
    '/api/auth/me',
}


def _schema_not_initialized_response():
    return jsonify({
        'error': 'Authentication database schema is not initialized. Run database setup and try again.'
    }), 503


def _comparison_now(reference_dt):
    if reference_dt and reference_dt.tzinfo and reference_dt.tzinfo.utcoffset(reference_dt) is not None:
        return datetime.now(timezone.utc)
    return datetime.now()


def _password_change_required(user: dict) -> bool:
    if user.get('must_change_password'):
        return True

    password_last_changed = user.get('password_last_changed')
    if not password_last_changed:
        return False

    password_expiry_days = int(os.getenv('PASSWORD_EXPIRY_DAYS', 90))
    expiry_date = password_last_changed + timedelta(days=password_expiry_days)
    return _comparison_now(expiry_date) > expiry_date


def authenticate(f):
    """
    Middleware to authenticate requests using session token
    HIPAA Compliance: Ensures only authenticated users can access PHI
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get session token from Authorization header or cookie
        auth_header = request.headers.get('Authorization')
        session_token = None
        
        if auth_header and auth_header.startswith('Bearer '):
            session_token = auth_header[7:]
        elif request.cookies.get('sessionToken'):
            session_token = request.cookies.get('sessionToken')
        
        if not session_token:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Validate session
        session = validate_session(session_token)
        
        if not session:
            return jsonify({'error': 'Invalid or expired session'}), 401
        
        # Get user details — require is_active (fail closed if column missing).
        query = """
            SELECT id, username, role, email, must_change_password, password_last_changed
            FROM users
            WHERE id = %s AND is_active = true
        """
        try:
            user = execute_query(query, (session['user_id'],), fetch_one=True)
        except Exception as exc:
            if isinstance(exc, (pg_errors.UndefinedTable, pg_errors.UndefinedColumn)):
                return _schema_not_initialized_response()
            raise
        
        if not user:
            return jsonify({'error': 'User not found or inactive'}), 401

        user_data = dict(user)
        require_password_change = _password_change_required(user_data)
        user_data['requirePasswordChange'] = require_password_change
        # Keep response payloads tidy — callers use requirePasswordChange.
        user_data.pop('must_change_password', None)
        user_data.pop('password_last_changed', None)

        # Attach user to request context
        request.user = user_data
        request.session_token = session_token

        if require_password_change and request.path not in _PASSWORD_CHANGE_ALLOWED_PATHS:
            return jsonify({
                'error': 'Password change required',
                'code': 'PASSWORD_CHANGE_REQUIRED',
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function

def authorize(*allowed_roles):
    """
    Middleware to check if user has required role
    
    Args:
        *allowed_roles: Roles that are allowed to access the endpoint
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'user'):
                return jsonify({'error': 'Authentication required'}), 401
            
            if request.user['role'] not in allowed_roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def check_account_lock(f):
    """
    Middleware to check account lock status before login
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        data = request.get_json()
        username = data.get('username') if data else None
        
        if not username:
            return f(*args, **kwargs)
        
        query = "SELECT account_locked_until FROM users WHERE username = %s"
        try:
            result = execute_query(query, (username,), fetch_one=True)
        except Exception as exc:
            if isinstance(exc, (pg_errors.UndefinedTable, pg_errors.UndefinedColumn)):
                return _schema_not_initialized_response()
            raise
        
        if result and result['account_locked_until']:
            lockout_time = result['account_locked_until']
            current_time = _comparison_now(lockout_time)

            if lockout_time > current_time:
                minutes_left = int((lockout_time - current_time).total_seconds() / 60) + 1
                return jsonify({
                    'error': 'Account temporarily locked',
                    'minutesRemaining': minutes_left
                }), 423
        
        return f(*args, **kwargs)
    
    return decorated_function

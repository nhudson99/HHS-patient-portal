"""
Authentication middleware for Flask
HIPAA Compliance: Ensures only authenticated users can access PHI
"""

from functools import wraps
from flask import request, jsonify
import os
from api.utils.session_manager import validate_session
from api.db.connection import execute_query

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
        
        # Get user details
        query = """
            SELECT id, username, role, email 
            FROM users 
            WHERE id = %s AND is_active = true
        """
        user = execute_query(query, (session['user_id'],), fetch_one=True)
        
        if not user:
            return jsonify({'error': 'User not found or inactive'}), 401
        
        # Attach user to request context
        request.user = dict(user)
        request.session_token = session_token
        
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
        result = execute_query(query, (username,), fetch_one=True)
        
        if result and result['account_locked_until']:
            lockout_time = result['account_locked_until']
            from datetime import datetime
            
            if lockout_time > datetime.now():
                minutes_left = int((lockout_time - datetime.now()).total_seconds() / 60) + 1
                return jsonify({
                    'error': 'Account temporarily locked',
                    'minutesRemaining': minutes_left
                }), 423
        
        return f(*args, **kwargs)
    
    return decorated_function

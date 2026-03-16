"""
HIPAA Compliance: Session Management Module

HIPAA requires:
- Automatic logoff after period of inactivity
- Session timeout enforcement
- Secure session tracking
"""

import os
from datetime import datetime, timedelta
from api.db.connection import execute_query
from api.utils.security import generate_session_token

def create_session(user_id, ip_address, user_agent):
    """
    Create a new session for a user
    
    Args:
        user_id: User UUID
        ip_address: Client IP address
        user_agent: Client user agent
        
    Returns:
        str: Session token
    """
    session_token = generate_session_token()
    timeout_minutes = int(os.getenv('SESSION_TIMEOUT_MINUTES', 15))
    expires_at = datetime.now() + timedelta(minutes=timeout_minutes)
    
    query = """
        INSERT INTO user_sessions 
        (user_id, session_token, ip_address, user_agent, expires_at)
        VALUES (%s, %s, %s, %s, %s)
    """
    
    execute_query(query, (user_id, session_token, ip_address, user_agent, expires_at))
    
    return session_token

def validate_session(session_token):
    """
    Validate session and check if it's still active
    
    Args:
        session_token: Session token to validate
        
    Returns:
        dict: Session data or None if invalid
    """
    query = """
        SELECT * FROM user_sessions 
        WHERE session_token = %s 
        AND expires_at > NOW()
    """
    
    session = execute_query(query, (session_token,), fetch_one=True)
    
    if not session:
        return None
    
    # Update last activity timestamp
    update_session_activity(session_token)
    
    return dict(session)

def update_session_activity(session_token):
    """
    Update session last activity and extend expiration
    
    Args:
        session_token: Session token to update
    """
    timeout_minutes = int(os.getenv('SESSION_TIMEOUT_MINUTES', 15))
    new_expires_at = datetime.now() + timedelta(minutes=timeout_minutes)
    
    query = """
        UPDATE user_sessions 
        SET last_activity = NOW(), expires_at = %s
        WHERE session_token = %s
    """
    
    execute_query(query, (new_expires_at, session_token))

def invalidate_session(session_token):
    """
    Invalidate a session (logout)
    
    Args:
        session_token: Session token to invalidate
    """
    query = """
        DELETE FROM user_sessions 
        WHERE session_token = %s
    """
    
    execute_query(query, (session_token,))

def invalidate_all_user_sessions(user_id):
    """
    Invalidate all sessions for a user (force logout from all devices)
    
    Args:
        user_id: User UUID
    """
    query = """
        DELETE FROM user_sessions 
        WHERE user_id = %s
    """
    
    execute_query(query, (user_id,))

def cleanup_expired_sessions():
    """Clean up expired sessions"""
    query = """
        DELETE FROM user_sessions 
        WHERE expires_at < NOW()
    """
    
    result = execute_query(query)
    print(f"Cleaned up {result} expired sessions")

def get_user_sessions(user_id):
    """
    Get active sessions for a user
    
    Args:
        user_id: User UUID
        
    Returns:
        list: Active sessions
    """
    query = """
        SELECT * FROM user_sessions 
        WHERE user_id = %s 
        AND expires_at > NOW()
        ORDER BY last_activity DESC
    """
    
    sessions = execute_query(query, (user_id,), fetch_all=True)
    return [dict(s) for s in sessions] if sessions else []

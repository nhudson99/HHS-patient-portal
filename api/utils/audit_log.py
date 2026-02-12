"""
HIPAA Compliance: Audit Logging Module

HIPAA requires tracking of all access to Protected Health Information (PHI)
This includes: who accessed what, when, from where, and what action was taken
"""

import json
import logging
from datetime import datetime, timedelta
from api.db.connection import execute_query
import os

logger = logging.getLogger(__name__)

def log_audit_event(user_id=None, action=None, table_name=None, record_id=None,
                   ip_address=None, user_agent=None, details=None):
    """
    Log an audit event to the database
    
    Args:
        user_id: UUID of user performing action
        action: Action performed (LOGIN_SUCCESS, DATA_VIEW, etc.)
        table_name: Database table accessed
        record_id: ID of record accessed
        ip_address: Client IP address
        user_agent: Client user agent string
        details: Additional details as dictionary
    """
    try:
        query = """
            INSERT INTO audit_logs 
            (user_id, action, table_name, record_id, ip_address, user_agent, details)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        details_json = json.dumps(details) if details else None
        
        execute_query(
            query,
            (user_id, action, table_name, record_id, ip_address, user_agent, details_json)
        )
    except Exception as e:
        logger.error(f"Failed to log audit event: {e}")
        # Don't throw - audit logging should not break application flow
        # But in production, this should trigger alerts

def get_client_ip(request):
    """
    Extract IP address from request (handles proxies)
    
    Args:
        request: Flask request object
        
    Returns:
        str: Client IP address
    """
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or 'unknown'

def log_login(user_id, username, success, request):
    """
    Log user login attempt
    
    Args:
        user_id: User ID (None if login failed)
        username: Username attempted
        success: Boolean indicating success
        request: Flask request object
    """
    log_audit_event(
        user_id=user_id,
        action='LOGIN_SUCCESS' if success else 'LOGIN_FAILURE',
        ip_address=get_client_ip(request),
        user_agent=request.headers.get('User-Agent'),
        details={
            'username': username,
            'timestamp': datetime.now().isoformat()
        }
    )

def log_logout(user_id, request):
    """
    Log user logout
    
    Args:
        user_id: User ID
        request: Flask request object
    """
    log_audit_event(
        user_id=user_id,
        action='LOGOUT',
        ip_address=get_client_ip(request),
        user_agent=request.headers.get('User-Agent'),
        details={'timestamp': datetime.now().isoformat()}
    )

def log_data_access(user_id, table_name, record_id, action, request):
    """
    Log data access (viewing PHI)
    
    Args:
        user_id: User ID
        table_name: Database table accessed
        record_id: Record ID accessed
        action: Action type (VIEW, CREATE, UPDATE, DELETE)
        request: Flask request object
    """
    log_audit_event(
        user_id=user_id,
        action=f'DATA_{action}',
        table_name=table_name,
        record_id=record_id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get('User-Agent'),
        details={'timestamp': datetime.now().isoformat()}
    )

def log_password_change(user_id, forced, request):
    """
    Log password changes
    
    Args:
        user_id: User ID
        forced: Boolean indicating if change was forced
        request: Flask request object
    """
    log_audit_event(
        user_id=user_id,
        action='PASSWORD_CHANGE',
        ip_address=get_client_ip(request),
        user_agent=request.headers.get('User-Agent'),
        details={
            'forced': forced,
            'timestamp': datetime.now().isoformat()
        }
    )

def log_account_lockout(user_id, reason, request):
    """
    Log account lockout
    
    Args:
        user_id: User ID
        reason: Reason for lockout
        request: Flask request object
    """
    log_audit_event(
        user_id=user_id,
        action='ACCOUNT_LOCKED',
        ip_address=get_client_ip(request),
        user_agent=request.headers.get('User-Agent'),
        details={
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        }
    )

def cleanup_old_audit_logs():
    """
    Clean up old audit logs based on retention policy
    HIPAA requires at least 6 years of retention
    """
    retention_days = int(os.getenv('AUDIT_LOG_RETENTION_DAYS', 2555))  # ~7 years default
    
    try:
        query = """
            DELETE FROM audit_logs 
            WHERE timestamp < NOW() - INTERVAL '%s days'
        """
        
        result = execute_query(query, (retention_days,))
        logger.info(f"Cleaned up {result} old audit log entries")
    except Exception as e:
        logger.error(f"Failed to cleanup audit logs: {e}")

"""
Security utilities for HHS Patient Portal
HIPAA-compliant password hashing and validation
"""

import bcrypt
import secrets
import os
import re
from datetime import datetime, timedelta

# HIPAA-compliant password hashing
SALT_ROUNDS = 12  # Higher rounds for better security

def generate_salt():
    """
    Generate a cryptographically secure salt
    This salt is stored separately in the database for additional security
    """
    return secrets.token_hex(32)

def hash_password(password, salt):
    """
    Hash password with bcrypt (includes its own salt) + additional pepper salt
    The pepper salt is stored in the database, bcrypt salt is embedded in hash
    
    Args:
        password: Plain text password
        salt: Pepper salt from database
        
    Returns:
        str: Hashed password
    """
    # Combine password with pepper salt
    peppered_password = (password + salt).encode('utf-8')
    # Hash with bcrypt (bcrypt adds its own salt internally)
    hashed = bcrypt.hashpw(peppered_password, bcrypt.gensalt(rounds=SALT_ROUNDS))
    return hashed.decode('utf-8')

def verify_password(password, hashed, salt):
    """
    Verify password against stored hash and salt
    
    Args:
        password: Plain text password to verify
        hashed: Stored password hash
        salt: Pepper salt from database
        
    Returns:
        bool: True if password matches
    """
    peppered_password = (password + salt).encode('utf-8')
    return bcrypt.checkpw(peppered_password, hashed.encode('utf-8'))

def verify_client_hashed_password(client_hash, stored_hash):
    """
    Verify a client-side hashed password against stored hash.
    
    When client sends a pre-hashed password (from bcryptjs), we compare it
    directly with the stored hash. The client used the same salt that we stored,
    so the hashes should match if the original password was correct.
    
    Args:
        client_hash: Hash from client (bcryptjs hash)
        stored_hash: Stored password hash from database
        
    Returns:
        bool: True if hashes match
    """
    return client_hash == stored_hash

def generate_session_token():
    """Generate secure session token"""
    return secrets.token_urlsafe(64)

def validate_password_strength(password):
    """
    Validate password strength (HIPAA compliance)
    Requirements:
    - At least 8 characters
    - Contains uppercase and lowercase
    - Contains numbers
    - Contains special characters
    
    Returns:
        dict: {'valid': bool, 'errors': list}
    """
    errors = []
    
    if len(password) < 8:
        errors.append('Password must be at least 8 characters long')
    
    if not re.search(r'[a-z]', password):
        errors.append('Password must contain at least one lowercase letter')
    
    if not re.search(r'[A-Z]', password):
        errors.append('Password must contain at least one uppercase letter')
    
    if not re.search(r'\d', password):
        errors.append('Password must contain at least one number')
    
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
        errors.append('Password must contain at least one special character')
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }

def is_password_expired(last_changed):
    """
    Check if password has expired (HIPAA compliance)
    
    Args:
        last_changed: datetime of last password change
        
    Returns:
        bool: True if password has expired
    """
    expiry_days = int(os.getenv('PASSWORD_EXPIRY_DAYS', 90))
    expiry_date = last_changed + timedelta(days=expiry_days)
    return datetime.now() > expiry_date

def sanitize_input(input_str):
    """
    Sanitize input to prevent SQL injection
    
    Args:
        input_str: Input string to sanitize
        
    Returns:
        str: Sanitized string
    """
    if not input_str:
        return input_str
    # Remove potentially dangerous characters
    return re.sub(r'[^\w\s@.-]', '', input_str.strip())

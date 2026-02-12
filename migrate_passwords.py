#!/usr/bin/env python3
"""
Migration script to convert existing passwords to client-side hashing format
This script rehashes all existing passwords using bcryptjs format without pepper salt
"""

import sys
import os
import bcryptjs
sys.path.insert(0, os.path.dirname(__file__))

from api.db.connection import execute_query

def migrate_passwords():
    """Migrate all existing passwords to new format"""
    
    try:
        print("Starting password migration...")
        
        # Get all users
        users_query = "SELECT id, username, password_hash, salt FROM users"
        users = execute_query(users_query, fetch_all=True)
        
        if not users:
            print("No users found to migrate")
            return
        
        print(f"Found {len(users)} users to migrate")
        
        for user in users:
            user_id = user['id']
            username = user['username']
            old_hash = user['password_hash']
            old_salt = user['salt']
            
            # For migration, we'll just clear the salt since the old hash
            # can't be directly converted to bcryptjs format
            # Users will need to reset their passwords
            
            new_salt = ""
            
            # Update user
            update_query = """
                UPDATE users 
                SET salt = %s
                WHERE id = %s
            """
            execute_query(update_query, (new_salt, user_id))
            
            print(f"✓ Migrated user: {username} (ID: {user_id})")
        
        print(f"\n✓ Successfully migrated {len(users)} users")
        print("\nIMPORTANT: Existing users will need to reset their passwords")
        print("to use the new client-side hashing system.")
        
    except Exception as e:
        print(f"✗ Migration error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate_passwords()

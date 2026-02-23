"""
Database connection module for HHS Patient Portal
PostgreSQL connection with HIPAA-compliant settings
"""

import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# PostgreSQL connection pool with HIPAA-compliant settings
connection_pool = None

def init_db_pool():
    """Initialize database connection pool"""
    global connection_pool
    
    try:
        connection_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=20,
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5432)),
            database=os.getenv('DB_NAME', 'hhs_patient_portal'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD'),
            # SSL for production (required for HIPAA compliance)
            sslmode='require' if os.getenv('NODE_ENV') == 'production' else 'prefer'
        )
        logger.info("✅ Connected to PostgreSQL database")
        return connection_pool
    except Exception as e:
        logger.error(f"❌ Failed to create connection pool: {e}")
        raise

def get_db_connection():
    """Get a connection from the pool"""
    if connection_pool is None:
        init_db_pool()
    return connection_pool.getconn()

def release_db_connection(conn):
    """Return a connection to the pool"""
    if connection_pool:
        connection_pool.putconn(conn)

def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    """
    Execute a query with error handling and logging
    
    Args:
        query: SQL query string
        params: Query parameters
        fetch_one: Return single result
        fetch_all: Return all results
        
    Returns:
        Query results or None
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(query, params)
        
        if fetch_one:
            result = cursor.fetchone()
            conn.commit()  # Commit after fetch for INSERT...RETURNING
        elif fetch_all:
            result = cursor.fetchall()
            conn.commit()  # Commit after fetch
        else:
            conn.commit()
            result = cursor.rowcount
            
        cursor.close()
        return result
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database query error: {e}")
        raise
    finally:
        if conn:
            release_db_connection(conn)

class DatabaseTransaction:
    """Context manager for database transactions"""
    
    def __init__(self):
        self.conn = None
        self.cursor = None
        
    def __enter__(self):
        self.conn = get_db_connection()
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        return self.cursor
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.conn.rollback()
        else:
            self.conn.commit()
        
        if self.cursor:
            self.cursor.close()
        if self.conn:
            release_db_connection(self.conn)
        
        return False

def close_db_pool():
    """Close all connections in the pool"""
    global connection_pool
    if connection_pool:
        connection_pool.closeall()
        logger.info("Database connection pool closed")

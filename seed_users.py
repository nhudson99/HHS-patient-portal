#!/usr/bin/env python3
"""
Seed script to create test users in the database
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.db.connection import execute_query, init_db_pool, DatabaseTransaction
from api.utils.security import generate_salt, hash_password
from dotenv import load_dotenv

load_dotenv()

def create_test_users():
    """Create test users for demo purposes"""
    
    print("🌱 Seeding database with test users...")
    
    init_db_pool()
    
    # Test patient user
    patient_username = "patient1"
    patient_password = "Patient123!"
    patient_email = "patient1@test.com"
    
    # Test doctor user
    doctor_username = "doctor1"
    doctor_password = "Doctor123!"
    doctor_email = "doctor1@test.com"
    
    try:
        # Use a transaction for each user creation
        # Check if patient already exists
        existing_patient = execute_query(
            "SELECT id FROM users WHERE username = %s",
            (patient_username,),
            fetch_one=True
        )
        
        if not existing_patient:
            print(f"Creating patient user: {patient_username}")
            
            # Create patient user and profile in a transaction
            with DatabaseTransaction() as cursor:
                # Create patient user
                patient_salt = generate_salt()
                patient_hash = hash_password(patient_password, patient_salt)
                
                cursor.execute(
                    """INSERT INTO users (username, email, password_hash, salt, role)
                       VALUES (%s, %s, %s, %s, 'patient')
                       RETURNING id""",
                    (patient_username, patient_email, patient_hash, patient_salt)
                )
                patient_result = cursor.fetchone()
                
                # Create patient profile
                cursor.execute(
                    """INSERT INTO patients (user_id, first_name, last_name, date_of_birth, phone)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (patient_result['id'], 'John', 'Smith', '1990-05-15', '555-0100')
                )
            
            print(f"✅ Created patient: {patient_username} / {patient_password}")
        else:
            print(f"ℹ️  Patient user already exists: {patient_username}")
        
        # Check if doctor already exists
        existing_doctor = execute_query(
            "SELECT id FROM users WHERE username = %s",
            (doctor_username,),
            fetch_one=True
        )
        
        if not existing_doctor:
            print(f"Creating doctor user: {doctor_username}")
            
            # Create doctor user and profile in a transaction
            with DatabaseTransaction() as cursor:
                # Create doctor user
                doctor_salt = generate_salt()
                doctor_hash = hash_password(doctor_password, doctor_salt)
                
                cursor.execute(
                    """INSERT INTO users (username, email, password_hash, salt, role)
                       VALUES (%s, %s, %s, %s, 'doctor')
                       RETURNING id""",
                    (doctor_username, doctor_email, doctor_hash, doctor_salt)
                )
                doctor_result = cursor.fetchone()
                
                # Create doctor profile
                cursor.execute(
                    """INSERT INTO doctors (user_id, first_name, last_name, specialty, license_number)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (doctor_result['id'], 'Sarah', 'Johnson', 'Family Medicine', 'MD12345')
                )
            
            print(f"✅ Created doctor: {doctor_username} / {doctor_password}")
        else:
            print(f"ℹ️  Doctor user already exists: {doctor_username}")
        
        print("\n" + "="*60)
        print("✅ Database seeding complete!")
        print("="*60)
        print("\nTest Credentials:")
        print(f"  Patient: {patient_username} / {patient_password}")
        print(f"  Doctor:  {doctor_username} / {doctor_password}")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    create_test_users()

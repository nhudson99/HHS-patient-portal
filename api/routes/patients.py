"""
Patients routes for HHS Patient Portal
Provides patient record access for doctors; allows doctors to create patients
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import date, datetime
from api.db.connection import execute_query
from api.middleware.auth import authenticate
import secrets
import string
import bcrypt
from api.db.connection import DatabaseTransaction

patients_bp = Blueprint('patients', __name__, url_prefix='/api/patients')
INSUFFICIENT_PERMISSIONS_ERROR = 'Insufficient permissions'


def _generate_temp_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def _hash_password(plain: str) -> tuple[str, str]:
    salt = bcrypt.gensalt(rounds=12).decode()
    hashed = bcrypt.hashpw(plain.encode(), salt.encode()).decode()
    return hashed, salt


def serialize_patient(patient):
    if not patient:
        return None
    result = dict(patient)
    for key, value in result.items():
        if isinstance(value, (datetime, date)):
            result[key] = value.isoformat()
    return result


def serialize_doctor(doctor):
    if not doctor:
        return None
    result = dict(doctor)
    for key, value in result.items():
        if isinstance(value, (datetime, date)):
            result[key] = value.isoformat()
    return result


@patients_bp.route('/doctors', methods=['GET'])
@authenticate
def list_doctors():
    try:
        user = request.user
        if user.get('role') not in ['patient', 'doctor']:
            return jsonify({'error': INSUFFICIENT_PERMISSIONS_ERROR}), 403

        query = """
            SELECT d.id, d.user_id, d.first_name, d.last_name, d.specialty,
                   d.license_number, d.phone, d.created_at, d.updated_at,
                   u.email AS portal_email
            FROM doctors d
            LEFT JOIN users u ON d.user_id = u.id
            ORDER BY d.last_name, d.first_name
        """
        doctors = execute_query(query, fetch_all=True) or []
        return jsonify({'doctors': [serialize_doctor(d) for d in doctors]}), 200

    except Exception:
        current_app.logger.exception('Doctors retrieval error')
        return jsonify({'error': 'Failed to retrieve doctors'}), 500


@patients_bp.route('/me', methods=['GET'])
@authenticate
def get_my_patient_record():
    """Get the currently authenticated patient's own record"""
    try:
        user = request.user
        if user.get('role') != 'patient':
            return jsonify({'error': INSUFFICIENT_PERMISSIONS_ERROR}), 403

        query = """
            SELECT p.id, p.user_id, p.first_name, p.last_name, p.date_of_birth,
                   p.phone, p.address, p.emergency_contact_name,
                   p.emergency_contact_phone, p.created_at, p.updated_at,
                   u.email AS portal_email
            FROM patients p
            LEFT JOIN users u ON p.user_id = u.id
            WHERE p.user_id = %s
        """
        patient = execute_query(query, (user['id'],), fetch_one=True)

        if not patient:
            return jsonify({'error': 'Patient record not found'}), 404

        return jsonify({'patient': serialize_patient(patient)}), 200

    except Exception:
        current_app.logger.exception('Patient self-lookup error')
        return jsonify({'error': 'Failed to retrieve patient record'}), 500


@patients_bp.route('', methods=['GET'])
@authenticate
def list_patients():
    try:
        user = request.user
        if user.get('role') != 'doctor':
            return jsonify({'error': INSUFFICIENT_PERMISSIONS_ERROR}), 403

        query = """
            SELECT p.id, p.user_id, p.first_name, p.last_name, p.date_of_birth,
                   p.phone, p.address, p.emergency_contact_name,
                   p.emergency_contact_phone, p.created_at, p.updated_at,
                   u.email AS portal_email
            FROM patients p
            LEFT JOIN users u ON p.user_id = u.id
            ORDER BY p.last_name, p.first_name
        """
        patients = execute_query(query, fetch_all=True) or []
        return jsonify({'patients': [serialize_patient(p) for p in patients]}), 200

    except Exception:
        current_app.logger.exception('Patients retrieval error')
        return jsonify({'error': 'Failed to retrieve patients'}), 500


@patients_bp.route('', methods=['POST'])
@authenticate
def create_patient():
    """
    POST /api/patients
    Doctor creates a new patient account with a temporary password.
    """
    try:
        user = request.user
        if user.get('role') != 'doctor':
            return jsonify({'error': INSUFFICIENT_PERMISSIONS_ERROR}), 403

        data = request.get_json(silent=True) or {}
        required = ['username', 'email', 'firstName', 'lastName']
        if not all(data.get(f) for f in required):
            return jsonify({'error': 'username, email, firstName, and lastName are required'}), 400

        username = data['username'].strip()
        email = data['email'].strip().lower()
        first_name = data['firstName'].strip()
        last_name = data['lastName'].strip()
        date_of_birth = data.get('dateOfBirth') or None
        phone = data.get('phone', '').strip() or None
        address = data.get('address', '').strip() or None

        # Check for duplicate username or email
        existing = execute_query(
            "SELECT id FROM users WHERE username = %s OR email = %s",
            (username, email),
            fetch_one=True,
        )
        if existing:
            return jsonify({'error': 'Username or email already in use'}), 409

        temp_password = _generate_temp_password()
        password_hash, salt = _hash_password(temp_password)

        with DatabaseTransaction() as cursor:
            cursor.execute(
                """
                INSERT INTO users (username, email, password_hash, salt, role, must_change_password)
                VALUES (%s, %s, %s, %s, 'patient', true)
                RETURNING id, username, email, role
                """,
                (username, email, password_hash, salt),
            )
            new_user = cursor.fetchone()

            cursor.execute(
                """
                INSERT INTO patients (user_id, first_name, last_name, date_of_birth, phone, address)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, user_id, first_name, last_name, date_of_birth, phone, address,
                          created_at, updated_at
                """,
                (new_user['id'], first_name, last_name, date_of_birth, phone, address),
            )
            patient = cursor.fetchone()

        result = serialize_patient(dict(patient))
        result['username'] = new_user['username']
        result['email'] = new_user['email']
        result['is_active'] = True

        current_app.logger.info(
            'Doctor %s created patient %s (%s)',
            user.get('username'),
            username,
            patient['id'],
        )

        return jsonify({
            'patient': result,
            'temporaryPassword': temp_password,
        }), 201

    except Exception:
        current_app.logger.exception('Doctor create patient error')
        return jsonify({'error': 'Failed to create patient'}), 500

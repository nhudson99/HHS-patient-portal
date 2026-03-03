"""
Patients routes for HHS Patient Portal
Provides read access to patient records for doctors
"""

from flask import Blueprint, request, jsonify
from datetime import date, datetime
from api.db.connection import execute_query
from api.middleware.auth import authenticate

patients_bp = Blueprint('patients', __name__, url_prefix='/api/patients')


def serialize_patient(patient):
    if not patient:
        return None
    result = dict(patient)
    for key, value in result.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, date):
            result[key] = value.isoformat()
    return result


def serialize_doctor(doctor):
    if not doctor:
        return None
    result = dict(doctor)
    for key, value in result.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, date):
            result[key] = value.isoformat()
    return result


@patients_bp.route('/doctors', methods=['GET'])
@authenticate
def list_doctors():
    try:
        user = request.user
        if user.get('role') not in ['patient', 'doctor']:
            return jsonify({'error': 'Insufficient permissions'}), 403

        query = """
            SELECT d.id, d.user_id, d.first_name, d.last_name, d.specialty,
                   d.phone, d.office_address, d.created_at, d.updated_at,
                   u.email AS portal_email
            FROM doctors d
            LEFT JOIN users u ON d.user_id = u.id
            ORDER BY d.last_name, d.first_name
        """
        doctors = execute_query(query, fetch_all=True) or []
        return jsonify({'doctors': [serialize_doctor(d) for d in doctors]}), 200

    except Exception as e:
        print(f"Doctors retrieval error: {e}")
        return jsonify({'error': 'Failed to retrieve doctors'}), 500


@patients_bp.route('', methods=['GET'])
@authenticate
def list_patients():
    try:
        user = request.user
        if user.get('role') != 'doctor':
            return jsonify({'error': 'Insufficient permissions'}), 403

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

    except Exception as e:
        print(f"Patients retrieval error: {e}")
        return jsonify({'error': 'Failed to retrieve patients'}), 500

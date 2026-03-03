"""
Appointments routes for patient appointment requests and management
Handles appointment requests, confirmations, and check-ins
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, date
from api.db.connection import execute_query
from api.middleware.auth import authenticate

appointments_bp = Blueprint('appointments', __name__, url_prefix='/api/appointments')


def serialize_appointment(apt):
    """Convert appointment dict with date/time objects to JSON-serializable dict"""
    if not apt:
        return None
    result = dict(apt)
    for key, value in result.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, date):
            result[key] = value.isoformat()
    return result


@appointments_bp.route('/patient', methods=['GET'])
@authenticate
def get_patient_appointments():
    """
    GET /api/appointments/patient
    Get appointments for the logged-in patient
    """
    try:
        user = request.user
        
        if user.get('role') != 'patient':
            return jsonify({'error': 'Only patients can access this endpoint'}), 403
        
        # Get patient ID from user
        patient_query = "SELECT id FROM patients WHERE user_id = %s"
        patient = execute_query(patient_query, (user['id'],), fetch_one=True)
        
        if not patient:
            return jsonify({'error': 'Patient record not found'}), 404
        
        patient_id = patient['id']
        
        # Get patient's appointments
        query = """
            SELECT a.id, a.patient_id, a.doctor_id, a.appointment_date, a.reason, a.status,
                   a.created_at, a.updated_at,
                   CONCAT(d.first_name, ' ', d.last_name) AS doctor_name
            FROM appointments a
            LEFT JOIN doctors d ON a.doctor_id = d.id
            WHERE a.patient_id = %s
            ORDER BY a.appointment_date DESC
        """
        
        appointments = execute_query(query, (patient_id,), fetch_all=True)
        
        return jsonify({
            'appointments': [serialize_appointment(apt) for apt in (appointments or [])]
        }), 200
        
    except Exception as e:
        print(f"Get patient appointments error: {e}")
        return jsonify({'error': 'Failed to retrieve appointments'}), 500


@appointments_bp.route('/request', methods=['POST'])
@authenticate
def request_appointment():
    """
    POST /api/appointments/request
    Patient requests an appointment with a doctor
    """
    try:
        user = request.user
        
        if user.get('role') != 'patient':
            return jsonify({'error': 'Only patients can request appointments'}), 403
        
        data = request.get_json()
        
        # Validate required fields
        required = ['doctor_id', 'appointment_date', 'appointment_time', 'reason']
        if not all(field in data for field in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Get patient ID from user
        patient_query = "SELECT id FROM patients WHERE user_id = %s"
        patient = execute_query(patient_query, (user['id'],), fetch_one=True)
        
        if not patient:
            return jsonify({'error': 'Patient record not found'}), 404
        
        patient_id = patient['id']
        doctor_id = data['doctor_id']
        
        # Verify doctor exists
        doctor_query = "SELECT id FROM doctors WHERE id = %s"
        doctor = execute_query(doctor_query, (doctor_id,), fetch_one=True)
        
        if not doctor:
            return jsonify({'error': 'Doctor not found'}), 404
        
        # Combine date and time into appointment_date
        appointment_date = f"{data['appointment_date']} {data['appointment_time']}"
        reason = data['reason']
        
        # Insert appointment with status 'pending'
        insert_query = """
            INSERT INTO appointments
            (patient_id, doctor_id, appointment_date, reason, status)
            VALUES (%s, %s, %s, %s, 'pending')
            RETURNING id, patient_id, doctor_id, appointment_date, reason, status,
                      created_at, updated_at
        """
        
        appointment = execute_query(
            insert_query,
            (patient_id, doctor_id, appointment_date, reason),
            fetch_one=True
        )
        
        return jsonify({
            'message': 'Appointment request submitted successfully',
            'appointment': serialize_appointment(appointment)
        }), 201
        
    except Exception as e:
        print(f"Appointment request error: {e}")
        return jsonify({'error': 'Failed to request appointment'}), 500


@appointments_bp.route('/<appointment_id>/checkin', methods=['POST'])
@authenticate
def checkin_appointment(appointment_id):
    """
    POST /api/appointments/<appointment_id>/checkin
    Check in to an appointment (patient-only)
    """
    try:
        user = request.user
        
        if user.get('role') != 'patient':
            return jsonify({'error': 'Only patients can check in'}), 403
        
        # Get patient ID from user
        patient_query = "SELECT id FROM patients WHERE user_id = %s"
        patient = execute_query(patient_query, (user['id'],), fetch_one=True)
        
        if not patient:
            return jsonify({'error': 'Patient record not found'}), 404
        
        patient_id = patient['id']
        
        # Verify appointment exists and belongs to patient
        apt_query = """
            SELECT id, appointment_date, status FROM appointments
            WHERE id = %s AND patient_id = %s
        """
        appointment = execute_query(apt_query, (appointment_id, patient_id), fetch_one=True)
        
        if not appointment:
            return jsonify({'error': 'Appointment not found'}), 404
        
        # Check if already checked in
        checkin_query = "SELECT id FROM appointment_checkins WHERE appointment_id = %s"
        existing_checkin = execute_query(checkin_query, (appointment_id,), fetch_one=True)
        
        if existing_checkin:
            return jsonify({'error': 'Already checked in for this appointment'}), 400
        
        # Record check-in
        insert_checkin = """
            INSERT INTO appointment_checkins
            (appointment_id, patient_id, check_in_method)
            VALUES (%s, %s, 'online')
            RETURNING id, appointment_id, patient_id, checked_in_at
        """
        
        checkin = execute_query(
            insert_checkin,
            (appointment_id, patient_id),
            fetch_one=True
        )
        
        return jsonify({
            'message': 'Check-in successful',
            'checkin': serialize_appointment(checkin)
        }), 201
        
    except Exception as e:
        print(f"Check-in error: {e}")
        return jsonify({'error': 'Failed to check in'}), 500


@appointments_bp.route('/<appointment_id>/checkin-guest', methods=['POST'])
def checkin_appointment_guest(appointment_id):
    """
    POST /api/appointments/<appointment_id>/checkin-guest
    Check in to an appointment as guest (name + DOB)
    No authentication required
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['patient_name', 'date_of_birth']
        if not all(field in data for field in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        patient_name = data['patient_name']
        dob = data['date_of_birth']
        
        # Find patient by name and DOB
        patient_query = """
            SELECT id FROM patients
            WHERE LOWER(CONCAT(first_name, ' ', last_name)) = LOWER(%s)
            AND date_of_birth = %s
        """
        
        patient = execute_query(
            patient_query,
            (patient_name, dob),
            fetch_one=True
        )
        
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        patient_id = patient['id']
        
        # Verify appointment exists and belongs to patient
        apt_query = """
            SELECT id FROM appointments
            WHERE id = %s AND patient_id = %s
        """
        appointment = execute_query(apt_query, (appointment_id, patient_id), fetch_one=True)
        
        if not appointment:
            return jsonify({'error': 'Appointment not found'}), 404
        
        # Check if already checked in
        checkin_query = "SELECT id FROM appointment_checkins WHERE appointment_id = %s"
        existing_checkin = execute_query(checkin_query, (appointment_id,), fetch_one=True)
        
        if existing_checkin:
            return jsonify({'error': 'Already checked in for this appointment'}), 400
        
        # Record guest check-in
        insert_checkin = """
            INSERT INTO appointment_checkins
            (appointment_id, patient_id, check_in_method)
            VALUES (%s, %s, 'guest')
            RETURNING id, appointment_id, patient_id, checked_in_at
        """
        
        checkin = execute_query(
            insert_checkin,
            (appointment_id, patient_id),
            fetch_one=True
        )
        
        return jsonify({
            'message': 'Guest check-in successful',
            'checkin': serialize_appointment(checkin)
        }), 201
        
    except Exception as e:
        print(f"Guest check-in error: {e}")
        return jsonify({'error': 'Failed to check in'}), 500

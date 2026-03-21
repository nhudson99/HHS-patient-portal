"""
Appointments routes for patient appointment requests and management
Handles appointment requests, confirmations, and check-ins
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, date, time
from api.db.connection import execute_query
from api.middleware.auth import authenticate
from api.utils.notifications import send_unregistered_checkin_alert

appointments_bp = Blueprint('appointments', __name__, url_prefix='/api/appointments')
APPOINTMENT_NOT_FOUND_ERROR = 'Appointment not found'
PATIENT_ID_BY_USER_QUERY = "SELECT id FROM patients WHERE user_id = %s"
PATIENT_RECORD_NOT_FOUND_ERROR = 'Patient record not found'


def _normalize_appointment_time(raw_time: str) -> str:
    value = (raw_time or '').strip()
    if not value:
        return ''
    if len(value) >= 5:
        return value[:5]
    return value


def _alert_unregistered_checkin(patient_name: str, appointment_time: str, note: str) -> None:
    send_unregistered_checkin_alert(
        patient_name=patient_name,
        appointment_time=appointment_time or 'not provided',
        note=note,
        logger=current_app.logger,
    )


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
        elif isinstance(value, time):
            result[key] = value.strftime('%H:%M:%S')
    return result


@appointments_bp.route('/kiosk/lookup', methods=['POST'])
def kiosk_lookup():
    """
    POST /api/appointments/kiosk/lookup
    No auth required — finds a patient's next upcoming appointment by name + DOB.
    Used by the front-desk tablet kiosk.
    """
    try:
        data = request.get_json(silent=True) or {}
        if not data or not data.get('patient_name') or not data.get('date_of_birth'):
            return jsonify({'error': 'Full name and date of birth are required'}), 400

        patient_name = data['patient_name'].strip()
        dob = data['date_of_birth']
        appointment_time = _normalize_appointment_time(data.get('appointment_time', ''))

        # Match patient by full name + DOB (case-insensitive)
        patient_query = """
            SELECT p.id,
                   u.username,
                   CONCAT(p.first_name, ' ', p.last_name) AS full_name
            FROM patients p
            JOIN users u ON u.id = p.user_id
            WHERE LOWER(CONCAT(p.first_name, ' ', p.last_name)) = LOWER(%s)
              AND p.date_of_birth = %s
        """
        patient = execute_query(patient_query, (patient_name, dob), fetch_one=True)

        if not patient:
            _alert_unregistered_checkin(
                patient_name=patient_name,
                appointment_time=appointment_time,
                note='No patient record matched kiosk lookup input',
            )
            return jsonify({'error': 'No patient found with that name and date of birth'}), 404

        # Find their next upcoming appointment
        apt_query = """
            SELECT a.id,
                   a.appointment_date,
                   a.reason,
                   a.status,
                   CONCAT(d_p.first_name, ' ', d_p.last_name) AS doctor_name
            FROM appointments a
            LEFT JOIN doctors doc ON doc.id = a.doctor_id
            LEFT JOIN patients d_p ON d_p.user_id = doc.user_id
            WHERE a.patient_id = %s
              AND a.appointment_date >= CURRENT_DATE
              AND a.status NOT IN ('cancelled', 'completed')
              AND (%s = '' OR TO_CHAR(a.appointment_date, 'HH24:MI') = %s)
            ORDER BY a.appointment_date ASC
            LIMIT 1
        """
        appointment = execute_query(apt_query, (patient['id'], appointment_time, appointment_time), fetch_one=True)

        if not appointment:
            _alert_unregistered_checkin(
                patient_name=patient_name,
                appointment_time=appointment_time,
                note='No appointment matched kiosk lookup criteria',
            )
            return jsonify({'error': 'No upcoming appointments found'}), 404

        return jsonify({'appointment': serialize_appointment(appointment)}), 200

    except Exception:
        current_app.logger.exception('Kiosk lookup error')
        return jsonify({'error': 'Lookup failed'}), 500


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
        patient = execute_query(PATIENT_ID_BY_USER_QUERY, (user['id'],), fetch_one=True)
        
        if not patient:
            return jsonify({'error': PATIENT_RECORD_NOT_FOUND_ERROR}), 404
        
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
        
    except Exception:
        current_app.logger.exception('Get patient appointments error')
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

        data = request.get_json(silent=True) or {}

        required = ['doctor_id', 'appointment_date', 'appointment_time', 'reason']
        if not all(field in data for field in required):
            return jsonify({'error': 'Missing required fields'}), 400

        patient = execute_query(PATIENT_ID_BY_USER_QUERY, (user['id'],), fetch_one=True)
        if not patient:
            return jsonify({'error': PATIENT_RECORD_NOT_FOUND_ERROR}), 404

        doctor_id = data['doctor_id']
        doctor = execute_query("SELECT id FROM doctors WHERE id = %s", (doctor_id,), fetch_one=True)
        if not doctor:
            return jsonify({'error': 'Doctor not found'}), 404

        insert_query = """
            INSERT INTO appointments
            (patient_id, doctor_id, appointment_date, reason, status)
            VALUES (%s, %s, (%s::date + %s::time), %s, 'pending')
            RETURNING id, patient_id, doctor_id, appointment_date, reason, status,
                      created_at, updated_at
        """

        appointment = execute_query(
            insert_query,
            (
                patient['id'],
                doctor_id,
                data['appointment_date'],
                data['appointment_time'],
                data['reason'],
            ),
            fetch_one=True,
        )

        return jsonify({
            'message': 'Appointment request submitted successfully',
            'appointment': serialize_appointment(appointment)
        }), 201

    except Exception:
        current_app.logger.exception('Appointment request error')
        return jsonify({'error': 'Failed to request appointment'}), 500


@appointments_bp.route('/<appointment_id>/confirm', methods=['PATCH'])
@authenticate
def confirm_appointment(appointment_id):
    """
    PATCH /api/appointments/<appointment_id>/confirm
    Doctor confirms a pending appointment
    """
    try:
        user = request.user

        if user.get('role') != 'doctor':
            return jsonify({'error': 'Only doctors can confirm appointments'}), 403

        # Get doctor ID
        doctor_query = "SELECT id FROM doctors WHERE user_id = %s"
        doctor = execute_query(doctor_query, (user['id'],), fetch_one=True)

        if not doctor:
            return jsonify({'error': 'Doctor record not found'}), 404

        # Verify appointment belongs to this doctor and is pending
        apt_query = """
            SELECT id, status FROM appointments
            WHERE id = %s AND doctor_id = %s
        """
        appointment = execute_query(apt_query, (appointment_id, doctor['id']), fetch_one=True)

        if not appointment:
            return jsonify({'error': APPOINTMENT_NOT_FOUND_ERROR}), 404

        if appointment['status'] != 'pending':
            return jsonify({'error': f"Cannot confirm appointment with status '{appointment['status']}'"}), 400

        # Update status to confirmed
        update_query = """
            UPDATE appointments
            SET status = 'confirmed', updated_at = NOW()
            WHERE id = %s
            RETURNING id, patient_id, doctor_id, appointment_date,
                      status, reason, notes, created_at, updated_at
        """
        updated = execute_query(update_query, (appointment_id,), fetch_one=True)

        return jsonify({
            'message': 'Appointment confirmed',
            'appointment': serialize_appointment(updated)
        }), 200

    except Exception:
        current_app.logger.exception('Appointment confirm error')
        return jsonify({'error': 'Failed to confirm appointment'}), 500


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
        patient = execute_query(PATIENT_ID_BY_USER_QUERY, (user['id'],), fetch_one=True)
        
        if not patient:
            return jsonify({'error': PATIENT_RECORD_NOT_FOUND_ERROR}), 404
        
        patient_id = patient['id']
        
        # Verify appointment exists and belongs to patient
        apt_query = """
            SELECT id, appointment_date, status FROM appointments
            WHERE id = %s AND patient_id = %s
        """
        appointment = execute_query(apt_query, (appointment_id, patient_id), fetch_one=True)
        
        if not appointment:
            return jsonify({'error': APPOINTMENT_NOT_FOUND_ERROR}), 404
        
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
        
    except Exception:
        current_app.logger.exception('Check-in error')
        return jsonify({'error': 'Failed to check in'}), 500


@appointments_bp.route('/<appointment_id>/checkin-guest', methods=['POST'])
def checkin_appointment_guest(appointment_id):
    """
    POST /api/appointments/<appointment_id>/checkin-guest
    Check in to an appointment as guest (name + DOB)
    No authentication required
    """
    try:
        data = request.get_json(silent=True) or {}
        
        # Validate required fields
        required = ['patient_name', 'date_of_birth']
        if not all(field in data for field in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        patient_name = data['patient_name'].strip()
        dob = data['date_of_birth']
        appointment_time = _normalize_appointment_time(data.get('appointment_time', ''))
        
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
            _alert_unregistered_checkin(
                patient_name=patient_name,
                appointment_time=appointment_time,
                note='Guest check-in could not find patient',
            )
            return jsonify({'error': 'Patient not found'}), 404
        
        patient_id = patient['id']
        
        # Verify appointment exists and belongs to patient
        apt_query = """
            SELECT id FROM appointments
            WHERE id = %s AND patient_id = %s
        """
        appointment = execute_query(apt_query, (appointment_id, patient_id), fetch_one=True)
        
        if not appointment:
            _alert_unregistered_checkin(
                patient_name=patient_name,
                appointment_time=appointment_time,
                note='Guest check-in could not match appointment id to patient',
            )
            return jsonify({'error': APPOINTMENT_NOT_FOUND_ERROR}), 404
        
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
        
    except Exception:
        current_app.logger.exception('Guest check-in error')
        return jsonify({'error': 'Failed to check in'}), 500

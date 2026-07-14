"""
Provider-only patient chart routes
Summary + CRUD for allergies, medications, and problems
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, date
from api.db.connection import execute_query
from api.middleware.auth import authenticate
from api.utils.audit_log import log_data_access

chart_bp = Blueprint('chart', __name__, url_prefix='/api/chart')

INSUFFICIENT_PERMISSIONS_ERROR = 'Insufficient permissions'
PATIENT_NOT_FOUND_ERROR = 'Patient not found'
FAILED_RETRIEVE_SUMMARY_ERROR = 'Failed to retrieve chart summary'
FAILED_RETRIEVE_ALLERGIES_ERROR = 'Failed to retrieve allergies'
FAILED_CREATE_ALLERGY_ERROR = 'Failed to create allergy'
FAILED_UPDATE_ALLERGY_ERROR = 'Failed to update allergy'
FAILED_DELETE_ALLERGY_ERROR = 'Failed to delete allergy'
FAILED_RETRIEVE_MEDICATIONS_ERROR = 'Failed to retrieve medications'
FAILED_CREATE_MEDICATION_ERROR = 'Failed to create medication'
FAILED_UPDATE_MEDICATION_ERROR = 'Failed to update medication'
FAILED_DELETE_MEDICATION_ERROR = 'Failed to delete medication'
FAILED_RETRIEVE_PROBLEMS_ERROR = 'Failed to retrieve problems'
FAILED_CREATE_PROBLEM_ERROR = 'Failed to create problem'
FAILED_UPDATE_PROBLEM_ERROR = 'Failed to update problem'
FAILED_DELETE_PROBLEM_ERROR = 'Failed to delete problem'

ALLERGY_SEVERITIES = {'mild', 'moderate', 'severe', 'unknown'}
ALLERGY_STATUSES = {'active', 'inactive'}
MEDICATION_STATUSES = {'active', 'discontinued', 'completed'}
PROBLEM_STATUSES = {'active', 'resolved', 'inactive'}

ALLERGY_SELECT = """
    SELECT a.id, a.patient_id, a.allergen, a.reaction, a.severity, a.status,
           a.notes, a.recorded_at, a.created_by_doctor_id,
           a.created_at, a.updated_at,
           d.first_name || ' ' || d.last_name AS created_by_name
    FROM allergies a
    LEFT JOIN doctors d ON d.id = a.created_by_doctor_id
"""

MEDICATION_SELECT = """
    SELECT m.id, m.patient_id, m.name, m.dosage, m.frequency, m.route, m.status,
           m.start_date, m.end_date, m.notes, m.prescribed_by_doctor_id,
           m.created_at, m.updated_at,
           d.first_name || ' ' || d.last_name AS prescribed_by_name
    FROM medications m
    LEFT JOIN doctors d ON d.id = m.prescribed_by_doctor_id
"""

PROBLEM_SELECT = """
    SELECT p.id, p.patient_id, p.name, p.status, p.onset_date, p.resolved_date,
           p.notes, p.created_by_doctor_id, p.created_at, p.updated_at,
           d.first_name || ' ' || d.last_name AS created_by_name
    FROM problems p
    LEFT JOIN doctors d ON d.id = p.created_by_doctor_id
"""


def serialize_row(row):
    if not row:
        return None
    result = dict(row)
    for key, value in result.items():
        if isinstance(value, (datetime, date)):
            result[key] = value.isoformat()
    return result


def _get_doctor_id(user_id):
    doctor_row = execute_query(
        'SELECT id FROM doctors WHERE user_id = %s',
        (user_id,),
        fetch_one=True,
    )
    return doctor_row['id'] if doctor_row else None


def _require_doctor():
    user = request.user
    if user.get('role') != 'doctor':
        return None, (jsonify({'error': INSUFFICIENT_PERMISSIONS_ERROR}), 403)
    doctor_id = _get_doctor_id(user['id'])
    if not doctor_id:
        return None, (jsonify({'error': INSUFFICIENT_PERMISSIONS_ERROR}), 403)
    return doctor_id, None


def _patient_exists(patient_id):
    row = execute_query(
        'SELECT id FROM patients WHERE id = %s',
        (patient_id,),
        fetch_one=True,
    )
    return bool(row)


def _parse_optional_date(value, field_name):
    if value is None or value == '':
        return None, None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value, None
    try:
        return date.fromisoformat(str(value)[:10]), None
    except ValueError:
        return None, (jsonify({'error': f'{field_name} must be a valid date (YYYY-MM-DD)'}), 400)


def _fetch_allergy(allergy_id, patient_id=None):
    query = f"{ALLERGY_SELECT} WHERE a.id = %s"
    params = [allergy_id]
    if patient_id:
        query += ' AND a.patient_id = %s'
        params.append(patient_id)
    return execute_query(query, tuple(params), fetch_one=True)


def _fetch_medication(medication_id, patient_id=None):
    query = f"{MEDICATION_SELECT} WHERE m.id = %s"
    params = [medication_id]
    if patient_id:
        query += ' AND m.patient_id = %s'
        params.append(patient_id)
    return execute_query(query, tuple(params), fetch_one=True)


def _fetch_problem(problem_id, patient_id=None):
    query = f"{PROBLEM_SELECT} WHERE p.id = %s"
    params = [problem_id]
    if patient_id:
        query += ' AND p.patient_id = %s'
        params.append(patient_id)
    return execute_query(query, tuple(params), fetch_one=True)


@chart_bp.route('/<patient_id>/summary', methods=['GET'])
@authenticate
def get_summary(patient_id):
    try:
        doctor_id, error_response = _require_doctor()
        if error_response:
            return error_response

        if not _patient_exists(patient_id):
            return jsonify({'error': PATIENT_NOT_FOUND_ERROR}), 404

        allergies = execute_query(
            f"{ALLERGY_SELECT} WHERE a.patient_id = %s AND a.status = 'active' ORDER BY a.allergen",
            (patient_id,),
            fetch_all=True,
        ) or []
        medications = execute_query(
            f"{MEDICATION_SELECT} WHERE m.patient_id = %s AND m.status = 'active' ORDER BY m.name",
            (patient_id,),
            fetch_all=True,
        ) or []
        problems = execute_query(
            f"{PROBLEM_SELECT} WHERE p.patient_id = %s AND p.status = 'active' ORDER BY p.name",
            (patient_id,),
            fetch_all=True,
        ) or []

        user = request.user
        log_data_access(user['id'], 'chart_summary', patient_id, 'VIEW', request)

        return jsonify({
            'summary': {
                'allergies': [serialize_row(row) for row in allergies],
                'medications': [serialize_row(row) for row in medications],
                'problems': [serialize_row(row) for row in problems],
                'allergy_count': len(allergies),
                'medication_count': len(medications),
                'problem_count': len(problems),
            }
        }), 200
    except Exception:
        current_app.logger.exception('Chart summary retrieval error')
        return jsonify({'error': FAILED_RETRIEVE_SUMMARY_ERROR}), 500


@chart_bp.route('/<patient_id>/allergies', methods=['GET'])
@authenticate
def list_allergies(patient_id):
    try:
        doctor_id, error_response = _require_doctor()
        if error_response:
            return error_response

        if not _patient_exists(patient_id):
            return jsonify({'error': PATIENT_NOT_FOUND_ERROR}), 404

        rows = execute_query(
            f"{ALLERGY_SELECT} WHERE a.patient_id = %s ORDER BY a.status, a.allergen",
            (patient_id,),
            fetch_all=True,
        ) or []
        log_data_access(request.user['id'], 'allergies', patient_id, 'VIEW', request)
        return jsonify({'allergies': [serialize_row(row) for row in rows]}), 200
    except Exception:
        current_app.logger.exception('Allergies list error')
        return jsonify({'error': FAILED_RETRIEVE_ALLERGIES_ERROR}), 500


@chart_bp.route('/<patient_id>/allergies', methods=['POST'])
@authenticate
def create_allergy(patient_id):
    try:
        doctor_id, error_response = _require_doctor()
        if error_response:
            return error_response

        if not _patient_exists(patient_id):
            return jsonify({'error': PATIENT_NOT_FOUND_ERROR}), 404

        data = request.get_json(silent=True) or {}
        allergen = (data.get('allergen') or '').strip()
        if not allergen:
            return jsonify({'error': 'allergen is required'}), 400

        severity = (data.get('severity') or 'unknown').strip().lower()
        if severity not in ALLERGY_SEVERITIES:
            return jsonify({'error': 'severity must be mild, moderate, severe, or unknown'}), 400

        status = (data.get('status') or 'active').strip().lower()
        if status not in ALLERGY_STATUSES:
            return jsonify({'error': 'status must be active or inactive'}), 400

        insert_query = """
            INSERT INTO allergies (
                patient_id, allergen, reaction, severity, status, notes, created_by_doctor_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        created = execute_query(
            insert_query,
            (
                patient_id,
                allergen,
                data.get('reaction'),
                severity,
                status,
                data.get('notes'),
                doctor_id,
            ),
            fetch_one=True,
        )
        allergy = _fetch_allergy(created['id'], patient_id)
        log_data_access(request.user['id'], 'allergies', created['id'], 'CREATE', request)
        return jsonify({'allergy': serialize_row(allergy)}), 201
    except Exception:
        current_app.logger.exception('Allergy creation error')
        return jsonify({'error': FAILED_CREATE_ALLERGY_ERROR}), 500


@chart_bp.route('/<patient_id>/allergies/<allergy_id>', methods=['PUT'])
@authenticate
def update_allergy(patient_id, allergy_id):
    try:
        doctor_id, error_response = _require_doctor()
        if error_response:
            return error_response

        existing = _fetch_allergy(allergy_id, patient_id)
        if not existing:
            return jsonify({'error': 'Allergy not found'}), 404

        data = request.get_json(silent=True) or {}
        allergen = data.get('allergen', existing['allergen'])
        allergen = (allergen or '').strip()
        if not allergen:
            return jsonify({'error': 'allergen cannot be empty'}), 400

        severity = (data.get('severity', existing['severity']) or 'unknown').strip().lower()
        if severity not in ALLERGY_SEVERITIES:
            return jsonify({'error': 'severity must be mild, moderate, severe, or unknown'}), 400

        status = (data.get('status', existing['status']) or 'active').strip().lower()
        if status not in ALLERGY_STATUSES:
            return jsonify({'error': 'status must be active or inactive'}), 400

        reaction = data['reaction'] if 'reaction' in data else existing.get('reaction')
        notes = data['notes'] if 'notes' in data else existing.get('notes')

        updated = execute_query(
            """
            UPDATE allergies
            SET allergen = %s, reaction = %s, severity = %s, status = %s,
                notes = %s, updated_at = NOW()
            WHERE id = %s AND patient_id = %s
            RETURNING id
            """,
            (allergen, reaction, severity, status, notes, allergy_id, patient_id),
            fetch_one=True,
        )
        if not updated:
            return jsonify({'error': 'Allergy not found'}), 404

        allergy = _fetch_allergy(allergy_id, patient_id)
        log_data_access(request.user['id'], 'allergies', allergy_id, 'UPDATE', request)
        return jsonify({'allergy': serialize_row(allergy)}), 200
    except Exception:
        current_app.logger.exception('Allergy update error')
        return jsonify({'error': FAILED_UPDATE_ALLERGY_ERROR}), 500


@chart_bp.route('/<patient_id>/allergies/<allergy_id>', methods=['DELETE'])
@authenticate
def delete_allergy(patient_id, allergy_id):
    try:
        doctor_id, error_response = _require_doctor()
        if error_response:
            return error_response

        existing = _fetch_allergy(allergy_id, patient_id)
        if not existing:
            return jsonify({'error': 'Allergy not found'}), 404

        deleted = execute_query(
            'DELETE FROM allergies WHERE id = %s AND patient_id = %s RETURNING id',
            (allergy_id, patient_id),
            fetch_one=True,
        )
        if not deleted:
            return jsonify({'error': 'Allergy not found'}), 404

        log_data_access(request.user['id'], 'allergies', allergy_id, 'DELETE', request)
        return jsonify({'message': 'Allergy deleted'}), 200
    except Exception:
        current_app.logger.exception('Allergy deletion error')
        return jsonify({'error': FAILED_DELETE_ALLERGY_ERROR}), 500


@chart_bp.route('/<patient_id>/medications', methods=['GET'])
@authenticate
def list_medications(patient_id):
    try:
        doctor_id, error_response = _require_doctor()
        if error_response:
            return error_response

        if not _patient_exists(patient_id):
            return jsonify({'error': PATIENT_NOT_FOUND_ERROR}), 404

        rows = execute_query(
            f"{MEDICATION_SELECT} WHERE m.patient_id = %s ORDER BY m.status, m.name",
            (patient_id,),
            fetch_all=True,
        ) or []
        log_data_access(request.user['id'], 'medications', patient_id, 'VIEW', request)
        return jsonify({'medications': [serialize_row(row) for row in rows]}), 200
    except Exception:
        current_app.logger.exception('Medications list error')
        return jsonify({'error': FAILED_RETRIEVE_MEDICATIONS_ERROR}), 500


@chart_bp.route('/<patient_id>/medications', methods=['POST'])
@authenticate
def create_medication(patient_id):
    try:
        doctor_id, error_response = _require_doctor()
        if error_response:
            return error_response

        if not _patient_exists(patient_id):
            return jsonify({'error': PATIENT_NOT_FOUND_ERROR}), 404

        data = request.get_json(silent=True) or {}
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'error': 'name is required'}), 400

        status = (data.get('status') or 'active').strip().lower()
        if status not in MEDICATION_STATUSES:
            return jsonify({'error': 'status must be active, discontinued, or completed'}), 400

        start_date, start_error = _parse_optional_date(data.get('start_date'), 'start_date')
        if start_error:
            return start_error
        end_date, end_error = _parse_optional_date(data.get('end_date'), 'end_date')
        if end_error:
            return end_error

        created = execute_query(
            """
            INSERT INTO medications (
                patient_id, name, dosage, frequency, route, status,
                start_date, end_date, notes, prescribed_by_doctor_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                patient_id,
                name,
                data.get('dosage'),
                data.get('frequency'),
                data.get('route'),
                status,
                start_date,
                end_date,
                data.get('notes'),
                doctor_id,
            ),
            fetch_one=True,
        )
        medication = _fetch_medication(created['id'], patient_id)
        log_data_access(request.user['id'], 'medications', created['id'], 'CREATE', request)
        return jsonify({'medication': serialize_row(medication)}), 201
    except Exception:
        current_app.logger.exception('Medication creation error')
        return jsonify({'error': FAILED_CREATE_MEDICATION_ERROR}), 500


@chart_bp.route('/<patient_id>/medications/<medication_id>', methods=['PUT'])
@authenticate
def update_medication(patient_id, medication_id):
    try:
        doctor_id, error_response = _require_doctor()
        if error_response:
            return error_response

        existing = _fetch_medication(medication_id, patient_id)
        if not existing:
            return jsonify({'error': 'Medication not found'}), 404

        data = request.get_json(silent=True) or {}
        name = data.get('name', existing['name'])
        name = (name or '').strip()
        if not name:
            return jsonify({'error': 'name cannot be empty'}), 400

        status = (data.get('status', existing['status']) or 'active').strip().lower()
        if status not in MEDICATION_STATUSES:
            return jsonify({'error': 'status must be active, discontinued, or completed'}), 400

        start_date, start_error = _parse_optional_date(
            data['start_date'] if 'start_date' in data else existing.get('start_date'),
            'start_date',
        )
        if start_error:
            return start_error
        end_date, end_error = _parse_optional_date(
            data['end_date'] if 'end_date' in data else existing.get('end_date'),
            'end_date',
        )
        if end_error:
            return end_error

        dosage = data['dosage'] if 'dosage' in data else existing.get('dosage')
        frequency = data['frequency'] if 'frequency' in data else existing.get('frequency')
        route = data['route'] if 'route' in data else existing.get('route')
        notes = data['notes'] if 'notes' in data else existing.get('notes')

        updated = execute_query(
            """
            UPDATE medications
            SET name = %s, dosage = %s, frequency = %s, route = %s, status = %s,
                start_date = %s, end_date = %s, notes = %s, updated_at = NOW()
            WHERE id = %s AND patient_id = %s
            RETURNING id
            """,
            (
                name, dosage, frequency, route, status,
                start_date, end_date, notes, medication_id, patient_id,
            ),
            fetch_one=True,
        )
        if not updated:
            return jsonify({'error': 'Medication not found'}), 404

        medication = _fetch_medication(medication_id, patient_id)
        log_data_access(request.user['id'], 'medications', medication_id, 'UPDATE', request)
        return jsonify({'medication': serialize_row(medication)}), 200
    except Exception:
        current_app.logger.exception('Medication update error')
        return jsonify({'error': FAILED_UPDATE_MEDICATION_ERROR}), 500


@chart_bp.route('/<patient_id>/medications/<medication_id>', methods=['DELETE'])
@authenticate
def delete_medication(patient_id, medication_id):
    try:
        doctor_id, error_response = _require_doctor()
        if error_response:
            return error_response

        existing = _fetch_medication(medication_id, patient_id)
        if not existing:
            return jsonify({'error': 'Medication not found'}), 404

        deleted = execute_query(
            'DELETE FROM medications WHERE id = %s AND patient_id = %s RETURNING id',
            (medication_id, patient_id),
            fetch_one=True,
        )
        if not deleted:
            return jsonify({'error': 'Medication not found'}), 404

        log_data_access(request.user['id'], 'medications', medication_id, 'DELETE', request)
        return jsonify({'message': 'Medication deleted'}), 200
    except Exception:
        current_app.logger.exception('Medication deletion error')
        return jsonify({'error': FAILED_DELETE_MEDICATION_ERROR}), 500


@chart_bp.route('/<patient_id>/problems', methods=['GET'])
@authenticate
def list_problems(patient_id):
    try:
        doctor_id, error_response = _require_doctor()
        if error_response:
            return error_response

        if not _patient_exists(patient_id):
            return jsonify({'error': PATIENT_NOT_FOUND_ERROR}), 404

        rows = execute_query(
            f"{PROBLEM_SELECT} WHERE p.patient_id = %s ORDER BY p.status, p.name",
            (patient_id,),
            fetch_all=True,
        ) or []
        log_data_access(request.user['id'], 'problems', patient_id, 'VIEW', request)
        return jsonify({'problems': [serialize_row(row) for row in rows]}), 200
    except Exception:
        current_app.logger.exception('Problems list error')
        return jsonify({'error': FAILED_RETRIEVE_PROBLEMS_ERROR}), 500


@chart_bp.route('/<patient_id>/problems', methods=['POST'])
@authenticate
def create_problem(patient_id):
    try:
        doctor_id, error_response = _require_doctor()
        if error_response:
            return error_response

        if not _patient_exists(patient_id):
            return jsonify({'error': PATIENT_NOT_FOUND_ERROR}), 404

        data = request.get_json(silent=True) or {}
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'error': 'name is required'}), 400

        status = (data.get('status') or 'active').strip().lower()
        if status not in PROBLEM_STATUSES:
            return jsonify({'error': 'status must be active, resolved, or inactive'}), 400

        onset_date, onset_error = _parse_optional_date(data.get('onset_date'), 'onset_date')
        if onset_error:
            return onset_error
        resolved_date, resolved_error = _parse_optional_date(data.get('resolved_date'), 'resolved_date')
        if resolved_error:
            return resolved_error

        created = execute_query(
            """
            INSERT INTO problems (
                patient_id, name, status, onset_date, resolved_date, notes, created_by_doctor_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                patient_id,
                name,
                status,
                onset_date,
                resolved_date,
                data.get('notes'),
                doctor_id,
            ),
            fetch_one=True,
        )
        problem = _fetch_problem(created['id'], patient_id)
        log_data_access(request.user['id'], 'problems', created['id'], 'CREATE', request)
        return jsonify({'problem': serialize_row(problem)}), 201
    except Exception:
        current_app.logger.exception('Problem creation error')
        return jsonify({'error': FAILED_CREATE_PROBLEM_ERROR}), 500


@chart_bp.route('/<patient_id>/problems/<problem_id>', methods=['PUT'])
@authenticate
def update_problem(patient_id, problem_id):
    try:
        doctor_id, error_response = _require_doctor()
        if error_response:
            return error_response

        existing = _fetch_problem(problem_id, patient_id)
        if not existing:
            return jsonify({'error': 'Problem not found'}), 404

        data = request.get_json(silent=True) or {}
        name = data.get('name', existing['name'])
        name = (name or '').strip()
        if not name:
            return jsonify({'error': 'name cannot be empty'}), 400

        status = (data.get('status', existing['status']) or 'active').strip().lower()
        if status not in PROBLEM_STATUSES:
            return jsonify({'error': 'status must be active, resolved, or inactive'}), 400

        onset_date, onset_error = _parse_optional_date(
            data['onset_date'] if 'onset_date' in data else existing.get('onset_date'),
            'onset_date',
        )
        if onset_error:
            return onset_error
        resolved_date, resolved_error = _parse_optional_date(
            data['resolved_date'] if 'resolved_date' in data else existing.get('resolved_date'),
            'resolved_date',
        )
        if resolved_error:
            return resolved_error

        notes = data['notes'] if 'notes' in data else existing.get('notes')

        updated = execute_query(
            """
            UPDATE problems
            SET name = %s, status = %s, onset_date = %s, resolved_date = %s,
                notes = %s, updated_at = NOW()
            WHERE id = %s AND patient_id = %s
            RETURNING id
            """,
            (name, status, onset_date, resolved_date, notes, problem_id, patient_id),
            fetch_one=True,
        )
        if not updated:
            return jsonify({'error': 'Problem not found'}), 404

        problem = _fetch_problem(problem_id, patient_id)
        log_data_access(request.user['id'], 'problems', problem_id, 'UPDATE', request)
        return jsonify({'problem': serialize_row(problem)}), 200
    except Exception:
        current_app.logger.exception('Problem update error')
        return jsonify({'error': FAILED_UPDATE_PROBLEM_ERROR}), 500


@chart_bp.route('/<patient_id>/problems/<problem_id>', methods=['DELETE'])
@authenticate
def delete_problem(patient_id, problem_id):
    try:
        doctor_id, error_response = _require_doctor()
        if error_response:
            return error_response

        existing = _fetch_problem(problem_id, patient_id)
        if not existing:
            return jsonify({'error': 'Problem not found'}), 404

        deleted = execute_query(
            'DELETE FROM problems WHERE id = %s AND patient_id = %s RETURNING id',
            (problem_id, patient_id),
            fetch_one=True,
        )
        if not deleted:
            return jsonify({'error': 'Problem not found'}), 404

        log_data_access(request.user['id'], 'problems', problem_id, 'DELETE', request)
        return jsonify({'message': 'Problem deleted'}), 200
    except Exception:
        current_app.logger.exception('Problem deletion error')
        return jsonify({'error': FAILED_DELETE_PROBLEM_ERROR}), 500

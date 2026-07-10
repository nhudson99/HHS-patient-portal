"""
Patient properties routes
Supports variable properties per patient (doctor-only)
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, date
from api.db.connection import execute_query
from api.middleware.auth import authenticate
from api.utils.audit_log import log_data_access

patient_properties_bp = Blueprint('patient_properties', __name__, url_prefix='/api/patient-properties')
INSUFFICIENT_PERMISSIONS_ERROR = 'Insufficient permissions'
FAILED_RETRIEVE_PROPERTIES_ERROR = 'Failed to retrieve patient properties'
FAILED_CREATE_PROPERTY_ERROR = 'Failed to create patient property'
FAILED_UPDATE_PROPERTY_ERROR = 'Failed to update patient property'
FAILED_DELETE_PROPERTY_ERROR = 'Failed to delete patient property'

PROPERTY_SELECT = """
    SELECT pp.patient_id, pp.property_id, pp.name, pp.description,
           pp.created_by_doctor_id, pp.updated_by_doctor_id,
           pp.created_at, pp.updated_at,
           cb.first_name || ' ' || cb.last_name AS created_by_name,
           ub.first_name || ' ' || ub.last_name AS updated_by_name
    FROM patient_properties pp
    LEFT JOIN doctors cb ON cb.id = pp.created_by_doctor_id
    LEFT JOIN doctors ub ON ub.id = pp.updated_by_doctor_id
"""


def serialize_property(prop):
    if not prop:
        return None
    result = dict(prop)
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


def _fetch_property(patient_id, property_id):
    query = f"""
        {PROPERTY_SELECT}
        WHERE pp.patient_id = %s AND pp.property_id = %s
    """
    return execute_query(query, (patient_id, property_id), fetch_one=True)


@patient_properties_bp.route('/<patient_id>', methods=['GET'])
@authenticate
def list_properties(patient_id):
    try:
        user = request.user
        if user.get('role') != 'doctor':
            return jsonify({'error': INSUFFICIENT_PERMISSIONS_ERROR}), 403

        query = f"""
            {PROPERTY_SELECT}
            WHERE pp.patient_id = %s
            ORDER BY pp.property_id
        """
        props = execute_query(query, (patient_id,), fetch_all=True) or []
        log_data_access(user['id'], 'patient_properties', patient_id, 'VIEW', request)
        return jsonify({'properties': [serialize_property(p) for p in props]}), 200
    except Exception:
        current_app.logger.exception('Patient properties retrieval error')
        return jsonify({'error': FAILED_RETRIEVE_PROPERTIES_ERROR}), 500


@patient_properties_bp.route('/<patient_id>', methods=['POST'])
@authenticate
def create_property(patient_id):
    try:
        doctor_id, error_response = _require_doctor()
        if error_response:
            return error_response

        user = request.user
        data = request.get_json(silent=True) or {}
        name = data.get('name')
        description = data.get('description', '')

        if not name:
            return jsonify({'error': 'name is required'}), 400

        next_id_query = """
            SELECT COALESCE(MAX(property_id), 0) + 1 AS next_id
            FROM patient_properties
            WHERE patient_id = %s
        """
        next_id_row = execute_query(next_id_query, (patient_id,), fetch_one=True)
        next_id = next_id_row['next_id'] if next_id_row else 1

        insert_query = """
            INSERT INTO patient_properties (
                patient_id, property_id, name, description,
                created_by_doctor_id, updated_by_doctor_id
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING patient_id, property_id
        """
        created = execute_query(
            insert_query,
            (patient_id, next_id, name, description, doctor_id, doctor_id),
            fetch_one=True,
        )
        log_data_access(
            user['id'],
            'patient_properties',
            f'{patient_id}:{created["property_id"]}',
            'CREATE',
            request,
        )
        property_row = _fetch_property(patient_id, created['property_id'])
        return jsonify({'property': serialize_property(property_row)}), 201
    except Exception:
        current_app.logger.exception('Patient property creation error')
        return jsonify({'error': FAILED_CREATE_PROPERTY_ERROR}), 500


@patient_properties_bp.route('/<patient_id>/<int:property_id>', methods=['PATCH'])
@authenticate
def update_property(patient_id, property_id):
    try:
        doctor_id, error_response = _require_doctor()
        if error_response:
            return error_response

        user = request.user
        data = request.get_json(silent=True) or {}
        name = data.get('name')
        description = data.get('description')
        client_updated_at = data.get('updated_at')

        if name is None and description is None:
            return jsonify({'error': 'At least one of name or description is required'}), 400

        if name is not None and not str(name).strip():
            return jsonify({'error': 'name cannot be empty'}), 400

        existing = _fetch_property(patient_id, property_id)
        if not existing:
            return jsonify({'error': 'Property not found'}), 404

        if client_updated_at and existing.get('updated_at'):
            existing_updated = existing['updated_at']
            if isinstance(existing_updated, datetime):
                existing_updated = existing_updated.isoformat()
            if str(client_updated_at) < str(existing_updated):
                return jsonify({
                    'error': 'Note was updated by another provider',
                    'property': serialize_property(existing),
                }), 409

        set_clauses = ['updated_at = NOW()', 'updated_by_doctor_id = %s']
        params = [doctor_id]

        if name is not None:
            set_clauses.append('name = %s')
            params.append(str(name).strip())

        if description is not None:
            set_clauses.append('description = %s')
            params.append(description)

        params.extend([patient_id, property_id])

        update_query = f"""
            UPDATE patient_properties
            SET {', '.join(set_clauses)}
            WHERE patient_id = %s AND property_id = %s
            RETURNING patient_id, property_id
        """
        updated = execute_query(update_query, tuple(params), fetch_one=True)
        if not updated:
            return jsonify({'error': 'Property not found'}), 404

        log_data_access(
            user['id'],
            'patient_properties',
            f'{patient_id}:{property_id}',
            'UPDATE',
            request,
        )
        property_row = _fetch_property(patient_id, property_id)
        return jsonify({'property': serialize_property(property_row)}), 200
    except Exception:
        current_app.logger.exception('Patient property update error')
        return jsonify({'error': FAILED_UPDATE_PROPERTY_ERROR}), 500


@patient_properties_bp.route('/<patient_id>/<int:property_id>', methods=['DELETE'])
@authenticate
def delete_property(patient_id, property_id):
    try:
        user = request.user
        if user.get('role') != 'doctor':
            return jsonify({'error': INSUFFICIENT_PERMISSIONS_ERROR}), 403

        existing = _fetch_property(patient_id, property_id)
        if not existing:
            return jsonify({'error': 'Property not found'}), 404

        delete_query = """
            DELETE FROM patient_properties
            WHERE patient_id = %s AND property_id = %s
            RETURNING patient_id
        """
        deleted = execute_query(delete_query, (patient_id, property_id), fetch_one=True)
        if not deleted:
            return jsonify({'error': 'Property not found'}), 404

        log_data_access(
            user['id'],
            'patient_properties',
            f'{patient_id}:{property_id}',
            'DELETE',
            request,
        )
        return jsonify({'message': 'Property deleted'}), 200
    except Exception:
        current_app.logger.exception('Patient property deletion error')
        return jsonify({'error': FAILED_DELETE_PROPERTY_ERROR}), 500

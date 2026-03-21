"""
Patient properties routes
Supports variable properties per patient (doctor-only)
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, date
from api.db.connection import execute_query
from api.middleware.auth import authenticate

patient_properties_bp = Blueprint('patient_properties', __name__, url_prefix='/api/patient-properties')
INSUFFICIENT_PERMISSIONS_ERROR = 'Insufficient permissions'
FAILED_RETRIEVE_PROPERTIES_ERROR = 'Failed to retrieve patient properties'
FAILED_CREATE_PROPERTY_ERROR = 'Failed to create patient property'
FAILED_DELETE_PROPERTY_ERROR = 'Failed to delete patient property'


def serialize_property(prop):
    if not prop:
        return None
    result = dict(prop)
    for key, value in result.items():
        if isinstance(value, (datetime, date)):
            result[key] = value.isoformat()
    return result


@patient_properties_bp.route('/<patient_id>', methods=['GET'])
@authenticate
def list_properties(patient_id):
    try:
        user = request.user
        if user.get('role') != 'doctor':
            return jsonify({'error': INSUFFICIENT_PERMISSIONS_ERROR}), 403

        query = """
            SELECT patient_id, property_id, name, description, created_at, updated_at
            FROM patient_properties
            WHERE patient_id = %s
            ORDER BY property_id
        """
        props = execute_query(query, (patient_id,), fetch_all=True) or []
        return jsonify({'properties': [serialize_property(p) for p in props]}), 200
    except Exception:
        current_app.logger.exception('Patient properties retrieval error')
        return jsonify({'error': FAILED_RETRIEVE_PROPERTIES_ERROR}), 500


@patient_properties_bp.route('/<patient_id>', methods=['POST'])
@authenticate
def create_property(patient_id):
    try:
        user = request.user
        if user.get('role') != 'doctor':
            return jsonify({'error': INSUFFICIENT_PERMISSIONS_ERROR}), 403

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
            INSERT INTO patient_properties (patient_id, property_id, name, description)
            VALUES (%s, %s, %s, %s)
            RETURNING patient_id, property_id, name, description, created_at, updated_at
        """
        created = execute_query(insert_query, (patient_id, next_id, name, description), fetch_one=True)
        return jsonify({'property': serialize_property(created)}), 201
    except Exception:
        current_app.logger.exception('Patient property creation error')
        return jsonify({'error': FAILED_CREATE_PROPERTY_ERROR}), 500


@patient_properties_bp.route('/<patient_id>/<int:property_id>', methods=['DELETE'])
@authenticate
def delete_property(patient_id, property_id):
    try:
        user = request.user
        if user.get('role') != 'doctor':
            return jsonify({'error': INSUFFICIENT_PERMISSIONS_ERROR}), 403

        delete_query = """
            DELETE FROM patient_properties
            WHERE patient_id = %s AND property_id = %s
            RETURNING patient_id
        """
        deleted = execute_query(delete_query, (patient_id, property_id), fetch_one=True)
        if not deleted:
            return jsonify({'error': 'Property not found'}), 404

        return jsonify({'message': 'Property deleted'}), 200
    except Exception:
        current_app.logger.exception('Patient property deletion error')
        return jsonify({'error': FAILED_DELETE_PROPERTY_ERROR}), 500

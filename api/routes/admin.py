"""
Admin SSO route — Microsoft Entra ID (Azure AD) token verification
-----------------------------------------------------------------
POST /api/admin/verify-token
  Body: { "idToken": "<Microsoft ID token JWT>" }

Steps:
  1. Fetch Microsoft's JWKS for the tenant configured in AZURE_TENANT_ID
  2. Validate the JWT signature, expiry, audience, and issuer
  3. Enforce the @hudsonitconsulting.com domain requirement
  4. Return { email, name } on success

Required env vars:
  AZURE_TENANT_ID  – Azure Active Directory tenant ID
  AZURE_CLIENT_ID  – App (client) ID registered in Azure Portal
"""

from flask import Blueprint, request, jsonify
from urllib.request import urlopen
from urllib.error import URLError
import json
import os
import logging
import secrets
from functools import wraps

import jwt
from jwt import PyJWKClient, PyJWKClientError
import bcrypt

from api.db.connection import execute_query, DatabaseTransaction

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

ALLOWED_DOMAIN = 'hudsonitconsulting.com'
_TENANT_ID = os.getenv('AZURE_TENANT_ID', '')
_CLIENT_ID = os.getenv('AZURE_CLIENT_ID', '')
BCRYPT_ROUNDS = int(os.getenv('BCRYPT_ROUNDS', 12))
DEFAULT_LIST_LIMIT = 100
MAX_LIST_LIMIT = 500
DOCTOR_NOT_FOUND_ERROR = 'Doctor not found'
PATIENT_NOT_FOUND_ERROR = 'Patient not found'


def _get_valid_issuers(tenant_id: str) -> set[str]:
    """Return trusted Microsoft issuer formats for a tenant."""
    return {
        f'https://login.microsoftonline.com/{tenant_id}/v2.0',
        f'https://login.microsoftonline.com/{tenant_id}/v2.0/',
        f'https://login.microsoftonline.com/{tenant_id}/',
        f'https://sts.windows.net/{tenant_id}/',
    }


def _get_jwks_uri() -> str:
    """Fetch the JWKS URI from Microsoft's OpenID Connect discovery document."""
    if not _TENANT_ID:
        raise ValueError('AZURE_TENANT_ID is not configured')

    discovery_url = (
        f'https://login.microsoftonline.com/{_TENANT_ID}/v2.0'
        '/.well-known/openid-configuration'
    )
    try:
        with urlopen(discovery_url, timeout=5) as resp:
            config = json.loads(resp.read())
        return config['jwks_uri']
    except (URLError, KeyError) as exc:
        raise RuntimeError(f'Failed to fetch OIDC discovery document: {exc}') from exc


def _verify_token_or_raise(id_token: str) -> dict:
    """Validate JWT signature, audience, issuer, and tenant for admin token."""
    if not _TENANT_ID or not _CLIENT_ID:
        raise ValueError('Admin SSO is not configured on this server')

    jwks_uri = _get_jwks_uri()
    jwks_client = PyJWKClient(jwks_uri)
    signing_key = jwks_client.get_signing_key_from_jwt(id_token)

    claims = jwt.decode(
        id_token,
        signing_key.key,
        algorithms=['RS256'],
        audience=_CLIENT_ID,
        options={
            'verify_exp': True,
            'verify_iss': False,
        }
    )

    issuer = str(claims.get('iss', ''))
    valid_issuers = _get_valid_issuers(_TENANT_ID)
    if issuer not in valid_issuers:
        raise jwt.InvalidIssuerError(f'Unexpected issuer: {issuer}')

    token_tenant_id = str(claims.get('tid', ''))
    if token_tenant_id and token_tenant_id != _TENANT_ID:
        raise jwt.InvalidIssuerError(
            f'Tenant mismatch: expected {_TENANT_ID}, got {token_tenant_id}'
        )

    email = (
        claims.get('preferred_username') or
        claims.get('email') or
        claims.get('upn') or
        ''
    ).lower()

    if not email.endswith(f'@{ALLOWED_DOMAIN}'):
        raise PermissionError(
            f'Access denied. Only @{ALLOWED_DOMAIN} accounts are permitted.'
        )

    return claims


def _extract_bearer_token() -> str:
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        raise ValueError('Authorization bearer token is required')
    return auth_header[7:]


def _error_response(message: str, status_code: int):
    return jsonify({'error': message}), status_code


def _map_admin_auth_exception(exc: Exception):
    if isinstance(exc, ValueError):
        return _error_response(str(exc), 401)
    if isinstance(exc, PermissionError):
        return _error_response(str(exc), 403)
    if isinstance(exc, PyJWKClientError):
        logger.warning('JWKS lookup failed: %s', exc)
        return _error_response('Token validation failed (JWKS)', 401)
    if isinstance(exc, jwt.ExpiredSignatureError):
        return _error_response('Token has expired', 401)
    if isinstance(exc, jwt.InvalidIssuerError):
        return _error_response('Token issuer is not trusted', 401)
    if isinstance(exc, jwt.InvalidAudienceError):
        return _error_response('Token audience mismatch', 401)
    if isinstance(exc, jwt.PyJWTError):
        logger.warning('JWT decode error: %s', exc)
        return _error_response('Invalid token', 401)
    if isinstance(exc, RuntimeError):
        logger.error('Admin SSO config error: %s', exc)
        return _error_response(str(exc), 503)
    return None


def _clean_text(value) -> str:
    return str(value or '').strip()


def _clean_optional(value):
    cleaned = _clean_text(value)
    return cleaned or None


def _clean_data_value(data: dict, key: str, fallback='') -> str:
    if key in data and data.get(key) is not None:
        return _clean_text(data.get(key))
    return _clean_text(fallback)


def _optional_data_value(data: dict, key: str, fallback=None):
    if key in data:
        return _clean_optional(data.get(key))
    return _clean_optional(fallback)


def _existing_date_iso(existing: dict, key: str) -> str:
    value = existing.get(key)
    if not value:
        return ''
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return str(value)


def _build_patient_insert_values(data: dict, user_id: str):
    return (
        user_id,
        _clean_data_value(data, 'firstName'),
        _clean_data_value(data, 'lastName'),
        _optional_data_value(data, 'dateOfBirth'),
        _optional_data_value(data, 'phone'),
        _optional_data_value(data, 'address'),
        _optional_data_value(data, 'city'),
        _optional_data_value(data, 'state'),
        _optional_data_value(data, 'zipCode'),
        _optional_data_value(data, 'emergencyContactName'),
        _optional_data_value(data, 'emergencyContactPhone'),
    )


def _build_patient_update_values(data: dict, existing: dict, patient_id: str):
    return (
        _clean_data_value(data, 'firstName', existing.get('first_name')),
        _clean_data_value(data, 'lastName', existing.get('last_name')),
        _optional_data_value(data, 'dateOfBirth', _existing_date_iso(existing, 'date_of_birth')),
        _optional_data_value(data, 'phone', existing.get('phone')),
        _optional_data_value(data, 'address', existing.get('address')),
        _optional_data_value(data, 'city', existing.get('city')),
        _optional_data_value(data, 'state', existing.get('state')),
        _optional_data_value(data, 'zipCode', existing.get('zip_code')),
        _optional_data_value(data, 'emergencyContactName', existing.get('emergency_contact_name')),
        _optional_data_value(data, 'emergencyContactPhone', existing.get('emergency_contact_phone')),
        patient_id,
    )


def require_admin_sso(f):
    """Decorator enforcing valid Microsoft admin token for admin management APIs."""
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            token = _extract_bearer_token()
            request.admin_claims = _verify_token_or_raise(token)
            return f(*args, **kwargs)
        except Exception as exc:
            mapped = _map_admin_auth_exception(exc)
            if mapped:
                return mapped
            raise

    return decorated


def _serialize_rows(rows: list[dict]) -> list[dict]:
    serialized: list[dict] = []
    for row in rows:
        item = dict(row)
        for key, value in item.items():
            if hasattr(value, 'isoformat'):
                item[key] = value.isoformat()
        serialized.append(item)
    return serialized


def _generate_temp_password() -> str:
    return f"HHS!{secrets.token_urlsafe(8)}aA1"


def _build_password_hash(password: str) -> tuple[str, str]:
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode('utf-8')
    salt = password_hash[:29]
    return password_hash, salt


@admin_bp.route('/verify-token', methods=['POST'])
def verify_token():
    """
    POST /api/admin/verify-token
    Validate a Microsoft-issued ID token and enforce domain restriction.
    """
    data = request.get_json(silent=True)
    if not data or 'idToken' not in data:
        return jsonify({'error': 'idToken is required'}), 400

    id_token: str = data['idToken']

    try:
        claims = _verify_token_or_raise(id_token)

    except Exception as exc:
        mapped = _map_admin_auth_exception(exc)
        if mapped:
            return mapped
        raise

    email: str = (
        claims.get('preferred_username') or
        claims.get('email') or
        claims.get('upn') or
        ''
    ).lower()

    name: str = claims.get('name') or email

    logger.info('Admin SSO success: %s', email)

    return jsonify({
        'email': email,
        'name': name,
        'tid': claims.get('tid', '')
    }), 200


@admin_bp.route('/doctors', methods=['GET'])
@require_admin_sso
def list_admin_doctors():
    query = """
        SELECT d.id, d.user_id, d.first_name, d.last_name, d.specialty,
               d.license_number, d.license_state, d.phone, d.office_address,
               d.created_at, d.updated_at,
               u.username, u.email, u.is_active
        FROM doctors d
        JOIN users u ON d.user_id = u.id
        ORDER BY d.last_name, d.first_name
    """
    doctors = execute_query(query, fetch_all=True) or []
    return jsonify({'doctors': _serialize_rows(doctors)}), 200


@admin_bp.route('/doctors', methods=['POST'])
@require_admin_sso
def create_doctor():
    data = request.get_json(silent=True) or {}
    required = ['username', 'email', 'firstName', 'lastName', 'specialty', 'licenseNumber']
    if not all(data.get(field) for field in required):
        return jsonify({'error': 'Missing required doctor fields'}), 400

    temp_password = _generate_temp_password()
    password_hash, salt = _build_password_hash(temp_password)

    with DatabaseTransaction() as cursor:
        cursor.execute(
            """
            INSERT INTO users (username, email, password_hash, salt, role, must_change_password)
            VALUES (%s, %s, %s, %s, 'doctor', true)
            RETURNING id, username, email, role
            """,
            (data['username'].strip(), data['email'].strip().lower(), password_hash, salt),
        )
        user = cursor.fetchone()

        cursor.execute(
            """
            INSERT INTO doctors (
                user_id, first_name, last_name, specialty, license_number,
                license_state, phone, office_address
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, user_id, first_name, last_name, specialty, license_number,
                      license_state, phone, office_address, created_at, updated_at
            """,
            (
                user['id'],
                data['firstName'].strip(),
                data['lastName'].strip(),
                data['specialty'].strip(),
                data['licenseNumber'].strip(),
                (data.get('licenseState') or '').strip() or None,
                (data.get('phone') or '').strip() or None,
                (data.get('officeAddress') or '').strip() or None,
            ),
        )
        doctor = cursor.fetchone()

    payload = dict(doctor)
    payload['username'] = user['username']
    payload['email'] = user['email']
    payload['is_active'] = True

    return jsonify({
        'doctor': _serialize_rows([payload])[0],
        'temporaryPassword': temp_password
    }), 201


@admin_bp.route('/doctors/<doctor_id>', methods=['PUT'])
@require_admin_sso
def update_doctor(doctor_id):
    data = request.get_json(silent=True) or {}
    existing = execute_query(
        """
        SELECT d.id, d.user_id, d.first_name, d.last_name, d.specialty,
               d.license_number, d.license_state, d.phone, d.office_address,
               u.email, u.is_active
        FROM doctors d
        JOIN users u ON d.user_id = u.id
        WHERE d.id = %s
        """,
        (doctor_id,),
        fetch_one=True
    )
    if not existing:
        return jsonify({'error': DOCTOR_NOT_FOUND_ERROR}), 404

    execute_query(
        """
        UPDATE users
        SET email = %s,
            is_active = %s,
            updated_at = NOW()
        WHERE id = %s
        """,
        (
            (data.get('email') or existing['email']).strip().lower(),
            data.get('isActive', existing['is_active']),
            existing['user_id']
        )
    )

    updated = execute_query(
        """
        UPDATE doctors
        SET first_name = %s,
            last_name = %s,
            specialty = %s,
            license_number = %s,
            license_state = %s,
            phone = %s,
            office_address = %s,
            updated_at = NOW()
        WHERE id = %s
        RETURNING id, user_id, first_name, last_name, specialty, license_number,
                  license_state, phone, office_address, created_at, updated_at
        """,
        (
            (data.get('firstName') or existing['first_name']).strip(),
            (data.get('lastName') or existing['last_name']).strip(),
            (data.get('specialty') or existing['specialty']).strip(),
            (data.get('licenseNumber') or existing['license_number']).strip(),
            (data.get('licenseState') or existing['license_state'] or '').strip() or None,
            (data.get('phone') or existing['phone'] or '').strip() or None,
            (data.get('officeAddress') or existing['office_address'] or '').strip() or None,
            doctor_id,
        ),
        fetch_one=True
    )

    payload = dict(updated)
    payload['email'] = (data.get('email') or existing['email']).strip().lower()
    payload['is_active'] = data.get('isActive', existing['is_active'])

    return jsonify({'doctor': _serialize_rows([payload])[0]}), 200


@admin_bp.route('/doctors/<doctor_id>', methods=['DELETE'])
@require_admin_sso
def delete_doctor(doctor_id):
    row = execute_query(
        'SELECT user_id FROM doctors WHERE id = %s',
        (doctor_id,),
        fetch_one=True
    )
    if not row:
        return jsonify({'error': DOCTOR_NOT_FOUND_ERROR}), 404

    execute_query('DELETE FROM users WHERE id = %s', (row['user_id'],))
    return jsonify({'message': 'Doctor deleted'}), 200


@admin_bp.route('/patients', methods=['GET'])
@require_admin_sso
def list_admin_patients():
    query = """
        SELECT p.id, p.user_id, p.first_name, p.last_name, p.date_of_birth,
               p.phone, p.address, p.city, p.state, p.zip_code,
               p.emergency_contact_name, p.emergency_contact_phone,
               p.created_at, p.updated_at,
               u.username, u.email, u.is_active
        FROM patients p
        JOIN users u ON p.user_id = u.id
        ORDER BY p.last_name, p.first_name
    """
    patients = execute_query(query, fetch_all=True) or []
    return jsonify({'patients': _serialize_rows(patients)}), 200


@admin_bp.route('/patients', methods=['POST'])
@require_admin_sso
def create_patient():
    data = request.get_json(silent=True) or {}
    required = ['username', 'email', 'firstName', 'lastName']
    if not all(data.get(field) for field in required):
        return jsonify({'error': 'Missing required patient fields'}), 400

    temp_password = _generate_temp_password()
    password_hash, salt = _build_password_hash(temp_password)

    with DatabaseTransaction() as cursor:
        cursor.execute(
            """
            INSERT INTO users (username, email, password_hash, salt, role, must_change_password)
            VALUES (%s, %s, %s, %s, 'patient', true)
            RETURNING id, username, email, role
            """,
            (_clean_data_value(data, 'username'), _clean_data_value(data, 'email').lower(), password_hash, salt),
        )
        user = cursor.fetchone()

        cursor.execute(
            """
            INSERT INTO patients (
                user_id, first_name, last_name, date_of_birth, phone, address, city,
                state, zip_code, emergency_contact_name, emergency_contact_phone
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, user_id, first_name, last_name, date_of_birth, phone,
                      address, city, state, zip_code, emergency_contact_name,
                      emergency_contact_phone, created_at, updated_at
            """,
            _build_patient_insert_values(data, user['id']),
        )
        patient = cursor.fetchone()

    payload = dict(patient)
    payload['username'] = user['username']
    payload['email'] = user['email']
    payload['is_active'] = True

    return jsonify({
        'patient': _serialize_rows([payload])[0],
        'temporaryPassword': temp_password
    }), 201


@admin_bp.route('/patients/<patient_id>', methods=['PUT'])
@require_admin_sso
def update_patient(patient_id):
    data = request.get_json(silent=True) or {}
    existing = execute_query(
        """
        SELECT p.id, p.user_id, p.first_name, p.last_name, p.date_of_birth,
               p.phone, p.address, p.city, p.state, p.zip_code,
               p.emergency_contact_name, p.emergency_contact_phone,
               u.email, u.is_active
        FROM patients p
        JOIN users u ON p.user_id = u.id
        WHERE p.id = %s
        """,
        (patient_id,),
        fetch_one=True
    )
    if not existing:
        return jsonify({'error': PATIENT_NOT_FOUND_ERROR}), 404

    execute_query(
        """
        UPDATE users
        SET email = %s,
            is_active = %s,
            updated_at = NOW()
        WHERE id = %s
        """,
        (
            _clean_data_value(data, 'email', existing['email']).lower(),
            data.get('isActive', existing['is_active']),
            existing['user_id']
        )
    )

    updated = execute_query(
        """
        UPDATE patients
        SET first_name = %s,
            last_name = %s,
            date_of_birth = %s,
            phone = %s,
            address = %s,
            city = %s,
            state = %s,
            zip_code = %s,
            emergency_contact_name = %s,
            emergency_contact_phone = %s,
            updated_at = NOW()
        WHERE id = %s
        RETURNING id, user_id, first_name, last_name, date_of_birth, phone,
                  address, city, state, zip_code, emergency_contact_name,
                  emergency_contact_phone, created_at, updated_at
        """,
        _build_patient_update_values(data, existing, patient_id),
        fetch_one=True
    )

    payload = dict(updated)
    payload['email'] = _clean_data_value(data, 'email', existing['email']).lower()
    payload['is_active'] = data.get('isActive', existing['is_active'])

    return jsonify({'patient': _serialize_rows([payload])[0]}), 200


@admin_bp.route('/patients/<patient_id>', methods=['DELETE'])
@require_admin_sso
def delete_patient(patient_id):
    row = execute_query(
        'SELECT user_id FROM patients WHERE id = %s',
        (patient_id,),
        fetch_one=True
    )
    if not row:
        return jsonify({'error': PATIENT_NOT_FOUND_ERROR}), 404

    execute_query('DELETE FROM users WHERE id = %s', (row['user_id'],))
    return jsonify({'message': 'Patient deleted'}), 200


@admin_bp.route('/error-logs', methods=['GET'])
@require_admin_sso
def get_error_logs():
    try:
        limit = int(request.args.get('limit', str(DEFAULT_LIST_LIMIT)))
        limit = max(1, min(limit, MAX_LIST_LIMIT))
    except ValueError:
        limit = DEFAULT_LIST_LIMIT

    logs = execute_query(
        """
        SELECT a.id, a.user_id, a.action, a.resource_type, a.resource_id,
               a.status, a.error_message, a.ip_address, a.created_at,
               u.username
        FROM audit_logs a
        LEFT JOIN users u ON a.user_id = u.id
        WHERE LOWER(COALESCE(a.status, '')) IN ('error', 'failed')
           OR a.error_message IS NOT NULL
        ORDER BY a.created_at DESC
        LIMIT %s
        """,
        (limit,),
        fetch_all=True
    ) or []

    return jsonify({'logs': _serialize_rows(logs)}), 200

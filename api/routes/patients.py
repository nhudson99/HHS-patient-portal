"""
Patients routes for HHS Patient Portal
Provides patient record access for providers; allows providers to create patients
"""

from flask import Blueprint, request, jsonify, current_app, send_file
from datetime import date, datetime
from io import BytesIO
import os
from werkzeug.datastructures import FileStorage
from api.db.connection import execute_query
from api.middleware.auth import authenticate
import secrets
import string
import bcrypt
from api.db.connection import DatabaseTransaction
from api.utils.audit_log import log_data_access, log_audit_event, get_client_ip
from api.routes.documents import (
    _save_file_to_storage,
    _download_file_from_storage,
    _delete_file_from_storage,
    DOCUMENT_COLUMNS,
)

patients_bp = Blueprint('patients', __name__, url_prefix='/api/patients')
INSUFFICIENT_PERMISSIONS_ERROR = 'Insufficient permissions'
PATIENT_NOT_FOUND_ERROR = 'Patient not found'
PROFILE_PHOTO_NOT_FOUND_ERROR = 'Profile photo not found'
PROFILE_PHOTO_TYPE = 'profile_photo'
MAX_KIOSK_PHOTO_BYTES = 2 * 1024 * 1024  # webcam JPEGs are typically well under 2MB
JPEG_MAGIC = b'\xff\xd8\xff'

PATIENT_SELECT_COLUMNS = """
    p.id, p.user_id, p.first_name, p.last_name, p.date_of_birth,
    p.phone, p.address, p.emergency_contact_name,
    p.emergency_contact_phone, p.created_at, p.updated_at,
    p.profile_photo_document_id,
    (p.profile_photo_document_id IS NOT NULL) AS has_profile_photo,
    u.email AS portal_email
"""


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
    photo_doc_id = result.pop('profile_photo_document_id', None)
    result['has_profile_photo'] = bool(photo_doc_id or result.get('has_profile_photo'))
    return result


def serialize_doctor(doctor):
    if not doctor:
        return None
    result = dict(doctor)
    for key, value in result.items():
        if isinstance(value, (datetime, date)):
            result[key] = value.isoformat()
    return result


def _verify_patient_identity(patient_id: str, patient_name: str, dob: str):
    """Match patient by id + full name + DOB (same rules as guest check-in)."""
    query = """
        SELECT id, first_name, last_name, date_of_birth, profile_photo_document_id
        FROM patients
        WHERE id = %s
          AND LOWER(CONCAT(first_name, ' ', last_name)) = LOWER(%s)
          AND date_of_birth = %s
    """
    return execute_query(query, (patient_id, patient_name.strip(), dob), fetch_one=True)


def _patient_accessible_by_user(patient_id: str, user: dict) -> bool:
    if user.get('role') == 'doctor':
        return True
    if user.get('role') != 'patient':
        return False
    patient = execute_query(
        "SELECT id FROM patients WHERE id = %s AND user_id = %s",
        (patient_id, user['id']),
        fetch_one=True,
    )
    return bool(patient)


def _validate_kiosk_jpeg(file) -> FileStorage:
    """
    Read the upload, enforce a tight size cap, and require JPEG magic bytes.
    Returns a fresh FileStorage ready for document storage helpers.
    """
    stream = file.stream
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(0)

    if size <= 0:
        raise ValueError('Photo file is empty')
    if size > MAX_KIOSK_PHOTO_BYTES:
        raise ValueError('Photo exceeds the 2MB kiosk upload limit')

    payload = stream.read()
    if not payload.startswith(JPEG_MAGIC):
        raise ValueError('Photo must be a JPEG image')

    content_type = (file.content_type or '').lower()
    if content_type and content_type not in ('image/jpeg', 'image/jpg', 'application/octet-stream'):
        raise ValueError('Photo must be a JPEG image')

    return FileStorage(
        stream=BytesIO(payload),
        filename='profile-photo.jpg',
        content_type='image/jpeg',
    )


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
        current_app.logger.exception('Providers retrieval error')
        return jsonify({'error': 'Failed to retrieve providers'}), 500


@patients_bp.route('/me', methods=['GET'])
@authenticate
def get_my_patient_record():
    """Get the currently authenticated patient's own record"""
    try:
        user = request.user
        if user.get('role') != 'patient':
            return jsonify({'error': INSUFFICIENT_PERMISSIONS_ERROR}), 403

        query = f"""
            SELECT {PATIENT_SELECT_COLUMNS}
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

        query = f"""
            SELECT {PATIENT_SELECT_COLUMNS}
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
    Provider creates a new patient account with a temporary password.
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
                          profile_photo_document_id, created_at, updated_at
                """,
                (new_user['id'], first_name, last_name, date_of_birth, phone, address),
            )
            patient = cursor.fetchone()

        result = serialize_patient(dict(patient))
        result['username'] = new_user['username']
        result['email'] = new_user['email']
        result['is_active'] = True

        current_app.logger.info(
            'Provider %s created patient %s (%s)',
            user.get('username'),
            username,
            patient['id'],
        )

        return jsonify({
            'patient': result,
            'temporaryPassword': temp_password,
        }), 201

    except Exception:
        current_app.logger.exception('Provider create patient error')
        return jsonify({'error': 'Failed to create patient'}), 500


@patients_bp.route('/<patient_id>/profile-photo/kiosk', methods=['POST'])
def upload_profile_photo_kiosk(patient_id):
    """
    POST /api/patients/<patient_id>/profile-photo/kiosk
    No auth — gated by patient_name + date_of_birth matching the patient.
    Accepts multipart JPEG from the kiosk camera step.
    """
    stored_path = None
    try:
        patient_name = (request.form.get('patient_name') or '').strip()
        dob = (request.form.get('date_of_birth') or '').strip()
        if not patient_name or not dob:
            return jsonify({'error': 'patient_name and date_of_birth are required'}), 400

        patient = _verify_patient_identity(patient_id, patient_name, dob)
        if not patient:
            return jsonify({'error': PATIENT_NOT_FOUND_ERROR}), 404

        file = request.files.get('file') or request.files.get('photo')
        if not file or not file.filename:
            return jsonify({'error': 'Photo file is required'}), 400

        try:
            jpeg_file = _validate_kiosk_jpeg(file)
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400

        original_name = 'profile-photo.jpg'
        stored_path, file_size = _save_file_to_storage(jpeg_file, original_name)

        old_doc_id = patient.get('profile_photo_document_id')
        old_file_path = None
        if old_doc_id:
            old_doc = execute_query(
                "SELECT id, file_path FROM medical_documents WHERE id = %s",
                (old_doc_id,),
                fetch_one=True,
            )
            if old_doc:
                old_file_path = old_doc.get('file_path')

        with DatabaseTransaction() as cursor:
            cursor.execute(
                f"""
                INSERT INTO medical_documents
                (patient_id, doctor_id, document_type, title, file_path, file_name,
                 file_size, document_date, patient_visible)
                VALUES (%s, NULL, %s, %s, %s, %s, %s, CURRENT_DATE, TRUE)
                RETURNING {DOCUMENT_COLUMNS}
                """,
                (
                    patient_id,
                    PROFILE_PHOTO_TYPE,
                    'Profile Photo',
                    stored_path,
                    original_name,
                    file_size,
                ),
            )
            new_doc = cursor.fetchone()

            cursor.execute(
                """
                UPDATE patients
                SET profile_photo_document_id = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (new_doc['id'], patient_id),
            )

            if old_doc_id:
                cursor.execute(
                    "DELETE FROM medical_documents WHERE id = %s",
                    (old_doc_id,),
                )

        # Delete prior storage object only after DB commit
        if old_file_path:
            try:
                _delete_file_from_storage(old_file_path)
            except Exception:
                current_app.logger.exception('Failed to delete previous profile photo file')

        log_audit_event(
            user_id=None,
            action='DATA_CREATE',
            table_name='profile_photo',
            record_id=str(patient_id),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get('User-Agent'),
            details={
                'source': 'kiosk',
                'document_id': str(new_doc['id']),
                'file_size': file_size,
            },
        )

        return jsonify({
            'has_profile_photo': True,
            'document_id': str(new_doc['id']),
        }), 201

    except Exception:
        if stored_path:
            try:
                _delete_file_from_storage(stored_path)
            except Exception:
                current_app.logger.exception('Failed to clean up profile photo after error')
        current_app.logger.exception('Kiosk profile photo upload error')
        return jsonify({'error': 'Failed to upload profile photo'}), 500


@patients_bp.route('/<patient_id>/profile-photo', methods=['GET'])
@authenticate
def get_profile_photo(patient_id):
    """
    GET /api/patients/<patient_id>/profile-photo
    Patient may fetch own photo; doctor may fetch any.
    """
    try:
        user = request.user
        if not _patient_accessible_by_user(patient_id, user):
            return jsonify({'error': INSUFFICIENT_PERMISSIONS_ERROR}), 403

        patient = execute_query(
            """
            SELECT p.id, p.profile_photo_document_id,
                   d.file_path, d.file_name
            FROM patients p
            LEFT JOIN medical_documents d ON d.id = p.profile_photo_document_id
            WHERE p.id = %s
            """,
            (patient_id,),
            fetch_one=True,
        )
        if not patient:
            return jsonify({'error': PATIENT_NOT_FOUND_ERROR}), 404

        if not patient.get('profile_photo_document_id') or not patient.get('file_path'):
            return jsonify({'error': PROFILE_PHOTO_NOT_FOUND_ERROR}), 404

        memory_file, local_file_path = _download_file_from_storage(patient['file_path'])
        download_name = patient.get('file_name') or 'profile-photo.jpg'

        log_data_access(user['id'], 'profile_photo', patient_id, 'VIEW', request)

        if memory_file:
            return send_file(
                memory_file,
                mimetype='image/jpeg',
                as_attachment=False,
                download_name=download_name,
            )
        if local_file_path:
            return send_file(
                str(local_file_path),
                mimetype='image/jpeg',
                as_attachment=False,
                download_name=download_name,
            )

        return jsonify({'error': PROFILE_PHOTO_NOT_FOUND_ERROR}), 404

    except Exception:
        current_app.logger.exception('Profile photo retrieval error')
        return jsonify({'error': 'Failed to retrieve profile photo'}), 500

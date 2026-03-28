"""
Documents routes for patient medical documents
Handles file upload, download, rename, and delete operations
"""

from flask import Blueprint, request, jsonify, send_file, current_app
from datetime import datetime, date
from io import BytesIO
import os
import uuid
from pathlib import Path
from werkzeug.utils import secure_filename
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import BlobServiceClient
from api.db.connection import execute_query
from api.middleware.auth import authenticate

documents_bp = Blueprint('documents', __name__, url_prefix='/api/documents')
INSUFFICIENT_PERMISSIONS_ERROR = 'Insufficient permissions'
DOCUMENT_NOT_FOUND_ERROR = 'Document not found'
FAILED_RETRIEVE_DOCUMENTS_ERROR = 'Failed to retrieve documents'
FAILED_UPLOAD_DOCUMENTS_ERROR = 'Failed to upload documents'
FAILED_RENAME_DOCUMENT_ERROR = 'Failed to rename document'
FAILED_DELETE_DOCUMENT_ERROR = 'Failed to delete document'

DOCUMENTS_STORAGE_BACKEND = (os.getenv('DOCUMENTS_STORAGE_BACKEND') or 'local').strip().lower()
LOCAL_UPLOAD_DIR = Path((os.getenv('DOCUMENTS_LOCAL_DIR') or str(Path.home() / 'hhs-documents')).strip())
DOCUMENTS_BLOB_CONTAINER = (os.getenv('DOCUMENTS_BLOB_CONTAINER') or 'hhs-documents').strip()
DOCUMENTS_BLOB_ENDPOINT = (os.getenv('DOCUMENTS_BLOB_ENDPOINT') or '').strip()
DOCUMENTS_BLOB_CREDENTIAL = os.getenv('DOCUMENTS_BLOB_CREDENTIAL') or ''
DOCUMENTS_BLOB_CONNECTION_STRING = (os.getenv('DOCUMENTS_BLOB_CONNECTION_STRING') or '').strip()

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'txt', 'rtf',
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff',
    'xls', 'xlsx', 'csv',
    'xml', 'json'
}

# Document type mapping based on extension
DOCUMENT_TYPE_MAP = {
    'pdf': 'document',
    'doc': 'document',
    'docx': 'document',
    'txt': 'document',
    'rtf': 'document',
    'jpg': 'imaging',
    'jpeg': 'imaging',
    'png': 'imaging',
    'gif': 'imaging',
    'bmp': 'imaging',
    'tiff': 'imaging',
    'xls': 'lab_result',
    'xlsx': 'lab_result',
    'csv': 'lab_result',
    'xml': 'other',
    'json': 'other'
}

_blob_service_client = None


def _is_blob_backend() -> bool:
    return DOCUMENTS_STORAGE_BACKEND in ('azure_blob', 'blob', 'azure')


def _get_blob_service_client() -> BlobServiceClient:
    global _blob_service_client
    if _blob_service_client is not None:
        return _blob_service_client

    # Try endpoint + credential first (preferred method)
    if DOCUMENTS_BLOB_ENDPOINT and DOCUMENTS_BLOB_CREDENTIAL:
        _blob_service_client = BlobServiceClient(
            account_url=DOCUMENTS_BLOB_ENDPOINT,
            credential=DOCUMENTS_BLOB_CREDENTIAL,
        )
        return _blob_service_client

    # Fall back to connection string if endpoint method not available
    if DOCUMENTS_BLOB_CONNECTION_STRING and DOCUMENTS_BLOB_CONNECTION_STRING.lower() not in ('disabled', ''):
        try:
            _blob_service_client = BlobServiceClient.from_connection_string(DOCUMENTS_BLOB_CONNECTION_STRING)
            return _blob_service_client
        except ValueError as e:
            current_app.logger.warning(f"Failed to parse connection string: {e}")

    raise RuntimeError(
        'Azure Blob storage backend selected but credentials are incomplete. '
        'Set both DOCUMENTS_BLOB_ENDPOINT and DOCUMENTS_BLOB_CREDENTIAL, or set a valid DOCUMENTS_BLOB_CONNECTION_STRING.'
    )


def _get_blob_container_client():
    service_client = _get_blob_service_client()
    container_client = service_client.get_container_client(DOCUMENTS_BLOB_CONTAINER)
    try:
        container_client.create_container()
    except ResourceExistsError:
        pass
    return container_client


def _save_file_to_storage(file, original_name: str) -> tuple[str, int]:
    unique_name = f"{uuid.uuid4()}_{original_name}"

    if _is_blob_backend():
        file.stream.seek(0, os.SEEK_END)
        file_size = file.stream.tell()
        file.stream.seek(0)

        container_client = _get_blob_container_client()
        blob_client = container_client.get_blob_client(unique_name)
        blob_client.upload_blob(file.stream, overwrite=False)
        return unique_name, file_size

    LOCAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_path = LOCAL_UPLOAD_DIR / unique_name
    file.save(str(file_path))
    return str(file_path), file_path.stat().st_size


def _download_file_from_storage(stored_path: str) -> tuple[BytesIO | None, Path | None]:
    if _is_blob_backend():
        container_client = _get_blob_container_client()
        blob_client = container_client.get_blob_client(stored_path)
        try:
            payload = blob_client.download_blob().readall()
            return BytesIO(payload), None
        except ResourceNotFoundError:
            return None, None

    local_path = Path(stored_path)
    if not local_path.exists():
        return None, None
    return None, local_path


def _delete_file_from_storage(stored_path: str) -> None:
    if not stored_path:
        return

    if _is_blob_backend():
        container_client = _get_blob_container_client()
        blob_client = container_client.get_blob_client(stored_path)
        try:
            blob_client.delete_blob()
        except ResourceNotFoundError:
            pass
        return

    local_path = Path(stored_path)
    if local_path.exists():
        local_path.unlink()


def get_file_extension(filename):
    """Get file extension from filename"""
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return ''


def allowed_file(filename):
    """Check if file extension is allowed"""
    return get_file_extension(filename) in ALLOWED_EXTENSIONS


def serialize_document(doc):
    """Convert document dict with date objects to JSON-serializable dict"""
    if not doc:
        return None
    result = dict(doc)
    for key, value in result.items():
        if isinstance(value, (datetime, date)):
            result[key] = value.isoformat()
    return result


@documents_bp.route('/<patient_id>', methods=['GET'])
@authenticate
def list_documents(patient_id):
    """
    GET /api/documents/<patient_id>
    List all documents for a patient (patients view own, doctors view any)
    """
    try:
        user = request.user
        
        # Verify authorization: patients can only view their own docs
        if user.get('role') == 'patient':
            patient_query = "SELECT id FROM patients WHERE user_id = %s"
            patient = execute_query(patient_query, (user['id'],), fetch_one=True)
            if not patient or patient['id'] != patient_id:
                return jsonify({'error': INSUFFICIENT_PERMISSIONS_ERROR}), 403
        elif user.get('role') != 'doctor':
            return jsonify({'error': INSUFFICIENT_PERMISSIONS_ERROR}), 403
        
        query = """
            SELECT id, patient_id, doctor_id, document_type, title, description,
                   file_path, file_name, file_size, document_date,
                   created_at, updated_at
            FROM medical_documents
            WHERE patient_id = %s
            ORDER BY created_at DESC
        """
        
        documents = execute_query(query, (patient_id,), fetch_all=True)
        
        return jsonify({
            'documents': [serialize_document(d) for d in (documents or [])]
        }), 200

    except Exception:
        current_app.logger.exception('Documents list error')
        return jsonify({'error': FAILED_RETRIEVE_DOCUMENTS_ERROR}), 500


@documents_bp.route('/<patient_id>', methods=['POST'])
@authenticate
def upload_document(patient_id):
    """
    POST /api/documents/<patient_id>
    Upload one or more documents for a patient
    """
    try:
        user = request.user
        
        if user.get('role') != 'doctor':
            return jsonify({'error': INSUFFICIENT_PERMISSIONS_ERROR}), 403
        
        # Get doctor ID
        doctor_query = "SELECT id FROM doctors WHERE user_id = %s"
        doctor = execute_query(doctor_query, (user['id'],), fetch_one=True)
        doctor_id = doctor['id'] if doctor else None
        
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        
        if not files or all(f.filename == '' for f in files):
            return jsonify({'error': 'No files selected'}), 400

        uploaded = []
        errors = []

        for file in files:
            if file.filename == '':
                continue

            if not allowed_file(file.filename):
                errors.append(f'{file.filename}: File type not allowed')
                continue

            # Secure filename and persist to selected backend.
            original_name = secure_filename(file.filename)
            file_ext = get_file_extension(original_name)
            stored_path, file_size = _save_file_to_storage(file, original_name)

            # Auto-detect document type
            doc_type = DOCUMENT_TYPE_MAP.get(file_ext, 'other')

            # Insert into database
            insert_query = """
                INSERT INTO medical_documents
                (patient_id, doctor_id, document_type, title, file_path, file_name, 
                 file_size, document_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_DATE)
                RETURNING id, patient_id, doctor_id, document_type, title, description,
                          file_path, file_name, file_size, document_date,
                          created_at, updated_at
            """
            
            doc = execute_query(
                insert_query,
                (patient_id, doctor_id, doc_type, original_name, stored_path,
                 original_name, file_size),
                fetch_one=True
            )

            if doc:
                uploaded.append(serialize_document(doc))

        return jsonify({
            'message': f'Uploaded {len(uploaded)} file(s)',
            'documents': uploaded,
            'errors': errors
        }), 201

    except Exception:
        current_app.logger.exception('Document upload error')
        return jsonify({'error': FAILED_UPLOAD_DOCUMENTS_ERROR}), 500


@documents_bp.route('/<doc_id>/rename', methods=['PUT'])
@authenticate
def rename_document(doc_id):
    """
    PUT /api/documents/<doc_id>/rename
    Rename a document (title only, not physical file)
    """
    try:
        user = request.user
        
        if user.get('role') != 'doctor':
            return jsonify({'error': INSUFFICIENT_PERMISSIONS_ERROR}), 403
        
        data = request.get_json(silent=True) or {}
        new_title = data.get('title', '').strip()
        
        if not new_title:
            return jsonify({'error': 'Title is required'}), 400
        
        # Update document title
        update_query = """
            UPDATE medical_documents
            SET title = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, patient_id, doctor_id, document_type, title, description,
                      file_path, file_name, file_size, document_date,
                      created_at, updated_at
        """
        
        doc = execute_query(update_query, (new_title, doc_id), fetch_one=True)
        
        if not doc:
            return jsonify({'error': DOCUMENT_NOT_FOUND_ERROR}), 404
        
        return jsonify({
            'message': 'Document renamed successfully',
            'document': serialize_document(doc)
        }), 200

    except Exception:
        current_app.logger.exception('Document rename error')
        return jsonify({'error': FAILED_RENAME_DOCUMENT_ERROR}), 500


@documents_bp.route('/<doc_id>', methods=['DELETE'])
@authenticate
def delete_document(doc_id):
    """
    DELETE /api/documents/<doc_id>
    Delete a document and its file
    """
    try:
        user = request.user
        
        if user.get('role') != 'doctor':
            return jsonify({'error': INSUFFICIENT_PERMISSIONS_ERROR}), 403
        
        # Get document to find file path
        get_query = "SELECT file_path FROM medical_documents WHERE id = %s"
        doc = execute_query(get_query, (doc_id,), fetch_one=True)
        
        if not doc:
            return jsonify({'error': DOCUMENT_NOT_FOUND_ERROR}), 404
        
        # Delete from database
        delete_query = "DELETE FROM medical_documents WHERE id = %s RETURNING id"
        result = execute_query(delete_query, (doc_id,), fetch_one=True)
        
        if not result:
            return jsonify({'error': FAILED_DELETE_DOCUMENT_ERROR}), 500

        _delete_file_from_storage(doc.get('file_path') or '')

        return jsonify({'message': 'Document deleted successfully'}), 200

    except Exception:
        current_app.logger.exception('Document delete error')
        return jsonify({'error': FAILED_DELETE_DOCUMENT_ERROR}), 500


@documents_bp.route('/download/<doc_id>', methods=['GET'])
@authenticate
def download_document(doc_id):
    """
    GET /api/documents/download/<doc_id>
    Download a document file (patient or doctor)
    """
    try:
        user = request.user
        
        # Get document
        query = "SELECT id, file_path, file_name, title, patient_id FROM medical_documents WHERE id = %s"
        doc = execute_query(query, (doc_id,), fetch_one=True)
        
        if not doc:
            return jsonify({'error': DOCUMENT_NOT_FOUND_ERROR}), 404
        
        # Patient can only download their own documents
        if user.get('role') == 'patient':
            patient_query = "SELECT id FROM patients WHERE user_id = %s"
            patient = execute_query(patient_query, (user['id'],), fetch_one=True)
            if not patient or patient['id'] != doc['patient_id']:
                return jsonify({'error': INSUFFICIENT_PERMISSIONS_ERROR}), 403
        elif user.get('role') != 'doctor':
            return jsonify({'error': INSUFFICIENT_PERMISSIONS_ERROR}), 403
        
        memory_file, local_file_path = _download_file_from_storage(doc.get('file_path') or '')

        if not memory_file and not local_file_path:
            return jsonify({'error': 'File not found on server'}), 404

        # Use title as download name if available, otherwise original filename
        download_name = doc.get('title') or doc.get('file_name') or 'document'

        if memory_file:
            memory_file.seek(0)
            return send_file(memory_file, as_attachment=True, download_name=download_name)

        return send_file(str(local_file_path), as_attachment=True, download_name=download_name)

    except Exception:
        current_app.logger.exception('Document download error')
        return jsonify({'error': 'Failed to download document'}), 500

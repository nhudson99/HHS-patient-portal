"""
Documents routes for patient medical documents
Handles file upload, download, rename, and delete operations
"""

from flask import Blueprint, request, jsonify, send_file
from datetime import datetime, date
import os
import uuid
from pathlib import Path
from werkzeug.utils import secure_filename
from api.db.connection import execute_query
from api.middleware.auth import authenticate

documents_bp = Blueprint('documents', __name__, url_prefix='/api/documents')

# Local storage directory (will be S3 in production)
UPLOAD_DIR = Path.home() / 'hhs-documents'

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


def ensure_upload_dir():
    """Create upload directory if it doesn't exist"""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, date):
            result[key] = value.isoformat()
    return result


@documents_bp.route('/<patient_id>', methods=['GET'])
@authenticate
def list_documents(patient_id):
    """
    GET /api/documents/<patient_id>
    List all documents for a patient
    """
    try:
        user = request.user
        
        # Only doctors can view documents (for now)
        if user.get('role') != 'doctor':
            return jsonify({'error': 'Insufficient permissions'}), 403
        
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
        
    except Exception as e:
        print(f"Documents list error: {e}")
        return jsonify({'error': 'Failed to retrieve documents'}), 500


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
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        # Get doctor ID
        doctor_query = "SELECT id FROM doctors WHERE user_id = %s"
        doctor = execute_query(doctor_query, (user['id'],), fetch_one=True)
        doctor_id = doctor['id'] if doctor else None
        
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        
        if not files or all(f.filename == '' for f in files):
            return jsonify({'error': 'No files selected'}), 400
        
        ensure_upload_dir()
        
        uploaded = []
        errors = []
        
        for file in files:
            if file.filename == '':
                continue
                
            if not allowed_file(file.filename):
                errors.append(f'{file.filename}: File type not allowed')
                continue
            
            # Secure the filename and generate unique storage name
            original_name = secure_filename(file.filename)
            file_ext = get_file_extension(original_name)
            unique_name = f"{uuid.uuid4()}_{original_name}"
            file_path = UPLOAD_DIR / unique_name
            
            # Save file
            file.save(str(file_path))
            file_size = file_path.stat().st_size
            
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
                (patient_id, doctor_id, doc_type, original_name, str(file_path), 
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
        
    except Exception as e:
        print(f"Document upload error: {e}")
        return jsonify({'error': 'Failed to upload documents'}), 500


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
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        data = request.get_json()
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
            return jsonify({'error': 'Document not found'}), 404
        
        return jsonify({
            'message': 'Document renamed successfully',
            'document': serialize_document(doc)
        }), 200
        
    except Exception as e:
        print(f"Document rename error: {e}")
        return jsonify({'error': 'Failed to rename document'}), 500


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
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        # Get document to find file path
        get_query = "SELECT file_path FROM medical_documents WHERE id = %s"
        doc = execute_query(get_query, (doc_id,), fetch_one=True)
        
        if not doc:
            return jsonify({'error': 'Document not found'}), 404
        
        # Delete from database
        delete_query = "DELETE FROM medical_documents WHERE id = %s RETURNING id"
        result = execute_query(delete_query, (doc_id,), fetch_one=True)
        
        if not result:
            return jsonify({'error': 'Failed to delete document'}), 500
        
        # Delete physical file
        if doc.get('file_path'):
            file_path = Path(doc['file_path'])
            if file_path.exists():
                file_path.unlink()
        
        return jsonify({'message': 'Document deleted successfully'}), 200
        
    except Exception as e:
        print(f"Document delete error: {e}")
        return jsonify({'error': 'Failed to delete document'}), 500


@documents_bp.route('/download/<doc_id>', methods=['GET'])
@authenticate
def download_document(doc_id):
    """
    GET /api/documents/download/<doc_id>
    Download a document file
    """
    try:
        user = request.user
        
        if user.get('role') != 'doctor':
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        # Get document
        query = "SELECT file_path, file_name, title FROM medical_documents WHERE id = %s"
        doc = execute_query(query, (doc_id,), fetch_one=True)
        
        if not doc:
            return jsonify({'error': 'Document not found'}), 404
        
        file_path = Path(doc['file_path'])
        
        if not file_path.exists():
            return jsonify({'error': 'File not found on server'}), 404
        
        # Use title as download name if available, otherwise original filename
        download_name = doc.get('title') or doc.get('file_name') or 'document'
        
        return send_file(
            str(file_path),
            as_attachment=True,
            download_name=download_name
        )
        
    except Exception as e:
        print(f"Document download error: {e}")
        return jsonify({'error': 'Failed to download document'}), 500

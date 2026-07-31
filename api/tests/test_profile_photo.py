from io import BytesIO

from api.db.connection import execute_query
from api.tests.conftest import login_as, requires_db


def _get_patient(username='patient1'):
    patient = execute_query(
        """
        SELECT p.id, p.first_name, p.last_name, p.date_of_birth,
               p.profile_photo_document_id
        FROM patients p
        JOIN users u ON u.id = p.user_id
        WHERE u.username = %s
        """,
        (username,),
        fetch_one=True,
    )
    assert patient is not None, f'Expected patient for {username}'
    return patient


def _jpeg_bytes():
    # Minimal valid JPEG (1x1 pixel)
    return BytesIO(
        bytes([
            0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
            0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
            0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
            0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
            0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
            0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
            0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
            0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
            0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x14, 0x00, 0x01,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x03, 0xFF, 0xC4, 0x00, 0x14, 0x10, 0x01, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F, 0x00,
            0x7F, 0xFF, 0xD9,
        ])
    )


def _upload_kiosk_photo(client, patient, *, name=None, dob=None):
    full_name = name if name is not None else f"{patient['first_name']} {patient['last_name']}"
    date_of_birth = dob if dob is not None else str(patient['date_of_birth'])
    data = {
        'patient_name': full_name,
        'date_of_birth': date_of_birth,
        'file': (_jpeg_bytes(), 'profile-photo.jpg'),
    }
    return client.post(
        f"/api/patients/{patient['id']}/profile-photo/kiosk",
        data=data,
        content_type='multipart/form-data',
    )


@requires_db
def test_kiosk_profile_photo_upload_and_get(client):
    patient = _get_patient('patient1')

    upload = _upload_kiosk_photo(client, patient)
    assert upload.status_code == 201, upload.get_json()
    assert upload.get_json()['has_profile_photo'] is True

    doctor_headers = login_as(client, 'doctor1')
    doctor_get = client.get(
        f"/api/patients/{patient['id']}/profile-photo",
        headers=doctor_headers,
    )
    assert doctor_get.status_code == 200
    assert doctor_get.content_type.startswith('image/')
    assert len(doctor_get.data) > 0

    patient_headers = login_as(client, 'patient1', 'Patient123!')
    patient_get = client.get(
        f"/api/patients/{patient['id']}/profile-photo",
        headers=patient_headers,
    )
    assert patient_get.status_code == 200

    me = client.get('/api/patients/me', headers=patient_headers)
    assert me.status_code == 200
    assert me.get_json()['patient']['has_profile_photo'] is True

    list_res = client.get('/api/patients', headers=doctor_headers)
    assert list_res.status_code == 200
    listed = next(p for p in list_res.get_json()['patients'] if p['id'] == str(patient['id']) or p['id'] == patient['id'])
    assert listed['has_profile_photo'] is True


@requires_db
def test_kiosk_profile_photo_rejects_identity_mismatch(client):
    patient = _get_patient('patient1')
    response = _upload_kiosk_photo(
        client,
        patient,
        name='Wrong Name',
        dob=str(patient['date_of_birth']),
    )
    assert response.status_code == 404


@requires_db
def test_profile_photo_excluded_from_document_list(client):
    patient = _get_patient('patient1')
    upload = _upload_kiosk_photo(client, patient)
    assert upload.status_code == 201, upload.get_json()

    doctor_headers = login_as(client, 'doctor1')
    docs = client.get(f"/api/documents/{patient['id']}", headers=doctor_headers)
    assert docs.status_code == 200, docs.get_json()
    for doc in docs.get_json()['documents']:
        assert doc['document_type'] != 'profile_photo'

    # Ensure a profile_photo row exists in DB even though list excludes it
    row = execute_query(
        """
        SELECT COUNT(*) AS count
        FROM medical_documents
        WHERE patient_id = %s AND document_type = 'profile_photo'
        """,
        (patient['id'],),
        fetch_one=True,
    )
    assert row['count'] >= 1


@requires_db
def test_profile_photo_not_mutable_via_generic_document_apis(client):
    patient = _get_patient('patient1')
    upload = _upload_kiosk_photo(client, patient)
    assert upload.status_code == 201, upload.get_json()

    photo = execute_query(
        """
        SELECT id
        FROM medical_documents
        WHERE patient_id = %s AND document_type = 'profile_photo'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (patient['id'],),
        fetch_one=True,
    )
    assert photo is not None
    doc_id = str(photo['id'])
    doctor_headers = login_as(client, 'doctor1')

    rename = client.put(
        f'/api/documents/{doc_id}/rename',
        headers=doctor_headers,
        json={'title': 'Should Not Rename'},
    )
    assert rename.status_code == 404

    visibility = client.put(
        f'/api/documents/{doc_id}/visibility',
        headers=doctor_headers,
        json={'patient_visible': False},
    )
    assert visibility.status_code == 404

    delete = client.delete(f'/api/documents/{doc_id}', headers=doctor_headers)
    assert delete.status_code == 404

    still_there = execute_query(
        "SELECT id FROM medical_documents WHERE id = %s",
        (doc_id,),
        fetch_one=True,
    )
    assert still_there is not None


@requires_db
def test_kiosk_profile_photo_rejects_non_jpeg(client):
    patient = _get_patient('patient1')
    data = {
        'patient_name': f"{patient['first_name']} {patient['last_name']}",
        'date_of_birth': str(patient['date_of_birth']),
        'file': (BytesIO(b'not-a-jpeg-payload'), 'profile-photo.jpg'),
    }
    response = client.post(
        f"/api/patients/{patient['id']}/profile-photo/kiosk",
        data=data,
        content_type='multipart/form-data',
    )
    assert response.status_code == 400
    assert 'JPEG' in (response.get_json() or {}).get('error', '')


@requires_db
def test_patient_cannot_get_other_patient_photo(client):
    patient1 = _get_patient('patient1')
    upload = _upload_kiosk_photo(client, patient1)
    assert upload.status_code == 201, upload.get_json()

    other_headers = login_as(client, 'patient2', 'Patient123!')
    response = client.get(
        f"/api/patients/{patient1['id']}/profile-photo",
        headers=other_headers,
    )
    assert response.status_code == 403

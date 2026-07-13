"""Tests for kiosk ID photo upload endpoint."""

from io import BytesIO

from api.tests.conftest import requires_db


# Minimal valid JPEG (1x1 pixel)
_MIN_JPEG = (
    b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
    b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
    b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e'
    b'\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342'
    b'\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00'
    b'\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00'
    b'\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b'
    b'\xff\xda\x00\x08\x01\x01\x00\x00?\x00\x7f\xff\xd9'
)


def _photo_data(filename='id-photo.jpg', content=_MIN_JPEG, content_type='image/jpeg', **fields):
    data = dict(fields)
    data['photo'] = (BytesIO(content), filename, content_type)
    return data


@requires_db
def test_kiosk_id_photo_requires_name_and_dob(client):
    response = client.post(
        '/api/documents/kiosk/id-photo',
        data=_photo_data(),
        content_type='multipart/form-data',
    )
    assert response.status_code == 400
    assert 'required' in response.get_json()['error'].lower()


@requires_db
def test_kiosk_id_photo_requires_photo(client):
    response = client.post(
        '/api/documents/kiosk/id-photo',
        data={
            'patient_name': 'John Smith',
            'date_of_birth': '1990-05-15',
        },
        content_type='multipart/form-data',
    )
    assert response.status_code == 400
    assert 'photo' in response.get_json()['error'].lower()


@requires_db
def test_kiosk_id_photo_rejects_non_image(client):
    response = client.post(
        '/api/documents/kiosk/id-photo',
        data=_photo_data(
            filename='notes.pdf',
            content=b'%PDF-1.4',
            content_type='application/pdf',
            patient_name='John Smith',
            date_of_birth='1990-05-15',
        ),
        content_type='multipart/form-data',
    )
    assert response.status_code == 400
    error = response.get_json()['error'].lower()
    assert 'jpeg' in error or 'png' in error


@requires_db
def test_kiosk_id_photo_patient_not_found(client):
    response = client.post(
        '/api/documents/kiosk/id-photo',
        data=_photo_data(
            patient_name='Nobody Here',
            date_of_birth='1900-01-01',
        ),
        content_type='multipart/form-data',
    )
    assert response.status_code == 404


@requires_db
def test_kiosk_id_photo_saves_to_patient_profile(client):
    from api.db.connection import execute_query

    patient = execute_query(
        """
        SELECT p.id, CONCAT(p.first_name, ' ', p.last_name) AS full_name, p.date_of_birth
        FROM patients p
        JOIN users u ON u.id = p.user_id
        WHERE u.username = 'patient1'
        """,
        fetch_one=True,
    )
    assert patient, 'Seeded patient1 is required for this test'

    dob = patient['date_of_birth']
    dob_str = dob.isoformat() if hasattr(dob, 'isoformat') else str(dob)

    response = client.post(
        '/api/documents/kiosk/id-photo',
        data=_photo_data(
            patient_name=patient['full_name'],
            date_of_birth=dob_str,
        ),
        content_type='multipart/form-data',
    )
    assert response.status_code == 201, response.get_json()
    payload = response.get_json()
    assert payload['message'] == 'ID photo saved'
    doc = payload['document']
    assert doc['document_type'] == 'id_photo'
    assert doc['patient_id'] == patient['id']
    assert 'ID Photo' in doc['title']

    # Clean up created document
    execute_query('DELETE FROM medical_documents WHERE id = %s', (doc['id'],))

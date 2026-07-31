from api.db.connection import execute_query
from api.tests.conftest import login_as, requires_db


def _get_patient_id():
    patient = execute_query('SELECT id FROM patients LIMIT 1', fetch_one=True)
    assert patient is not None, 'Expected at least one patient in seed data'
    return patient['id']


def _get_doctor_name(username):
    doctor = execute_query(
        """
        SELECT d.first_name, d.last_name
        FROM doctors d
        JOIN users u ON u.id = d.user_id
        WHERE u.username = %s
        """,
        (username,),
        fetch_one=True,
    )
    assert doctor is not None
    return f"{doctor['first_name']} {doctor['last_name']}"


def _count_audit_logs(action, resource_id):
    row = execute_query(
        """
        SELECT COUNT(*) AS count
        FROM audit_logs
        WHERE action = %s AND resource_id = %s
        """,
        (action, resource_id),
        fetch_one=True,
    )
    return row['count'] if row else 0


@requires_db
def test_doctor_can_create_note_with_attribution(client):
    headers = login_as(client, 'doctor1')
    patient_id = _get_patient_id()
    expected_name = _get_doctor_name('doctor1')

    response = client.post(
        f'/api/patient-properties/{patient_id}',
        headers=headers,
        json={'name': 'Initial Assessment', 'description': 'Patient is stable.'},
    )
    assert response.status_code == 201, response.get_json()
    payload = response.get_json()
    note = payload['property']

    assert note['name'] == 'Initial Assessment'
    assert note['description'] == 'Patient is stable.'
    assert note['created_by_name'] == expected_name
    assert note['updated_by_name'] == expected_name
    assert note['created_by_doctor_id'] == note['updated_by_doctor_id']


@requires_db
def test_doctor_can_patch_note_description(client):
    headers = login_as(client, 'doctor1')
    patient_id = _get_patient_id()

    create_response = client.post(
        f'/api/patient-properties/{patient_id}',
        headers=headers,
        json={'name': 'Follow-up', 'description': 'Original note'},
    )
    assert create_response.status_code == 201, create_response.get_json()
    note = create_response.get_json()['property']

    patch_response = client.patch(
        f'/api/patient-properties/{patient_id}/{note["property_id"]}',
        headers=headers,
        json={
            'description': 'Updated note body',
            'updated_at': note['updated_at'],
        },
    )
    assert patch_response.status_code == 200, patch_response.get_json()
    updated = patch_response.get_json()['property']

    assert updated['description'] == 'Updated note body'
    assert updated['updated_by_name'] == _get_doctor_name('doctor1')
    assert updated['updated_at'] >= note['updated_at']


@requires_db
def test_patch_requires_doctor_role(client):
    headers = login_as(client, 'patient1', 'Patient123!')
    patient_id = _get_patient_id()

    response = client.patch(
        f'/api/patient-properties/{patient_id}/1',
        headers=headers,
        json={'description': 'Should fail'},
    )
    assert response.status_code == 403, response.get_json()


@requires_db
def test_patch_note_not_found(client):
    headers = login_as(client, 'doctor1')
    patient_id = _get_patient_id()

    response = client.patch(
        f'/api/patient-properties/{patient_id}/99999',
        headers=headers,
        json={'description': 'Missing note'},
    )
    assert response.status_code == 404, response.get_json()


@requires_db
def test_list_notes_includes_provider_names(client):
    headers = login_as(client, 'doctor1')
    patient_id = _get_patient_id()
    expected_name = _get_doctor_name('doctor1')

    create_response = client.post(
        f'/api/patient-properties/{patient_id}',
        headers=headers,
        json={'name': 'List Test Note', 'description': 'Visible in list'},
    )
    assert create_response.status_code == 201, create_response.get_json()
    created = create_response.get_json()['property']

    list_response = client.get(
        f'/api/patient-properties/{patient_id}',
        headers=headers,
    )
    assert list_response.status_code == 200, list_response.get_json()
    notes = list_response.get_json()['properties']
    matched = [note for note in notes if note['property_id'] == created['property_id']]
    assert len(matched) == 1
    assert matched[0]['created_by_name'] == expected_name
    assert matched[0]['updated_by_name'] == expected_name


@requires_db
def test_note_crud_writes_audit_log(client):
    headers = login_as(client, 'doctor1')
    patient_id = _get_patient_id()

    create_response = client.post(
        f'/api/patient-properties/{patient_id}',
        headers=headers,
        json={'name': 'Audit Trail', 'description': 'Before update'},
    )
    assert create_response.status_code == 201, create_response.get_json()
    note = create_response.get_json()['property']
    resource_id = f'{patient_id}:{note["property_id"]}'

    assert _count_audit_logs('DATA_CREATE', resource_id) >= 1

    patch_response = client.patch(
        f'/api/patient-properties/{patient_id}/{note["property_id"]}',
        headers=headers,
        json={'description': 'After update', 'updated_at': note['updated_at']},
    )
    assert patch_response.status_code == 200, patch_response.get_json()
    assert _count_audit_logs('DATA_UPDATE', resource_id) >= 1

    delete_response = client.delete(
        f'/api/patient-properties/{patient_id}/{note["property_id"]}',
        headers=headers,
    )
    assert delete_response.status_code == 200, delete_response.get_json()
    assert _count_audit_logs('DATA_DELETE', resource_id) >= 1

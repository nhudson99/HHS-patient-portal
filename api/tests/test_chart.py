from api.db.connection import execute_query
from api.tests.conftest import login_as, requires_db


def _get_patient_id(username='patient1'):
    patient = execute_query(
        """
        SELECT p.id
        FROM patients p
        JOIN users u ON u.id = p.user_id
        WHERE u.username = %s
        """,
        (username,),
        fetch_one=True,
    )
    assert patient is not None, f'Expected patient for {username}'
    return patient['id']


def _count_audit_logs(action, resource_type=None, resource_id=None):
    clauses = ['action = %s']
    params = [action]
    if resource_type:
        clauses.append('resource_type = %s')
        params.append(resource_type)
    if resource_id:
        clauses.append('resource_id = %s')
        params.append(str(resource_id))
    row = execute_query(
        f"SELECT COUNT(*) AS count FROM audit_logs WHERE {' AND '.join(clauses)}",
        tuple(params),
        fetch_one=True,
    )
    return row['count'] if row else 0


@requires_db
def test_patient_cannot_access_chart_summary(client):
    headers = login_as(client, 'patient1', 'Patient123!')
    patient_id = _get_patient_id()
    response = client.get(f'/api/chart/{patient_id}/summary', headers=headers)
    assert response.status_code == 403, response.get_json()


@requires_db
def test_doctor_chart_summary_includes_active_items(client):
    headers = login_as(client, 'doctor1')
    patient_id = _get_patient_id()

    response = client.get(f'/api/chart/{patient_id}/summary', headers=headers)
    assert response.status_code == 200, response.get_json()
    summary = response.get_json()['summary']

    assert 'allergies' in summary
    assert 'medications' in summary
    assert 'problems' in summary
    assert summary['allergy_count'] == len(summary['allergies'])
    assert summary['medication_count'] == len(summary['medications'])
    assert summary['problem_count'] == len(summary['problems'])
    assert _count_audit_logs('DATA_VIEW', 'chart_summary', patient_id) >= 1


@requires_db
def test_allergy_crud_flow(client):
    headers = login_as(client, 'doctor1')
    patient_id = _get_patient_id()

    create_response = client.post(
        f'/api/chart/{patient_id}/allergies',
        headers=headers,
        json={
            'allergen': 'Sulfa Drugs',
            'reaction': 'Itching',
            'severity': 'mild',
            'status': 'active',
            'notes': 'Avoid sulfonamides',
        },
    )
    assert create_response.status_code == 201, create_response.get_json()
    allergy = create_response.get_json()['allergy']
    allergy_id = allergy['id']
    assert allergy['allergen'] == 'Sulfa Drugs'
    assert allergy['severity'] == 'mild'
    assert _count_audit_logs('DATA_CREATE', 'allergies', allergy_id) >= 1

    update_response = client.put(
        f'/api/chart/{patient_id}/allergies/{allergy_id}',
        headers=headers,
        json={'severity': 'moderate', 'status': 'inactive'},
    )
    assert update_response.status_code == 200, update_response.get_json()
    updated = update_response.get_json()['allergy']
    assert updated['severity'] == 'moderate'
    assert updated['status'] == 'inactive'

    list_response = client.get(f'/api/chart/{patient_id}/allergies', headers=headers)
    assert list_response.status_code == 200
    ids = [row['id'] for row in list_response.get_json()['allergies']]
    assert allergy_id in ids

    delete_response = client.delete(
        f'/api/chart/{patient_id}/allergies/{allergy_id}',
        headers=headers,
    )
    assert delete_response.status_code == 200, delete_response.get_json()
    assert _count_audit_logs('DATA_DELETE', 'allergies', allergy_id) >= 1


@requires_db
def test_medication_and_problem_crud(client):
    headers = login_as(client, 'doctor1')
    patient_id = _get_patient_id()

    med_response = client.post(
        f'/api/chart/{patient_id}/medications',
        headers=headers,
        json={
            'name': 'Atorvastatin',
            'dosage': '20 mg',
            'frequency': 'Nightly',
            'route': 'Oral',
            'status': 'active',
            'start_date': '2026-01-01',
        },
    )
    assert med_response.status_code == 201, med_response.get_json()
    medication = med_response.get_json()['medication']
    assert medication['name'] == 'Atorvastatin'

    med_update = client.put(
        f'/api/chart/{patient_id}/medications/{medication["id"]}',
        headers=headers,
        json={'status': 'discontinued', 'end_date': '2026-07-01'},
    )
    assert med_update.status_code == 200, med_update.get_json()
    assert med_update.get_json()['medication']['status'] == 'discontinued'

    problem_response = client.post(
        f'/api/chart/{patient_id}/problems',
        headers=headers,
        json={
            'name': 'Hyperlipidemia',
            'status': 'active',
            'onset_date': '2025-12-01',
            'notes': 'Diet and statin therapy',
        },
    )
    assert problem_response.status_code == 201, problem_response.get_json()
    problem = problem_response.get_json()['problem']

    problem_update = client.put(
        f'/api/chart/{patient_id}/problems/{problem["id"]}',
        headers=headers,
        json={'status': 'resolved', 'resolved_date': '2026-07-01'},
    )
    assert problem_update.status_code == 200, problem_update.get_json()
    assert problem_update.get_json()['problem']['status'] == 'resolved'

    assert client.delete(
        f'/api/chart/{patient_id}/medications/{medication["id"]}',
        headers=headers,
    ).status_code == 200
    assert client.delete(
        f'/api/chart/{patient_id}/problems/{problem["id"]}',
        headers=headers,
    ).status_code == 200


@requires_db
def test_document_visibility_gates_patient_access(client):
    doctor_headers = login_as(client, 'doctor1')
    patient_headers = login_as(client, 'patient1', 'Patient123!')
    patient_id = _get_patient_id()

    # Ensure at least one provider-only and one visible document exist via visibility toggle
    doctor_list = client.get(f'/api/documents/{patient_id}', headers=doctor_headers)
    assert doctor_list.status_code == 200, doctor_list.get_json()
    docs = doctor_list.get_json()['documents']
    assert len(docs) >= 1

    # Pick first doc and force provider-only, then verify patient cannot see it
    target = docs[0]
    hide = client.put(
        f'/api/documents/{target["id"]}/visibility',
        headers=doctor_headers,
        json={'patient_visible': False},
    )
    assert hide.status_code == 200, hide.get_json()
    assert hide.get_json()['document']['patient_visible'] is False

    patient_list_hidden = client.get(f'/api/documents/{patient_id}', headers=patient_headers)
    assert patient_list_hidden.status_code == 200, patient_list_hidden.get_json()
    patient_ids = {d['id'] for d in patient_list_hidden.get_json()['documents']}
    assert target['id'] not in patient_ids

    download_hidden = client.get(
        f'/api/documents/download/{target["id"]}',
        headers=patient_headers,
    )
    assert download_hidden.status_code == 403, download_hidden.get_json()

    show = client.put(
        f'/api/documents/{target["id"]}/visibility',
        headers=doctor_headers,
        json={'patient_visible': True},
    )
    assert show.status_code == 200, show.get_json()
    assert show.get_json()['document']['patient_visible'] is True

    patient_list_visible = client.get(f'/api/documents/{patient_id}', headers=patient_headers)
    assert patient_list_visible.status_code == 200, patient_list_visible.get_json()
    visible_ids = {d['id'] for d in patient_list_visible.get_json()['documents']}
    assert target['id'] in visible_ids

    # Patient cannot toggle visibility
    patient_toggle = client.put(
        f'/api/documents/{target["id"]}/visibility',
        headers=patient_headers,
        json={'patient_visible': False},
    )
    assert patient_toggle.status_code == 403, patient_toggle.get_json()

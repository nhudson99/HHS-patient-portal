from api.db.connection import execute_query
from api.tests.conftest import login_as, requires_db


@requires_db
def test_all_providers_redacts_other_provider_phi(client):
    headers = login_as(client, 'doctor1')

    response = client.get(
        '/api/events?start_date=2026-07-10&end_date=2026-07-13&include_all_providers=true',
        headers=headers,
    )
    assert response.status_code == 200, response.get_json()
    events = response.get_json()['events']
    assert len(events) > 0

    doctor_ids = {event['doctor_id'] for event in events}
    assert len(doctor_ids) > 1, 'Expected events from multiple providers in seed data'

    own_events = [event for event in events if event['is_own_event']]
    other_events = [event for event in events if not event['is_own_event']]

    assert len(own_events) > 0
    assert len(other_events) > 0

    for event in own_events:
        assert event['patient_name'] is not None or event['event_type'] in ('meeting', 'blocked_time', 'note', 'other')

    for event in other_events:
        assert event['patient_name'] is None
        assert event['patient_id'] is None
        assert event['description'] is None
        assert 'Jane' not in (event.get('title') or '')
        assert 'Smith' not in (event.get('title') or '')
        assert 'Doe' not in (event.get('title') or '')


@requires_db
def test_default_events_request_returns_only_own_events(client):
    headers = login_as(client, 'doctor1')

    response = client.get(
        '/api/events?start_date=2026-07-10&end_date=2026-07-10',
        headers=headers,
    )
    assert response.status_code == 200, response.get_json()
    events = response.get_json()['events']

    assert len(events) > 0
    assert all(event['is_own_event'] for event in events)

    doctor_row = execute_query(
        "SELECT d.id FROM doctors d JOIN users u ON u.id = d.user_id WHERE u.username = %s",
        ('doctor1',),
        fetch_one=True,
    )
    assert all(str(event['doctor_id']) == str(doctor_row['id']) for event in events)


@requires_db
def test_doctor_cannot_update_another_providers_event(client):
    headers = login_as(client, 'doctor1')

    other_event = execute_query(
        """
        SELECT e.id
        FROM events e
        JOIN doctors d ON d.id = e.doctor_id
        JOIN users u ON u.id = d.user_id
        WHERE u.username = %s
        LIMIT 1
        """,
        ('doctor2',),
        fetch_one=True,
    )
    assert other_event is not None

    response = client.put(
        f"/api/events/{other_event['id']}",
        headers=headers,
        json={'title': 'Unauthorized update'},
    )
    assert response.status_code == 404


@requires_db
def test_doctor_cannot_delete_another_providers_event(client):
    headers = login_as(client, 'doctor1')

    other_event = execute_query(
        """
        SELECT e.id
        FROM events e
        JOIN doctors d ON d.id = e.doctor_id
        JOIN users u ON u.id = d.user_id
        WHERE u.username = %s
        LIMIT 1
        """,
        ('doctor2',),
        fetch_one=True,
    )
    assert other_event is not None

    response = client.delete(
        f"/api/events/{other_event['id']}",
        headers=headers,
    )
    assert response.status_code == 404


@requires_db
def test_doctor_cannot_confirm_another_providers_appointment(client):
    headers = login_as(client, 'doctor1')

    other_appointment = execute_query(
        """
        SELECT a.id
        FROM appointments a
        JOIN doctors d ON d.id = a.doctor_id
        JOIN users u ON u.id = d.user_id
        WHERE u.username = %s
          AND a.status = 'pending'
        LIMIT 1
        """,
        ('doctor2',),
        fetch_one=True,
    )
    assert other_appointment is not None

    response = client.patch(
        f"/api/appointments/{other_appointment['id']}/confirm",
        headers=headers,
    )
    assert response.status_code == 404

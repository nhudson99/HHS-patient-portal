from urllib.parse import quote

from api.db.connection import execute_query
from api.tests.conftest import login_as, requires_db


def _user_id(username):
    row = execute_query(
        'SELECT id FROM users WHERE username = %s',
        (username,),
        fetch_one=True,
    )
    assert row is not None, f'Expected seeded user {username}'
    return str(row['id'])


@requires_db
def test_doctor_and_patient_can_dm_and_reply_in_thread(client):
    doctor_headers = login_as(client, 'doctor1')
    patient_headers = login_as(client, 'patient1', 'Patient123!')
    patient_user_id = _user_id('patient1')

    create_response = client.post(
        '/api/conversations',
        headers=doctor_headers,
        json={'type': 'dm', 'participant_user_id': patient_user_id},
    )
    assert create_response.status_code in (200, 201), create_response.get_json()
    conversation = create_response.get_json()['conversation']
    conversation_id = conversation['id']
    assert conversation['type'] == 'dm'
    assert len(conversation['participants']) == 2

    send_response = client.post(
        f'/api/conversations/{conversation_id}/messages',
        headers=doctor_headers,
        json={'body': 'Please confirm your medication list before Friday.'},
    )
    assert send_response.status_code == 201, send_response.get_json()
    parent = send_response.get_json()['message']
    assert parent['body'] == 'Please confirm your medication list before Friday.'
    assert parent['parent_message_id'] is None

    reply_response = client.post(
        f'/api/conversations/{conversation_id}/messages',
        headers=patient_headers,
        json={
            'body': 'Confirmed — no changes since last visit.',
            'parent_message_id': parent['id'],
        },
    )
    assert reply_response.status_code == 201, reply_response.get_json()
    reply = reply_response.get_json()['message']
    assert reply['parent_message_id'] == parent['id']

    thread_response = client.get(
        f'/api/conversations/{conversation_id}/messages?parent_message_id={parent["id"]}',
        headers=doctor_headers,
    )
    assert thread_response.status_code == 200
    thread_messages = thread_response.get_json()['messages']
    assert any(msg['id'] == reply['id'] for msg in thread_messages)

    list_response = client.get(
        f'/api/conversations/{conversation_id}/messages',
        headers=patient_headers,
    )
    assert list_response.status_code == 200
    top_level = list_response.get_json()['messages']
    matched = next(msg for msg in top_level if msg['id'] == parent['id'])
    assert matched['reply_count'] >= 1


@requires_db
def test_patient_cannot_message_other_patients(client):
    patient_headers = login_as(client, 'patient1', 'Patient123!')
    other_patient_id = _user_id('patient2')

    response = client.post(
        '/api/conversations',
        headers=patient_headers,
        json={'type': 'dm', 'participant_user_id': other_patient_id},
    )
    assert response.status_code == 403


@requires_db
def test_patient_cannot_create_channel(client):
    patient_headers = login_as(client, 'patient1', 'Patient123!')
    response = client.post(
        '/api/conversations',
        headers=patient_headers,
        json={'type': 'channel', 'title': 'Test Channel Blocked'},
    )
    assert response.status_code == 403


@requires_db
def test_doctor_can_create_channel_and_non_participant_cannot_read(client):
    doctor_headers = login_as(client, 'doctor1')
    outsider_headers = login_as(client, 'doctor3')
    patient_user_id = _user_id('patient1')

    create_response = client.post(
        '/api/conversations',
        headers=doctor_headers,
        json={
            'type': 'channel',
            'title': 'Test Channel Care Sync',
            'participant_user_ids': [patient_user_id],
        },
    )
    assert create_response.status_code == 201, create_response.get_json()
    conversation_id = create_response.get_json()['conversation']['id']

    send_response = client.post(
        f'/api/conversations/{conversation_id}/messages',
        headers=doctor_headers,
        json={'body': 'Channel kickoff note'},
    )
    assert send_response.status_code == 201

    blocked = client.get(
        f'/api/conversations/{conversation_id}/messages',
        headers=outsider_headers,
    )
    assert blocked.status_code == 404

    # Cleanup channel created by this test
    execute_query(
        "DELETE FROM conversations WHERE id = %s",
        (conversation_id,),
    )


@requires_db
def test_unread_count_updates_after_read(client):
    doctor_headers = login_as(client, 'doctor1')
    patient_headers = login_as(client, 'patient1', 'Patient123!')
    doctor_user_id = _user_id('doctor1')

    create_response = client.post(
        '/api/conversations',
        headers=patient_headers,
        json={'type': 'dm', 'participant_user_id': doctor_user_id},
    )
    assert create_response.status_code in (200, 201), create_response.get_json()
    conversation_id = create_response.get_json()['conversation']['id']

    send_response = client.post(
        f'/api/conversations/{conversation_id}/messages',
        headers=patient_headers,
        json={'body': 'Quick question about my labs'},
    )
    assert send_response.status_code == 201

    unread_before = client.get('/api/conversations/unread-count', headers=doctor_headers)
    assert unread_before.status_code == 200
    assert unread_before.get_json()['unread_count'] >= 1

    mark_read = client.patch(
        f'/api/conversations/{conversation_id}/read',
        headers=doctor_headers,
    )
    assert mark_read.status_code == 200

    conversation_unread = client.get(
        '/api/conversations',
        headers=doctor_headers,
    )
    assert conversation_unread.status_code == 200
    conversations = conversation_unread.get_json()['conversations']
    target = next(c for c in conversations if c['id'] == conversation_id)
    assert target['unread_count'] == 0


@requires_db
def test_contacts_endpoint_returns_opposite_roles_for_patients(client):
    patient_headers = login_as(client, 'patient1', 'Patient123!')
    response = client.get('/api/conversations/contacts', headers=patient_headers)
    assert response.status_code == 200
    contacts = response.get_json()['contacts']
    assert len(contacts) >= 1
    assert all(contact['role'] == 'doctor' for contact in contacts)


@requires_db
def test_list_messages_since_returns_only_newer_rows(client):
    doctor_headers = login_as(client, 'doctor1')
    patient_user_id = _user_id('patient1')

    create_response = client.post(
        '/api/conversations',
        headers=doctor_headers,
        json={'type': 'dm', 'participant_user_id': patient_user_id},
    )
    assert create_response.status_code in (200, 201), create_response.get_json()
    conversation_id = create_response.get_json()['conversation']['id']

    first_response = client.post(
        f'/api/conversations/{conversation_id}/messages',
        headers=doctor_headers,
        json={'body': 'First message for since filter'},
    )
    assert first_response.status_code == 201, first_response.get_json()
    first = first_response.get_json()['message']

    empty_delta = client.get(
        f'/api/conversations/{conversation_id}/messages?since={quote(first["created_at"])}',
        headers=doctor_headers,
    )
    assert empty_delta.status_code == 200
    assert empty_delta.get_json()['messages'] == []

    second_response = client.post(
        f'/api/conversations/{conversation_id}/messages',
        headers=doctor_headers,
        json={'body': 'Second message for since filter'},
    )
    assert second_response.status_code == 201, second_response.get_json()
    second = second_response.get_json()['message']

    # Also accept unencoded '+' offsets (decoded as space by query parsers).
    delta_response = client.get(
        f'/api/conversations/{conversation_id}/messages?since={first["created_at"]}',
        headers=doctor_headers,
    )
    assert delta_response.status_code == 200
    delta_messages = delta_response.get_json()['messages']
    assert [msg['id'] for msg in delta_messages] == [second['id']]
    assert delta_messages[0]['body'] == 'Second message for since filter'

    invalid = client.get(
        f'/api/conversations/{conversation_id}/messages?since=not-a-timestamp',
        headers=doctor_headers,
    )
    assert invalid.status_code == 400


@requires_db
def test_list_thread_messages_since_returns_only_newer_replies(client):
    doctor_headers = login_as(client, 'doctor1')
    patient_headers = login_as(client, 'patient1', 'Patient123!')
    patient_user_id = _user_id('patient1')

    create_response = client.post(
        '/api/conversations',
        headers=doctor_headers,
        json={'type': 'dm', 'participant_user_id': patient_user_id},
    )
    assert create_response.status_code in (200, 201), create_response.get_json()
    conversation_id = create_response.get_json()['conversation']['id']

    parent_response = client.post(
        f'/api/conversations/{conversation_id}/messages',
        headers=doctor_headers,
        json={'body': 'Thread root for since filter'},
    )
    assert parent_response.status_code == 201, parent_response.get_json()
    parent = parent_response.get_json()['message']

    first_reply_response = client.post(
        f'/api/conversations/{conversation_id}/messages',
        headers=patient_headers,
        json={'body': 'First reply', 'parent_message_id': parent['id']},
    )
    assert first_reply_response.status_code == 201, first_reply_response.get_json()
    first_reply = first_reply_response.get_json()['message']

    second_reply_response = client.post(
        f'/api/conversations/{conversation_id}/messages',
        headers=doctor_headers,
        json={'body': 'Second reply', 'parent_message_id': parent['id']},
    )
    assert second_reply_response.status_code == 201, second_reply_response.get_json()
    second_reply = second_reply_response.get_json()['message']

    delta_response = client.get(
        f'/api/conversations/{conversation_id}/messages'
        f'?parent_message_id={parent["id"]}&since={quote(first_reply["created_at"])}',
        headers=doctor_headers,
    )
    assert delta_response.status_code == 200
    delta_messages = delta_response.get_json()['messages']
    assert [msg['id'] for msg in delta_messages] == [second_reply['id']]

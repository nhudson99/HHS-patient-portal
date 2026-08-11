"""
Auth session lifecycle and admin user-creation tests.
"""

from unittest.mock import patch
import uuid

import pytest

from api.db.connection import execute_query
from api.tests.conftest import login_as, requires_db


def _unique_suffix():
    return uuid.uuid4().hex[:10]


def _admin_auth_headers():
    return {
        'Authorization': 'Bearer fake-admin-token',
        'Content-Type': 'application/json',
    }


def _cleanup_user(username: str):
    row = execute_query(
        'SELECT id FROM users WHERE username = %s',
        (username,),
        fetch_one=True,
    )
    if row:
        execute_query('DELETE FROM users WHERE id = %s', (row['id'],))


@requires_db
def test_logout_invalidates_session(client):
    headers = login_as(client, 'doctor1', 'Doctor123!')
    token = headers['Authorization'].split(' ', 1)[1]

    logout_response = client.post('/api/auth/logout', headers=headers)
    assert logout_response.status_code == 200, logout_response.get_json()

    me_response = client.get(
        '/api/auth/me',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert me_response.status_code == 401


@requires_db
def test_logout_clears_cookie_auth(client):
    login_response = client.post('/api/auth/login', json={
        'username': 'doctor1',
        'password': 'Doctor123!',
    })
    assert login_response.status_code == 200, login_response.get_json()
    token = login_response.get_json()['sessionToken']

    # Use cookie only (no Bearer) — mirrors post-localStorage-clear behavior.
    client.set_cookie('sessionToken', token)
    logout_response = client.post('/api/auth/logout')
    assert logout_response.status_code == 200, logout_response.get_json()

    me_response = client.get('/api/auth/me')
    assert me_response.status_code == 401


@requires_db
def test_change_password_keeps_current_session(client):
    suffix = _unique_suffix()
    username = f'pwchange_{suffix}'
    email = f'{username}@example.com'
    original_password = 'TempPass123!'
    new_password = 'NewPass456!'

    register = client.post('/api/auth/register', json={
        'username': username,
        'email': email,
        'password': original_password,
        'firstName': 'Pw',
        'lastName': 'Change',
        'dateOfBirth': '1990-01-01',
    })
    assert register.status_code == 201, register.get_json()

    try:
        headers = login_as(client, username, original_password)
        change = client.post('/api/auth/change-password', headers=headers, json={
            'currentPassword': original_password,
            'newPassword': new_password,
        })
        assert change.status_code == 200, change.get_json()

        me = client.get('/api/auth/me', headers=headers)
        assert me.status_code == 200, me.get_json()
        assert me.get_json()['user']['username'] == username
    finally:
        _cleanup_user(username)


@requires_db
def test_must_change_password_blocks_phi_but_allows_auth_endpoints(client):
    suffix = _unique_suffix()
    username = f'mustchg_{suffix}'
    email = f'{username}@example.com'
    password = 'TempPass123!'

    register = client.post('/api/auth/register', json={
        'username': username,
        'email': email,
        'password': password,
        'firstName': 'Must',
        'lastName': 'Change',
        'dateOfBirth': '1991-02-02',
    })
    assert register.status_code == 201, register.get_json()

    try:
        execute_query(
            'UPDATE users SET must_change_password = true WHERE username = %s',
            (username,),
        )
        headers = login_as(client, username, password)

        me = client.get('/api/auth/me', headers=headers)
        assert me.status_code == 200, me.get_json()
        assert me.get_json()['requirePasswordChange'] is True

        blocked = client.get('/api/patients/me', headers=headers)
        assert blocked.status_code == 403
        assert blocked.get_json().get('code') == 'PASSWORD_CHANGE_REQUIRED'

        change = client.post('/api/auth/change-password', headers=headers, json={
            'currentPassword': password,
            'newPassword': 'ChangedPass123!',
        })
        assert change.status_code == 200, change.get_json()

        allowed = client.get('/api/patients/me', headers=headers)
        assert allowed.status_code == 200, allowed.get_json()
    finally:
        _cleanup_user(username)


@requires_db
@patch('api.routes.admin._verify_token_or_raise')
def test_admin_create_doctor_duplicate_returns_409(mock_verify, client):
    mock_verify.return_value = {
        'preferred_username': 'admin@hudsonitconsulting.com',
        'email': 'admin@hudsonitconsulting.com',
        'name': 'Admin User',
        'tid': 'test-tenant',
    }
    suffix = _unique_suffix()
    username = f'admdoc_{suffix}'
    email = f'{username}@example.com'
    payload = {
        'username': username,
        'email': email,
        'firstName': 'Ada',
        'lastName': 'Doctor',
        'specialty': 'Internal Medicine',
        'licenseNumber': f'LIC-{suffix}',
        'isActive': True,
    }

    try:
        first = client.post(
            '/api/admin/doctors',
            headers=_admin_auth_headers(),
            json=payload,
        )
        assert first.status_code == 201, first.get_json()
        assert first.get_json().get('temporaryPassword')

        duplicate = client.post(
            '/api/admin/doctors',
            headers=_admin_auth_headers(),
            json=payload,
        )
        assert duplicate.status_code == 409
        assert 'already in use' in duplicate.get_json()['error'].lower()
    finally:
        _cleanup_user(username)


@requires_db
@patch('api.routes.admin._verify_token_or_raise')
def test_admin_create_patient_respects_is_active(mock_verify, client):
    mock_verify.return_value = {
        'preferred_username': 'admin@hudsonitconsulting.com',
        'email': 'admin@hudsonitconsulting.com',
        'name': 'Admin User',
        'tid': 'test-tenant',
    }
    suffix = _unique_suffix()
    username = f'admpat_{suffix}'
    email = f'{username}@example.com'

    try:
        created = client.post(
            '/api/admin/patients',
            headers=_admin_auth_headers(),
            json={
                'username': username,
                'email': email,
                'firstName': 'Pat',
                'lastName': 'Inactive',
                'isActive': False,
            },
        )
        assert created.status_code == 201, created.get_json()
        body = created.get_json()
        assert body['patient']['is_active'] is False
        assert body.get('temporaryPassword')

        login = client.post('/api/auth/login', json={
            'username': username,
            'password': body['temporaryPassword'],
        })
        assert login.status_code == 403
        assert 'inactive' in login.get_json()['error'].lower()
    finally:
        _cleanup_user(username)


@requires_db
@patch('api.routes.admin._verify_token_or_raise')
def test_admin_create_rejects_blank_required_fields(mock_verify, client):
    mock_verify.return_value = {
        'preferred_username': 'admin@hudsonitconsulting.com',
        'email': 'admin@hudsonitconsulting.com',
        'name': 'Admin User',
        'tid': 'test-tenant',
    }

    response = client.post(
        '/api/admin/doctors',
        headers=_admin_auth_headers(),
        json={
            'username': '   ',
            'email': 'blank@example.com',
            'firstName': 'A',
            'lastName': 'B',
            'specialty': 'Family',
            'licenseNumber': 'L1',
        },
    )
    assert response.status_code == 400
    assert 'username' in response.get_json()['error'].lower()

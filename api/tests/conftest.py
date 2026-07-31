import pytest

from api.app import app
from api.db.connection import execute_query, init_db_pool


def _db_available():
    try:
        init_db_pool()
        execute_query('SELECT 1', fetch_one=True)
        return True
    except Exception:
        return False


requires_db = pytest.mark.skipif(not _db_available(), reason='PostgreSQL database is not available')


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as test_client:
        yield test_client


def login_as(client, username='doctor1', password='Doctor123!'):
    response = client.post('/api/auth/login', json={
        'username': username,
        'password': password,
    })
    assert response.status_code == 200, response.get_json()
    payload = response.get_json()
    token = payload['sessionToken']
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }

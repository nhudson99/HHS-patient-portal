from api.app import app


def test_health_endpoint_returns_ok():
    client = app.test_client()
    response = client.get('/health')
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert "timestamp" in payload

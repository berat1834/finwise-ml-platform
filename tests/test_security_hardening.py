"""Security hardening regression tests for the v2 secure API."""


def test_security_headers_present(client):
    resp = client.get('/health')
    assert resp.status_code == 200
    assert resp.headers.get('X-Content-Type-Options') == 'nosniff'
    assert resp.headers.get('X-Frame-Options') == 'DENY'
    assert 'Content-Security-Policy' in resp.headers
    assert 'X-Request-ID' in resp.headers


def test_auth_requires_json_content_type(client):
    resp = client.post('/auth/login', data='username=testuser&password=testpass123')
    assert resp.status_code == 415


def test_login_rate_limit_lockout(client):
    # Default lockout policy: block after repeated failures in same window.
    lockout_username = 'lockout_user'
    for _ in range(5):
        resp = client.post('/auth/login', json={'username': lockout_username, 'password': 'WrongPass123'})
        assert resp.status_code == 401

    blocked = client.post('/auth/login', json={'username': lockout_username, 'password': 'WrongPass123'})
    assert blocked.status_code == 429
    payload = blocked.get_json() or {}
    assert 'retry_after_seconds' in payload


def test_override_forbidden_for_analyst(client, auth_headers):
    resp = client.post(
        '/override',
        json={
            'application_id': 1,
            'new_decision': 'ONAYLANDI',
            'reason': 'role test',
        },
        headers=auth_headers,
    )
    assert resp.status_code == 403


def test_fraud_stats_allowed_for_admin(client, admin_auth_headers):
    resp = client.get('/api/v2/offers/fraud-stats', headers=admin_auth_headers)
    assert resp.status_code == 200


def test_static_file_access_restricted_for_py_extension(client):
    resp = client.get('/app_v2_secure.py')
    assert resp.status_code == 403

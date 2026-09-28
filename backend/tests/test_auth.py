import pytest

pytestmark = pytest.mark.asyncio


async def _register(client, slug="acme", email="owner@acme.com"):
    return await client.post(
        "/api/auth/register",
        json={
            "organization_name": "Acme Inc",
            "organization_slug": slug,
            "email": email,
            "password": "supersecret123",
            "full_name": "Ada Owner",
        },
    )


async def test_register_creates_owner_and_returns_tokens(client):
    response = await _register(client)
    assert response.status_code == 201
    body = response.json()
    assert "access_token" in body and "refresh_token" in body


async def test_register_duplicate_slug_rejected(client):
    await _register(client, slug="dupe-slug", email="a@dupe.com")
    response = await _register(client, slug="dupe-slug", email="b@dupe.com")
    assert response.status_code == 409


async def test_login_with_wrong_password_rejected(client):
    await _register(client, slug="loginco", email="user@loginco.com")
    response = await client.post(
        "/api/auth/login", json={"email": "user@loginco.com", "password": "wrong-password"}
    )
    assert response.status_code == 401


async def test_login_success_and_me_endpoint(client):
    await _register(client, slug="meco", email="me@meco.com")
    login = await client.post(
        "/api/auth/login", json={"email": "me@meco.com", "password": "supersecret123"}
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "me@meco.com"
    assert "OWNER" in me.json()["roles"]


async def test_unauthenticated_request_rejected(client):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


async def test_refresh_token_issues_new_access_token(client):
    await _register(client, slug="refreshco", email="r@refreshco.com")
    login = await client.post(
        "/api/auth/login", json={"email": "r@refreshco.com", "password": "supersecret123"}
    )
    refresh_token = login.json()["refresh_token"]
    refreshed = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 200
    assert "access_token" in refreshed.json()

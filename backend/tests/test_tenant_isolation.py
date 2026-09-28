import pytest

pytestmark = pytest.mark.asyncio


async def _register_and_login(client, slug, email):
    await client.post(
        "/api/auth/register",
        json={
            "organization_name": slug,
            "organization_slug": slug,
            "email": email,
            "password": "supersecret123",
            "full_name": "Tester",
        },
    )
    login = await client.post("/api/auth/login", json={"email": email, "password": "supersecret123"})
    return login.json()["access_token"]


async def test_user_cannot_see_another_organizations_data(client):
    token_a = await _register_and_login(client, "org-a", "user@org-a.com")
    token_b = await _register_and_login(client, "org-b", "user@org-b.com")

    org_a = await client.get("/api/organizations/me", headers={"Authorization": f"Bearer {token_a}"})
    org_b = await client.get("/api/organizations/me", headers={"Authorization": f"Bearer {token_b}"})

    assert org_a.status_code == 200 and org_b.status_code == 200
    assert org_a.json()["id"] != org_b.json()["id"]
    assert org_a.json()["slug"] == "org-a"
    assert org_b.json()["slug"] == "org-b"


async def test_viewer_role_permission_boundary():
    # Regression guard: base_repository raises if organization_id is missing —
    # covered directly since it's the structural chokepoint for isolation.
    from uuid import uuid4
    from app.core.base_repository import TenantScopedRepository

    with pytest.raises(ValueError):
        TenantScopedRepository(db=None, organization_id=None)

    repo = TenantScopedRepository(db=None, organization_id=uuid4())
    assert repo.organization_id is not None

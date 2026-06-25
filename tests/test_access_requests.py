from app.models.enums import GlobalGrantType


async def test_request_then_approve_grants_global_create(client, user_factory, admin_headers):
    user = await user_factory()

    denied = await client.post(
        "/storages", json={"name": "G", "type": "global"}, headers=user["headers"]
    )
    assert denied.status_code == 403

    req = await client.post("/access-requests", json={}, headers=user["headers"])
    assert req.status_code == 201, req.text
    assert req.json()["status"] == "pending"

    listing = await client.get("/admin/access-requests", headers=admin_headers)
    assert listing.status_code == 200
    items = listing.json()
    assert len(items) == 1
    assert items[0]["user_email"] == user["email"]
    request_id = items[0]["id"]

    approved = await client.post(
        f"/admin/access-requests/{request_id}/approve", headers=admin_headers
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    ok = await client.post(
        "/storages", json={"name": "G", "type": "global"}, headers=user["headers"]
    )
    assert ok.status_code == 201
    assert ok.json()["type"] == "global"


async def test_non_admin_cannot_list_requests(client, user_factory):
    user = await user_factory()
    resp = await client.get("/admin/access-requests", headers=user["headers"])
    assert resp.status_code == 403


async def test_request_conflict_when_already_granted(client, user_factory, grant_global):
    user = await user_factory()
    await grant_global(user["id"], GlobalGrantType.CAN_CREATE_GLOBAL_STORAGE)
    resp = await client.post("/access-requests", json={}, headers=user["headers"])
    assert resp.status_code == 409


async def test_reject_request_keeps_user_without_right(client, user_factory, admin_headers):
    user = await user_factory()

    req = await client.post("/access-requests", json={}, headers=user["headers"])
    request_id = req.json()["id"]

    rejected = await client.post(
        f"/admin/access-requests/{request_id}/reject", headers=admin_headers
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    denied = await client.post(
        "/storages", json={"name": "G", "type": "global"}, headers=user["headers"]
    )
    assert denied.status_code == 403


async def test_me_access_reflects_state(client, user_factory, grant_global):
    user = await user_factory()

    initial = await client.get("/auth/me/access", headers=user["headers"])
    assert initial.json() == {
        "can_create_global_storage": False,
        "can_manage_users": False,
        "pending_request": False,
    }

    await client.post("/access-requests", json={}, headers=user["headers"])
    after_request = await client.get("/auth/me/access", headers=user["headers"])
    assert after_request.json()["pending_request"] is True

    await grant_global(user["id"], GlobalGrantType.CAN_CREATE_GLOBAL_STORAGE)
    after_grant = await client.get("/auth/me/access", headers=user["headers"])
    assert after_grant.json()["can_create_global_storage"] is True


async def test_admin_email_is_recognized_as_manager(client, admin_headers):
    resp = await client.get("/auth/me/access", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["can_manage_users"] is True

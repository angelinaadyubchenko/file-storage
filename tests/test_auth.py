import pytest


async def test_register_creates_user_and_personal_storage(client, user_factory):
    user = await user_factory()

    resp = await client.get("/storages", headers=user["headers"])
    assert resp.status_code == 200
    storages = resp.json()
    personal = [s for s in storages if s["type"] == "personal"]
    assert len(personal) == 1
    assert personal[0]["owner_id"] == user["id"]
    assert personal[0]["policy"]["max_file_size"] > 0
    assert personal[0]["policy"]["allowed_mime_types"] is None


async def test_register_duplicate_email_conflict(client):
    payload = {"email": "dup@example.com", "password": "password123"}
    first = await client.post("/auth/register", json=payload)
    assert first.status_code == 201
    second = await client.post("/auth/register", json=payload)
    assert second.status_code == 409
    assert second.json()["error_code"] == "email_already_registered"


async def test_login_wrong_password_returns_401(client):
    await client.post("/auth/register", json={"email": "a@example.com", "password": "password123"})
    resp = await client.post("/auth/login", json={"email": "a@example.com", "password": "wrong"})
    assert resp.status_code == 401
    assert resp.json()["error_code"] == "invalid_credentials"


async def test_login_unknown_email_returns_401(client):
    resp = await client.post("/auth/login", json={"email": "ghost@example.com", "password": "x"})
    assert resp.status_code == 401

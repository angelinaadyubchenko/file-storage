import pytest


async def test_register_creates_only_account(client):
    email = "fresh@example.com"
    reg = await client.post("/auth/register", json={"email": email, "password": "password123"})
    assert reg.status_code == 201

    login = await client.post("/auth/login", json={"email": email, "password": "password123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = await client.get("/storages", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


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

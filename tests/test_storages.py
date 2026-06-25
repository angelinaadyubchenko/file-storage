from app.models.enums import GlobalGrantType

from tests.helpers import TEXT_CONTENT, upload_files


async def test_create_global_storage_requires_grant(client, user_factory):
    user = await user_factory()
    resp = await client.post(
        "/storages", json={"name": "Shared"}, headers=user["headers"]
    )
    assert resp.status_code == 403
    assert resp.json()["error_code"] == "permission_denied"


async def test_create_global_storage_with_grant(client, user_factory, grant_global):
    user = await user_factory()
    await grant_global(user["id"], GlobalGrantType.CAN_CREATE_GLOBAL_STORAGE)

    resp = await client.post(
        "/storages",
        json={"name": "Shared", "policy": {"max_file_size": 1000, "max_storage_size": 5000}},
        headers=user["headers"],
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["type"] == "global"
    assert body["policy"]["max_file_size"] == 1000


async def test_get_storage_reports_usage(client, user_factory):
    user = await user_factory()
    sid = user["personal_storage_id"]

    up = await client.post(
        f"/storages/{sid}/files",
        files=upload_files("note.txt", TEXT_CONTENT, "text/plain"),
        headers=user["headers"],
    )
    assert up.status_code == 201, up.text

    info = await client.get(f"/storages/{sid}", headers=user["headers"])
    assert info.status_code == 200
    assert info.json()["used_bytes"] == len(TEXT_CONTENT)


async def test_owner_can_update_policy(client, user_factory):
    user = await user_factory()
    sid = user["personal_storage_id"]
    resp = await client.put(
        f"/storages/{sid}/policy",
        json={"max_file_size": 12345},
        headers=user["headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["max_file_size"] == 12345

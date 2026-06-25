from app.models.enums import StorageGrantType

from tests.helpers import TEXT_CONTENT, upload_text_file


async def test_grant_read_lets_other_user_download(client, user_factory):
    owner = await user_factory()
    other = await user_factory()
    sid = owner["personal_storage_id"]
    file_id = await upload_text_file(client, owner, sid)

    denied = await client.get(f"/files/{file_id}/download", headers=other["headers"])
    assert denied.status_code == 403

    grant = await client.post(
        f"/storages/{sid}/access",
        json={"target_user_id": other["id"], "grant_type": StorageGrantType.STORAGE_READ.value},
        headers=owner["headers"],
    )
    assert grant.status_code == 201, grant.text

    allowed = await client.get(f"/files/{file_id}/download", headers=other["headers"])
    assert allowed.status_code == 200
    assert allowed.content == TEXT_CONTENT


async def test_revoke_grant_removes_access(client, user_factory):
    owner = await user_factory()
    other = await user_factory()
    sid = owner["personal_storage_id"]
    file_id = await upload_text_file(client, owner, sid)

    await client.post(
        f"/storages/{sid}/access",
        json={"target_user_id": other["id"], "grant_type": StorageGrantType.STORAGE_READ.value},
        headers=owner["headers"],
    )
    assert (await client.get(f"/files/{file_id}/download", headers=other["headers"])).status_code == 200

    revoke = await client.delete(
        f"/storages/{sid}/access/{other['id']}", headers=owner["headers"]
    )
    assert revoke.status_code == 204

    after = await client.get(f"/files/{file_id}/download", headers=other["headers"])
    assert after.status_code == 403


async def test_non_manager_cannot_grant(client, user_factory):
    owner = await user_factory()
    other = await user_factory()
    sid = owner["personal_storage_id"]

    resp = await client.post(
        f"/storages/{sid}/access",
        json={"target_user_id": owner["id"], "grant_type": StorageGrantType.STORAGE_READ.value},
        headers=other["headers"],
    )
    assert resp.status_code == 403


async def _delegate_management(client, owner, sid, manager):
    resp = await client.post(
        f"/storages/{sid}/access",
        json={"target_user_id": manager["id"], "grant_type": StorageGrantType.STORAGE_MANAGE_ACCESS.value},
        headers=owner["headers"],
    )
    assert resp.status_code == 201, resp.text


async def test_manager_cannot_grant_rights_to_self(client, user_factory):
    owner = await user_factory()
    manager = await user_factory()
    sid = owner["personal_storage_id"]
    await _delegate_management(client, owner, sid, manager)

    resp = await client.post(
        f"/storages/{sid}/access",
        json={"target_user_id": manager["id"], "grant_type": StorageGrantType.STORAGE_WRITE.value},
        headers=manager["headers"],
    )
    assert resp.status_code == 403


async def test_only_owner_can_delegate_manage_access(client, user_factory):
    owner = await user_factory()
    manager = await user_factory()
    outsider = await user_factory()
    sid = owner["personal_storage_id"]
    await _delegate_management(client, owner, sid, manager)

    resp = await client.post(
        f"/storages/{sid}/access",
        json={"target_user_id": outsider["id"], "grant_type": StorageGrantType.STORAGE_MANAGE_ACCESS.value},
        headers=manager["headers"],
    )
    assert resp.status_code == 403


async def test_duplicate_grant_returns_200(client, user_factory):
    owner = await user_factory()
    other = await user_factory()
    sid = owner["personal_storage_id"]
    payload = {"target_user_id": other["id"], "grant_type": StorageGrantType.STORAGE_READ.value}

    first = await client.post(f"/storages/{sid}/access", json=payload, headers=owner["headers"])
    assert first.status_code == 201
    again = await client.post(f"/storages/{sid}/access", json=payload, headers=owner["headers"])
    assert again.status_code == 200

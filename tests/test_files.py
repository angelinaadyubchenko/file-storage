import os

from app.core.config import settings

from tests.helpers import PNG_1X1, TEXT_CONTENT, upload_files


def _storage_dir(storage_id: str) -> str:
    return os.path.join(settings.STORAGE_ROOT_PATH, storage_id)


async def test_upload_and_download_roundtrip(client, user_factory):
    user = await user_factory()
    sid = user["personal_storage_id"]

    up = await client.post(
        f"/storages/{sid}/files",
        files=upload_files("файл.txt", TEXT_CONTENT, "text/plain"),
        headers=user["headers"],
    )
    assert up.status_code == 201, up.text
    file_id = up.json()["id"]

    down = await client.get(f"/files/{file_id}/download", headers=user["headers"])
    assert down.status_code == 200
    assert down.content == TEXT_CONTENT
    assert "filename*=UTF-8''" in down.headers["content-disposition"]


async def test_upload_exceeding_max_file_size_returns_413_and_leaves_no_file(client, user_factory):
    user = await user_factory()
    sid = user["personal_storage_id"]

    await client.put(
        f"/storages/{sid}/policy", json={"max_file_size": 10}, headers=user["headers"]
    )
    big = b"x" * 100
    up = await client.post(
        f"/storages/{sid}/files",
        files=upload_files("big.txt", big, "text/plain"),
        headers=user["headers"],
    )
    assert up.status_code == 413
    assert up.json()["error_code"] == "file_too_large"

    sdir = _storage_dir(sid)
    assert (not os.path.isdir(sdir)) or len(os.listdir(sdir)) == 0


async def test_upload_disallowed_mime_returns_415(client, user_factory):
    user = await user_factory()
    sid = user["personal_storage_id"]

    await client.put(
        f"/storages/{sid}/policy",
        json={"allowed_mime_types": ["text/plain"]},
        headers=user["headers"],
    )
    up = await client.post(
        f"/storages/{sid}/files",
        files=upload_files("image.txt", PNG_1X1, "text/plain"),
        headers=user["headers"],
    )
    assert up.status_code == 415
    assert up.json()["error_code"] == "invalid_file_type"


async def test_storage_quota_exceeded_on_later_file(client, user_factory):
    user = await user_factory()
    sid = user["personal_storage_id"]

    await client.put(
        f"/storages/{sid}/policy",
        json={"max_file_size": 40, "max_storage_size": 50},
        headers=user["headers"],
    )
    blob = b"a" * 40

    first = await client.post(
        f"/storages/{sid}/files",
        files=upload_files("a.txt", blob, "text/plain"),
        headers=user["headers"],
    )
    assert first.status_code == 201

    second = await client.post(
        f"/storages/{sid}/files",
        files=upload_files("b.txt", blob, "text/plain"),
        headers=user["headers"],
    )
    assert second.status_code == 413
    assert second.json()["error_code"] == "storage_quota_exceeded"


async def test_other_user_cannot_download_without_grant(client, user_factory):
    owner = await user_factory()
    other = await user_factory()
    sid = owner["personal_storage_id"]

    up = await client.post(
        f"/storages/{sid}/files",
        files=upload_files("note.txt", TEXT_CONTENT, "text/plain"),
        headers=owner["headers"],
    )
    file_id = up.json()["id"]

    down = await client.get(f"/files/{file_id}/download", headers=other["headers"])
    assert down.status_code == 403


async def test_soft_delete_blocks_download(client, user_factory):
    user = await user_factory()
    sid = user["personal_storage_id"]

    up = await client.post(
        f"/storages/{sid}/files",
        files=upload_files("note.txt", TEXT_CONTENT, "text/plain"),
        headers=user["headers"],
    )
    file_id = up.json()["id"]

    delete = await client.delete(f"/files/{file_id}", headers=user["headers"])
    assert delete.status_code == 204

    down = await client.get(f"/files/{file_id}/download", headers=user["headers"])
    assert down.status_code == 404
    assert down.json()["error_code"] == "file_not_found"

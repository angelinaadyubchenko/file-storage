from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models.share_token import FileShareToken

from tests.helpers import TEXT_CONTENT, upload_text_file


async def test_public_download_via_share_token(client, user_factory):
    user = await user_factory()
    file_id = await upload_text_file(client, user, user["personal_storage_id"])

    share = await client.post(
        f"/files/{file_id}/share", json={"expires_in_hours": 24}, headers=user["headers"]
    )
    assert share.status_code == 201, share.text
    token = share.json()["token"]

    resp = await client.get(f"/shared/{token}")
    assert resp.status_code == 200
    assert resp.content == TEXT_CONTENT


async def test_expired_token_returns_404(client, user_factory, db_session):
    user = await user_factory()
    file_id = await upload_text_file(client, user, user["personal_storage_id"])

    share = await client.post(
        f"/files/{file_id}/share", json={"expires_in_hours": 1}, headers=user["headers"]
    )
    token = share.json()["token"]

    row = (
        await db_session.execute(select(FileShareToken).where(FileShareToken.token == token))
    ).scalar_one()
    row.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    await db_session.commit()

    resp = await client.get(f"/shared/{token}")
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "share_token_invalid"


async def test_token_over_max_downloads_returns_404(client, user_factory):
    user = await user_factory()
    file_id = await upload_text_file(client, user, user["personal_storage_id"])

    share = await client.post(
        f"/files/{file_id}/share",
        json={"expires_in_hours": 24, "max_downloads": 1},
        headers=user["headers"],
    )
    token = share.json()["token"]

    first = await client.get(f"/shared/{token}")
    assert first.status_code == 200

    second = await client.get(f"/shared/{token}")
    assert second.status_code == 404


async def test_manual_revoke_blocks_token(client, user_factory):
    user = await user_factory()
    file_id = await upload_text_file(client, user, user["personal_storage_id"])

    share = await client.post(
        f"/files/{file_id}/share", json={"expires_in_hours": 24}, headers=user["headers"]
    )
    token = share.json()["token"]

    revoke = await client.delete(f"/files/{file_id}/share/{token}", headers=user["headers"])
    assert revoke.status_code == 204

    resp = await client.get(f"/shared/{token}")
    assert resp.status_code == 404

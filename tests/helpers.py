import base64

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)

TEXT_CONTENT = b"hello world, this is a plain text file.\n"


def upload_files(filename: str, content: bytes, content_type: str) -> dict:
    return {"file": (filename, content, content_type)}


async def upload_text_file(client, user: dict, storage_id: str, filename: str = "note.txt") -> str:
    resp = await client.post(
        f"/storages/{storage_id}/files",
        files=upload_files(filename, TEXT_CONTENT, "text/plain"),
        headers=user["headers"],
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]

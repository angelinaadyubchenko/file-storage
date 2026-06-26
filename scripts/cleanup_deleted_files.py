import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import settings
from app.core.logging_config import configure_logging, get_audit_logger
from app.db.session import async_session_maker
from app.models.file import File
from app.services.file_service import absolute_path_for


async def cleanup_deleted_files(retention_days: int | None = None) -> int:
    days = retention_days if retention_days is not None else settings.CLEANUP_RETENTION_DAYS
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    audit = get_audit_logger()
    purged = 0

    async with async_session_maker() as db:
        result = await db.execute(
            select(File).where(File.deleted_at.is_not(None), File.deleted_at < cutoff)
        )
        files = list(result.scalars().all())

        for file_row in files:
            path = absolute_path_for(file_row)
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:
                audit.warning("cleanup_failed file_id=%s path=%s err=%s", file_row.id, path, exc)
                continue
            await db.delete(file_row)
            purged += 1
            audit.info("file_purged file_id=%s path=%s", file_row.id, path)

        await db.commit()

    audit.info("cleanup_deleted_files done purged=%s cutoff=%s", purged, cutoff.isoformat())
    return purged


if __name__ == "__main__":
    configure_logging()
    count = asyncio.run(cleanup_deleted_files())
    print(f"Purged {count} files.")

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import access, admin, auth, files, requests, shared, storages
from app.core.logging_config import configure_logging
from app.exceptions import register_exception_handlers

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
FRONTEND_INDEX = FRONTEND_DIR / "index.html"


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title="File Storage Service",
        description="File storage backend with flexible, grant-based access control.",
        version="1.0.0",
    )

    register_exception_handlers(app)

    app.include_router(auth.router)
    app.include_router(storages.router)
    app.include_router(access.router)
    app.include_router(files.router)
    app.include_router(shared.router)
    app.include_router(admin.router)
    app.include_router(requests.router)

    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(FRONTEND_INDEX)

    return app


app = create_app()

import os
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

_TEST_STORAGE_DIR = Path(os.environ.get("TEST_STORAGE_DIR", "/tmp/filestorage_test_storage"))
_TEST_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
os.environ["STORAGE_ROOT_PATH"] = str(_TEST_STORAGE_DIR)

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/filestorage_test",
)

from app.core.config import settings  # noqa: E402
settings.STORAGE_ROOT_PATH = str(_TEST_STORAGE_DIR)

from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
import app.models  # noqa: E402,F401  (register all tables on Base.metadata)
from app.main import app  # noqa: E402
from app.models.enums import GlobalGrantType  # noqa: E402
from app.services import grant_service  # noqa: E402

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def _prepare_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client():

    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
def user_factory(client):
    counter = {"n": 0}

    async def make_user(password: str = "password123") -> dict:
        counter["n"] += 1
        email = f"user{counter['n']}_{uuid.uuid4().hex[:8]}@example.com"

        reg = await client.post("/auth/register", json={"email": email, "password": password})
        assert reg.status_code == 201, reg.text
        user_id = reg.json()["id"]

        login = await client.post("/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        created = await client.post(
            "/storages",
            json={"name": "Personal", "type": "personal"},
            headers=headers,
        )
        assert created.status_code == 201, created.text

        return {
            "id": user_id,
            "email": email,
            "password": password,
            "headers": headers,
            "personal_storage_id": created.json()["id"],
        }

    return make_user


@pytest_asyncio.fixture
async def admin_headers(client):
    await client.post(
        "/auth/register", json={"email": settings.ADMIN_EMAIL, "password": "password123"}
    )
    login = await client.post(
        "/auth/login", json={"email": settings.ADMIN_EMAIL, "password": "password123"}
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest_asyncio.fixture
async def grant_global():

    async def _grant(user_id: str, grant_type: GlobalGrantType):
        async with TestSessionLocal() as session:
            await grant_service.grant_global_access(
                session, user_id=uuid.UUID(user_id), grant_type=grant_type
            )

    return _grant

import pytest
import pytest_asyncio
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from fastapi import FastAPI, Depends

from app.db.models import Base, Organization, User
from app.db.session import get_db
from app.api.routes.auth import router as auth_router
from app.core.dependencies import get_current_admin

# Fix UUID for SQLite compilation
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import UUID

@compiles(UUID, 'sqlite')
def compile_uuid(type_, compiler, **kw):
    return "VARCHAR"

# Create test app
app = FastAPI()
app.include_router(auth_router)

@app.get("/admin/users")
async def admin_users(admin: User = Depends(get_current_admin)):
    return [{"status": "success"}]

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestingSessionLocal() as session:
        org = Organization(id=uuid.uuid4(), name="Test Org")
        session.add(org)
        await session.commit()
    
    yield
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

@pytest_asyncio.fixture
async def db_session():
    async with TestingSessionLocal() as session:
        yield session

@pytest_asyncio.fixture
async def test_org_id(db_session):
    from sqlalchemy.future import select
    result = await db_session.execute(select(Organization).limit(1))
    org = result.scalars().first()
    return str(org.id)

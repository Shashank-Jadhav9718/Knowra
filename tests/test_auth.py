import pytest
from httpx import AsyncClient

# Enable asyncio for all tests in this file
pytestmark = pytest.mark.asyncio

async def test_register_success(async_client: AsyncClient, test_org_id: str):
    response = await async_client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "password123",
            "organization_id": test_org_id
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    # Depending on pydantic version enum might be returned as value or enum name
    assert data["role"] in ("user", "UserRole.user")

async def test_register_duplicate_email(async_client: AsyncClient, test_org_id: str):
    # Register the user first
    await async_client.post(
        "/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "password123",
            "organization_id": test_org_id
        }
    )
    
    # Try to register again
    response = await async_client.post(
        "/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "password123",
            "organization_id": test_org_id
        }
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

async def test_login_success(async_client: AsyncClient, test_org_id: str):
    # Register first
    await async_client.post(
        "/auth/register",
        json={
            "email": "login@example.com",
            "password": "password123",
            "organization_id": test_org_id
        }
    )
    
    # Login
    response = await async_client.post(
        "/auth/login",
        data={
            "username": "login@example.com",
            "password": "password123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

async def test_login_wrong_password(async_client: AsyncClient, test_org_id: str):
    # Register first
    await async_client.post(
        "/auth/register",
        json={
            "email": "wrong@example.com",
            "password": "password123",
            "organization_id": test_org_id
        }
    )
    
    # Login with wrong password
    response = await async_client.post(
        "/auth/login",
        data={
            "username": "wrong@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"

async def test_protected_route_without_token(async_client: AsyncClient):
    response = await async_client.get("/admin/users")
    assert response.status_code == 401

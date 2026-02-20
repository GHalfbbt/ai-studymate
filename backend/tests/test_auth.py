"""
Phase 1 — Authentication validation tests.

Tests cover:
- User registration (valid, short password, duplicate email)
- User login (success, wrong password, wrong email)
- JWT token validation (/me endpoint)
- Password minimum length enforcement
"""

import pytest
from fastapi.testclient import TestClient


class TestRegistration:
    """Test user registration endpoint."""

    def test_register_valid_user(self, client: TestClient):
        """Valid registration should return 201 with user data."""
        response = client.post("/api/v1/auth/register", json={
            "email": "newuser@test.com",
            "password": "ValidPass123!",
            "full_name": "New User",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@test.com"
        assert data["full_name"] == "New User"
        assert "id" in data
        assert "hashed_password" not in data  # Password must not leak

    def test_register_short_password(self, client: TestClient):
        """Password shorter than 8 chars should return 422."""
        response = client.post("/api/v1/auth/register", json={
            "email": "short@test.com",
            "password": "abc",  # Too short
            "full_name": "Short Pass",
        })
        assert response.status_code == 422
        # Pydantic validation error for min_length
        detail = response.json()["detail"]
        assert any("password" in str(err).lower() for err in detail)

    def test_register_exactly_8_chars_password(self, client: TestClient):
        """Password with exactly 8 chars should succeed."""
        response = client.post("/api/v1/auth/register", json={
            "email": "exact8@test.com",
            "password": "12345678",
            "full_name": "Exact Eight",
        })
        assert response.status_code == 201

    def test_register_duplicate_email(self, client: TestClient, test_user):
        """Registering with an existing email should return 400."""
        from tests.conftest import TEST_USER_EMAIL
        response = client.post("/api/v1/auth/register", json={
            "email": TEST_USER_EMAIL,
            "password": "AnotherPass123!",
            "full_name": "Duplicate User",
        })
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_invalid_email_format(self, client: TestClient):
        """Invalid email format should return 422."""
        response = client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "password": "ValidPass123!",
            "full_name": "Bad Email",
        })
        assert response.status_code == 422

    def test_register_missing_email(self, client: TestClient):
        """Missing email field should return 422."""
        response = client.post("/api/v1/auth/register", json={
            "password": "ValidPass123!",
            "full_name": "No Email",
        })
        assert response.status_code == 422

    def test_register_creates_default_workspace(self, client: TestClient, db):
        """Registration should create a default workspace for the user."""
        from uuid import UUID as PyUUID
        from app.models.workspace import Workspace

        response = client.post("/api/v1/auth/register", json={
            "email": "workspace@test.com",
            "password": "ValidPass123!",
            "full_name": "Workspace User",
        })
        assert response.status_code == 201
        user_id = PyUUID(response.json()["id"])

        # Verify workspace was created (use native UUID for SQLite compat)
        workspaces = db.query(Workspace).filter(
            Workspace.user_id == user_id
        ).all()
        assert len(workspaces) == 1
        assert workspaces[0].name == "My Workspace"


class TestLogin:
    """Test user login endpoints."""

    def test_login_success_json(self, client: TestClient, test_user):
        """Valid credentials via JSON should return access token."""
        from tests.conftest import TEST_USER_EMAIL, TEST_USER_PASSWORD
        response = client.post("/api/v1/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 20  # JWT should be substantial

    def test_login_wrong_password(self, client: TestClient, test_user):
        """Wrong password should return 401."""
        from tests.conftest import TEST_USER_EMAIL
        response = client.post("/api/v1/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": "WrongPassword!",
        })
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_login_nonexistent_email(self, client: TestClient):
        """Non-existent email should return 401."""
        response = client.post("/api/v1/auth/login", json={
            "email": "nobody@test.com",
            "password": "SomePassword123!",
        })
        assert response.status_code == 401

    def test_login_oauth2_form(self, client: TestClient, test_user):
        """OAuth2 form login (Swagger) should work with username=email."""
        from tests.conftest import TEST_USER_EMAIL, TEST_USER_PASSWORD
        response = client.post("/api/v1/auth/token", data={
            "username": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data


class TestAuthenticatedEndpoints:
    """Test JWT-protected endpoints."""

    def test_get_me_authenticated(self, client: TestClient, auth_headers, test_user):
        """Authenticated /me should return user profile."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["full_name"] == test_user.full_name

    def test_get_me_no_token(self, client: TestClient):
        """Unauthenticated /me should return 401."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_get_me_invalid_token(self, client: TestClient):
        """Invalid token should return 401."""
        response = client.get("/api/v1/auth/me", headers={
            "Authorization": "Bearer invalid.token.here"
        })
        assert response.status_code == 401

    def test_get_me_expired_token(self, client: TestClient, test_user):
        """Expired token should return 401."""
        from datetime import timedelta
        from app.core.security import create_access_token

        expired_token = create_access_token(
            subject=str(test_user.id),
            expires_delta=timedelta(seconds=-1),  # Already expired
        )
        response = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {expired_token}"
        })
        assert response.status_code == 401

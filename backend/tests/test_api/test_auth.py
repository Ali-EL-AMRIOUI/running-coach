"""
tests/test_api/test_auth.py
API tests for api/auth.py — register and login.
"""


class TestRegister:

    def test_register_returns_token_and_user(self, client):
        response = client.post(
            "/auth/register",
            json={"email": "new@example.com", "password": "securepass123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "new@example.com"
        assert data["user"]["subscription_status"] == "free"

    def test_register_duplicate_email_fails(self, client, registered_user):
        response = client.post(
            "/auth/register",
            json={"email": registered_user["email"], "password": "anotherpass"},
        )
        assert response.status_code == 400

    def test_register_invalid_email_fails(self, client):
        response = client.post(
            "/auth/register",
            json={"email": "not-an-email", "password": "securepass123"},
        )
        assert response.status_code == 422


class TestLogin:

    def test_login_with_correct_credentials_succeeds(self, client, registered_user):
        response = client.post(
            "/auth/login",
            json={"email": registered_user["email"], "password": registered_user["password"]},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_with_wrong_password_fails(self, client, registered_user):
        response = client.post(
            "/auth/login",
            json={"email": registered_user["email"], "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_login_with_unknown_email_fails(self, client):
        response = client.post(
            "/auth/login",
            json={"email": "nobody@example.com", "password": "whatever123"},
        )
        assert response.status_code == 401

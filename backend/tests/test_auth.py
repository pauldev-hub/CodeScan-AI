from unittest.mock import patch

import pytest

from app import create_app, db
from app.models.user import User


@pytest.fixture()
def app_instance():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app_instance):
    return app_instance.test_client()


def _create_user(app_instance, email="test@example.com", password="Password123", username="tester"):
    with app_instance.app_context():
        user = User(email=email, username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user.id


@patch("app.routes.auth.enforce_rate_limit", return_value=True)
def test_register_success(mock_rate_limit, client):
    del mock_rate_limit
    response = client.post(
        "/api/auth/register",
        json={
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "Password123",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["user"]["email"] == "newuser@example.com"
    assert payload["access_token"]
    assert payload["refresh_token"]


@patch("app.routes.auth.enforce_rate_limit", return_value=True)
def test_register_invalid_email(mock_rate_limit, client):
    del mock_rate_limit
    response = client.post(
        "/api/auth/register",
        json={
            "email": "not-an-email",
            "username": "broken",
            "password": "Password123",
        },
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["status"] == "validation_error"


@patch("app.routes.auth.enforce_rate_limit", return_value=True)
def test_login_success(mock_rate_limit, app_instance, client):
    del mock_rate_limit
    _create_user(app_instance, email="login@example.com", password="Password123")

    response = client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "Password123"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["user"]["email"] == "login@example.com"
    assert payload["access_token"]
    assert payload["refresh_token"]


@patch("app.routes.auth.enforce_rate_limit", return_value=True)
def test_login_invalid_password(mock_rate_limit, app_instance, client):
    del mock_rate_limit
    _create_user(app_instance, email="wrongpass@example.com", password="Password123")

    response = client.post(
        "/api/auth/login",
        json={"email": "wrongpass@example.com", "password": "Wrong999"},
    )

    assert response.status_code == 401
    payload = response.get_json()
    assert payload["status"] == "unauthorized"


@patch("app.routes.auth.enforce_rate_limit", return_value=True)
def test_refresh_token_revoked_after_logout(mock_rate_limit, app_instance, client):
    del mock_rate_limit
    _create_user(app_instance, email="logout@example.com", password="Password123")

    login_response = client.post(
        "/api/auth/login",
        json={"email": "logout@example.com", "password": "Password123"},
    )
    refresh_token = login_response.get_json()["refresh_token"]

    logout_response = client.post("/api/auth/logout", json={"refresh_token": refresh_token})
    assert logout_response.status_code == 200

    refresh_response = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 401
    payload = refresh_response.get_json()
    assert payload["status"] == "unauthorized"

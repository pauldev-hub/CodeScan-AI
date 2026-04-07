from unittest.mock import patch


def test_refresh_token_rotation_revokes_old_token(client, create_user):
    create_user(email="rotate@example.com")

    with patch("app.routes.auth.enforce_rate_limit", return_value=True):
        login_response = client.post(
            "/api/auth/login",
            json={"email": "rotate@example.com", "password": "Password123"},
        )

    assert login_response.status_code == 200
    login_payload = login_response.get_json()
    old_refresh = login_payload["refresh_token"]

    first_refresh = client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert first_refresh.status_code == 200
    new_refresh = first_refresh.get_json()["refresh_token"]

    second_with_old = client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert second_with_old.status_code == 401

    second_with_new = client.post("/api/auth/refresh", json={"refresh_token": new_refresh})
    assert second_with_new.status_code == 200

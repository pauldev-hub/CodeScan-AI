import json

from app.models.user import User


def test_get_settings_returns_defaults(client, auth_headers):
    headers, _user = auth_headers(email="settings-get@example.com")
    response = client.get("/api/settings", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["preferences"]["persona"] == "student"
    assert payload["profile"]["email"] == "settings-get@example.com"


def test_update_settings_persists_preferences(client, auth_headers):
    headers, user_id = auth_headers(email="settings-update@example.com")
    response = client.put(
        "/api/settings",
        json={
            "profile": {"username": "operator"},
            "preferences": {"persona": "security engineer", "roast_mode": True},
        },
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["profile"]["username"] == "operator"
    assert payload["preferences"]["persona"] == "security engineer"
    assert payload["preferences"]["roast_mode"] is True

    from app import db

    user = db.session.get(User, user_id)
    stored = json.loads(user.settings)
    assert stored["persona"] == "security engineer"


def test_update_settings_persists_extended_profile_fields(client, auth_headers):
    headers, user_id = auth_headers(email="settings-profile@example.com")
    response = client.put(
        "/api/settings",
        json={
            "profile": {
                "username": "operator-two",
                "name": "Pratyush",
                "age": 24,
                "about_me": "Builder of secure developer tools",
            },
            "preferences": {"theme": "light"},
        },
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["profile"]["name"] == "Pratyush"
    assert payload["profile"]["age"] == 24
    assert payload["profile"]["about_me"] == "Builder of secure developer tools"
    assert payload["preferences"]["theme"] == "dark"

    from app import db

    user = db.session.get(User, user_id)
    assert user.name == "Pratyush"
    assert user.age == 24
    assert user.about_me == "Builder of secure developer tools"

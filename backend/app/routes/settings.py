import json

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app import db
from app.models.user import User
from app.utils.responses import error_response, success_response


settings_bp = Blueprint("settings", __name__, url_prefix="/api/settings")


def _default_settings(user):
    try:
        stored = json.loads(user.settings) if user.settings else {}
    except (TypeError, ValueError):
        stored = {}

    return {
        "profile": {
            "email": user.email,
            "username": user.username or "",
            "name": user.name or "",
            "age": user.age,
            "about_me": user.about_me or "",
            "plan": user.plan,
        },
        "preferences": {
            "theme": "dark",
            "beginner_mode": bool(stored.get("beginner_mode", True)),
            "persona": stored.get("persona", "student"),
            "explanation_depth": stored.get("explanation_depth", "Beginner"),
            "roast_mode": bool(stored.get("roast_mode", False)),
        },
    }


@settings_bp.get("")
@jwt_required()
def get_settings():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return error_response("User not found", "not_found", 404)
    return success_response(_default_settings(user))


@settings_bp.put("")
@jwt_required()
def update_settings():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return error_response("User not found", "not_found", 404)

    payload = request.get_json(silent=True) or {}
    profile = payload.get("profile") or {}
    preferences = payload.get("preferences") or {}

    username = str(profile.get("username") or "").strip()
    if username:
        user.username = username
    user.name = str(profile.get("name") or "").strip() or None
    user.about_me = str(profile.get("about_me") or "").strip() or None

    raw_age = profile.get("age")
    if raw_age in (None, "", False):
        user.age = None
    else:
        try:
            age = int(raw_age)
        except (TypeError, ValueError):
            return error_response("age must be an integer", "validation_error", 400)
        if age < 0 or age > 120:
            return error_response("age must be between 0 and 120", "validation_error", 400)
        user.age = age

    current = _default_settings(user)["preferences"]
    current.update({key: value for key, value in preferences.items() if key != "theme"})
    current["theme"] = "dark"
    user.settings = json.dumps(current)
    db.session.commit()

    return success_response(_default_settings(user))

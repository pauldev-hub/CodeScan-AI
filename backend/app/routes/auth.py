from flask import Blueprint, request

from app import db
from app.models.user import User
from app.services.auth_service import AuthService
from app.utils.constants import (
    RATE_LIMIT_AUTH_MAX_REQUESTS,
    RATE_LIMIT_AUTH_WINDOW_SECONDS,
)
from app.utils.responses import error_response, success_response
from app.utils.security import enforce_rate_limit
from app.utils.validators import is_valid_email, is_valid_password


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/register")
def register():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    username = (payload.get("username") or "").strip() or None
    password = payload.get("password") or ""

    if not enforce_rate_limit(
        f"auth:register:{request.remote_addr}",
        RATE_LIMIT_AUTH_MAX_REQUESTS,
        RATE_LIMIT_AUTH_WINDOW_SECONDS,
    ):
        return error_response("Too many requests", "rate_limited", 429)

    if not is_valid_email(email):
        return error_response("Invalid email", "validation_error", 400)
    if not is_valid_password(password):
        return error_response(
            "Password must be at least 8 chars and include letters and numbers",
            "validation_error",
            400,
        )

    created = AuthService.register_user(email, username, password)
    if not created:
        return error_response("Email already registered", "conflict", 409)

    return success_response(
        {
            "user": AuthService.user_payload(created["user"]),
            "access_token": created["access_token"],
            "refresh_token": created["refresh_token"],
        },
        201,
    )


@auth_bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    if not enforce_rate_limit(
        f"auth:login:{request.remote_addr}",
        RATE_LIMIT_AUTH_MAX_REQUESTS,
        RATE_LIMIT_AUTH_WINDOW_SECONDS,
    ):
        return error_response("Too many requests", "rate_limited", 429)

    data, error_type = AuthService.login_user(email, password)
    if error_type == "not_found":
        return error_response("User not found", "not_found", 404)
    if error_type == "unauthorized":
        return error_response("Invalid credentials", "unauthorized", 401)

    return success_response(
        {
            "user": AuthService.user_payload(data["user"]),
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
        }
    )


@auth_bp.post("/refresh")
def refresh():
    payload = request.get_json(silent=True) or {}
    refresh_token = payload.get("refresh_token")
    if not refresh_token:
        return error_response("refresh_token is required", "validation_error", 400)

    try:
        refreshed = AuthService.refresh_tokens(refresh_token)
    except Exception:
        return error_response("Invalid or expired refresh token", "unauthorized", 401)

    decoded = refreshed["decoded"]

    user = db.session.get(User, int(decoded.get("sub")))
    if not user or not user.is_active:
        return error_response("User not found", "not_found", 404)

    return success_response(
        {
            "access_token": refreshed["access_token"],
            "refresh_token": refreshed["refresh_token"],
        }
    )


@auth_bp.post("/logout")
def logout():
    payload = request.get_json(silent=True) or {}
    refresh_token = payload.get("refresh_token")
    if not refresh_token:
        return error_response("refresh_token is required", "validation_error", 400)

    try:
        AuthService.logout_refresh_token(refresh_token)
    except Exception:
        return error_response("Invalid or expired refresh token", "unauthorized", 401)

    return success_response({"message": "Logged out successfully"}, 200)

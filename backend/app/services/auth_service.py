from datetime import datetime, timezone
import secrets

from flask_jwt_extended import create_access_token, create_refresh_token, decode_token

from app import db
from app.models.user import User
from app.utils.security import blacklist_refresh_token, is_token_blacklisted, mark_session_revoked


class AuthService:
    @staticmethod
    def register_user(email, username, password):
        existing = User.query.filter_by(email=email).first()
        if existing:
            return None

        user = User(email=email, username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))

        return {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    @staticmethod
    def login_user(email, password):
        user = User.query.filter_by(email=email).first()
        if not user:
            return None, "not_found"
        if not user.check_password(password):
            return None, "unauthorized"

        user.last_login_at = datetime.now(timezone.utc)
        db.session.commit()

        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))

        return {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }, None

    @staticmethod
    def login_guest_user():
        guest_email = "guest@codescan.local"
        guest_user = User.query.filter_by(email=guest_email).first()

        if not guest_user:
            guest_user = User(email=guest_email, username="Guest", plan="free")
            guest_user.set_password(secrets.token_urlsafe(24))
            db.session.add(guest_user)

        guest_user.last_login_at = datetime.now(timezone.utc)
        db.session.commit()

        access_token = create_access_token(identity=str(guest_user.id))
        refresh_token = create_refresh_token(identity=str(guest_user.id))

        return {
            "user": guest_user,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    @staticmethod
    def refresh_tokens(refresh_token):
        decoded = decode_token(refresh_token)
        if decoded.get("type") != "refresh":
            raise ValueError("Provided token is not a refresh token")

        jti = decoded.get("jti")
        user_id = decoded.get("sub")
        exp = decoded.get("exp")
        if not jti or not user_id or not exp:
            raise ValueError("Refresh token missing claims")
        if is_token_blacklisted(jti):
            raise ValueError("Refresh token has been revoked")

        blacklist_refresh_token(jti, exp)

        return {
            "access_token": create_access_token(identity=user_id),
            "refresh_token": create_refresh_token(identity=user_id),
            "decoded": decoded,
        }

    @staticmethod
    def logout_refresh_token(refresh_token):
        decoded = decode_token(refresh_token)
        if decoded.get("type") != "refresh":
            raise ValueError("Provided token is not a refresh token")

        jti = decoded.get("jti")
        user_id = decoded.get("sub")
        exp = decoded.get("exp")
        if not jti or not user_id or not exp:
            raise ValueError("Refresh token missing claims")

        blacklist_refresh_token(jti, exp)
        mark_session_revoked(user_id, jti, exp)

    @staticmethod
    def user_payload(user):
        payload = user.to_dict()
        payload["created_at"] = payload.get("created_at")
        return payload

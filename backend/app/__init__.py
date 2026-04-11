import sqlite3

from celery import Celery, Task
from flask import Flask, jsonify
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import OperationalError
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.utils.security import is_token_blacklisted


db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()
migrate = Migrate()
socketio = SocketIO()
celery_app = Celery(__name__)


class FlaskTask(Task):
    flask_app = None

    def __call__(self, *args, **kwargs):
        if self.flask_app is None:
            return self.run(*args, **kwargs)
        with self.flask_app.app_context():
            return self.run(*args, **kwargs)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    del connection_record
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def register_extensions(app):
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db, compare_type=True)
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})
    socketio.init_app(
        app,
        cors_allowed_origins=app.config["CORS_ORIGINS"],
        message_queue=app.config.get("REDIS_URL"),
    )


def celery_init_app(app):
    FlaskTask.flask_app = app
    celery = Celery(app.name, task_cls=FlaskTask)
    celery.conf.update(
        broker_url=app.config.get("CELERY_BROKER_URL"),
        result_backend=app.config.get("CELERY_RESULT_BACKEND"),
        task_ignore_result=False,
        task_always_eager=app.config.get("CELERY_TASK_ALWAYS_EAGER", False),
        task_store_eager_result=app.config.get("CELERY_TASK_STORE_EAGER_RESULT", False),
        broker_connection_retry_on_startup=True,
        worker_pool=app.config.get("CELERY_WORKER_POOL"),
    )
    celery.set_default()
    app.extensions["celery"] = celery
    return celery


def register_error_handlers(app):
    @app.errorhandler(OperationalError)
    def database_operational_error(error):
        message = str(getattr(error, "orig", error) or "").lower()
        if "no such column" in message or "no such table" in message:
            app.logger.exception("Database schema mismatch detected")
            return (
                jsonify(
                    {
                        "error": "Database migration required",
                        "status": "migration_required",
                        "message": "The database schema is behind the current app version. Run the latest migrations and retry.",
                    }
                ),
                500,
            )
        raise error

    @app.errorhandler(404)
    def not_found(error):
        del error
        return jsonify({"error": "Route not found", "status": "not_found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        del error
        return jsonify({"error": "Method not allowed", "status": "method_not_allowed"}), 405

    @app.errorhandler(500)
    def internal_error(error):
        del error
        return jsonify({"error": "Internal server error", "status": "internal_error"}), 500


def register_routes(app):
    from app.routes import ALL_BLUEPRINTS

    @app.get("/")
    def health_check():
        return jsonify({"status": "ok", "message": "CodeScan AI backend is running"}), 200

    @app.get("/health")
    def ready_check():
        from app.services.ai_provider import get_ai_provider_service
        from app.utils.security import get_redis_client

        redis_client = get_redis_client()
        redis_ok = False
        if redis_client:
            try:
                redis_ok = bool(redis_client.ping())
            except Exception:
                redis_ok = False

        provider_service = get_ai_provider_service()
        provider_status = provider_service.provider_status()
        queue_mode = "celery" if redis_ok else "inline_background"
        return (
            jsonify(
                {
                    "status": "ok",
                    "redis": {"configured": redis_client is not None, "healthy": redis_ok},
                    "celery": {
                        "broker_url": app.config.get("CELERY_BROKER_URL"),
                        "result_backend": app.config.get("CELERY_RESULT_BACKEND"),
                        "worker_pool": app.config.get("CELERY_WORKER_POOL"),
                        "queue_mode": queue_mode,
                    },
                    "ai_providers": provider_status,
                }
            ),
            200,
        )

    for blueprint in ALL_BLUEPRINTS:
        app.register_blueprint(blueprint)


def create_app(config_name=None):
    app = Flask(__name__)

    from app.config import get_config

    app.config.from_object(get_config(config_name))

    register_extensions(app)

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(_jwt_header, jwt_payload):
        return is_token_blacklisted(jwt_payload.get("jti"))

    register_error_handlers(app)
    register_routes(app)

    from app.sockets import register_socket_handlers

    register_socket_handlers(socketio)

    global celery_app
    celery_app = celery_init_app(app)

    # Import models so SQLAlchemy metadata is available for migrations.
    with app.app_context():
        from app.models import chat, report, scan, user
        from app.tasks import scan_tasks

        del chat, report, scan, user, scan_tasks

    return app

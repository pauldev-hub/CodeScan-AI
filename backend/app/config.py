import os
from datetime import timedelta

from dotenv import load_dotenv


BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(BACKEND_ROOT, ".env"))


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name, default):
    value = os.getenv(name)
    raw = value if value is not None else default
    return [item.strip() for item in str(raw).split(",") if item.strip()]


def _default_cors_origins():
    frontend_url = os.getenv("FRONTEND_URL")
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]
    if frontend_url:
        origins.insert(0, frontend_url)
    # Keep original order while removing duplicates.
    return list(dict.fromkeys(origins))


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///codescan.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)

    BCRYPT_LOG_ROUNDS = int(os.getenv("BCRYPT_LOG_ROUNDS", "12"))

    CORS_ORIGINS = _env_list("CORS_ORIGINS", ",".join(_default_cors_origins()))

    REDIS_URL = os.getenv("REDIS_URL")
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL or "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL or "redis://localhost:6379/1")
    CELERY_TASK_ALWAYS_EAGER = _env_bool("CELERY_TASK_ALWAYS_EAGER", False)
    CELERY_TASK_STORE_EAGER_RESULT = _env_bool("CELERY_TASK_STORE_EAGER_RESULT", False)
    CELERY_WORKER_POOL = os.getenv("CELERY_WORKER_POOL", "solo" if os.name == "nt" else "prefork")
    SCAN_INLINE_FALLBACK_ON_QUEUE_FAILURE = _env_bool("SCAN_INLINE_FALLBACK_ON_QUEUE_FAILURE", False)
    SCAN_WATCHDOG_INLINE_ON_PENDING = _env_bool("SCAN_WATCHDOG_INLINE_ON_PENDING", False)
    SCAN_PENDING_WATCHDOG_DELAY_SECONDS = int(os.getenv("SCAN_PENDING_WATCHDOG_DELAY_SECONDS", "20"))

    RATE_LIMIT_AUTH_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_AUTH_MAX_REQUESTS", "20"))
    RATE_LIMIT_AUTH_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_AUTH_WINDOW_SECONDS", "60"))
    RATE_LIMIT_SCAN_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_SCAN_MAX_REQUESTS", "10"))
    RATE_LIMIT_SCAN_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_SCAN_WINDOW_SECONDS", "3600"))


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SCAN_INLINE_FALLBACK_ON_QUEUE_FAILURE = _env_bool("SCAN_INLINE_FALLBACK_ON_QUEUE_FAILURE", True)
    SCAN_WATCHDOG_INLINE_ON_PENDING = _env_bool("SCAN_WATCHDOG_INLINE_ON_PENDING", True)


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    CELERY_TASK_ALWAYS_EAGER = True
    SCAN_INLINE_FALLBACK_ON_QUEUE_FAILURE = _env_bool("SCAN_INLINE_FALLBACK_ON_QUEUE_FAILURE", False)


class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:////var/data/codescan.db")


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(config_name=None):
    name = config_name or os.getenv("FLASK_ENV", "development")
    return CONFIG_BY_NAME.get(name, DevelopmentConfig)

import time
from datetime import datetime, timedelta, timezone

import redis
from flask import current_app


_in_memory_store = {}


def get_redis_client():
    redis_url = current_app.config.get("REDIS_URL")
    if not redis_url:
        return None
    try:
        return redis.Redis.from_url(redis_url, decode_responses=True)
    except Exception:
        return None


def _in_memory_setex(key, ttl_seconds, value):
    _in_memory_store[key] = {
        "value": value,
        "expires_at": time.time() + ttl_seconds,
    }


def _in_memory_get(key):
    entry = _in_memory_store.get(key)
    if not entry:
        return None
    if entry["expires_at"] <= time.time():
        _in_memory_store.pop(key, None)
        return None
    return entry["value"]


def blacklist_refresh_token(jti, expires_at_epoch):
    ttl = max(1, int(expires_at_epoch - time.time()))
    key = f"jwt:blacklist:{jti}"

    client = get_redis_client()
    if client:
        client.setex(key, ttl, "1")
        return

    _in_memory_setex(key, ttl, "1")


def is_token_blacklisted(jti):
    key = f"jwt:blacklist:{jti}"
    client = get_redis_client()
    if client:
        return client.get(key) is not None
    return _in_memory_get(key) is not None


def mark_session_revoked(user_id, jti, expires_at_epoch):
    ttl = max(1, int(expires_at_epoch - time.time()))
    marker_payload = f"{jti}:{int(time.time())}"

    session_key = f"session:revoked:user:{user_id}"
    hook_key = f"session:hook:user:{user_id}"

    client = get_redis_client()
    if client:
        client.setex(session_key, ttl, marker_payload)
        client.setex(hook_key, ttl, marker_payload)
        return

    _in_memory_setex(session_key, ttl, marker_payload)
    _in_memory_setex(hook_key, ttl, marker_payload)


def get_session_revoke_marker(user_id):
    key = f"session:revoked:user:{user_id}"
    client = get_redis_client()
    if client:
        return client.get(key)
    return _in_memory_get(key)


def enforce_rate_limit(scope_key, max_requests, window_seconds):
    now = datetime.now(timezone.utc)
    bucket = int(now.timestamp() // window_seconds)
    key = f"rate:{scope_key}:{bucket}"

    client = get_redis_client()
    if client:
        count = client.incr(key)
        if count == 1:
            client.expire(key, window_seconds)
        return count <= max_requests

    cache_key = key
    existing = _in_memory_get(cache_key)
    if existing is None:
        _in_memory_setex(cache_key, window_seconds, "1")
        return True

    count = int(existing) + 1
    expires_at = _in_memory_store[cache_key]["expires_at"]
    _in_memory_store[cache_key] = {"value": str(count), "expires_at": expires_at}
    return count <= max_requests


def now_plus_days(days):
    return datetime.now(timezone.utc) + timedelta(days=days)

import os
import json
import redis

_client = None

def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True,
        )
    return _client


def cache_get(key: str):
    val = get_redis().get(key)
    if val:
        return json.loads(val)
    return None


def cache_set(key: str, value, ttl: int):
    get_redis().setex(key, ttl, json.dumps(value, default=str))


def cache_delete(key: str):
    get_redis().delete(key)

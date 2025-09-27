import logging
import redis
import redis.asyncio as redis_async
from redis.exceptions import RedisError
from functools import wraps
import json
import os
from datetime import timedelta
from typing import Optional, Any, Dict, Callable, Union

# Initialize Redis connection
redis_client = None
redis_async_client = None

def init_redis():
    """Initialize Redis connections for pub/sub and caching."""
    global redis_client, redis_async_client
    
    # Use service name 'redis' in Docker Compose network
    redis_url = os.getenv('REDIS_URL', 'redis://redis:6379/0')
    logger = logging.getLogger(__name__)
    logger.info(f"Connecting to Redis at {redis_url}")
    
    # Sync client for pub/sub and caching
    redis_client = redis.Redis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_keepalive=True
    )
    
    # Async client for Pub/Sub
    redis_async_client = redis_async.Redis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_keepalive=True
    )

def get_redis() -> redis.Redis:
    """Get Redis client instance."""
    if redis_client is None:
        init_redis()
    return redis_client

def get_async_redis() -> redis_async.Redis:
    """Get async Redis client instance."""
    if redis_async_client is None:
        init_redis()
    return redis_async_client

# Celery task management functions
def get_celery_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Get Celery task status and result by ID."""
    try:
        from .celery_app import celery_app
        result = celery_app.AsyncResult(task_id)
        
        return {
            'id': task_id,
            'status': result.status,
            'result': result.result if result.successful() else None,
            'error': str(result.info) if result.failed() else None,
            'state': result.state,
            'info': result.info
        }
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting task status: {e}")
        return None

# Caching Layer
def cache_result(key: str, value: Any, ttl: int = 3600) -> bool:
    """Cache a value in Redis with TTL."""
    try:
        redis = get_redis()
        serialized = json.dumps(value)
        return bool(redis.setex(f"cache:{key}", timedelta(seconds=ttl), serialized))
    except (TypeError, RedisError):
        return False

async def cache_result_async(key: str, value: Any, ttl: int = 3600) -> bool:
    """Cache a value in Redis with TTL asynchronously."""
    try:
        redis = get_async_redis()
        serialized = json.dumps(value)
        await redis.setex(f"cache:{key}", timedelta(seconds=ttl), serialized)
        return True
    except (TypeError, RedisError):
        return False

def get_cached_result(key: str) -> Any:
    """Get a cached value from Redis."""
    try:
        cached = redis_client.get(f"cache:{key}")
        if cached:
            return json.loads(cached)
        return None
    except (TypeError, json.JSONDecodeError, RedisError):
        return None

def invalidate_cache(key: str) -> bool:
    """Invalidate a cached value."""
    try:
        return bool(redis_client.delete(f"cache:{key}"))
    except RedisError:
        return False

# Pub/Sub for Real-time Updates
def publish_message(channel: str, message: Dict[str, Any]) -> bool:
    """Publish a message to a Redis channel synchronously."""
    try:
        redis = get_redis()
        redis.publish(channel, json.dumps(message))
        return True
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to publish message: {e}")
        return False

async def publish_message_async(channel: str, message: Dict[str, Any]) -> bool:
    """Publish a message to a Redis channel asynchronously."""
    try:
        redis = get_async_redis()
        await redis.publish(channel, json.dumps(message))
        return True
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to publish message: {e}")
        return False

async def get_pubsub():
    """Get a Redis PubSub instance."""
    return get_async_redis().pubsub()

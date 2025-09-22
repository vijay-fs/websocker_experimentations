import logging
import redis
import redis.asyncio as redis_async
from redis.exceptions import RedisError
from functools import wraps
import json
import os
from datetime import timedelta
from rq import Queue
from rq.job import Job
from typing import Optional, Any, Dict, Callable, Union

# Initialize Redis connection
redis_client = None
redis_async_client = None
job_queue = None

def init_redis():
    """Initialize Redis connections and queue."""
    global redis_client, redis_async_client, job_queue
    
    # Use service name 'redis' in Docker Compose network
    redis_url = os.getenv('REDIS_URL', 'redis://redis:6379/0')
    logger = logging.getLogger(__name__)
    logger.info(f"Connecting to Redis at {redis_url}")
    
    # Sync client for RQ
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
    
    # Initialize RQ queue with 'default' name to match entrypoint.sh
    job_queue = Queue('default', connection=redis_client, default_timeout=3600)

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

def get_queue() -> Queue:
    """Get RQ queue instance."""
    if job_queue is None:
        init_redis()
    return job_queue

# Feature 1: Job Queue with RQ
def enqueue_job(
    func: Callable,
    *args,
    job_id: Optional[str] = None,
    **kwargs
) -> Job:
    """
    Enqueue a job to be processed by the worker.
    
    Args:
        func: The function to execute
        job_id: Optional job ID
        *args, **kwargs: Arguments to pass to the function
        
    Returns:
        Job: The RQ job instance
    """
    return job_queue.enqueue(
        func,
        args=args,
        kwargs=kwargs,
        job_id=job_id,
        result_ttl=86400,  # Keep results for 24 hours
        failure_ttl=86400  # Keep failed jobs for 24 hours
    )

def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Get job status and result by ID."""
    try:
        job = Job.fetch(job_id, connection=redis_client)
        return {
            'id': job.id,
            'status': job.get_status(),
            'result': job.result,
            'error': job.exc_info,
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'enqueued_at': job.enqueued_at.isoformat() if job.enqueued_at else None,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'ended_at': job.ended_at.isoformat() if job.ended_at else None,
        }
    except Exception as e:
        return None

# Feature 2: Caching Layer
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

# Feature 3: Pub/Sub for Real-time Updates
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

"""
PostHog Analytics Integration for Backend
Tracks events, errors, and performance metrics
"""
import os
from typing import Optional, Dict, Any
from posthog import Posthog
import logging

logger = logging.getLogger(__name__)

# Initialize PostHog client
posthog_client: Optional[Posthog] = None

def init_posthog():
    """Initialize PostHog client with environment variables"""
    global posthog_client
    
    api_key = os.getenv("POSTHOG_API_KEY")
    host = os.getenv("POSTHOG_HOST", "https://app.posthog.com")
    
    if api_key:
        try:
            posthog_client = Posthog(
                project_api_key=api_key,
                host=host
            )
            logger.info("PostHog analytics initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PostHog: {e}")
            posthog_client = None
    else:
        logger.warning("PostHog API key not found. Analytics disabled.")
        posthog_client = None

def track_event(
    event_name: str,
    distinct_id: str,
    properties: Optional[Dict[str, Any]] = None
):
    """
    Track an event in PostHog
    
    Args:
        event_name: Name of the event (e.g., 'api_upload_received')
        distinct_id: Unique identifier (batch_id, user_id, etc.)
        properties: Additional event properties
    """
    if not posthog_client:
        return
    
    try:
        posthog_client.capture(
            distinct_id=distinct_id,
            event=event_name,
            properties=properties or {}
        )
    except Exception as e:
        logger.error(f"Failed to track event '{event_name}': {e}")

def track_upload(batch_id: str, file_size: int, file_type: str):
    """Track file upload event"""
    track_event(
        event_name="api_upload_received",
        distinct_id=batch_id,
        properties={
            "file_size_bytes": file_size,
            "file_type": file_type,
            "component": "backend_api"
        }
    )

def track_task_queued(batch_id: str, task_id: str):
    """Track Celery task queued event"""
    track_event(
        event_name="celery_task_queued",
        distinct_id=batch_id,
        properties={
            "task_id": task_id,
            "component": "celery"
        }
    )

def track_processing_started(batch_id: str, image_size: tuple):
    """Track OCR processing started event"""
    track_event(
        event_name="ocr_processing_started",
        distinct_id=batch_id,
        properties={
            "image_width": image_size[0],
            "image_height": image_size[1],
            "component": "celery_worker"
        }
    )

def track_processing_completed(
    batch_id: str,
    processing_time: float,
    detections_count: int,
    high_confidence_count: int
):
    """Track OCR processing completed event"""
    track_event(
        event_name="ocr_processing_completed",
        distinct_id=batch_id,
        properties={
            "processing_time_seconds": processing_time,
            "total_detections": detections_count,
            "high_confidence_detections": high_confidence_count,
            "component": "celery_worker"
        }
    )

def track_processing_failed(batch_id: str, error_type: str, error_message: str):
    """Track OCR processing failure event"""
    track_event(
        event_name="ocr_processing_failed",
        distinct_id=batch_id,
        properties={
            "error_type": error_type,
            "error_message": error_message,
            "component": "celery_worker"
        }
    )

def track_pusher_event(batch_id: str, event_type: str, success: bool):
    """Track Pusher event delivery"""
    track_event(
        event_name="pusher_event_sent",
        distinct_id=batch_id,
        properties={
            "event_type": event_type,
            "success": success,
            "component": "backend_api"
        }
    )

def track_cache_operation(batch_id: str, operation: str, hit: bool):
    """Track Redis cache operations"""
    event_name = "redis_cache_hit" if hit else "redis_cache_miss"
    track_event(
        event_name=event_name,
        distinct_id=batch_id,
        properties={
            "operation": operation,
            "component": "redis"
        }
    )

def track_api_error(batch_id: str, endpoint: str, error_type: str, status_code: int):
    """Track API errors"""
    track_event(
        event_name="api_error_occurred",
        distinct_id=batch_id,
        properties={
            "endpoint": endpoint,
            "error_type": error_type,
            "status_code": status_code,
            "component": "backend_api"
        }
    )

def shutdown_posthog():
    """Shutdown PostHog client gracefully"""
    global posthog_client
    if posthog_client:
        try:
            posthog_client.shutdown()
            logger.info("PostHog client shutdown successfully")
        except Exception as e:
            logger.error(f"Error shutting down PostHog: {e}")

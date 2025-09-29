"""
Celery configuration for OCR processing application.
"""
import os
from kombu import Queue

class CeleryConfig:
    """Celery configuration class."""
    
    # Broker settings
    broker_url = os.getenv('CELERY_BROKER_URL', os.getenv('REDIS_URL', 'redis://redis:6379/0'))
    result_backend = os.getenv('CELERY_RESULT_BACKEND', os.getenv('REDIS_URL', 'redis://redis:6379/0'))
    
    # Task settings
    task_serializer = 'json'
    accept_content = ['json']
    result_serializer = 'json'
    timezone = 'UTC'
    enable_utc = True
    
    # Task execution settings
    task_always_eager = False
    task_eager_propagates = True
    task_ignore_result = False
    task_store_eager_result = True
    
    # Worker settings
    worker_prefetch_multiplier = int(os.getenv('CELERY_WORKER_PREFETCH_MULTIPLIER', '1'))
    worker_max_tasks_per_child = int(os.getenv('CELERY_WORKER_MAX_TASKS_PER_CHILD', '1000'))
    worker_disable_rate_limits = True
    worker_concurrency = int(os.getenv('CELERY_WORKER_CONCURRENCY', '2'))
    
    # Task routing
    task_routes = {
        'app.tasks.process_engineering_drawing_task': {'queue': 'default'},
    }
    
    # Queue configuration
    task_default_queue = 'default'
    task_queues = (
        Queue('default', routing_key='default'),
    )
    
    # Result backend settings
    result_expires = int(os.getenv('TASK_RESULT_TTL', '3600'))  # 1 hour default
    result_persistent = True
    
    # Task result settings
    task_track_started = True
    task_send_sent_event = True
    
    # Monitoring
    worker_send_task_events = True
    task_send_events = True
    
    # Error handling
    task_reject_on_worker_lost = True
    task_acks_late = True

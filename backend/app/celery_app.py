"""
Celery application setup for OCR processing tasks.
"""
import os
from celery import Celery
from .celery_config import CeleryConfig

def create_celery_app() -> Celery:
    """Create and configure Celery application."""
    
    # Create Celery instance
    celery_app = Celery('ocr_processor')
    
    # Load configuration
    celery_app.config_from_object(CeleryConfig)
    
    # Auto-discover tasks from the app module
    celery_app.autodiscover_tasks(['app'])
    
    return celery_app

# Create the Celery app instance
celery_app = create_celery_app()

# Make it available for imports
__all__ = ['celery_app']

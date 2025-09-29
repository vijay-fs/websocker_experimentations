"""
Application configuration management.
"""
import os
from typing import Optional

class Settings:
    """Application settings from environment variables."""
    
    # Redis Configuration
    REDIS_HOST: str = os.getenv('REDIS_HOST', 'redis')
    REDIS_PORT: int = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_URL: str = os.getenv('REDIS_URL', f'redis://{REDIS_HOST}:{REDIS_PORT}/0')
    
    # Celery Configuration
    CELERY_BROKER_URL: str = os.getenv('CELERY_BROKER_URL', REDIS_URL)
    CELERY_RESULT_BACKEND: str = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)
    CELERY_WORKER_CONCURRENCY: int = int(os.getenv('CELERY_WORKER_CONCURRENCY', '2'))
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = int(os.getenv('CELERY_WORKER_PREFETCH_MULTIPLIER', '1'))
    
    # Pusher Configuration
    PUSHER_APP_ID: str = os.getenv('PUSHER_APP_ID', '')
    PUSHER_APP_KEY: str = os.getenv('PUSHER_APP_KEY', '')
    PUSHER_APP_SECRET: str = os.getenv('PUSHER_APP_SECRET', '')
    PUSHER_CLUSTER: str = os.getenv('PUSHER_CLUSTER', 'us2')
    PUSHER_USE_TLS: bool = os.getenv('PUSHER_USE_TLS', 'true').lower() == 'true'
    
    # Application Settings
    DEBUG: bool = os.getenv('DEBUG', 'false').lower() == 'true'
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    # OCR Processing Settings
    OCR_CONFIDENCE_THRESHOLD: float = float(os.getenv('OCR_CONFIDENCE_THRESHOLD', '0.2'))
    OCR_LANGUAGES: str = os.getenv('OCR_LANGUAGES', 'en')
    MAX_IMAGE_SIZE_MB: int = int(os.getenv('MAX_IMAGE_SIZE_MB', '10'))
    
    # Task Settings
    TASK_RESULT_TTL: int = int(os.getenv('TASK_RESULT_TTL', '3600'))
    TASK_FAILURE_TTL: int = int(os.getenv('TASK_FAILURE_TTL', '86400'))
    
    @classmethod
    def validate_pusher_config(cls) -> bool:
        """Validate that required Pusher configuration is present."""
        return all([cls.PUSHER_APP_ID, cls.PUSHER_APP_KEY, cls.PUSHER_APP_SECRET])
    
    @classmethod
    def get_redis_url(cls) -> str:
        """Get the Redis URL for connections."""
        return cls.REDIS_URL
    
    @classmethod
    def get_celery_broker_url(cls) -> str:
        """Get the Celery broker URL."""
        return cls.CELERY_BROKER_URL

# Global settings instance
settings = Settings()

#!/bin/bash
set -e

# Wait for Redis to be ready
echo "Waiting for Redis to be ready..."
until redis-cli -h $REDIS_HOST -p $REDIS_PORT ping &>/dev/null; do
  sleep 1
done

# Run the application
if [ "$1" = "celery-worker" ]; then
    echo "Starting Celery worker..."
    exec celery -A app.celery_app worker --loglevel=info --concurrency=2
elif [ "$1" = "worker" ]; then
    echo "Starting Celery worker (legacy command)..."
    exec celery -A app.celery_app worker --loglevel=info --concurrency=2
else
    echo "Starting FastAPI server..."
    exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
fi

# Backend - FastAPI OCR Service

FastAPI-based backend service for real-time OCR processing of engineering drawings with WebSocket communication via Pusher.

## 🏗️ Architecture

The backend consists of several key components:
- **FastAPI Application**: Main web server handling HTTP requests
- **Celery Workers**: Distributed background job processors for OCR tasks (2 replicas)
- **Redis Integration**: Message broker, result backend, and caching
- **Pusher Integration**: Real-time WebSocket communication
- **EasyOCR Engine**: Advanced text detection and recognition with pre-downloaded models

## 🛠️ Tech Stack

- **FastAPI**: Modern, fast web framework for building APIs
- **EasyOCR**: Deep learning-based OCR library
- **Pillow (PIL)**: Image processing and manipulation
- **Redis**: In-memory data structure store for message broker and caching
- **Celery**: Distributed task queue for background job processing
- **Pusher**: Real-time WebSocket service
- **Pydantic**: Data validation using Python type annotations

## 📁 Project Structure

```
backend/
├── app/
│   ├── celery_app.py       # Celery application configuration
│   ├── celery_config.py    # Celery settings and configuration
│   ├── redis_utils.py      # Redis connection and utilities
│   ├── tasks.py            # Celery task definitions for OCR processing
│   └── config.py           # Application configuration
├── Dockerfile              # Container configuration with EasyOCR model pre-download
├── entrypoint.sh           # Container startup script (supports celery-worker mode)
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

## 🔌 API Endpoints

### Core Endpoints
- `POST /api/upload` - Upload and process engineering drawing
- `GET /api/batch-status/{batch_id}` - Get processing status and results for a batch
- `GET /api/batch-result/{batch_id}` - Get full result with annotated image from cache
- `GET /api/health` - Health check endpoint (includes Redis, Celery, and Pusher status)
- `POST /api/test-pusher/{batch_id}` - Test Pusher event delivery

### Documentation
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation (ReDoc)

## 🔄 Processing Flow

1. **File Upload**: Client uploads image via `/api/upload`
2. **Task Queuing**: Celery task queued with image data (base64 encoded)
3. **Background Processing**: Celery worker picks up task and processes with EasyOCR
4. **Progress Updates**: Worker publishes progress to Redis Pub/Sub (10%, 30%, 40%, 50%, 70%, 85%, 100%)
5. **Real-time Forwarding**: Backend Redis listener forwards updates to Pusher
6. **Result Caching**: Full result with annotated image cached in Redis (1 hour TTL)
7. **Client Notification**: Lightweight completion message sent via Pusher (without image to avoid size limits)
8. **Image Fetch**: Frontend automatically fetches full result with image from `/api/batch-result/{batch_id}`

## ⚙️ Environment Variables

### Required Configuration
```bash
# Pusher Configuration
PUSHER_APP_ID=your_pusher_app_id
PUSHER_APP_KEY=your_pusher_app_key
PUSHER_APP_SECRET=your_pusher_app_secret
PUSHER_CLUSTER=us2
PUSHER_USE_TLS=true

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_URL=redis://redis:6379/0

# Celery Configuration
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
CELERY_WORKER_CONCURRENCY=2
```

## 🐳 Docker Configuration

The backend uses a multi-stage Docker build for optimization:

### Dockerfile Features
- **Python 3.11**: Latest stable Python version
- **System Dependencies**: Required libraries for image processing
- **EasyOCR Model Pre-download**: Models downloaded during build to prevent runtime issues
- **Security**: Non-root user execution
- **Optimization**: Minimal runtime dependencies

### Container Services
- **Backend API**: Main FastAPI application server (port 8000)
- **Celery Workers**: Background OCR processors (2 replicas, scalable)
- **Redis**: Message broker, result backend, and cache (port 6379)

## 🔧 Key Components

### Celery Tasks (`app/tasks.py`)
- `process_engineering_drawing_task`: Main OCR processing task
- EasyOCR singleton reader initialization
- Image preprocessing and optimization
- Text detection with confidence scoring
- Annotated image generation with bounding boxes
- Progress updates via Redis Pub/Sub
- Result caching with full image data

### Celery Configuration (`app/celery_app.py` & `app/celery_config.py`)
- Redis broker and result backend setup
- Task routing and queue configuration
- Worker concurrency settings
- Task serialization (JSON)
- Result expiration and cleanup

### Redis Integration (`app/redis_utils.py`)
- Connection management and pooling
- Celery task status tracking
- Result caching and retrieval
- Pub/Sub messaging for real-time updates
- Async Redis client for non-blocking operations

### FastAPI Application (`main.py`)
- CORS configuration for frontend communication
- File upload handling and validation
- Celery task dispatching
- Redis Pub/Sub listener for Pusher forwarding
- Health check with Redis, Celery, and Pusher status
- Batch status and result retrieval endpoints

## 📊 Processing Features

### Image Processing
- **Format Support**: JPG, PNG, BMP, TIFF
- **Automatic Resizing**: Optimized for processing speed
- **Compression**: Reduced file sizes for transmission
- **Validation**: File type and size checks

### OCR Capabilities
- **Multi-language Support**: Configurable language detection
- **High Accuracy**: Deep learning-based text recognition
- **Confidence Scoring**: Quality metrics for detected text
- **Bounding Box Detection**: Precise text location mapping

### Real-time Updates
- **Progress Tracking**: Step-by-step processing updates
- **Error Handling**: Comprehensive error reporting
- **Status Management**: Batch processing state tracking
- **Result Delivery**: Immediate notification of completion

## 🔍 Monitoring & Debugging

### Health Checks
```bash
# Check API health (includes Redis, Celery, and Pusher status)
curl http://localhost:8000/api/health

# View container logs
docker compose logs backend
docker compose logs worker

# Check Celery worker status
docker compose exec backend celery -A app.celery_app inspect active

# Monitor Redis
docker compose exec redis redis-cli ping
docker compose exec redis redis-cli INFO
```

### Common Issues
- **Memory Usage**: OCR processing can be memory-intensive (EasyOCR models ~100MB)
- **Processing Time**: Large images may take 5-15 seconds to process
- **Redis Connection**: Ensure Redis is accessible and running
- **Pusher Limits**: Check API rate limits and quotas (10KB message size limit)
- **Model Download**: Models are pre-downloaded during build; if issues occur, rebuild with `--no-cache`
- **Worker Scaling**: Increase workers with `docker compose up --scale worker=4`

## 🚀 Performance Optimization

- **Celery Distributed Processing**: Horizontal scaling with multiple workers
- **Redis Caching**: Efficient result storage with TTL (1 hour)
- **Image Optimization**: JPEG compression at 85% quality
- **Connection Pooling**: Efficient Redis connections
- **Model Pre-loading**: EasyOCR models downloaded during build
- **Singleton Pattern**: Single EasyOCR reader instance per worker
- **Two-phase Result Delivery**: Lightweight progress via Pusher, full image via API
- **Error Recovery**: Robust error handling with Celery task state management
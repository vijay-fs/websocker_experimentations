# Backend - FastAPI OCR Service

FastAPI-based backend service for real-time OCR processing of engineering drawings with WebSocket communication via Pusher.

## 🏗️ Architecture

The backend consists of several key components:
- **FastAPI Application**: Main web server handling HTTP requests
- **RQ Worker**: Background job processor for OCR tasks
- **Redis Integration**: Message queuing and caching
- **Pusher Integration**: Real-time WebSocket communication
- **EasyOCR Engine**: Advanced text detection and recognition

## 🛠️ Tech Stack

- **FastAPI**: Modern, fast web framework for building APIs
- **EasyOCR**: Deep learning-based OCR library
- **Pillow (PIL)**: Image processing and manipulation
- **Redis**: In-memory data structure store for queuing
- **RQ (Redis Queue)**: Simple job queues for Python
- **Pusher**: Real-time WebSocket service
- **Pydantic**: Data validation using Python type annotations

## 📁 Project Structure

```
backend/
├── app/
│   ├── redis_utils.py      # Redis connection and utilities
│   └── tasks.py           # Background job definitions
├── Dockerfile             # Container configuration
├── entrypoint.sh          # Container startup script
├── main.py               # FastAPI application entry point
├── requirements.txt      # Python dependencies
├── pyproject.toml        # Project configuration
└── README.md            # This file
```

## 🔌 API Endpoints

### Core Endpoints
- `POST /api/upload-drawing` - Upload and process engineering drawing
- `GET /api/batch-status/{batch_id}` - Get processing status for a batch
- `GET /api/health` - Health check endpoint

### Documentation
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation (ReDoc)

## 🔄 Processing Flow

1. **File Upload**: Client uploads image via `/api/upload-drawing`
2. **Job Queuing**: Image processing job added to Redis queue
3. **Background Processing**: RQ worker processes OCR task
4. **Progress Updates**: Real-time updates sent via Pusher
5. **Result Storage**: Processed results cached in Redis
6. **Client Notification**: Final results pushed to frontend

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
RQ_REDIS_URL=redis://redis:6379/0
```

## 🐳 Docker Configuration

The backend uses a multi-stage Docker build for optimization:

### Dockerfile Features
- **Python 3.11**: Latest stable Python version
- **System Dependencies**: Required libraries for image processing
- **Security**: Non-root user execution
- **Optimization**: Minimal runtime dependencies

### Container Services
- **Backend API**: Main FastAPI application server
- **Worker**: Background job processor
- **Redis**: Message queue and cache

## 🔧 Key Components

### OCR Processing (`app/tasks.py`)
- EasyOCR initialization and configuration
- Image preprocessing and optimization
- Text detection and confidence scoring
- Result formatting and annotation

### Redis Integration (`app/redis_utils.py`)
- Connection management and pooling
- Job queuing and status tracking
- Result caching and retrieval
- Pub/Sub messaging for real-time updates

### FastAPI Application (`main.py`)
- CORS configuration for frontend communication
- File upload handling and validation
- Background job management
- Health check and monitoring endpoints

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
# Check API health
curl http://localhost:8000/api/health

# View container logs
docker-compose logs backend
docker-compose logs worker
```

### Common Issues
- **Memory Usage**: OCR processing can be memory-intensive
- **Processing Time**: Large images may take longer to process
- **Redis Connection**: Ensure Redis is accessible and running
- **Pusher Limits**: Check API rate limits and quotas

## 🚀 Performance Optimization

- **Background Processing**: Non-blocking OCR operations
- **Redis Caching**: Efficient result storage and retrieval
- **Image Optimization**: Automatic resizing and compression
- **Connection Pooling**: Efficient database connections
- **Error Recovery**: Robust error handling and retry logic
# Real-Time OCR Engineering Drawing Processor

A containerized full-stack application for processing engineering drawings with real-time OCR text detection and WebSocket-based progress updates using Pusher.

## 🚀 Features

### Core Functionality
- **Real-Time OCR Processing**: Advanced text detection in engineering drawings using EasyOCR
- **Live Progress Updates**: WebSocket-based real-time progress tracking with detailed status messages
- **Multi-Format Support**: Supports JPG, PNG, BMP, and TIFF image formats
- **Image Optimization**: Automatic compression and resizing for efficient transmission
- **Batch Processing**: Handle multiple files with individual progress tracking

### User Interface
- **Modern React Frontend**: Built with Next.js 15 and TypeScript
- **Drag-and-Drop Upload**: Intuitive file selection with format validation
- **Real-Time Progress Visualization**: Animated progress bars with processing step indicators
- **Toast Notifications**: Success, error, and info notifications with auto-dismiss
- **Responsive Design**: Clean, modern interface optimized for all devices

### Results Display
- **Annotated Image Viewer**: Click-to-expand processed images with OCR markings
- **Processing Statistics**: Detailed metrics including detection counts and processing time
- **Full-Size Image View**: Open processed images in new window for detailed inspection
- **Collapsible Results**: Expandable sections for comprehensive OCR analysis

## 🏗️ Architecture

```
Frontend (Next.js) ←→ Pusher WebSocket Service ←→ Backend (FastAPI)
                                ↓                        ↓
                        Real-time Progress Updates    Redis Queue
                                ↓                        ↓
                        EasyOCR Processing Engine ←→ RQ Worker
```

## 🛠️ Tech Stack

### Backend
- **FastAPI**: High-performance Python web framework
- **EasyOCR**: Advanced OCR library for text detection
- **Pillow (PIL)**: Image processing and manipulation
- **Pusher**: Real-time WebSocket communication service
- **Redis**: Message queuing and caching
- **RQ**: Background job processing

### Frontend
- **Next.js 15**: React framework with TypeScript
- **Pusher-JS**: Real-time WebSocket integration
- **Tailwind CSS**: Modern styling and responsive design
- **Custom React Hooks**: WebSocket management and state handling

### Infrastructure
- **Docker & Docker Compose**: Containerized deployment
- **Redis**: In-memory data structure store
- **Multi-stage Docker builds**: Optimized container images

## 📋 Prerequisites

- **Docker** and **Docker Compose**
- **Git**
- **Pusher Account** (free tier available at [pusher.com](https://pusher.com/))

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone <repository-url>
cd websocker_experimentations
```

### 2. Configure Environment
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your Pusher credentials
# Get these from https://dashboard.pusher.com/
nano .env
```

### 3. Start Application

```bash
# Build and start all services
docker compose up --build

# Or start in background
docker compose up --build -d
```

### 4. Access Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🐳 Docker Commands

### Basic Operations
```bash
# Start all services
docker-compose up

# Start with rebuild
docker-compose up --build

# Start in background
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs backend
docker-compose logs frontend
docker-compose logs worker

# Rebuild specific service
docker-compose build backend
docker-compose build frontend
```

### Development Commands
```bash
# Start only backend services
docker-compose up backend worker redis

# Execute commands in running container
docker-compose exec backend bash
docker-compose exec frontend sh

# Check container status
docker-compose ps

# Remove all containers and volumes
docker-compose down -v
```

## 📖 Usage

1. **Upload Engineering Drawing**: Select an image file (JPG, PNG, BMP, TIFF)
2. **Monitor Progress**: Watch real-time processing updates with detailed steps
3. **View Results**: Access processed images with OCR annotations
4. **Analyze Data**: Review detection statistics and processing metrics
5. **Full-Size Viewing**: Click images to open in new window for detailed inspection

## 🔌 API Endpoints

- `POST /api/upload-drawing`: Upload and process engineering drawing
- `GET /api/batch-status/{batch_id}`: Get processing status
- `GET /api/health`: Health check endpoint
- `GET /docs`: Interactive API documentation (Swagger UI)

## 📡 WebSocket Events

- **Channel**: `batch.{batch_id}` - Subscribe to specific batch updates
- **Event**: `batch_update` - Real-time progress notifications with OCR results

## ⚙️ Environment Variables

### Required Pusher Configuration
```bash
PUSHER_APP_ID=your_pusher_app_id
PUSHER_APP_KEY=your_pusher_app_key
PUSHER_APP_SECRET=your_pusher_app_secret
PUSHER_CLUSTER=us2  # or your preferred cluster
PUSHER_USE_TLS=true

# Frontend environment variables (prefixed with NEXT_PUBLIC_)
NEXT_PUBLIC_PUSHER_APP_KEY=your_pusher_app_key
NEXT_PUBLIC_PUSHER_CLUSTER=us2
NEXT_PUBLIC_PUSHER_USE_TLS=true
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Optional Configuration
```bash
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_URL=redis://redis:6379/0
RQ_REDIS_URL=redis://redis:6379/0
```

## 🏗️ Project Structure

```
websocker_experimentations/
├── backend/                 # FastAPI backend application
│   ├── app/                # Application modules
│   ├── Dockerfile          # Backend container configuration
│   ├── requirements.txt    # Python dependencies
│   ├── main.py            # FastAPI application entry point
│   └── entrypoint.sh      # Container startup script
├── frontend/               # Next.js frontend application
│   ├── app/               # Next.js app directory
│   ├── hooks/             # Custom React hooks
│   ├── public/            # Static assets
│   ├── Dockerfile         # Frontend container configuration
│   └── package.json       # Node.js dependencies
├── assets/                # Demo images and documentation
├── docker-compose.yml     # Multi-container orchestration
├── .env.example          # Environment variables template
└── README.md             # This file
```

## 🔧 Troubleshooting

### Common Issues

**Container fails to start:**
```bash
# Check logs
docker-compose logs [service-name]

# Rebuild containers
docker-compose down
docker-compose up --build
```

**Pusher connection issues:**
- Verify Pusher credentials in `.env` file
- Check if `NEXT_PUBLIC_` prefixed variables are set for frontend
- Ensure Pusher cluster is correct

**Redis connection errors:**
- Ensure Redis container is running: `docker-compose ps`
- Check Redis logs: `docker-compose logs redis`

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with Docker
5. Submit a pull request
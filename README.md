# Real-Time OCR Engineering Drawing Processor

A full-stack application for processing engineering drawings with real-time OCR text detection and WebSocket-based progress updates.

## Demo

![Demo 1](assets/demo1.PNG)
*Real-time processing interface with progress tracking*

![Demo 2](assets/demo2.PNG)
*OCR results with annotated engineering drawing*

## Features

### Core Functionality
- **Real-Time OCR Processing**: Uses EasyOCR for accurate text detection in engineering drawings
- **Live Progress Updates**: WebSocket-based real-time progress tracking with detailed status messages
- **Multi-Format Support**: Supports JPG, PNG, BMP, and TIFF image formats
- **Image Optimization**: Automatic compression and resizing for efficient transmission

### User Interface
- **File Upload Interface**: Drag-and-drop file selection with format validation
- **Progress Visualization**: Animated progress bars with current processing step indicators
- **Toast Notifications**: Success, error, and info notifications with auto-dismiss
- **Responsive Design**: Modern, clean interface with hover effects and transitions

### Results Display
- **Processed Image Viewer**: Click-to-expand  annotated images with OCR markings
- **Processing Statistics**: Image dimensions, file sizes, detection counts, and processing time
- **Full-Size Image View**: Open processed images in new window for detailed inspection
- **Collapsible Results**: Expandable sections for detailed OCR analysis

### Real-Time Features
- **WebSocket Connection**: Live connection status indicator
- **Process Monitoring**: Track multiple concurrent processing jobs
- **Automatic Recovery**: Reconnection handling and batch status restoration
- **Persistent State**: Process history maintained across browser sessions

## Tech Stack

### Backend
- **FastAPI**: High-performance Python web framework
- **EasyOCR**: Advanced OCR library for text detection
- **Pillow**: Image processing and manipulation
- **Socket.IO**: Real-time WebSocket communication
- **Asyncio**: Asynchronous processing for concurrent operations

### WebSocket Server
- **Node.js/TypeScript**: Real-time message broadcasting
- **Socket.IO**: WebSocket server with room-based subscriptions
- **Express**: HTTP server for health checks

### Frontend
- **Next.js 15**: React framework with TypeScript
- **Socket.IO Client**: Real-time WebSocket integration
- **Tailwind CSS**: Modern styling and responsive design
- **React Hooks**: Custom WebSocket management and state handling

## Architecture

```
Frontend (Next.js) ←→ WebSocket Server (Node.js) ←→ Backend (FastAPI)
                                ↓
                        Real-time Progress Updates
                                ↓
                        EasyOCR Processing Engine
```

## Key Capabilities

1. **Engineering Drawing Analysis**: Specialized for technical drawings and schematic
2. **Real-Time Feedback**: Incremental progress updates during processing
3. **Image Annotation**: Visual markup of detected text elements
4. **Batch Processing**: Handle multiple files with individual progress tracking
5. **Error Handling**: Comprehensive error recovery and user feedback
6. **Performance Optimization**: Compressed image transmission and efficient rendering

## Getting Started

### Prerequisites
- Docker and Docker Compose
- Git

### Docker Installation (Recommended)

1. **Clone and start with Docker**:
   ```bash
   git clone <your-repo-url>
   cd websocker_experimentations
   docker-compose up --build
   ```

2. **Access application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - WebSocket Server: http://localhost:8001

### Manual Installation (Alternative)

#### Prerequisites
- Node.js 18+
- Python 3.8+
- Yarn package manager

#### Steps

1. **Install dependencies**:
   ```bash
   yarn install
   ```

2. **Backend setup**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Start services**:
   ```bash
   # Terminal 1: WebSocket Server
   cd websocket-server
   yarn dev

   # Terminal 2: Backend API
   cd backend
   python main.py

   # Terminal 3: Frontend
   yarn dev
   ```

4. **Access application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - WebSocket Server: http://localhost:8001

## Docker Commands

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

# Rebuild specific service
docker-compose build backend
```

### Development with Docker
```bash
# Start only backend and websocket
docker-compose up backend websocket-server

# Scale services (if needed)
docker-compose up --scale backend=2

# Execute commands in running container
docker-compose exec backend bash
docker-compose exec frontend sh
```

## Usage

1. **Upload Engineering Drawing**: Select an image file (JPG, PNG, BMP, TIFF)
2. **Monitor Progress**: Watch real-time processing updates with detailed steps
3. **View Results**: Access processed images with OCR annotations
4. **Analyze Data**: Review detection statistics and processing metrics
5. **Full-Size Viewing**: Click images to open in new window for detailed inspection

## API Endpoints

- `POST /api/upload-drawing`: Upload and process engineering drawing
- `GET /api/batch-status/{batch_id}`: Get processing status
- `GET /api/health`: Health check endpoint

## WebSocket Events

- `subscribe_to_batch`: Subscribe to processing updates
- `unsubscribe_from_batch`: Unsubscribe from updates
- `batch_progress`: Real-time progress notifications
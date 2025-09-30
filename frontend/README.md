# Frontend - Next.js OCR Interface

Modern React-based frontend application for real-time OCR processing with WebSocket communication and responsive design.

## 🚀 Features

### User Interface
- **Modern React Frontend**: Built with Next.js 15 and TypeScript
- **Drag-and-Drop Upload**: Intuitive file selection with format validation
- **Real-Time Progress Visualization**: Animated progress bars with processing step indicators
- **Toast Notifications**: Success, error, and info notifications with auto-dismiss
- **Responsive Design**: Clean, modern interface optimized for all devices

### Real-Time Communication
- **Pusher WebSocket Integration**: Live connection status and real-time updates
- **Custom React Hooks**: Efficient WebSocket management and state handling
- **Automatic Reconnection**: Robust connection handling with retry logic
- **Progress Tracking**: Real-time batch processing status updates

### Results Display
- **Annotated Image Viewer**: Click-to-expand processed images with OCR markings
- **Processing Statistics**: Detailed metrics including detection counts and processing time
- **Full-Size Image View**: Open processed images in new window for detailed inspection
- **Collapsible Results**: Expandable sections for comprehensive OCR analysis

## 🛠️ Tech Stack

- **Next.js 15**: React framework with App Router and TypeScript
- **React 18**: Latest React with concurrent features
- **Pusher-JS**: Real-time WebSocket communication
- **Tailwind CSS**: Utility-first CSS framework for styling
- **TypeScript**: Type-safe JavaScript development
- **ESLint**: Code linting and quality assurance

## 📁 Project Structure

```
frontend/
├── app/
│   ├── favicon.ico         # Application favicon
│   ├── globals.css         # Global styles and Tailwind imports
│   ├── layout.tsx          # Root layout component
│   └── page.tsx           # Main application page
├── hooks/
│   └── useSocket.ts       # Custom WebSocket hook for Pusher
├── public/
│   └── *.svg              # Static SVG assets
├── Dockerfile             # Container configuration
├── next.config.ts         # Next.js configuration
├── package.json           # Node.js dependencies
├── tailwind.config.ts     # Tailwind CSS configuration
└── README.md             # This file
```

## 🔌 Key Components

### Main Application (`app/page.tsx`)
- File upload interface with drag-and-drop support
- Real-time progress tracking and visualization
- Results display with expandable sections
- Toast notification system
- Batch processing management

### WebSocket Hook (`hooks/useSocket.ts`)
- Pusher client initialization and management
- Connection status monitoring
- Batch subscription and event handling
- Progress state management with Map-based storage
- Automatic image fetching when progress reaches 100%
- Error handling and reconnection logic

### Styling (`globals.css` + Tailwind)
- Modern, responsive design system
- Custom animations and transitions
- Toast notification styling
- Progress bar animations
- Hover effects and interactions

## ⚙️ Environment Variables

### Required Configuration
```bash
# Pusher Configuration (prefixed with NEXT_PUBLIC_ for client-side access)
NEXT_PUBLIC_PUSHER_APP_KEY=your_pusher_app_key
NEXT_PUBLIC_PUSHER_CLUSTER=us2
NEXT_PUBLIC_PUSHER_USE_TLS=true

# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 🐳 Docker Configuration

The frontend uses a multi-stage Docker build for optimization:

### Build Features
- **Node.js 22 Alpine**: Lightweight base image
- **Multi-stage Build**: Separate build and runtime environments
- **Standalone Output**: Optimized Next.js build for containers
- **Non-root User**: Security-focused container execution

### Build Process
1. **Dependencies Installation**: Install all build dependencies
2. **Application Build**: Create optimized production build
3. **Runtime Setup**: Copy only necessary files to runtime image
4. **Security**: Run as non-root user

## 🔄 Application Flow

1. **File Selection**: User selects engineering drawing file
2. **Upload Initiation**: File uploaded to backend API via `/api/upload`
3. **WebSocket Connection**: Subscribe to batch-specific Pusher channel (`batch.{batch_id}`)
4. **Progress Updates**: Real-time processing status updates (10% → 30% → 40% → 50% → 70% → 85% → 100%)
5. **Image Fetch**: When progress reaches 100%, automatically fetch full result from `/api/batch-result/{batch_id}`
6. **Result Display**: Show processed images with OCR annotations and statistics
7. **Full-Size Viewing**: Click images to open in new window for detailed inspection

## 🎨 UI/UX Features

### File Upload
- Drag-and-drop interface
- File format validation (JPG, PNG, BMP, TIFF)
- Visual feedback during upload
- Error handling for invalid files

### Progress Tracking
- Animated progress bars
- Step-by-step processing indicators
- Real-time status messages
- Processing time tracking

### Results Presentation
- Expandable result sections
- Annotated image with bounding boxes and detected text
- OCR text extraction display with confidence scores
- Processing statistics (total detections, high confidence count, processing time)
- Base64 image rendering with Next.js Image component

### Notifications
- Toast notifications for user feedback
- Auto-dismiss functionality
- Different notification types (success, error, info, warning)
- Non-intrusive positioning

## 🔧 Development Features

### TypeScript Integration
- Full type safety across components
- Interface definitions for API responses
- Type-safe WebSocket event handling
- Compile-time error checking

### Code Quality
- ESLint configuration for code quality
- Consistent code formatting
- Import organization
- Error boundary implementation

### Performance Optimization
- Next.js automatic code splitting
- Image optimization with Next.js Image component
- Lazy loading for components
- Efficient state management with React hooks
- Two-phase data loading (progress via WebSocket, image via API)
- Map-based batch progress tracking for O(1) lookups

## 🚀 Build & Deployment

### Docker Build
```bash
# Build frontend container
docker-compose build frontend

# Run frontend service
docker-compose up frontend
```

### Standalone Deployment
The application is configured for standalone deployment with optimized bundle size and runtime performance.

## 🔍 Monitoring & Debugging

### Connection Status
- Visual WebSocket connection indicator
- Automatic reconnection handling
- Error state management
- Connection quality monitoring

### Development Tools
- React Developer Tools support
- Next.js built-in debugging
- TypeScript error reporting
- Hot reload for development

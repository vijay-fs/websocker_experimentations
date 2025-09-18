import asyncio
import uuid
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import socketio
import json
import base64
from io import BytesIO
import logging

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Import EasyOCR and image processing libraries
import easyocr
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="WebSocket Tutorial Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage
batch_status_memory: Dict[str, Dict[str, Any]] = {}

# Initialize EasyOCR reader (supports multiple languages)
reader = easyocr.Reader(['en'])

# Load environment variables
load_dotenv()

# Get WebSocket server URL from environment variable with default
SOCKETIO_SERVER_URL = os.getenv("SOCKETIO_SERVER_URL", "http://localhost:8001")
logger.info(f"Connecting to Socket.IO server at {SOCKETIO_SERVER_URL}")
sio = socketio.AsyncClient()

# Constants for retry logic
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 1  # seconds
CLEANUP_INTERVAL_SECONDS = 300  # 5 minutes

# Supported image formats
SUPPORTED_IMAGE_FORMATS = {
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'image/gif': ['.gif'],
    'image/bmp': ['.bmp'],
    'image/tiff': ['.tiff', '.tif'],
    'image/webp': ['.webp']
}

SUPPORTED_EXTENSIONS = [ext for exts in SUPPORTED_IMAGE_FORMATS.values() for ext in exts]

class StartProcessRequest(BaseModel):
    process_type: str = "default"
    parameters: Optional[Dict[str, Any]] = None

class BatchStatusResponse(BaseModel):
    batch_id: str
    status: str
    progress: int
    messages: list[str]
    created_at: str
    updated_at: str
    process_type: str
    parameters: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

def get_batch_status(batch_id: str) -> Optional[Dict[str, Any]]:
    """Get batch status from in-memory storage"""
    return batch_status_memory.get(batch_id)

def set_batch_status(batch_id: str, status_data: Dict[str, Any]) -> bool:
    """Save batch status to in-memory storage"""
    batch_status_memory[batch_id] = status_data
    return True

def get_all_batch_ids() -> list:
    """Get all batch IDs from in-memory storage"""
    return list(batch_status_memory.keys())

def validate_image_file(file: UploadFile) -> tuple[bool, str]:
    """Validate uploaded image file format and size"""
    # Check content type
    if not file.content_type or file.content_type not in SUPPORTED_IMAGE_FORMATS:
        return False, f"Unsupported file format. Supported formats: {', '.join(SUPPORTED_IMAGE_FORMATS.keys())}"
    
    # Check file extension
    if file.filename:
        file_ext = '.' + file.filename.split('.')[-1].lower()
        if file_ext not in SUPPORTED_EXTENSIONS:
            return False, f"Unsupported file extension. Supported extensions: {', '.join(SUPPORTED_EXTENSIONS)}"
    
    return True, "Valid image file"

def convert_image_format(image_data: bytes, target_format: str = "RGB") -> Image.Image:
    """Convert image to target format for processing"""
    try:
        image = Image.open(BytesIO(image_data))
        
        # Convert to RGB if needed (for JPEG compatibility)
        if image.mode != target_format:
            if image.mode == 'RGBA' and target_format == 'RGB':
                # Create white background for transparent images
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            else:
                image = image.convert(target_format)
        
        return image
    except Exception as e:
        raise ValueError(f"Failed to convert image format: {str(e)}")

async def send_to_socketio_with_retry(batch_id: str, message: str, progress: int, result: Optional[Dict[str, Any]] = None, message_type: str = "info"):
    """Send message to Socket.IO server with retry logic"""
    for attempt in range(MAX_RETRY_ATTEMPTS):
        try:
            # Ensure connection before sending
            if not sio.connected:
                logger.info(f"Connecting to Socket.IO server at {SOCKETIO_SERVER_URL} (attempt {attempt + 1})")
                await sio.connect(SOCKETIO_SERVER_URL)
                logger.info("Connected to Socket.IO server")
            
            data = {
                "type": "batch_update",
                "batch_id": batch_id,
                "message": message,
                "progress": progress,
                "timestamp": datetime.now().isoformat(),
                "message_type": message_type  # info, success, error, warning
            }
            
            if result:
                data["result"] = result
            
            # Log without large image data to avoid terminal flooding
            log_data = data.copy()
            if log_data.get("result") and log_data["result"].get("marked_image"):
                log_data["result"] = {**log_data["result"], "marked_image": f"[BASE64_IMAGE_{len(log_data['result']['marked_image'])}chars]"}
            logger.info(f"Sending to Socket.IO: {log_data}")
            await sio.emit('batch_update', data)
            logger.info(f"Successfully sent batch update for {batch_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send to Socket.IO server (attempt {attempt + 1}): {e}")
            if attempt < MAX_RETRY_ATTEMPTS - 1:
                await asyncio.sleep(RETRY_DELAY * (2 ** attempt))  # Exponential backoff
            else:
                logger.error(f"Max retry attempts reached for batch {batch_id}")
                return False
    return False

async def send_to_socketio(batch_id: str, message: str, progress: int, result: Optional[Dict[str, Any]] = None, message_type: str = "info"):
    """Send message to Socket.IO server with improved error handling"""
    try:
        success = await send_to_socketio_with_retry(batch_id, message, progress, result, message_type)
        if not success:
            # Update batch status with error
            batch_data = get_batch_status(batch_id)
            if batch_data:
                batch_data["status"] = "error"
                batch_data["messages"].append("Failed to send progress update to frontend")
                batch_data["updated_at"] = datetime.now().isoformat()
                set_batch_status(batch_id, batch_data)
        return success
    except Exception as e:
        logger.error(f"Critical error in send_to_socketio for batch {batch_id}: {e}")
        # Update batch status with error
        batch_data = get_batch_status(batch_id)
        if batch_data:
            batch_data["status"] = "error"
            batch_data["messages"].append(f"Critical error: {str(e)}")
            batch_data["updated_at"] = datetime.now().isoformat()
            set_batch_status(batch_id, batch_data)
        return False

async def simulate_long_process(batch_id: str):
    messages = [
        "Starting process...",
        "Loading files...",
        "Processing data...",
        "Extracting information...",
        "Analyzing content...",
        "Detecting patterns...",
        "Generating results...",
        "Finalizing output...",
        "Process completed!"
    ]
    
    # Get current batch status from in-memory storage
    batch_data = get_batch_status(batch_id)
    if not batch_data:
        print(f"Batch {batch_id} not found in memory")
        return
    
    batch_data["status"] = "running"
    batch_data["process_type"] = batch_data.get("process_type", "default")
    set_batch_status(batch_id, batch_data)
    
    for i, message in enumerate(messages):
        progress = int((i + 1) / len(messages) * 100)
        batch_data["messages"].append(message)
        batch_data["progress"] = progress
        batch_data["updated_at"] = datetime.now().isoformat()
        
        # Save updated status to in-memory storage
        set_batch_status(batch_id, batch_data)
        
        await send_to_socketio(batch_id, message, progress, None)
        
        # Check if the process was cancelled or completed
        updated_batch_data = get_batch_status(batch_id)
        if not updated_batch_data or updated_batch_data.get("status") == "cancelled":
            print(f"Process {batch_id} was cancelled")
            return
        
        await asyncio.sleep(2)
    
    batch_data["status"] = "completed"
    set_batch_status(batch_id, batch_data)

@app.post("/api/start-process")
async def start_process(request: StartProcessRequest):
    batch_id = str(uuid.uuid4())
    
    batch_data = {
        "batch_id": batch_id,
        "status": "initialized",
        "progress": 0,
        "messages": [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "process_type": request.process_type,
        "parameters": request.parameters or {}
    }
    
    # Save to in-memory storage
    if not set_batch_status(batch_id, batch_data):
        raise HTTPException(status_code=500, detail="Failed to save batch status")
    
    asyncio.create_task(simulate_long_process(batch_id))
    
    return {"batch_id": batch_id, "status": "initialized"}

@app.get("/api/batch-status/{batch_id}", response_model=BatchStatusResponse)
async def get_batch_status_endpoint(batch_id: str):
    batch_data = get_batch_status(batch_id)
    if not batch_data:
        raise HTTPException(status_code=404, detail="Batch ID not found")
    
    return batch_data

async def process_engineering_drawing(batch_id: str, image_data: bytes):
    """Process engineering drawing with comprehensive error handling and progress updates"""
    try:
        # Get current batch status from in-memory storage
        batch_data = get_batch_status(batch_id)
        if not batch_data:
            await send_to_socketio(batch_id, "Error: Batch not found", 0, None, "error")
            return False
        
        batch_data["status"] = "running"
        set_batch_status(batch_id, batch_data)
        
        # Send initial progress update
        await send_to_socketio(batch_id, "Starting image processing...", 5, None, "info")
        await asyncio.sleep(1)
        
        # Validate and convert image
        await send_to_socketio(batch_id, "Validating and converting image...", 10, None, "info")
        await asyncio.sleep(1)
        
        try:
            image = convert_image_format(image_data, "RGB")
        except ValueError as e:
            await send_to_socketio(batch_id, f"Image conversion failed: {str(e)}", 100, None, "error")
            return False
        
        # Convert PIL Image to numpy array for EasyOCR
        await send_to_socketio(batch_id, "Preparing image for OCR analysis...", 20, None, "info")
        await asyncio.sleep(1)
        image_np = np.array(image)
        
        # Perform OCR with EasyOCR
        await send_to_socketio(batch_id, "Performing OCR analysis with EasyOCR...", 40, None, "info")
        
        try:
            results = reader.readtext(image_np)
            await send_to_socketio(batch_id, "OCR analysis completed successfully!", 50, None, "info")
        except Exception as e:
            await send_to_socketio(batch_id, f"OCR analysis failed: {str(e)}", 100, None, "error")
            return False
        
        # Process and mark detected text
        await send_to_socketio(batch_id, "Processing detected text and creating annotations...", 60, None, "info")
        await asyncio.sleep(1)
        
        marked_image = image.copy()
        draw = ImageDraw.Draw(marked_image)
        
        detected_symbols = []
        for (bbox, text, confidence) in results:
            if confidence > 0.3:  # Lower threshold for better detection
                # Draw rectangle around detected text
                (top_left, top_right, bottom_right, bottom_left) = bbox
                top_left_int = (int(top_left[0]), int(top_left[1]))
                top_right_int = (int(top_right[0]), int(top_right[1]))
                bottom_right_int = (int(bottom_right[0]), int(bottom_right[1]))
                bottom_left_int = (int(bottom_left[0]), int(bottom_left[1]))
                
                # Draw bounding box
                draw.polygon([top_left_int, top_right_int, bottom_right_int, bottom_left_int], outline="red", width=2)
                
                # Add text label with background
                text_bbox = draw.textbbox((0, 0), text)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                
                label_pos = (top_left_int[0], max(0, top_left_int[1] - text_height - 5))
                draw.rectangle([label_pos, (label_pos[0] + text_width + 4, label_pos[1] + text_height + 4)], fill="red")
                draw.text((label_pos[0] + 2, label_pos[1] + 2), text, fill="white")
                
                detected_symbols.append({
                    "text": text.strip(),
                    "confidence": float(confidence),
                    "bbox": {
                        "top_left": top_left_int,
                        "top_right": top_right_int,
                        "bottom_right": bottom_right_int,
                        "bottom_left": bottom_left_int
                    }
                })
        
        # Convert processed image to base64 with compression
        await send_to_socketio(batch_id, "Encoding processed image for display...", 80, None, "info")
        await asyncio.sleep(1)
        
        # Resize image if too large for better WebSocket transmission
        max_width = 1200
        if marked_image.width > max_width:
            ratio = max_width / marked_image.width
            new_height = int(marked_image.height * ratio)
            # Handle all Pillow versions for image resizing
            try:
                # Pillow 9.0.0+ with Resampling enum
                marked_image = marked_image.resize((max_width, new_height), Image.Resampling.LANCZOS)
            except (AttributeError, TypeError):
                # Pillow < 9.0.0 with direct LANCZOS constant, or fallback to default resizing
                marked_image = marked_image.resize((max_width, new_height), getattr(Image, 'LANCZOS', 1))
        
        buffered = BytesIO()
        # Use JPEG with quality optimization for smaller file size
        marked_image.save(buffered, format="JPEG", quality=85, optimize=True)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        logger.info(f"Compressed image size: {len(img_str)} characters ({len(img_str)/1024:.1f}KB)")
        
        await send_to_socketio(batch_id, "Finalizing results...", 95, None, "info")
        await asyncio.sleep(1)
        
        # Prepare final results
        result_data = {
            "detected_symbols": detected_symbols,
            "marked_image": img_str,
            "symbol_count": len(detected_symbols),
            "processing_stats": {
                "total_detections": len(results),
                "high_confidence_detections": len(detected_symbols),
                "image_dimensions": f"{marked_image.width}x{marked_image.height}",
                "original_dimensions": f"{image.width}x{image.height}",
                "processing_time": datetime.now().isoformat(),
                "compressed_size_kb": round(len(img_str)/1024, 1)
            }
        }
        
        # Send completion message with success toast
        completion_message = f"✅ Processing complete! Detected {len(detected_symbols)} text elements with high confidence."
        await send_to_socketio(batch_id, completion_message, 100, result_data, "success")
        
        # Update batch status
        batch_data = get_batch_status(batch_id)
        if batch_data:
            batch_data["status"] = "completed"
            batch_data["progress"] = 100
            batch_data["messages"].append(completion_message)
            batch_data["result"] = result_data
            batch_data["updated_at"] = datetime.now().isoformat()
            set_batch_status(batch_id, batch_data)
            
        return True
        
    except Exception as e:
        error_msg = f"❌ Critical error during image processing: {str(e)}"
        print(f"Error in process_engineering_drawing: {e}")
        
        # Send error notification
        await send_to_socketio(batch_id, error_msg, 100, None, "error")
        
        # Update batch status with error
        batch_data = get_batch_status(batch_id)
        if batch_data:
            batch_data["status"] = "error"
            batch_data["messages"].append(error_msg)
            batch_data["updated_at"] = datetime.now().isoformat()
            set_batch_status(batch_id, batch_data)
        
        return False

@app.post("/api/upload-drawing")
async def upload_drawing(file: UploadFile = File(...)):
    """Upload and process engineering drawing with comprehensive validation"""
    try:
        # Validate file
        is_valid, validation_message = validate_image_file(file)
        if not is_valid:
            raise HTTPException(status_code=400, detail=validation_message)
        
        # Read and validate file contents
        contents = await file.read()
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
        
        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(contents) > max_size:
            raise HTTPException(status_code=400, detail=f"File too large. Maximum size: {max_size // (1024*1024)}MB")
        
        # Generate unique batch ID
        batch_id = str(uuid.uuid4())
        
        # Initialize batch status
        batch_data = {
            "batch_id": batch_id,
            "status": "initialized",
            "progress": 0,
            "messages": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "process_type": "image_processing",
            "parameters": {
                "filename": file.filename,
                "content_type": file.content_type,
                "file_size": len(contents),
                "file_size_mb": round(len(contents) / (1024*1024), 2)
            }
        }
        
        # Save to in-memory storage
        if not set_batch_status(batch_id, batch_data):
            raise HTTPException(status_code=500, detail="Failed to initialize processing batch")
        
        # Start processing immediately
        asyncio.create_task(process_engineering_drawing(batch_id, contents))
        
        return {
            "batch_id": batch_id, 
            "status": "initialized",
            "message": f"✅ File '{file.filename}' uploaded successfully. Processing started.",
            "file_info": {
                "name": file.filename,
                "size": f"{batch_data['parameters']['file_size_mb']}MB",
                "type": file.content_type
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
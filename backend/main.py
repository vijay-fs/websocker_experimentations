import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import socketio
import json
import base64
from io import BytesIO

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import EasyOCR and image processing libraries
import easyocr
from PIL import Image, ImageDraw
import numpy as np

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

SOCKETIO_SERVER_URL = "http://localhost:8001"
sio = socketio.AsyncClient()

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

async def send_to_socketio(batch_id: str, message: str, progress: int, result: Optional[Dict[str, Any]] = None):
    try:
        if not sio.connected:
            print(f"Connecting to Socket.IO server at {SOCKETIO_SERVER_URL}")
            await sio.connect(SOCKETIO_SERVER_URL)
            print("Connected to Socket.IO server")
        
        data = {
            "type": "batch_update",
            "batch_id": batch_id,
            "message": message,
            "progress": progress,
            "timestamp": datetime.now().isoformat(),
            "result": result  # Include result data if available
        }
        print(f"Sending to Socket.IO: {data}")
        await sio.emit('batch_update', data)
        print(f"Successfully sent batch update for {batch_id}")
    except Exception as e:
        print(f"Failed to send to Socket.IO server: {e}")
        # Don't print full traceback in production, but it's helpful for debugging
        # import traceback
        # traceback.print_exc()

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

# Image processing function using EasyOCR
async def process_engineering_drawing(batch_id: str, image_data: bytes):
    try:
        # Send initial progress update
        await send_to_socketio(batch_id, "Starting image processing...", 5)
        
        # Load image
        await send_to_socketio(batch_id, "Loading image...", 10)
        image = Image.open(BytesIO(image_data))
        
        # Convert PIL Image to numpy array for EasyOCR
        await send_to_socketio(batch_id, "Converting image format...", 15)
        image_np = np.array(image)
        
        # Perform OCR with EasyOCR
        await send_to_socketio(batch_id, "Performing OCR with EasyOCR...", 30)
        results = reader.readtext(image_np)
        
        # Mark detected text on image
        await send_to_socketio(batch_id, "Marking detected symbols...", 50)
        marked_image = image.copy()
        draw = ImageDraw.Draw(marked_image)
        
        detected_symbols = []
        for (bbox, text, confidence) in results:
            if confidence > 0.5:  # Only consider high confidence detections
                # Draw rectangle around detected text
                (top_left, top_right, bottom_right, bottom_left) = bbox
                # Convert coordinates to integers for drawing
                top_left_int = (int(top_left[0]), int(top_left[1]))
                top_right_int = (int(top_right[0]), int(top_right[1]))
                bottom_right_int = (int(bottom_right[0]), int(bottom_right[1]))
                bottom_left_int = (int(bottom_left[0]), int(bottom_left[1]))
                
                draw.polygon([top_left_int, top_right_int, bottom_left_int], outline="red", width=2)
                
                # Add text label
                draw.text((top_left_int[0], top_left_int[1] - 10), text, fill="blue")
                
                detected_symbols.append({
                    "text": text,
                    "confidence": float(confidence),
                    "bbox": {
                        "top_left": top_left_int,
                        "top_right": top_right_int,
                        "bottom_right": bottom_right_int,
                        "bottom_left": bottom_left_int
                    }
                })
        
        # Convert marked image to base64 for transmission
        await send_to_socketio(batch_id, "Encoding processed image...", 70)
        buffered = BytesIO()
        marked_image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # Update batch status with results BEFORE sending final progress
        batch_data = get_batch_status(batch_id)
        if batch_data:
            batch_data["status"] = "completed"
            batch_data["progress"] = 100  # Set to 100% when complete
            batch_data["messages"].append(f"Processing complete. Detected {len(detected_symbols)} symbols.")
            batch_data["result"] = {
                "detected_symbols": detected_symbols,
                "marked_image": img_str,
                "symbol_count": len(detected_symbols)
            }
            batch_data["updated_at"] = datetime.now().isoformat()
            set_batch_status(batch_id, batch_data)
        
        # Send final progress with results
        result_data = {
            "detected_symbols": detected_symbols,
            "marked_image": img_str,
            "symbol_count": len(detected_symbols)
        }
        await send_to_socketio(batch_id, f"Processing complete. Detected {len(detected_symbols)} symbols.", 100, result_data)
            
        return True
    except Exception as e:
        error_msg = f"Error processing image: {str(e)}"
        print(error_msg)
        # Update batch status with error
        batch_data = get_batch_status(batch_id)
        if batch_data:
            batch_data["status"] = "error"
            batch_data["messages"].append(error_msg)
            batch_data["updated_at"] = datetime.now().isoformat()
            set_batch_status(batch_id, batch_data)
        await send_to_socketio(batch_id, error_msg, 100)
        return False

@app.post("/api/upload-drawing")
async def upload_drawing(file: UploadFile = File(...)):
    # Generate batch ID
    batch_id = str(uuid.uuid4())
    
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")
    
    # Read file content
    contents = await file.read()
    
    # Initialize batch status
    batch_data = {
        "batch_id": batch_id,
        "status": "initialized",
        "progress": 0,
        "messages": [f"Received file: {file.filename}"],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "process_type": "image_processing",
        "parameters": {
            "filename": file.filename,
            "content_type": file.content_type
        }
    }
    
    # Save to in-memory storage
    if not set_batch_status(batch_id, batch_data):
        raise HTTPException(status_code=500, detail="Failed to save batch status")
    
    # Start image processing asynchronously
    asyncio.create_task(process_engineering_drawing(batch_id, contents))
    
    return {"batch_id": batch_id, "status": "initialized", "message": "Image processing started"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

import asyncio
import json
import logging
import uuid
import hmac
import hashlib
import time
import os
import base64
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode
from io import BytesIO

import httpx
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from rq import Queue
import easyocr
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from app.redis_utils import get_redis, get_async_redis, get_queue, enqueue_job, get_job, cache_result, cache_result_async, get_cached_result, publish_message, publish_message_async, init_redis
from app.tasks import process_engineering_drawing_task

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="WebSocket Tutorial Backend")

# Minimal CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple middleware to add CORS headers
@app.middleware("http")
async def add_cors_headers(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

# Initialize Redis and RQ queue
redis_client = None
rq_queue = None

# Initialize EasyOCR reader (supports multiple languages)
reader = easyocr.Reader(['en'])

# Get Redis host from environment or use 'redis' as default
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
os.environ['REDIS_URL'] = REDIS_URL
os.environ['RQ_REDIS_URL'] = REDIS_URL

# Load environment variables
load_dotenv()

# Set Redis URL if not already set in environment
if 'REDIS_URL' not in os.environ:
    os.environ['REDIS_URL'] = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
if 'RQ_REDIS_URL' not in os.environ:
    os.environ['RQ_REDIS_URL'] = os.environ['REDIS_URL']

# Get Soketi server configuration from environment variables
SOKETI_SERVER_URL = os.getenv("SOKETI_SERVER_URL", "http://soketi:6001")
SOKETI_APP_ID = os.getenv("SOKETI_APP_ID", "app-id")
SOKETI_APP_KEY = os.getenv("SOKETI_APP_KEY", "app-key")
SOKETI_APP_SECRET = os.getenv("SOKETI_APP_SECRET", "app-secret")

def create_pusher_auth_signature(method: str, path: str, query_string: str = "") -> str:
    """Create Pusher authentication signature for Soketi HTTP API"""
    timestamp = str(int(time.time()))
    
    # Build query parameters
    auth_params = {
        "auth_key": SOKETI_APP_KEY,
        "auth_timestamp": timestamp,
        "auth_version": "1.0"
    }
    
    # Add any additional query parameters
    if query_string:
        for param in query_string.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                auth_params[key] = value
    
    # Create query string from sorted parameters
    query_string = urlencode(sorted(auth_params.items()))
    
    # Create string to sign
    string_to_sign = f"{method}\n{path}\n{query_string}"
    
    # Create auth signature
    signature = hmac.new(
        SOKETI_APP_SECRET.encode('utf-8'),
        string_to_sign.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return f"{query_string}&auth_signature={signature}"

logger.info(f"Connecting to Soketi server at {SOKETI_SERVER_URL}")

# HTTP client for Soketi requests
http_client = httpx.AsyncClient()

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
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)
    use_cache: bool = True

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

async def get_batch_status(batch_id: str):
    """Get batch status from Redis cache"""
    # First check if we have a cached result
    cached_status = get_cached_result(f"batch_status:{batch_id}")
    if cached_status:
        return cached_status
    
    # Check if it's an RQ job
    job_data = get_job(batch_id)
    if job_data:
        return job_data
    
    return {"status": "not_found", "message": "Batch ID not found"}

async def set_batch_status(batch_id: str, status_data: Dict[str, Any]) -> bool:
    """Save batch status to Redis"""
    # Save to Redis
    await cache_result_async(f"batch_status:{batch_id}", status_data)
    return True

async def get_all_batch_ids() -> List[str]:
    """Get all batch IDs from Redis"""
    # This is a simplified version - in production, you might want to use a Redis set
    # to track all batch IDs for better performance
    return []  # Not implemented for Redis in this example

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

async def send_to_soketi(batch_id: str, message: str, progress: int, result: Optional[Dict[str, Any]] = None, message_type: str = "info"):
    """Send message to Soketi server"""
    try:
        data = {
            "type": "batch_update",
            "batch_id": batch_id,
            "message": message,
            "progress": progress,
            "timestamp": datetime.utcnow().isoformat(),
            "message_type": message_type,
            "result": result
        }
        
        payload = {
            "name": "batch_update",
            "channel": f"batch.{batch_id}",
            "data": data
        }
        
        # Send to Soketi HTTP API with proper Pusher authentication
        path = f"/apps/{SOKETI_APP_ID}/events"
        auth_query = create_pusher_auth_signature("POST", path)
        
        logger.info(f"🚀 Sending to Soketi: {SOKETI_SERVER_URL}{path}?{auth_query}")
        logger.info(f"📦 Payload: {json.dumps(payload, indent=2)}")
        
        response = await http_client.post(
            f"{SOKETI_SERVER_URL}{path}?{auth_query}",
            json=payload,
            headers={
                "Content-Type": "application/json"
            }
        )
        
        logger.info(f"📡 Soketi response status: {response.status_code}")
        logger.info(f"📡 Soketi response headers: {dict(response.headers)}")
        logger.info(f"📡 Soketi response body: {response.text}")
        
        if response.status_code == 200:
            logger.info(f"✅ Soketi: batch {batch_id} sent successfully")
            return True
        else:
            logger.error(f"❌ Soketi failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Critical error in send_to_soketi for batch {batch_id}: {e}")
        # Update batch status with error
        batch_data = await get_batch_status(batch_id)
        if batch_data:
            batch_data["status"] = "error"
            batch_data["messages"].append(f"Critical error: {str(e)}")
            batch_data["updated_at"] = datetime.now().isoformat()
            await set_batch_status(batch_id, batch_data)
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
    
    # Get current batch status from Redis
    batch_data = await get_batch_status(batch_id)
    if not batch_data:
        print(f"Batch {batch_id} not found in Redis")
        return
    
    batch_data["status"] = "running"
    batch_data["process_type"] = batch_data.get("process_type", "default")
    await set_batch_status(batch_id, batch_data)
    
    for i, message in enumerate(messages):
        progress = int((i + 1) / len(messages) * 100)
        batch_data["messages"].append(message)
        batch_data["progress"] = progress
        batch_data["updated_at"] = datetime.now().isoformat()
        
        # Save updated status to Redis
        await set_batch_status(batch_id, batch_data)
        
        await send_to_soketi(batch_id, message, progress, None)
        
        # Check if the process was cancelled or completed
        updated_batch_data = await get_batch_status(batch_id)
        if not updated_batch_data or updated_batch_data.get("status") == "cancelled":
            print(f"Process {batch_id} was cancelled")
            return
        
        await asyncio.sleep(2)
    
    batch_data["status"] = "completed"
    await set_batch_status(batch_id, batch_data)

async def start_redis_listener():
    """Start listening to Redis Pub/Sub channels and forward to Soketi"""
    try:
        # Use async Redis client for Pub/Sub
        redis = get_async_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe("jobs:new", "jobs:update")
        
        logger.info("Started Redis Pub/Sub listener")
        
        # Run the listener in a background task to avoid blocking startup
        async def listen_loop():
            try:
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        channel = message["channel"]
                        data = json.loads(message["data"]) if isinstance(message["data"], (str, bytes)) else message["data"]
                        
                        # Forward relevant messages to Soketi
                        if channel == "jobs:update" and "batch_id" in data:
                            logger.info(f"Forwarding job update to Soketi: {data['batch_id']} - {data.get('message')}")

                            # Send to Soketi using HTTP API
                            payload = {
                                "name": "batch_update",
                                "channel": f"batch.{data['batch_id']}",
                                "data": {
                                    "type": "batch_update",
                                    "batch_id": data["batch_id"],
                                    "message": data.get("message", "Processing..."),
                                    "progress": data.get("progress", 0),
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "message_type": data.get("message_type", "info"),
                                    "result": data.get("result")
                                }
                            }
                            
                            try:
                                # Try multiple approaches to ensure event delivery
                                
                                # 1. Direct Redis pub/sub to Soketi adapter
                                redis_adapter = get_async_redis()
                                
                                # Format for Soketi Redis adapter
                                soketi_redis_message = {
                                    "event": "batch_update",
                                    "data": json.dumps({
                                        "type": "batch_update",
                                        "batch_id": data["batch_id"],
                                        "message": data.get("message", "Processing..."),
                                        "progress": data.get("progress", 0),
                                        "timestamp": datetime.utcnow().isoformat(),
                                        "message_type": data.get("message_type", "info"),
                                        "result": data.get("result")
                                    }),
                                    "channel": f"batch.{data['batch_id']}"
                                }
                                
                                # 2. HTTP API with authentication (Primary approach)
                                path = f"/apps/{SOKETI_APP_ID}/events"
                                auth_query = create_pusher_auth_signature("POST", path)
                                
                                response = await http_client.post(
                                    f"{SOKETI_SERVER_URL}{path}?{auth_query}",
                                    json=payload,
                                    headers={
                                        "Content-Type": "application/json"
                                    }
                                )
                                
                                logger.info(f"📡 HTTP API: {response.status_code} - {response.text[:100]}")
                                
                                # Only try Redis approach if HTTP API fails
                                if response.status_code != 200:
                                    logger.warning("HTTP API failed, trying Redis approach")
                                    # Publish to the correct channel format for Soketi Redis adapter
                                    soketi_channel_name = f"batch.{data['batch_id']}"
                                    await redis_adapter.publish(soketi_channel_name, json.dumps(soketi_redis_message))
                                    logger.info(f"✅ Redis->Soketi: batch {data['batch_id']} published via Redis")
                                
                            except Exception as e:
                                logger.error(f"Error sending to Soketi: {str(e)}")
                                
                                # Fallback: try direct Redis publish
                                try:
                                    soketi_channel_name = f"batch.{data['batch_id']}"
                                    await redis_adapter.publish(soketi_channel_name, json.dumps(soketi_redis_message))
                                    logger.info(f"✅ Fallback Redis->Soketi: batch {data['batch_id']} published via Redis")
                                except Exception as fallback_error:
                                    logger.error(f"Fallback also failed: {fallback_error}")
                                
            except Exception as e:
                logger.error(f"Error in Redis Pub/Sub listener: {str(e)}")
        
        # Start the listener as a background task
        asyncio.create_task(listen_loop())
        
    except Exception as e:
        logger.error(f"Failed to start Redis Pub/Sub listener: {str(e)}")
        # Don't raise here to prevent blocking startup

@app.post("/api/process/start")
async def start_process(
    request: StartProcessRequest,
    background_tasks: BackgroundTasks
):
    """Start a new processing batch"""
    batch_id = str(uuid.uuid4())
    
    # Check cache first if enabled
    cache_key = None
    if request.use_cache and request.parameters and "image_hash" in request.parameters:
        cache_key = f"ocr_result:{request.parameters['image_hash']}"
        cached_result = get_cached_result(cache_key)
        if cached_result:
            return {"batch_id": "cached_" + str(uuid.uuid4())[:8], "status": "completed", "cached": True, "result": cached_result}
    
    # Initialize batch status
    status_data = {
        "batch_id": batch_id,
        "status": "queued",
        "progress": 0,
        "messages": ["Batch created and queued for processing"],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "process_type": request.process_type,
        "parameters": request.parameters or {}
    }
    
    # Save initial status to Redis
    await set_batch_status(batch_id, status_data)
    
    # For immediate processing (synchronous)
    if request.process_type == "immediate":
        background_tasks.add_task(simulate_long_process, batch_id)
    # For background processing (asynchronous)
    else:
        # Enqueue the job with RQ
        job = enqueue_job(
            process_engineering_drawing_task,
            batch_id=batch_id,
            image_data_base64=request.parameters.get("image_data"),
            process_type=request.process_type,
            parameters=request.parameters,
            job_id=batch_id
        )
        
        # Publish an event that a new job was queued
        publish_message("jobs:new", {
            "batch_id": batch_id,
            "status": "queued",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Return initial response
        return {"batch_id": batch_id, "status": "queued"}

@app.get("/api/batch-status/{batch_id}")
async def get_batch_status_endpoint(batch_id: str):
    """Get the current status of a batch process"""
    try:
        status = await get_batch_status(batch_id)
        if status and status.get("status") != "not_found":
            # Check if we have cached result with image
            cached_result = get_cached_result(f"batch_result:{batch_id}")
            if cached_result and cached_result.get("marked_image"):
                status["result"] = cached_result
            return status
        else:
            raise HTTPException(status_code=404, detail="Batch not found")
    except Exception as e:
        logger.error(f"Error getting batch status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/upload")
async def upload_drawing(
    file: UploadFile = File(...),
    use_cache: bool = True,
    background_tasks: BackgroundTasks = None
):
    """Upload and process engineering drawing with comprehensive validation"""
    # Validate file
    is_valid, error_message = validate_image_file(file)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_message)
    
    # Read file content
    try:
        image_data = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
    
    # Generate a unique batch ID
    batch_id = str(uuid.uuid4())
    
    # Create image hash for caching
    import hashlib
    image_hash = hashlib.md5(image_data).hexdigest()
    
    # Check cache first if enabled
    cache_key = f"ocr_result:{image_hash}"
    if use_cache:
        cached_result = get_cached_result(cache_key)
        if cached_result:
            return {
                "batch_id": "cached_" + str(uuid.uuid4())[:8],
                "status": "completed",
                "cached": True,
                "result": cached_result
            }
    
    # Initialize batch status
    status_data = {
        "batch_id": batch_id,
        "status": "queued",
        "progress": 0,
        "messages": ["File uploaded and queued for processing"],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "process_type": "engineering_drawing",
        "file_name": file.filename,
        "file_size": len(image_data),
        "content_type": file.content_type,
        "image_hash": image_hash
    }
    
    # Save initial status
    await set_batch_status(batch_id, status_data)
    
    try:
        # Convert image to base64 for the task
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Enqueue the job with RQ
        job = enqueue_job(
            process_engineering_drawing_task,
            batch_id=batch_id,
            image_data_base64=image_base64,
            process_type="engineering_drawing",
            parameters={
                "file_name": file.filename,
                "file_size": len(image_data),
                "content_type": file.content_type,
                "image_hash": image_hash
            },
            job_id=batch_id
        )
        
        # Publish an event that a new job was queued
        await publish_message_async("jobs:new", {
            "batch_id": batch_id,
            "status": "queued",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Return initial response
        return {
            "batch_id": batch_id,
            "status": "queued",
            "message": "File uploaded and queued for processing"
        }
        
    except Exception as e:
        # Update status with error
        error_status = {
            "status": "failed",
            "progress": 0,
            "message": f"Error queuing job: {str(e)}",
            "error": str(e),
            "updated_at": datetime.utcnow().isoformat()
        }
        await set_batch_status(batch_id, {**status_data, **error_status})
        
        # Re-raise the exception with HTTP 500
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/test-soketi/{batch_id}")
async def test_soketi_event(batch_id: str):
    """Manual test endpoint to trigger Soketi events"""
    success = await send_to_soketi(
        batch_id=batch_id,
        message="Manual test event from API",
        progress=50,
        message_type="info"
    )
    return {"success": success, "batch_id": batch_id, "message": "Test event sent"}

@app.get("/api/health", response_model=Dict[str, Any])
async def health_check():
    """Health check endpoint with detailed status"""
    status = {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "redis": False,
            "soketi": False,
            "api": True
        },
        "details": {}
    }
    
    # Check Redis connection
    try:
        redis_ok = get_redis().ping()
        status["services"]["redis"] = redis_ok
        status["details"]["redis"] = "Connected" if redis_ok else "Connection failed"
    except Exception as e:
        status["details"]["redis_error"] = str(e)
    
    # Check RQ connection
    try:
        rq_ok = get_queue().connection.ping()
        status["services"]["rq"] = rq_ok
        status["details"]["rq"] = "Connected" if rq_ok else "Connection failed"
    except Exception as e:
        status["details"]["rq_error"] = str(e)
    # Check Soketi connection
    try:
        response = await http_client.get(f"{SOKETI_SERVER_URL}")
        if response.status_code == 200:
            status["services"]["soketi"] = True
            status["details"]["soketi"] = "Connected"
        else:
            status["details"]["soketi_error"] = response.text
    except Exception as e:
        status["details"]["soketi_error"] = str(e)
    
    # If any critical service is down, mark status as error
    if not all(status["services"].values()):
        status["status"] = "error"
    
    return status

# Start the Soketi client when the app starts
@app.on_event("startup")
async def startup_event():
    # Initialize Redis with retry logic
    max_retries = 5
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            # Initialize Redis with the correct URL
            init_redis()
            redis = get_redis()
            redis.ping()
            
            # Initialize RQ queue
            global rq_queue
            rq_queue = get_queue()
            
            logger.info(f"Successfully connected to Redis at {REDIS_URL}")
            logger.info("RQ queue initialized successfully")
            break
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to connect to Redis at {REDIS_URL} after {max_retries} attempts: {str(e)}")
                raise
            logger.warning(f"Attempt {attempt + 1} failed. Retrying in {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)

    # Start Redis Pub/Sub listener in the background
    asyncio.create_task(start_redis_listener())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

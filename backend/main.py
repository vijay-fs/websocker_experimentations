import asyncio
import logging
import uuid
import os
from datetime import datetime
from typing import Dict, Any, Optional

import pusher
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# In-memory storage for batch results (in production, use Redis/database)
batch_results_cache: Dict[str, Dict[str, Any]] = {}

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get Pusher configuration from environment variables
PUSHER_APP_ID = os.getenv("PUSHER_APP_ID", "2054052")
PUSHER_KEY = os.getenv("PUSHER_KEY", "f69118021e989cd5a601")
PUSHER_SECRET = os.getenv("PUSHER_SECRET", "88860a25217dd497edca")
PUSHER_CLUSTER = os.getenv("PUSHER_CLUSTER", "ap2")

# Initialize Pusher client using the official library
pusher_client = pusher.Pusher(
    app_id=PUSHER_APP_ID,
    key=PUSHER_KEY,
    secret=PUSHER_SECRET,
    cluster=PUSHER_CLUSTER,
    ssl=True
)

logger.info(f"✅ Pusher client initialized for cluster {PUSHER_CLUSTER}")

async def send_to_pusher(batch_id: str, message: str, progress: int, result: Optional[Dict[str, Any]] = None, message_type: str = "info"):
    """Send message to Pusher service using official library"""
    try:
        data = {
            "type": "batch_update",
            "batch_id": batch_id,
            "message": message,
            "progress": progress,
            "timestamp": datetime.utcnow().isoformat(),
            "message_type": message_type
        }

        if result:
            data["result"] = result

        channel_name = f"batch.{batch_id}"
        event_name = "batch_update"

        logger.info(f"🚀 Sending to Pusher channel: {channel_name}, event: {event_name}")
        logger.info(f"📦 Payload: {data}")

        # Use the official Pusher library with detailed response tracking
        import time
        start_time = time.time()

        response = pusher_client.trigger(channel_name, event_name, data)

        end_time = time.time()
        response_time = round((end_time - start_time) * 1000, 2)  # milliseconds

        # Enhanced logging with more details
        logger.info(f"📡 Pusher response: {response}")
        logger.info(f"📡 Response type: {type(response)}")
        logger.info(f"⏱️ Response time: {response_time}ms")

        # Try to get more detailed information
        if hasattr(response, '__dict__'):
            logger.info(f"📋 Response attributes: {response.__dict__}")

        # Check if the response indicates success
        success = False
        if response is None or response == {}:
            success = True
            logger.info(f"✅ Pusher: batch {batch_id} sent successfully (empty response indicates success)")
        elif isinstance(response, dict):
            if response.get('status_code') in [200, 201] or response.get('status') in [200, 201]:
                success = True
                logger.info(f"✅ Pusher: batch {batch_id} sent successfully (status: {response.get('status_code', response.get('status'))})")
            else:
                logger.error(f"❌ Pusher failed: {response}")
        else:
            # For other response types, assume success if no exception was thrown
            success = True
            logger.info(f"✅ Pusher: batch {batch_id} sent successfully (non-dict response: {response})")

        # Log additional Pusher client info
        logger.info(f"🔧 Pusher client config - App ID: {PUSHER_APP_ID}, Cluster: {PUSHER_CLUSTER}")

        return success

    except Exception as e:
        logger.error(f"Critical error in send_to_pusher for batch {batch_id}: {e}")
        logger.error(f"Error type: {type(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return False

app = FastAPI(title="OCR Backend with Pusher")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "OCR backend is running",
        "pusher": {
            "cluster": PUSHER_CLUSTER,
            "app_id": PUSHER_APP_ID
        }
    }

@app.post("/api/test-pusher/{batch_id}")
async def test_pusher_event(batch_id: str):
    """Manual test endpoint to trigger Pusher events"""
    logger.info(f"Testing Pusher for batch: {batch_id}")

    success = await send_to_pusher(
        batch_id=batch_id,
        message="Manual test event from API",
        progress=50,
        result={"test": True, "timestamp": datetime.utcnow().isoformat()},
        message_type="test"
    )

    return {
        "batch_id": batch_id,
        "pusher_sent": success,
        "message": "Test event sent" if success else "Failed to send test event"
    }

async def process_file_background(batch_id: str, file_data: bytes, filename: str, content_type: str):
    """Background processing function that sends real-time updates"""
    try:
        # Send detailed progress updates with percentages

        # Stage 1: File validation (0-10%)
        await send_to_pusher(batch_id, "📁 Validating uploaded file...", 5)
        await asyncio.sleep(0.5)
        await send_to_pusher(batch_id, "✅ File validation complete", 10)

        # Stage 2: File processing (10-30%)
        await send_to_pusher(batch_id, "🔄 Initializing file processing...", 15)
        await asyncio.sleep(0.5)
        await send_to_pusher(batch_id, "📊 Analyzing file structure...", 20)
        await asyncio.sleep(0.5)
        await send_to_pusher(batch_id, "🎯 File analysis complete", 30)

        # Stage 3: Image preprocessing (30-60%)
        await send_to_pusher(batch_id, "🖼️ Preprocessing image data...", 35)
        await asyncio.sleep(0.5)
        await send_to_pusher(batch_id, "🔧 Applying image filters...", 45)
        await asyncio.sleep(0.5)
        await send_to_pusher(batch_id, "📐 Optimizing image quality...", 55)
        await asyncio.sleep(0.5)
        await send_to_pusher(batch_id, "✨ Image preprocessing complete", 60)

        # Stage 4: OCR processing (60-90%)
        await send_to_pusher(batch_id, "🔍 Initializing OCR engine...", 65)
        await asyncio.sleep(0.5)
        await send_to_pusher(batch_id, "📝 Detecting text regions...", 70)
        await asyncio.sleep(0.5)
        await send_to_pusher(batch_id, "🎯 Extracting text content...", 80)
        await asyncio.sleep(0.5)
        await send_to_pusher(batch_id, "📋 Formatting extracted text...", 85)
        await asyncio.sleep(0.5)
        await send_to_pusher(batch_id, "✅ OCR processing complete", 90)

        # Stage 5: Finalization (90-100%)
        await send_to_pusher(batch_id, "📦 Preparing final results...", 95)
        await asyncio.sleep(0.5)

        # Send completion with detailed results
        result = {
            "filename": filename,
            "size": len(file_data),
            "content_type": content_type,
            "message": "File processed successfully!",
            "processing_time": "6 seconds (simulated)",
            "extracted_text": "Sample extracted text content...",
            "confidence_score": 95.8,
            "detected_language": "English",
            "processing_stages": [
                "File validation",
                "File analysis",
                "Image preprocessing",
                "OCR processing",
                "Result formatting"
            ]
        }

        await send_to_pusher(batch_id, "🎉 Processing complete! File successfully processed.", 100, result, "success")

        # Store result in cache for fallback API calls
        batch_results_cache[batch_id] = {
            "batch_id": batch_id,
            "status": "completed",
            "progress": 100,
            "result": result,
            "completed_at": datetime.utcnow().isoformat()
        }

        logger.info(f"✅ Background processing complete for batch {batch_id}")

    except Exception as e:
        logger.error(f"❌ Error in background processing for batch {batch_id}: {e}")

        # Store error in cache for fallback API calls
        batch_results_cache[batch_id] = {
            "batch_id": batch_id,
            "status": "failed",
            "progress": 0,
            "error": str(e),
            "failed_at": datetime.utcnow().isoformat()
        }

        await send_to_pusher(batch_id, f"❌ Error: {str(e)}", 0, None, "error")

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """File upload that returns batch_id immediately and processes in background"""

    # Generate a batch ID
    batch_id = str(uuid.uuid4())
    logger.info(f"📤 Upload started with batch_id: {batch_id}")

    try:
        # Read file data
        file_data = await file.read()

        # Send initial status
        await send_to_pusher(batch_id, "🚀 Upload received, starting processing...", 0)

        # Start background processing (don't await it)
        asyncio.create_task(process_file_background(batch_id, file_data, file.filename, file.content_type))

        # Return immediately with batch_id
        return {
            "batch_id": batch_id,
            "status": "processing",
            "message": "File uploaded successfully, processing started"
        }

    except Exception as e:
        logger.error(f"❌ Error in upload for batch {batch_id}: {e}")
        await send_to_pusher(batch_id, f"❌ Upload Error: {str(e)}", 0, None, "error")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/batch-status/{batch_id}")
async def get_batch_status(batch_id: str):
    """Fallback endpoint to get batch status when Pusher connection is lost"""
    logger.info(f"🔄 Fallback API call for batch {batch_id}")

    if batch_id in batch_results_cache:
        cached_result = batch_results_cache[batch_id]
        logger.info(f"📦 Returning cached result for batch {batch_id}")
        return cached_result
    else:
        # Batch not found in cache
        logger.warning(f"⚠️ Batch {batch_id} not found in cache")
        raise HTTPException(
            status_code=404,
            detail=f"Batch {batch_id} not found. It may have expired or never existed."
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
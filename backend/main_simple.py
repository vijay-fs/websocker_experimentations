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
import redis
from PIL import Image
from pydantic import BaseModel, Field
from dotenv import load_dotenv

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

def create_pusher_auth_signature(method: str, path: str, query_string: str = "") -> str:
    """Create Pusher authentication signature for Pusher HTTP API"""
    timestamp = str(int(time.time()))
    body_md5 = hashlib.md5("".encode('utf-8')).hexdigest()

    string_to_sign = f"{method}\n{path}\n"
    string_to_sign += f"auth_key={PUSHER_KEY}&auth_timestamp={timestamp}&auth_version=1.0&body_md5={body_md5}"
    if query_string:
        string_to_sign += f"&{query_string}"

    signature = hmac.new(
        PUSHER_SECRET.encode('utf-8'),
        string_to_sign.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return f"auth_key={PUSHER_KEY}&auth_timestamp={timestamp}&auth_version=1.0&body_md5={body_md5}&auth_signature={signature}"

logger.info(f"Using Pusher service with cluster {PUSHER_CLUSTER}")

# HTTP client for Pusher requests
http_client = httpx.AsyncClient()

async def send_to_pusher(batch_id: str, message: str, progress: int, result: Optional[Dict[str, Any]] = None, message_type: str = "info"):
    """Send message to Pusher service"""
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

        payload = {
            "name": "batch_update",
            "channel": f"batch.{batch_id}",
            "data": data
        }

        # Send to Pusher HTTP API with proper authentication
        # For ap2 cluster, use the regional endpoint
        if PUSHER_CLUSTER == "ap2":
            pusher_url = f"https://api-ap2.pusher.com"
        else:
            pusher_url = f"https://api.pusherapp.com"
        path = f"/apps/{PUSHER_APP_ID}/events"
        auth_query = create_pusher_auth_signature("POST", path)

        logger.info(f"🚀 Sending to Pusher: {pusher_url}{path}?{auth_query}")

        headers = {
            "Content-Type": "application/json",
            "X-Pusher-Cluster": PUSHER_CLUSTER
        }

        response = await http_client.post(
            f"{pusher_url}{path}?{auth_query}",
            json=payload,
            headers=headers
        )

        logger.info(f"📡 Pusher response status: {response.status_code}")
        logger.info(f"📡 Pusher response body: {response.text}")

        if response.status_code == 200:
            logger.info(f"✅ Pusher: batch {batch_id} sent successfully")
            return True
        else:
            logger.error(f"❌ Pusher failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Critical error in send_to_pusher for batch {batch_id}: {e}")
        return False

app = FastAPI(title="Simple OCR Backend")

# Minimal CORS configuration
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
    return {"status": "healthy", "message": "Simple backend is running"}

@app.post("/api/test-pusher/{batch_id}")
async def test_pusher_event(batch_id: str):
    """Manual test endpoint to trigger Pusher events"""
    logger.info(f"Testing Pusher for batch: {batch_id}")

    success = await send_to_pusher(
        batch_id=batch_id,
        message="Manual test event from API",
        progress=50,
        result={"test": True},
        message_type="test"
    )

    return {
        "batch_id": batch_id,
        "pusher_sent": success,
        "message": "Test event sent" if success else "Failed to send test event"
    }

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Simple file upload that sends progress updates via Pusher"""

    # Generate a batch ID
    batch_id = str(uuid.uuid4())
    logger.info(f"Processing upload with batch_id: {batch_id}")

    try:
        # Read file data
        file_data = await file.read()

        # Send initial progress
        await send_to_pusher(batch_id, "File uploaded, starting processing...", 25)

        # Simulate processing
        await asyncio.sleep(1)
        await send_to_pusher(batch_id, "Processing file data...", 50)

        await asyncio.sleep(1)
        await send_to_pusher(batch_id, "Analyzing content...", 75)

        await asyncio.sleep(1)

        # Send completion
        result = {
            "filename": file.filename,
            "size": len(file_data),
            "content_type": file.content_type,
            "message": "File processed successfully (simulated)"
        }

        await send_to_pusher(batch_id, "Processing complete!", 100, result, "success")

        return {
            "batch_id": batch_id,
            "status": "completed",
            "result": result
        }

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        await send_to_pusher(batch_id, f"Error: {str(e)}", 0, None, "error")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
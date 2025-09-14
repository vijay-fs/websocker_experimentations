import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import socketio
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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

async def send_to_socketio(batch_id: str, message: str, progress: int):
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
            "timestamp": datetime.now().isoformat()
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
    set_batch_status(batch_id, batch_data)
    
    for i, message in enumerate(messages):
        progress = int((i + 1) / len(messages) * 100)
        batch_data["messages"].append(message)
        batch_data["progress"] = progress
        batch_data["updated_at"] = datetime.now().isoformat()
        
        # Save updated status to in-memory storage
        set_batch_status(batch_id, batch_data)
        
        await send_to_socketio(batch_id, message, progress)
        
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

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

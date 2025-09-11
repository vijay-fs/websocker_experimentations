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

batch_status: Dict[str, Dict[str, Any]] = {}

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
        import traceback
        traceback.print_exc()

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
    
    batch_status[batch_id]["status"] = "running"
    
    for i, message in enumerate(messages):
        progress = int((i + 1) / len(messages) * 100)
        batch_status[batch_id]["messages"].append(message)
        batch_status[batch_id]["progress"] = progress
        batch_status[batch_id]["updated_at"] = datetime.now().isoformat()
        
        await send_to_socketio(batch_id, message, progress)
        
        await asyncio.sleep(2)
    
    batch_status[batch_id]["status"] = "completed"

@app.post("/api/start-process")
async def start_process(request: StartProcessRequest):
    batch_id = str(uuid.uuid4())
    
    batch_status[batch_id] = {
        "batch_id": batch_id,
        "status": "initialized",
        "progress": 0,
        "messages": [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "process_type": request.process_type,
        "parameters": request.parameters or {}
    }
    
    asyncio.create_task(simulate_long_process(batch_id))
    
    return {"batch_id": batch_id, "status": "initialized"}

@app.get("/api/batch-status/{batch_id}", response_model=BatchStatusResponse)
async def get_batch_status(batch_id: str):
    if batch_id not in batch_status:
        raise HTTPException(status_code=404, detail="Batch ID not found")
    
    return batch_status[batch_id]

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

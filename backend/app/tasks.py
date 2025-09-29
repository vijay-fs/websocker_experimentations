import os
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from PIL import Image, ImageDraw
import numpy as np
import easyocr
from io import BytesIO
import base64

from .celery_app import celery_app
from .redis_utils import get_redis, publish_message

# Configure logging
logger = logging.getLogger(__name__)

# Reduce the number of threads used by math libs to avoid potential deadlocks
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

# Lazily initialized EasyOCR reader to avoid heavy init at import time in prefork workers
_reader = None

def get_reader():
    """Return a singleton EasyOCR reader instance (CPU-only)."""
    global _reader
    if _reader is None:
        logger.info("Initializing EasyOCR reader (CPU, en)...")
        # Ensure model directory exists and is writable
        model_dir = os.path.expanduser("~/.EasyOCR")
        os.makedirs(os.path.join(model_dir, "model"), exist_ok=True)
        # Force CPU and explicit model dir to prevent unexpected downloads/permissions issues
        _reader = easyocr.Reader(['en'], gpu=False, model_storage_directory=model_dir, download_enabled=True, verbose=False)
    return _reader

@celery_app.task(bind=True, name='app.tasks.process_engineering_drawing_task')
def process_engineering_drawing_task(
    self,
    image_data_base64: str, 
    batch_id: str,
    process_type: str = "default",
    parameters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Process engineering drawing with OCR and return results.
    This function runs in a background worker.
    """
    try:
        # Update task state and publish progress
        logger.info(f"Starting OCR processing for batch {batch_id}")
        
        # Update Celery task state
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 10,
                'total': 100,
                'status': 'Starting image processing...',
                'batch_id': batch_id
            }
        )
        
        # Publish to Redis pub/sub for real-time updates
        status_update = {
            "status": "processing",
            "progress": 10,
            "message": "Starting image processing...",
            "message_type": "info",
            "process_type": process_type,
            "parameters": parameters or {}
        }
        publish_message("jobs:update", {"batch_id": batch_id, **status_update})
        
        # Convert base64 image data to PIL Image
        try:
            image_data = base64.b64decode(image_data_base64)
            image = Image.open(BytesIO(image_data)).convert('RGB')
            image_np = np.array(image)
        except Exception as e:
            error_msg = f"Failed to process image data: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)

        # Update status
        logger.info(f"Starting OCR detection for batch {batch_id}")
        
        # Update Celery task state
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 30,
                'total': 100,
                'status': 'Performing OCR on the image...',
                'batch_id': batch_id
            }
        )
        
        publish_message("jobs:update", {
            "batch_id": batch_id,
            "status": "processing",
            "progress": 30,
            "message": "Performing OCR on the image...",
            "message_type": "info"
        })

        # Perform OCR
        try:
            # Initialize OCR reader
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': 40,
                    'total': 100,
                    'status': 'Initializing OCR engine...',
                    'batch_id': batch_id
                }
            )
            publish_message("jobs:update", {
                "batch_id": batch_id,
                "status": "processing",
                "progress": 40,
                "message": "Initializing OCR engine...",
                "message_type": "info"
            })
            
            ocr_reader = get_reader()
            
            # Start text detection
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': 50,
                    'total': 100,
                    'status': 'Detecting text regions...',
                    'batch_id': batch_id
                }
            )
            publish_message("jobs:update", {
                "batch_id": batch_id,
                "status": "processing",
                "progress": 50,
                "message": "Detecting text regions...",
                "message_type": "info"
            })
            
            logger.info("Running EasyOCR readtext() ...")
            results = ocr_reader.readtext(image_np)
            
            # Process OCR results
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': 70,
                    'total': 100,
                    'status': 'Processing detected text...',
                    'batch_id': batch_id
                }
            )
            publish_message("jobs:update", {
                "batch_id": batch_id,
                "status": "processing",
                "progress": 70,
                "message": "Processing detected text...",
                "message_type": "info"
            })
            
            # Extract text and bounding boxes
            detected_texts = []
            for (bbox, text, prob) in results:
                if prob > 0.2:  # Confidence threshold
                    # Convert numpy arrays to lists for JSON serialization
                    bbox_list = [[float(coord[0]), float(coord[1])] for coord in bbox]
                    detected_texts.append({
                        "text": text,
                        "confidence": float(prob),
                        "bounding_box": bbox_list
                    })
            
            # Generate visualization
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': 85,
                    'total': 100,
                    'status': 'Creating annotated image...',
                    'batch_id': batch_id
                }
            )
            publish_message("jobs:update", {
                "batch_id": batch_id,
                "status": "processing",
                "progress": 85,
                "message": "Creating annotated image...",
                "message_type": "info"
            })
            
            # Mark the image with bounding boxes (for visualization)
            marked_image = image.copy()
            draw = ImageDraw.Draw(marked_image)
            
            for item in detected_texts:
                bbox = item["bounding_box"]
                # Draw rectangle
                draw.polygon([(bbox[0][0], bbox[0][1]), 
                            (bbox[1][0], bbox[1][1]),
                            (bbox[2][0], bbox[2][1]),
                            (bbox[3][0], bbox[3][1])], 
                            outline="red", width=2)
                # Add text label
                draw.text((bbox[0][0], bbox[0][1] - 10), 
                         item["text"], 
                         fill="red")
            
            # Convert marked image to base64
            buffered = BytesIO()
            marked_image.save(buffered, format="JPEG", quality=85, optimize=True)
            marked_image_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            # Prepare result with frontend-compatible structure
            result = {
                "detected_symbols": detected_texts,  # Changed from detected_texts to match frontend
                "marked_image": marked_image_base64,
                "symbol_count": len(detected_texts),
                "processing_stats": {
                    "total_detections": len(detected_texts),
                    "high_confidence_detections": len([t for t in detected_texts if t.get('confidence', 0) > 0.8]),
                    "image_dimensions": f"{image.width}x{image.height}",
                    "original_dimensions": f"{image.width}x{image.height}",
                    "processing_time": datetime.now().isoformat(),
                    "compressed_size_kb": len(image_data) // 1024
                }
            }
            
            # Final status update (without base64 image to reduce log spam)
            logger.info(f"Publishing completion message for batch {batch_id} with {len(detected_texts)} detections")
            result_without_image = {
                "detected_symbols": detected_texts,  # Changed from detected_texts to match frontend
                "symbol_count": len(detected_texts),
                "processing_stats": {
                    "total_detections": len(detected_texts),
                    "high_confidence_detections": len([t for t in detected_texts if t.get('confidence', 0) > 0.8]),
                    "image_dimensions": f"{image.width}x{image.height}",
                    "original_dimensions": f"{image.width}x{image.height}",
                    "processing_time": datetime.now().isoformat(),
                    "compressed_size_kb": len(image_data) // 1024
                }
            }
            
            # Update Celery task state to SUCCESS
            self.update_state(
                state='SUCCESS',
                meta={
                    'current': 100,
                    'total': 100,
                    'status': 'Processing completed successfully',
                    'batch_id': batch_id,
                    'result': result_without_image
                }
            )
            
            publish_message("jobs:update", {
                "batch_id": batch_id,
                "status": "completed",
                "progress": 100,
                "message": "✅ Processing completed successfully",
                "message_type": "success",
                "result": result_without_image
            })
            
            # Store full result with image in cache for API access
            from app.redis_utils import cache_result
            cache_result(f"batch_result:{batch_id}", result, ttl=3600)
            
            return result
            
        except Exception as e:
            error_msg = f"Error during OCR processing: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Update Celery task state to FAILURE
            self.update_state(
                state='FAILURE',
                meta={
                    'current': 0,
                    'total': 100,
                    'status': f'Processing failed: {str(e)}',
                    'batch_id': batch_id,
                    'error': str(e)
                }
            )
            
            # Send error status
            publish_message("jobs:update", {
                "batch_id": batch_id,
                "status": "failed",
                "progress": 0,
                "message": f"Processing failed: {str(e)}",
                "error": str(e)
            })
            
            raise
            
    except Exception as e:
        logger.error(f"Unexpected error in process_engineering_drawing_task: {str(e)}", exc_info=True)
        
        # Update Celery task state to FAILURE for unexpected errors
        self.update_state(
            state='FAILURE',
            meta={
                'current': 0,
                'total': 100,
                'status': f'Unexpected error: {str(e)}',
                'batch_id': batch_id,
                'error': str(e)
            }
        )
        
        # Ensure we send a failure message even for unexpected errors
        publish_message("jobs:update", {
            "batch_id": batch_id,
            "status": "failed",
            "progress": 0,
            "message": f"Unexpected error: {str(e)}",
            "error": str(e)
        })
        
        raise

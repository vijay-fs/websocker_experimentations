#!/usr/bin/env python3
"""
Test script for Celery migration validation.
"""
import os
import sys
import time
import base64
import asyncio
from pathlib import Path

# Add the backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.celery_app import celery_app
from app.tasks import process_engineering_drawing_task
from app.redis_utils import get_redis, get_celery_task_status

def test_celery_connection():
    """Test Celery broker connection."""
    print("🔍 Testing Celery connection...")
    try:
        # Test broker connection
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        if stats:
            print("✅ Celery broker connection: OK")
            print(f"   Active workers: {len(stats)}")
            return True
        else:
            print("❌ Celery broker connection: No workers found")
            return False
    except Exception as e:
        print(f"❌ Celery broker connection failed: {e}")
        return False

def test_redis_connection():
    """Test Redis connection."""
    print("🔍 Testing Redis connection...")
    try:
        redis_client = get_redis()
        redis_client.ping()
        print("✅ Redis connection: OK")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False

def create_test_image():
    """Create a simple test image in base64 format."""
    from PIL import Image, ImageDraw, ImageFont
    import io
    
    # Create a simple test image with text
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    
    # Add some text
    try:
        # Try to use a default font
        font = ImageFont.load_default()
    except:
        font = None
    
    draw.text((50, 80), "TEST OCR TEXT", fill='black', font=font)
    draw.text((50, 120), "Sample Engineering Drawing", fill='black', font=font)
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return img_base64

def test_task_submission():
    """Test Celery task submission."""
    print("🔍 Testing task submission...")
    try:
        # Create test image
        test_image = create_test_image()
        batch_id = "test_batch_123"
        
        # Submit task
        task = process_engineering_drawing_task.delay(
            image_data_base64=test_image,
            batch_id=batch_id,
            process_type="test",
            parameters={"test": True}
        )
        
        print(f"✅ Task submitted successfully")
        print(f"   Task ID: {task.id}")
        print(f"   Batch ID: {batch_id}")
        
        return task.id, batch_id
    except Exception as e:
        print(f"❌ Task submission failed: {e}")
        return None, None

def test_task_status_tracking(task_id, batch_id):
    """Test task status tracking."""
    print("🔍 Testing task status tracking...")
    
    max_wait = 60  # Maximum wait time in seconds
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            # Check task status
            status = get_celery_task_status(task_id)
            if status:
                print(f"   Task Status: {status.get('status', 'UNKNOWN')}")
                
                if status.get('status') == 'SUCCESS':
                    print("✅ Task completed successfully")
                    result = status.get('result')
                    if result and isinstance(result, dict):
                        symbol_count = result.get('symbol_count', 0)
                        print(f"   Detected symbols: {symbol_count}")
                    return True
                elif status.get('status') == 'FAILURE':
                    print(f"❌ Task failed: {status.get('error', 'Unknown error')}")
                    return False
                elif status.get('status') in ['PENDING', 'PROGRESS']:
                    if 'info' in status and isinstance(status['info'], dict):
                        progress = status['info'].get('current', 0)
                        print(f"   Progress: {progress}%")
            
            time.sleep(2)
        except Exception as e:
            print(f"   Error checking status: {e}")
            time.sleep(2)
    
    print("❌ Task status tracking: Timeout")
    return False

def test_worker_availability():
    """Test if Celery workers are available."""
    print("🔍 Testing worker availability...")
    try:
        inspect = celery_app.control.inspect()
        
        # Check active workers
        active = inspect.active()
        if active:
            print(f"✅ Active workers: {len(active)}")
            for worker, tasks in active.items():
                print(f"   {worker}: {len(tasks)} active tasks")
        else:
            print("❌ No active workers found")
            return False
        
        # Check registered tasks
        registered = inspect.registered()
        if registered:
            for worker, tasks in registered.items():
                if 'app.tasks.process_engineering_drawing_task' in tasks:
                    print("✅ OCR task registered in workers")
                    return True
            print("❌ OCR task not registered in workers")
            return False
        else:
            print("❌ No registered tasks found")
            return False
            
    except Exception as e:
        print(f"❌ Worker availability check failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Starting Celery Migration Validation Tests")
    print("=" * 50)
    
    tests = [
        ("Redis Connection", test_redis_connection),
        ("Celery Connection", test_celery_connection),
        ("Worker Availability", test_worker_availability),
    ]
    
    results = {}
    
    # Run basic connectivity tests
    for test_name, test_func in tests:
        results[test_name] = test_func()
        print()
    
    # Only run task tests if basic connectivity works
    if all(results.values()):
        print("🔍 Running task execution tests...")
        task_id, batch_id = test_task_submission()
        print()
        
        if task_id:
            results["Task Submission"] = True
            results["Task Execution"] = test_task_status_tracking(task_id, batch_id)
        else:
            results["Task Submission"] = False
            results["Task Execution"] = False
    else:
        print("⚠️  Skipping task tests due to connectivity issues")
        results["Task Submission"] = False
        results["Task Execution"] = False
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<20}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Celery migration successful!")
        return 0
    else:
        print("⚠️  Some tests failed. Check the issues above.")
        return 1

if __name__ == "__main__":
    exit(main())

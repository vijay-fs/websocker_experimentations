#!/usr/bin/env python3
"""
Standalone Flower monitoring script that doesn't import the main FastAPI application.
This prevents conflicts and ensures Flower runs independently.
"""
import os
import sys
from flower.command import FlowerCommand

if __name__ == '__main__':
    # Set up Flower command with broker URL
    broker_url = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
    
    # Flower command arguments
    sys.argv = [
        'flower',
        '--broker=' + broker_url,
        '--port=5555',
        '--basic_auth=admin:admin',
        '--address=0.0.0.0'
    ]
    
    # Start Flower
    flower_cmd = FlowerCommand()
    flower_cmd.execute_from_commandline()

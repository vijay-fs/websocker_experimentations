# Use Python 3.11 for better package compatibility
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for CPU processing and Redis
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libfontconfig1 \
    libjpeg-dev \
    zlib1g-dev \
    libtiff5-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libwebp-dev \
    gcc \
    python3-dev \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Install NumPy first as it's a common dependency
RUN pip install --no-cache-dir numpy>=1.24.0

# Copy and install remaining requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create a non-root user first
RUN useradd -m appuser

# Create model cache directory and set permissions
RUN mkdir -p /home/appuser/.EasyOCR && chown -R appuser:appuser /home/appuser

# Download EasyOCR models during build as root first
RUN python -c "import easyocr; reader = easyocr.Reader(['en']); print('Models downloaded successfully')"

# Copy models to user directory
RUN cp -r /root/.EasyOCR/* /home/appuser/.EasyOCR/ 2>/dev/null || true

# Make scripts executable and fix permissions
RUN chmod +x /app/entrypoint.sh && chown -R appuser:appuser /app

# Expose port
EXPOSE 8000

# Switch to non-root user
USER appuser

# Set environment variables with safe defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    REDIS_HOST=localhost \
    REDIS_PORT=6379 \
    REDIS_URL=redis://localhost:6379/0 \
    RQ_REDIS_URL=redis://localhost:6379/0 \
    SOCKETIO_SERVER_URL=http://websocket-server:8001

# Remove the inline entrypoint script creation since we have a separate entrypoint.sh file

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command (can be overridden in docker-compose)
CMD ["api"]

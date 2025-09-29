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
RUN pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y torch torchvision \
    && pip install --no-cache-dir torch==2.0.1+cpu torchvision==0.15.2+cpu -f https://download.pytorch.org/whl/torch_stable.html

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Make scripts executable
RUN chmod +x /app/entrypoint.sh

# Create a non-root user and switch to it
RUN useradd -m appuser && chown -R appuser:appuser /app

# Create EasyOCR model directory with proper permissions and pre-download models
RUN mkdir -p /home/appuser/.EasyOCR/model && \
    chown -R appuser:appuser /home/appuser/.EasyOCR

# Pre-download EasyOCR models as root to prevent runtime downloads
RUN python -c "import easyocr; reader = easyocr.Reader(['en'], gpu=False, model_storage_directory='/home/appuser/.EasyOCR', download_enabled=True)" || true

# Fix ownership after model download
RUN chown -R appuser:appuser /home/appuser/.EasyOCR

USER appuser

# Set environment variables with safe defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    REDIS_HOST=localhost \
    REDIS_PORT=6379 \
    REDIS_URL=redis://localhost:6379/0 \
    RQ_REDIS_URL=redis://localhost:6379/0

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command (can be overridden in docker-compose)
CMD ["api"]

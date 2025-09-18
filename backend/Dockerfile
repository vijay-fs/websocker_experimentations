# Use Python 3.13 to match local environment
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies required by EasyOCR and build tools
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libgthread-2.0-0 \
    libfontconfig1 \
    libgtk-3-0 \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "main.py"]

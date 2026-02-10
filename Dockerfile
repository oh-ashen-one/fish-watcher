# Fish Watcher Docker Image
# Build: docker build -t fish-watcher .
# Run:   docker run -d --device /dev/video0 -p 5555:5555 -v ./clips:/app/clips fish-watcher

FROM python:3.11-slim

# Install OpenCV dependencies
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libv4l-dev \
    v4l-utils \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create directories
RUN mkdir -p clips data

# Expose dashboard port
EXPOSE 5555

# Default command: run watcher
CMD ["python", "run.py"]

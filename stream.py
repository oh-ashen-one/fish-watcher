#!/usr/bin/env python3
"""
Fish Watcher Live Stream Server
MJPEG stream with timestamp overlay
LOCAL ONLY - secured with token auth
"""

import cv2
import yaml
import time
import secrets
from datetime import datetime
from flask import Flask, Response, request, abort
from pathlib import Path

app = Flask(__name__)

def require_password(f):
    """Decorator to require valid password"""
    def wrapper(*args, **kwargs):
        pwd = request.args.get('p') or request.args.get('password')
        if pwd != STREAM_PASSWORD:
            abort(403)
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# Load config
config_path = Path(__file__).parent / "config.yaml"
config = {}
if config_path.exists():
    with open(config_path) as f:
        config = yaml.safe_load(f) or {}

CAMERA_DEVICE = config.get("camera", {}).get("device", 0)

# Stream password - from config or generate random
STREAM_PASSWORD = config.get("stream", {}).get("password")
if not STREAM_PASSWORD:
    # Fallback to random token if no password configured
    STREAM_PASSWORD = secrets.token_urlsafe(16)
    print(f"⚠️  No password in config — using random token: {STREAM_PASSWORD}")

# Stream settings
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS = 60  # Smooth 60fps
QUALITY = 85  # JPEG quality


def add_timestamp(frame):
    """Add timestamp overlay to frame"""
    timestamp = datetime.now().strftime("%b %d, %I:%M:%S %p")
    
    # Add black background for readability
    cv2.rectangle(frame, (5, 5), (280, 35), (0, 0, 0), -1)
    
    # Add timestamp text
    cv2.putText(
        frame,
        f"LIVE {timestamp}",
        (10, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 255),  # Cyan color
        2
    )
    return frame


def generate_frames():
    """Generate MJPEG frames from camera"""
    camera = cv2.VideoCapture(CAMERA_DEVICE)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    camera.set(cv2.CAP_PROP_FPS, FPS)
    
    frame_time = 1.0 / FPS
    
    try:
        while True:
            start = time.time()
            
            success, frame = camera.read()
            if not success:
                # Try to reconnect
                camera.release()
                time.sleep(1)
                camera = cv2.VideoCapture(CAMERA_DEVICE)
                continue
            
            # Add timestamp overlay
            frame = add_timestamp(frame)
            
            # Encode as JPEG
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, QUALITY])
            if not ret:
                continue
                
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            # Rate limiting
            elapsed = time.time() - start
            if elapsed < frame_time:
                time.sleep(frame_time - elapsed)
                
    finally:
        camera.release()


@app.route('/')
@require_password
def index():
    """Simple HTML page with the stream"""
    pwd = request.args.get('p') or request.args.get('password')
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🐟 Fish Watcher Live</title>
        <style>
            body {
                background: #1a1a2e;
                color: #eee;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
                padding: 20px;
                box-sizing: border-box;
            }
            h1 {
                color: #00d4ff;
                margin-bottom: 20px;
            }
            .stream-container {
                border: 3px solid #00d4ff;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 0 30px rgba(0, 212, 255, 0.3);
            }
            img {
                display: block;
                max-width: 100%;
            }
            .status {
                margin-top: 15px;
                color: #00ff88;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <h1>🐟 Fish Watcher Live</h1>
        <div class="stream-container">
            <img src="/stream?p={pwd}" alt="Live Feed">
        </div>
        <div class="status">● Live</div>
    </body>
    </html>
    '''


@app.route('/stream')
@require_password
def stream():
    """MJPEG stream endpoint"""
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


if __name__ == '__main__':
    print("🐟 Fish Watcher Live Stream")
    print(f"📺 Stream URL: http://localhost:5555/?p={STREAM_PASSWORD}")
    print(f"📷 Camera: Device {CAMERA_DEVICE}")
    print(f"🔐 Password: {STREAM_PASSWORD}")
    print("\n⚠️  Only share this link with the user!")
    print("Press Ctrl+C to stop\n")
    
    # Bind to localhost only — no external access without tunnel
    app.run(host='127.0.0.1', port=5555, threaded=True)

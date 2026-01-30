#!/usr/bin/env python3
"""
Fish Watcher Live Stream Server
MJPEG stream with timestamp overlay
LOCAL ONLY - secured with password auth
"""

import cv2
import yaml
import time
import secrets
from datetime import datetime
from flask import Flask, Response, request, abort
from pathlib import Path

app = Flask(__name__)

# Load config
config_path = Path(__file__).parent / "config.yaml"
config = {}
if config_path.exists():
    with open(config_path) as f:
        config = yaml.safe_load(f) or {}

# Stream config
stream_config = config.get("stream", {})

# Stream password - from config or generate random
STREAM_PASSWORD = stream_config.get("password")
if not STREAM_PASSWORD:
    # Fallback to random token if no password configured
    STREAM_PASSWORD = secrets.token_urlsafe(16)
    print(f"⚠️  No password in config — using random token: {STREAM_PASSWORD}")

# Stream settings from config (with defaults)
STREAM_PORT = stream_config.get("port", 5555)
FPS = stream_config.get("fps", 60)
QUALITY = stream_config.get("quality", 85)

# Camera settings from config
camera_config = config.get("camera", {})
CAMERA_DEVICE = camera_config.get("device", 0)
FRAME_WIDTH = camera_config.get("width", 640)
FRAME_HEIGHT = camera_config.get("height", 480)


def require_password(f):
    """Decorator to require valid password"""
    def wrapper(*args, **kwargs):
        pwd = request.args.get('p') or request.args.get('password')
        if pwd != STREAM_PASSWORD:
            abort(403)
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


def add_timestamp(frame):
    """Add timestamp overlay to frame"""
    timestamp = datetime.now().strftime("%b %d, %I:%M:%S %p")
    text = f"LIVE  {timestamp}"
    
    # Calculate text size to fit background properly
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.6
    thickness = 2
    (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    
    # Add black background with padding
    padding = 10
    cv2.rectangle(
        frame, 
        (5, 5), 
        (5 + text_width + padding * 2, 5 + text_height + padding * 2), 
        (0, 0, 0), 
        -1
    )
    
    # Add timestamp text
    cv2.putText(
        frame,
        text,
        (5 + padding, 5 + padding + text_height),
        font,
        font_scale,
        (0, 255, 255),  # Cyan color
        thickness
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
    print(f"📺 Stream URL: http://localhost:{STREAM_PORT}/?p={STREAM_PASSWORD}")
    print(f"📷 Camera: Device {CAMERA_DEVICE} ({FRAME_WIDTH}x{FRAME_HEIGHT})")
    print(f"🎬 FPS: {FPS} | Quality: {QUALITY}")
    print(f"🔐 Password: {STREAM_PASSWORD}")
    print("\n⚠️  Only share this link with the user!")
    print("Press Ctrl+C to stop\n")
    
    # Bind to localhost only — no external access without tunnel
    app.run(host='127.0.0.1', port=STREAM_PORT, threaded=True)

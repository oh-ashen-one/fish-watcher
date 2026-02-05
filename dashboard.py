#!/usr/bin/env python3
"""
Fish Watcher Web Dashboard
View status, clips, and live stream from any browser.
"""

import os
import json
import yaml
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, Response, request, abort, jsonify, send_from_directory

app = Flask(__name__)

# Load config
BASE_DIR = Path(__file__).parent
config_path = BASE_DIR / "config.yaml"
config = {}
if config_path.exists():
    with open(config_path) as f:
        config = yaml.safe_load(f) or {}

# Dashboard settings
stream_config = config.get("stream", {})
DASHBOARD_PORT = stream_config.get("port", 5555)
DASHBOARD_PASSWORD = stream_config.get("password")
if not DASHBOARD_PASSWORD:
    DASHBOARD_PASSWORD = secrets.token_urlsafe(16)
    print(f"⚠️  No password in config — using random token: {DASHBOARD_PASSWORD}")

# Directories
CLIPS_DIR = Path(config.get("recording", {}).get("output_dir", "./clips"))
DATA_DIR = Path(config.get("reports", {}).get("data_dir", "./data"))


def require_password(f):
    """Decorator to require valid password"""
    def wrapper(*args, **kwargs):
        pwd = request.args.get('p') or request.args.get('password')
        if pwd != DASHBOARD_PASSWORD:
            abort(403)
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


def get_clips():
    """Get list of recorded clips"""
    clips = []
    if CLIPS_DIR.exists():
        for f in sorted(CLIPS_DIR.glob("*.mp4"), reverse=True):
            stat = f.stat()
            # Parse filename: 20260129_183045_no_motion.mp4
            name = f.stem
            parts = name.split("_", 2)
            
            date_str = parts[0] if len(parts) > 0 else ""
            time_str = parts[1] if len(parts) > 1 else ""
            alert_type = parts[2] if len(parts) > 2 else "unknown"
            
            # Parse datetime
            try:
                dt = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                timestamp = dt.isoformat()
                friendly_time = dt.strftime("%b %d, %I:%M %p")
            except:
                timestamp = ""
                friendly_time = name
            
            clips.append({
                "filename": f.name,
                "alert_type": alert_type.replace("_", " ").title(),
                "timestamp": timestamp,
                "friendly_time": friendly_time,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
            })
    return clips[:50]  # Limit to most recent 50


def get_status():
    """Get current status from data files"""
    status = {
        "health_score": None,
        "last_alert": None,
        "alerts_today": 0,
        "clips_today": 0,
        "uptime": None,
    }
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Try to read today's data
    today_file = DATA_DIR / f"daily_{today}.json"
    if today_file.exists():
        try:
            with open(today_file) as f:
                data = json.load(f)
                status["health_score"] = data.get("health_score")
                status["alerts_today"] = data.get("alert_count", 0)
                status["clips_today"] = data.get("clip_count", 0)
        except:
            pass
    
    # Get last alert from clips
    clips = get_clips()
    if clips:
        status["last_alert"] = {
            "type": clips[0]["alert_type"],
            "time": clips[0]["friendly_time"],
        }
    
    return status


def get_recent_alerts():
    """Get recent alerts from data files"""
    alerts = []
    
    # Look at last 7 days of data
    for i in range(7):
        day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        day_file = DATA_DIR / f"daily_{day}.json"
        
        if day_file.exists():
            try:
                with open(day_file) as f:
                    data = json.load(f)
                    for alert in data.get("alerts", [])[-10:]:
                        alerts.append({
                            "type": alert.get("type", "unknown"),
                            "timestamp": alert.get("timestamp", day),
                            "is_cool": alert.get("is_cool_moment", False),
                        })
            except:
                pass
    
    return alerts[:20]  # Most recent 20


# ============ HTML Templates ============

def base_html(title, content, pwd):
    """Base HTML template"""
    return f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Fish Watcher</title>
    <style>
        :root {{
            --bg: #0f0f1a;
            --card: #1a1a2e;
            --accent: #00d4ff;
            --accent2: #00ff88;
            --text: #e0e0e0;
            --text-dim: #888;
            --danger: #ff4757;
            --warning: #ffa502;
        }}
        
        * {{ box-sizing: border-box; }}
        
        body {{
            background: var(--bg);
            color: var(--text);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            line-height: 1.6;
        }}
        
        .navbar {{
            background: var(--card);
            padding: 15px 30px;
            display: flex;
            align-items: center;
            gap: 30px;
            border-bottom: 1px solid rgba(0, 212, 255, 0.2);
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        
        .navbar .logo {{
            font-size: 1.5rem;
            font-weight: bold;
            color: var(--accent);
            text-decoration: none;
        }}
        
        .navbar nav a {{
            color: var(--text-dim);
            text-decoration: none;
            padding: 8px 16px;
            border-radius: 8px;
            transition: all 0.2s;
        }}
        
        .navbar nav a:hover, .navbar nav a.active {{
            color: var(--accent);
            background: rgba(0, 212, 255, 0.1);
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 30px;
        }}
        
        h1, h2, h3 {{
            color: var(--accent);
            margin-top: 0;
        }}
        
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .card {{
            background: var(--card);
            border-radius: 12px;
            padding: 24px;
            border: 1px solid rgba(0, 212, 255, 0.1);
        }}
        
        .card h3 {{
            margin-bottom: 15px;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-dim);
        }}
        
        .stat {{
            font-size: 2.5rem;
            font-weight: bold;
            color: var(--accent2);
        }}
        
        .stat.warning {{ color: var(--warning); }}
        .stat.danger {{ color: var(--danger); }}
        
        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        .badge.cool {{ background: rgba(0, 255, 136, 0.2); color: var(--accent2); }}
        .badge.alert {{ background: rgba(255, 71, 87, 0.2); color: var(--danger); }}
        
        .clip-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }}
        
        .clip-card {{
            background: var(--card);
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid rgba(0, 212, 255, 0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        .clip-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 10px 30px rgba(0, 212, 255, 0.2);
        }}
        
        .clip-card video {{
            width: 100%;
            display: block;
        }}
        
        .clip-card .info {{
            padding: 15px;
        }}
        
        .clip-card .type {{
            font-weight: 600;
            color: var(--accent);
        }}
        
        .clip-card .meta {{
            font-size: 0.85rem;
            color: var(--text-dim);
            margin-top: 5px;
        }}
        
        .stream-container {{
            border: 3px solid var(--accent);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 0 30px rgba(0, 212, 255, 0.3);
            max-width: 800px;
            margin: 0 auto;
        }}
        
        .stream-container img {{
            width: 100%;
            display: block;
        }}
        
        .live-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(255, 71, 87, 0.2);
            color: var(--danger);
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 20px;
        }}
        
        .live-badge::before {{
            content: "";
            width: 8px;
            height: 8px;
            background: var(--danger);
            border-radius: 50%;
            animation: pulse 1.5s infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.4; }}
        }}
        
        .alert-list {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        
        .alert-list li {{
            padding: 12px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .alert-list li:last-child {{
            border-bottom: none;
        }}
        
        .empty {{
            text-align: center;
            padding: 60px 20px;
            color: var(--text-dim);
        }}
        
        .empty .icon {{
            font-size: 4rem;
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
    <header class="navbar">
        <a href="/?p={pwd}" class="logo">🐟 Fish Watcher</a>
        <nav>
            <a href="/?p={pwd}">Dashboard</a>
            <a href="/clips?p={pwd}">Clips</a>
            <a href="/live?p={pwd}">Live</a>
        </nav>
    </header>
    <main class="container">
        {content}
    </main>
</body>
</html>
'''


# ============ Routes ============

@app.route('/')
@require_password
def dashboard():
    """Main dashboard page"""
    pwd = request.args.get('p') or request.args.get('password')
    status = get_status()
    clips = get_clips()[:5]
    alerts = get_recent_alerts()[:5]
    
    # Health score display
    health = status.get("health_score")
    if health is not None:
        health_class = "" if health >= 80 else "warning" if health >= 50 else "danger"
        health_display = f'{health}/100'
    else:
        health_class = ""
        health_display = "—"
    
    # Last alert display
    last_alert = status.get("last_alert")
    last_alert_html = f'{last_alert["type"]}<br><small style="color: var(--text-dim)">{last_alert["time"]}</small>' if last_alert else "None"
    
    # Recent clips HTML
    clips_html = ""
    for clip in clips:
        clips_html += f'''
        <div class="clip-card">
            <video controls preload="metadata">
                <source src="/clips/{clip["filename"]}?p={pwd}" type="video/mp4">
            </video>
            <div class="info">
                <div class="type">{clip["alert_type"]}</div>
                <div class="meta">{clip["friendly_time"]} • {clip["size_mb"]} MB</div>
            </div>
        </div>
        '''
    
    if not clips_html:
        clips_html = '<div class="empty"><div class="icon">📹</div><p>No clips recorded yet</p></div>'
    
    # Recent alerts HTML
    alerts_html = ""
    for alert in alerts:
        badge_class = "cool" if alert.get("is_cool") else "alert"
        badge_text = "✨ Cool" if alert.get("is_cool") else "⚠️ Alert"
        alerts_html += f'''
        <li>
            <span>{alert["type"].replace("_", " ").title()}</span>
            <span class="badge {badge_class}">{badge_text}</span>
        </li>
        '''
    
    if not alerts_html:
        alerts_html = '<li style="color: var(--text-dim)">No recent alerts</li>'
    
    content = f'''
    <h1>Dashboard</h1>
    
    <div class="grid">
        <div class="card">
            <h3>🏥 Health Score</h3>
            <div class="stat {health_class}">{health_display}</div>
        </div>
        
        <div class="card">
            <h3>🚨 Alerts Today</h3>
            <div class="stat">{status.get("alerts_today", 0)}</div>
        </div>
        
        <div class="card">
            <h3>📹 Clips Today</h3>
            <div class="stat">{status.get("clips_today", 0)}</div>
        </div>
        
        <div class="card">
            <h3>⏰ Last Alert</h3>
            <div style="font-size: 1.2rem">{last_alert_html}</div>
        </div>
    </div>
    
    <h2>Recent Clips</h2>
    <div class="clip-grid" style="margin-bottom: 40px;">
        {clips_html}
    </div>
    
    <h2>Recent Activity</h2>
    <div class="card">
        <ul class="alert-list">
            {alerts_html}
        </ul>
    </div>
    '''
    
    return base_html("Dashboard", content, pwd)


@app.route('/clips')
@require_password
def clips_page():
    """Clips browser page"""
    pwd = request.args.get('p') or request.args.get('password')
    clips = get_clips()
    
    clips_html = ""
    for clip in clips:
        clips_html += f'''
        <div class="clip-card">
            <video controls preload="metadata">
                <source src="/clips/{clip["filename"]}?p={pwd}" type="video/mp4">
            </video>
            <div class="info">
                <div class="type">{clip["alert_type"]}</div>
                <div class="meta">{clip["friendly_time"]} • {clip["size_mb"]} MB</div>
            </div>
        </div>
        '''
    
    if not clips_html:
        clips_html = '<div class="empty"><div class="icon">📹</div><p>No clips recorded yet.<br>Clips will appear here when alerts are triggered.</p></div>'
    
    content = f'''
    <h1>Clips</h1>
    <p style="color: var(--text-dim); margin-bottom: 30px;">
        Showing {len(clips)} most recent clips. Each clip includes 10 seconds before the trigger.
    </p>
    <div class="clip-grid">
        {clips_html}
    </div>
    '''
    
    return base_html("Clips", content, pwd)


@app.route('/live')
@require_password
def live_page():
    """Live stream page"""
    pwd = request.args.get('p') or request.args.get('password')
    
    content = f'''
    <h1>Live Stream</h1>
    <div class="live-badge">LIVE</div>
    <div class="stream-container">
        <img src="/stream?p={pwd}" alt="Live Feed">
    </div>
    <p style="text-align: center; color: var(--text-dim); margin-top: 20px;">
        Refresh the page if the stream disconnects.
    </p>
    '''
    
    return base_html("Live", content, pwd)


@app.route('/stream')
@require_password
def stream():
    """MJPEG stream endpoint - delegates to stream.py logic"""
    import cv2
    import time
    from datetime import datetime
    
    camera_config = config.get("camera", {})
    device = camera_config.get("device", 0)
    width = camera_config.get("width", 640)
    height = camera_config.get("height", 480)
    fps = stream_config.get("fps", 30)
    quality = stream_config.get("quality", 85)
    
    def add_timestamp(frame):
        timestamp = datetime.now().strftime("%b %d, %I:%M:%S %p")
        text = f"LIVE  {timestamp}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        (tw, th), _ = cv2.getTextSize(text, font, 0.6, 2)
        cv2.rectangle(frame, (5, 5), (15 + tw + 10, 15 + th + 10), (0, 0, 0), -1)
        cv2.putText(frame, text, (15, 15 + th), font, 0.6, (0, 255, 255), 2)
        return frame
    
    def generate():
        camera = cv2.VideoCapture(device)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        camera.set(cv2.CAP_PROP_FPS, fps)
        frame_time = 1.0 / fps
        
        try:
            while True:
                start = time.time()
                success, frame = camera.read()
                if not success:
                    camera.release()
                    time.sleep(1)
                    camera = cv2.VideoCapture(device)
                    continue
                
                frame = add_timestamp(frame)
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                
                elapsed = time.time() - start
                if elapsed < frame_time:
                    time.sleep(frame_time - elapsed)
        finally:
            camera.release()
    
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/clips/<filename>')
@require_password
def serve_clip(filename):
    """Serve a clip file"""
    # Security: ensure filename doesn't contain path traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        abort(404)
    return send_from_directory(CLIPS_DIR, filename)


# ============ API Endpoints ============

@app.route('/api/status')
@require_password
def api_status():
    """API: Get current status"""
    return jsonify(get_status())


@app.route('/api/clips')
@require_password
def api_clips():
    """API: Get list of clips"""
    return jsonify(get_clips())


@app.route('/api/alerts')
@require_password
def api_alerts():
    """API: Get recent alerts"""
    return jsonify(get_recent_alerts())


# ============ Main ============

if __name__ == '__main__':
    print("🐟 Fish Watcher Dashboard")
    print(f"📊 Dashboard URL: http://localhost:{DASHBOARD_PORT}/?p={DASHBOARD_PASSWORD}")
    print(f"📺 Live Stream:   http://localhost:{DASHBOARD_PORT}/live?p={DASHBOARD_PASSWORD}")
    print(f"📹 Clips:         http://localhost:{DASHBOARD_PORT}/clips?p={DASHBOARD_PASSWORD}")
    print(f"🔐 Password: {DASHBOARD_PASSWORD}")
    print("\n⚠️  Only share this URL with trusted users!")
    print("Press Ctrl+C to stop\n")
    
    # Ensure clips directory exists
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    app.run(host='127.0.0.1', port=DASHBOARD_PORT, threaded=True)

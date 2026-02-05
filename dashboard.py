#!/usr/bin/env python3
"""
Fish Watcher Web Dashboard
View status, clips, and live stream from any browser.
"""

import json
import yaml
import secrets
from datetime import datetime
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

stream_config = config.get("stream", {})
DASHBOARD_PORT = stream_config.get("port", 5555)
DASHBOARD_PASSWORD = stream_config.get("password") or secrets.token_urlsafe(16)
CLIPS_DIR = Path(config.get("recording", {}).get("output_dir", "./clips"))
DATA_DIR = Path(config.get("reports", {}).get("data_dir", "./data"))


def require_password(f):
    def wrapper(*args, **kwargs):
        pwd = request.args.get('p') or request.args.get('password')
        if pwd != DASHBOARD_PASSWORD:
            abort(403)
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


def get_clips():
    clips = []
    if CLIPS_DIR.exists():
        for f in sorted(CLIPS_DIR.glob("*.mp4"), reverse=True)[:50]:
            stat = f.stat()
            parts = f.stem.split("_", 2)
            try:
                dt = datetime.strptime(f"{parts[0]}_{parts[1]}", "%Y%m%d_%H%M%S")
                friendly = dt.strftime("%b %d, %I:%M %p")
            except:
                friendly = f.stem
            clips.append({
                "filename": f.name,
                "alert_type": (parts[2] if len(parts) > 2 else "unknown").replace("_", " ").title(),
                "friendly_time": friendly,
                "size_mb": round(stat.st_size / 1048576, 2),
            })
    return clips


def get_status():
    status = {"health_score": None, "alerts_today": 0, "clips_today": 0, "last_alert": None}
    today_file = DATA_DIR / f"daily_{datetime.now().strftime('%Y-%m-%d')}.json"
    if today_file.exists():
        try:
            data = json.load(open(today_file))
            status.update(health_score=data.get("health_score"), alerts_today=data.get("alert_count", 0), clips_today=data.get("clip_count", 0))
        except: pass
    clips = get_clips()
    if clips:
        status["last_alert"] = {"type": clips[0]["alert_type"], "time": clips[0]["friendly_time"]}
    return status


STYLE = ''':root{--bg:#0f0f1a;--card:#1a1a2e;--accent:#00d4ff;--accent2:#00ff88;--text:#e0e0e0;--dim:#888;--danger:#ff4757}*{box-sizing:border-box}body{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:0;padding:0;line-height:1.6}.navbar{background:var(--card);padding:15px 30px;display:flex;align-items:center;gap:30px;border-bottom:1px solid rgba(0,212,255,.2);position:sticky;top:0;z-index:100}.navbar .logo{font-size:1.5rem;font-weight:bold;color:var(--accent);text-decoration:none}.navbar nav a{color:var(--dim);text-decoration:none;padding:8px 16px;border-radius:8px;transition:all .2s}.navbar nav a:hover{color:var(--accent);background:rgba(0,212,255,.1)}.container{max-width:1200px;margin:0 auto;padding:30px}h1,h2{color:var(--accent);margin-top:0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:20px;margin-bottom:30px}.card{background:var(--card);border-radius:12px;padding:24px;border:1px solid rgba(0,212,255,.1)}.card h3{margin:0 0 15px;font-size:.9rem;text-transform:uppercase;letter-spacing:1px;color:var(--dim)}.stat{font-size:2.5rem;font-weight:bold;color:var(--accent2)}.clip-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:20px}.clip-card{background:var(--card);border-radius:12px;overflow:hidden;border:1px solid rgba(0,212,255,.1);transition:transform .2s}.clip-card:hover{transform:translateY(-4px);box-shadow:0 10px 30px rgba(0,212,255,.2)}.clip-card video{width:100%;display:block}.clip-card .info{padding:15px}.clip-card .type{font-weight:600;color:var(--accent)}.clip-card .meta{font-size:.85rem;color:var(--dim);margin-top:5px}.stream-container{border:3px solid var(--accent);border-radius:12px;overflow:hidden;box-shadow:0 0 30px rgba(0,212,255,.3);max-width:800px;margin:0 auto}.stream-container img{width:100%;display:block}.live-badge{display:inline-flex;align-items:center;gap:6px;background:rgba(255,71,87,.2);color:var(--danger);padding:6px 12px;border-radius:20px;font-weight:600;margin-bottom:20px}.empty{text-align:center;padding:60px 20px;color:var(--dim)}'''


def html(title, content, pwd):
    return f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} - Fish Watcher</title><style>{STYLE}</style></head><body><header class="navbar"><a href="/?p={pwd}" class="logo">🐟 Fish Watcher</a><nav><a href="/?p={pwd}">Dashboard</a><a href="/clips?p={pwd}">Clips</a><a href="/live?p={pwd}">Live</a></nav></header><main class="container">{content}</main></body></html>'''


@app.route('/')
@require_password
def dashboard():
    pwd = request.args.get('p') or request.args.get('password')
    s = get_status()
    clips = get_clips()[:5]
    h = f'{s["health_score"]}/100' if s["health_score"] else "—"
    la = f'{s["last_alert"]["type"]}<br><small style="color:var(--dim)">{s["last_alert"]["time"]}</small>' if s["last_alert"] else "None"
    ch = "".join(f'<div class="clip-card"><video controls preload="metadata"><source src="/clips/{c["filename"]}?p={pwd}" type="video/mp4"></video><div class="info"><div class="type">{c["alert_type"]}</div><div class="meta">{c["friendly_time"]} • {c["size_mb"]} MB</div></div></div>' for c in clips) or '<div class="empty">📹 No clips yet</div>'
    return html("Dashboard", f'<h1>Dashboard</h1><div class="grid"><div class="card"><h3>🏥 Health</h3><div class="stat">{h}</div></div><div class="card"><h3>🚨 Alerts Today</h3><div class="stat">{s["alerts_today"]}</div></div><div class="card"><h3>📹 Clips Today</h3><div class="stat">{s["clips_today"]}</div></div><div class="card"><h3>⏰ Last Alert</h3><div style="font-size:1.2rem">{la}</div></div></div><h2>Recent Clips</h2><div class="clip-grid">{ch}</div>', pwd)


@app.route('/clips')
@require_password
def clips_page():
    pwd = request.args.get('p') or request.args.get('password')
    clips = get_clips()
    ch = "".join(f'<div class="clip-card"><video controls preload="metadata"><source src="/clips/{c["filename"]}?p={pwd}" type="video/mp4"></video><div class="info"><div class="type">{c["alert_type"]}</div><div class="meta">{c["friendly_time"]} • {c["size_mb"]} MB</div></div></div>' for c in clips) or '<div class="empty">📹 No clips yet</div>'
    return html("Clips", f'<h1>Clips</h1><p style="color:var(--dim);margin-bottom:30px">{len(clips)} clips</p><div class="clip-grid">{ch}</div>', pwd)


@app.route('/live')
@require_password
def live_page():
    pwd = request.args.get('p') or request.args.get('password')
    return html("Live", f'<h1>Live Stream</h1><div class="live-badge">● LIVE</div><div class="stream-container"><img src="/stream?p={pwd}" alt="Live"></div><p style="text-align:center;color:var(--dim);margin-top:20px">Refresh if disconnected</p>', pwd)


@app.route('/stream')
@require_password
def stream():
    import cv2, time
    cam = config.get("camera", {})
    dev, fps, q = cam.get("device", 0), stream_config.get("fps", 30), stream_config.get("quality", 85)
    def gen():
        c = cv2.VideoCapture(dev)
        try:
            while True:
                ok, f = c.read()
                if not ok: time.sleep(1); c = cv2.VideoCapture(dev); continue
                cv2.putText(f, f"LIVE  {datetime.now().strftime('%b %d, %I:%M:%S %p')}", (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                _, b = cv2.imencode('.jpg', f, [cv2.IMWRITE_JPEG_QUALITY, q])
                yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + b.tobytes() + b'\r\n'
                time.sleep(1/fps)
        finally: c.release()
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/clips/<fn>')
@require_password
def serve_clip(fn):
    if '..' in fn or '/' in fn or '\\' in fn: abort(404)
    return send_from_directory(CLIPS_DIR, fn)


@app.route('/api/status')
@require_password
def api_status(): return jsonify(get_status())


@app.route('/api/clips')
@require_password
def api_clips(): return jsonify(get_clips())


if __name__ == '__main__':
    print(f"🐟 Fish Watcher Dashboard\n📊 http://localhost:{DASHBOARD_PORT}/?p={DASHBOARD_PASSWORD}\n🔐 {DASHBOARD_PASSWORD}\n")
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    app.run(host='127.0.0.1', port=DASHBOARD_PORT, threaded=True)

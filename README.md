# 🐟 Fish Watcher

AI-powered fish tank monitoring that watches your aquarium 24/7, alerts you when something's wrong, and clips cool moments.

## What It Does

### 🚨 Health & Emergency Detection
- Fish not moving (dead/sick check)
- Fish floating at surface
- Fish stuck at bottom
- Erratic swimming (spinning, darting)
- Gasping at surface (oxygen issues)
- Fish aggression

### 🔧 Tank Issue Detection
- Water cloudiness
- Algae growth (green tint)
- Filter stopped (no bubbles)
- Water color changes

### 🐟 Behavior Analysis
- Fish clustering in corners (stress)
- Hiding too long
- Activity levels below normal
- Fish count tracking

### ✨ Cool Moment Capture
- Feeding frenzies
- Interesting activity
- Fish playing/interacting
- Unusual behaviors worth saving

### 📊 Reports
- Daily health score (0-100)
- Weekly trends
- Activity tracking

---

## 🖥️ Web Dashboard (NEW!)

Access everything from your browser:

```bash
python dashboard.py
```

Opens at `http://localhost:5555/?p=<password>`

**Features:**
- **Dashboard** — Health score, alerts today, recent activity
- **Clips Browser** — Watch all recorded clips with inline video player
- **Live Stream** — Real-time camera feed with timestamp overlay
- **API** — JSON endpoints for integrations (`/api/status`, `/api/clips`, `/api/alerts`)

Password protected — only share the URL with people you trust.

---

## 🧠 Claude Vision Analysis (NEW!)

When an alert triggers, Fish Watcher can use Claude to analyze the clip and provide intelligent insights:

```
📊 Vision Analysis:
   Summary: Fish appears to be resting near bottom, normal behavior for this time of day
   Severity: normal
   👁️ Observations:
      - Clear water with good visibility
      - Fish colors appear healthy and vibrant
      - Normal fin position and movement
   💡 Recommendations:
      - No action needed
```

**Setup:** Set `ANTHROPIC_API_KEY` env var or have `claude` CLI installed. Enable in config:

```yaml
vision:
  enabled: true
  model: "claude-sonnet-4-20250514"
```

---

## Quick Start

### Option A: Telegram Setup (Recommended)

If you have [Clawdbot](https://github.com/clawdbot/clawdbot), just say:

> "Set up fish watcher" or "Monitor my fish tank"

Your AI assistant will:
1. Install everything automatically
2. Find your camera
3. Send you a test snapshot to confirm
4. Start monitoring

All via Telegram chat. No terminal needed.

---

### Option B: Manual Setup (2 minutes)

```bash
# 1. Clone & Install
git clone https://github.com/oh-ashen-one/fish-watcher.git
cd fish-watcher
pip install -r requirements.txt

# 2. Test Camera
python test_camera.py

# 3. Run
python run.py
```

That's it. It's now watching your tank 24/7.

---

## Camera Options

### USB Webcam (Easiest)
Just plug it in. Device is usually `0` or `1`.

```yaml
camera:
  type: "usb"
  device: 0
```

### Phone as Webcam
Install DroidCam, Iriun, or IP Webcam on your phone:

```yaml
camera:
  type: "ip"
  url: "http://192.168.1.100:4747/video"  # DroidCam
  # url: "http://192.168.1.100:8080/video"  # IP Webcam
```

### IP Camera / RTSP
```yaml
camera:
  type: "rtsp"
  url: "rtsp://192.168.1.100:554/stream"
```

---

## How It Works

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Camera    │────▶│ Rolling      │────▶│  Detectors  │
│   Feed      │     │ Buffer (10s) │     │  (6 types)  │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
                              Alert triggered?  │
                                                ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  You get    │◀────│  Clawdbot    │◀────│ Save Clip   │
│  notified   │     │  analyzes    │     │ (40 sec)    │
└─────────────┘     └──────────────┘     └─────────────┘
```

**The magic:** The rolling buffer keeps the last 10 seconds always. So when something triggers, you get footage from BEFORE it happened.

---

## Clips

Saved to `./clips/` with format:
```
20260129_183045_no_motion.mp4
20260129_194522_feeding_frenzy.mp4
```

Each clip is 40 seconds: 10 sec before trigger + 30 sec after.

---

## Configuration

All settings in `config.yaml`:

| Setting | What It Does | Default |
|---------|--------------|---------|
| `recording.pre_roll` | Seconds before trigger | 10 |
| `recording.post_roll` | Seconds after trigger | 30 |
| `detection.motion_sensitivity` | 0-100, higher = more sensitive | 50 |
| `detection.no_motion_threshold` | Seconds before "no motion" alert | 300 (5 min) |
| `alerts.cooldown` | Min seconds between same alert | 60 |
| `alerts.clip_cool_moments` | Also clip good moments, not just problems | true |

---

## Telegram Commands

Once set up with Clawdbot, just chat naturally:

| You Say | What Happens |
|---------|--------------|
| "Set up fish watcher" | Guided setup wizard |
| "How are my fish?" | Current tank status |
| "Show me the tank" | Live snapshot |
| "Fish report" | Today's health summary |
| "Start/stop fish watcher" | Control monitoring |
| "Make it more sensitive" | Adjust detection |
| "Name my fish Gerald and Nemo" | Personalize alerts |
| "Show recent clips" | Get alert videos |

---

## Clawdbot Integration

Fish Watcher writes alerts to `~/clawd/fish-watcher-pending-alert.json`.

Your Clawdbot can:
1. Pick up alerts during heartbeats
2. Analyze the clip with vision
3. Send you a message with the video + commentary

Example alert you'd receive:
> 🚨 **Fish Tank Alert**
> Gerald hasn't moved in 8 minutes. Could be sleeping, but worth a check. Here's the clip.

---

## Name Your Fish (Optional)

Edit `config.yaml`:

```yaml
fish:
  count: 3
  profiles:
    - name: "Gerald"
      species: "Betta"
      color: "blue"
    - name: "Nemo"
      species: "Clownfish"
      color: "orange"
```

This enables personalized alerts like "Gerald is acting weird" instead of "Fish #1 alert".

---

## Daily Reports

Get a daily summary at 8 PM:

```
📊 Daily Fish Report - 2026-01-29

🏥 Health Score: 92/100

📈 Activity:
  • Average: 45.2
  • Peak: 2:30 PM (feeding time)
  
🚨 Alerts: 2
  📝 motion_spike: 1
  📝 interesting_moment: 1

📹 Clips: 2
✨ Cool moments: 1

🐟 Your fish are thriving!
```

---

## Commands

| Command | Description |
|---------|-------------|
| `python run.py` | Start 24/7 monitoring |
| `python dashboard.py` | Launch web dashboard |
| `python stream.py` | Live stream only |
| `python test_camera.py` | Test camera connection |

---

## Requirements

- Python 3.10+
- USB webcam, IP camera, or phone with webcam app
- ~100MB disk space per day of clips

---

## License

MIT - do whatever you want with it.

---

## 🖥️ Web Dashboard

Fish Watcher includes a beautiful web dashboard for monitoring your tank from any browser.

### Start the Dashboard

```bash
# Install dashboard dependencies
pip install -r requirements.txt

# Run the dashboard
python dashboard.py

# Or with custom options
python dashboard.py --port 8080 --host 0.0.0.0  # LAN access
```

Dashboard will be available at: **http://localhost:8080**

### Dashboard Features

| Page | What It Shows |
|------|---------------|
| **Dashboard** | Health score, recent alerts, live preview, clips |
| **Live Stream** | Full-screen live feed from your tank |
| **Clips** | Browse, play, and download recorded clips |
| **Reports** | Daily/weekly health reports with charts |
| **Settings** | Current configuration view |

### API Endpoints

The dashboard also provides a REST API:

```
GET /api/status       - Current status and health score
GET /api/clips        - List all clips
GET /api/clips/{file} - Download a specific clip
GET /api/alerts       - Alert history
GET /api/reports/daily  - Today's report
GET /api/reports/weekly - Weekly report
GET /api/stats        - Historical statistics
GET /api/config       - Current configuration
```

### Screenshots

Dashboard home:
```
┌─────────────────────────────────────────────────┐
│  🐟 Fish Watcher                                │
├─────────────────────────────────────────────────┤
│  Health: 92/100  │  Alerts: 2  │  Clips: 5     │
├─────────────────────────────────────────────────┤
│  📺 Live Preview          │  🚨 Recent Alerts  │
│  ┌─────────────────────┐  │  ⚠️ no_motion     │
│  │    [Live Feed]      │  │  ✨ feeding_frenzy │
│  └─────────────────────┘  │                    │
└─────────────────────────────────────────────────┘
```

---

Built with 🐟 by [@ashen_one](https://twitter.com/ashen_one)

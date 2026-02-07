# 🐟 Fish Watcher

[![CI](https://github.com/oh-ashen-one/fish-watcher/actions/workflows/ci.yml/badge.svg)](https://github.com/oh-ashen-one/fish-watcher/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

**AI-powered fish tank monitoring** — watches your aquarium 24/7, alerts you when something's wrong, and clips cool moments.

<p align="center">
  <img src="https://img.shields.io/badge/🐟-Fish_Watcher-00d4ff?style=for-the-badge" alt="Fish Watcher">
</p>

---

## ✨ Features

| Category | What It Does |
|----------|--------------|
| 🚨 **Health Detection** | Dead/sick fish, floating, stuck at bottom, erratic swimming, gasping |
| 🔧 **Tank Monitoring** | Water cloudiness, algae, color changes, filter stopped |
| 🐟 **Behavior Analysis** | Clustering, hiding, low activity, fish count tracking |
| 📹 **Clip Recording** | Auto-records alerts with 10s pre-roll buffer |
| 🧠 **AI Analysis** | Claude vision analyzes clips for intelligent insights |
| 🖥️ **Web Dashboard** | View status, clips, and live stream from any browser |
| 📊 **Reports** | Daily health scores and weekly trends |
| 😌 **Tank Mood** | Fun personality indicator — is your tank "vibin" or "stressed"? |
| 🎬 **Highlight Reels** | Auto-compile best clips into shareable weekly videos |
| 📱 **Social Sharing** | Auto-generate GIFs for Twitter/TikTok/Instagram |
| 💬 **Discord/Telegram** | Direct alerts to your chat — no middleman needed |

---

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/oh-ashen-one/fish-watcher.git
cd fish-watcher

# Install
pip install -r requirements.txt

# Test camera
python test_camera.py

# Run
python run.py
```

That's it. Now watching your tank 24/7.

---

## 🖥️ Web Dashboard

```bash
python run_dashboard.py
# Or: python run_dashboard.py --port 8080 --host 0.0.0.0
```

Opens at `http://localhost:8080`

| Page | Features |
|------|----------|
| **Dashboard** | Health score, alerts today, recent activity at a glance |
| **Clips** | Browse and play all recorded clips with inline video |
| **Live** | Real-time camera feed with timestamp overlay |

**API Endpoints:**
- `GET /api/status` — Current health and alerts
- `GET /api/clips` — List all clips
- `GET /api/alerts` — Recent alert history

---

## 🧠 Claude Vision Analysis

When alerts trigger, Claude analyzes the clip:

```
📊 Vision Analysis:
   Summary: Fish resting near bottom, normal behavior
   Severity: normal
   Observations:
      - Clear water, good visibility
      - Healthy colors, normal fin position
   Recommendations:
      - No action needed
```

**Enable:** Set `ANTHROPIC_API_KEY` or install `claude` CLI.

---

## 📷 Camera Setup

**USB Webcam** (easiest):
```yaml
camera:
  type: "usb"
  device: 0
```

**Phone as Webcam** (DroidCam, IP Webcam):
```yaml
camera:
  type: "ip"
  url: "http://192.168.1.100:4747/video"
```

**IP Camera / RTSP**:
```yaml
camera:
  type: "rtsp"
  url: "rtsp://192.168.1.100:554/stream"
```

---

## ⚙️ How It Works

```
Camera → Rolling Buffer (10s) → Detectors → Alert?
                                              ↓
         You ← Clawdbot ← Vision Analysis ← Save Clip
```

The rolling buffer keeps the last 10 seconds always — so when something triggers, you get footage from *before* it happened.

**Clips:** 40 seconds total (10s pre + 30s post), saved to `./clips/`

---

## 🐠 Personalize Your Fish

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

Get alerts like "Gerald hasn't moved" instead of "Fish #1 alert".

---

## 📊 Daily Reports

```
📊 Daily Fish Report - 2026-01-29

🏥 Health Score: 92/100
📈 Peak Activity: 2:30 PM (feeding time)
🚨 Alerts: 2
📹 Clips: 2

🐟 Your fish are thriving!
```

---

## 🤖 Clawdbot Integration

Works seamlessly with [Clawdbot](https://github.com/clawdbot/clawdbot). Just say:

- "Set up fish watcher" — guided setup
- "How are my fish?" — current status
- "Show me the tank" — live snapshot
- "Fish report" — today's health summary

Fish Watcher writes alerts to `~/clawd/fish-watcher-pending-alert.json` for Clawdbot to pick up.

---

## 📋 Commands

| Command | Description |
|---------|-------------|
| `python run.py` | Start 24/7 monitoring (single tank) |
| `python run_multi.py` | Multi-tank mode (monitor multiple tanks) |
| `python run_dashboard.py` | Launch web dashboard |
| `python stream.py` | Live stream only |
| `python test_camera.py` | Test camera connection |
| `python status.py` | Quick health check |
| `python -m src.tank_mood` | Check tank mood/vibe |
| `python -m src.highlights` | Generate highlight reel |
| `python -m src.highlights --gif clips/video.mp4` | Make a GIF from clip |

---

## 🐠 Multi-Tank Support

Monitor multiple tanks from one instance:

```bash
# Copy example config
cp tanks.example.yaml tanks.yaml

# Edit with your tank details
# Then run:
python run_multi.py
```

**tanks.yaml:**
```yaml
tanks:
  - id: "living_room"
    name: "Living Room Tank"
    camera:
      type: "usb"
      device: 0
    fish:
      count: 5
  
  - id: "office"
    name: "Office Tank"
    camera:
      type: "ip"
      url: "http://192.168.1.100:4747/video"
    fish:
      count: 3
```

Each tank gets its own:
- Detection settings
- Clips folder (`./clips/<tank_id>/`)
- Data/reports (`./data/<tank_id>/`)
- Fish profiles

---

## 🐳 Docker

```bash
# Run with Docker Compose
docker-compose up -d

# Or build manually
docker build -t fish-watcher .
docker run -d --device /dev/video0 -p 5555:5555 -v ./clips:/app/clips fish-watcher
```

The compose file includes:
- `watcher` — Main monitoring service
- `dashboard` — Web dashboard on port 5555
- `multi` — Multi-tank mode (run with `--profile multi`)

---

## 😌 Tank Mood

Your tank has a personality. Check its vibe:

```bash
python -m src.tank_mood
```

```
╔══════════════════════════════╗
║   🎉 TANK MOOD: PLAYFUL      ║
╠══════════════════════════════╣
║ Lots of activity! Happy fish ║
║                              ║
║ Activity: active             ║
║ Health:   thriving           ║
║                              ║
║ Peak time: 2 PM              ║
║ Peak day:  Saturday          ║
╚══════════════════════════════╝
```

**Possible moods:** zen, peaceful, vibin, playful, zoomies, hangry, shy, social, restless, stressed, lethargic, needs attention

**Activity heatmap:**
```bash
python -m src.tank_mood --heatmap
```

Shows when your fish are most active throughout the week.

---

## 🎬 Highlight Reels

Auto-compile your best clips into shareable videos:

```bash
# Generate weekly highlights
python -m src.highlights

# See stats only
python -m src.highlights --stats-only

# Generate a GIF from any clip (perfect for Twitter/TikTok)
python -m src.highlights --gif clips/20260129_143022_feeding_frenzy.mp4
```

The highlight reel:
- Scores clips by how interesting they are (feeding frenzy > motion spike > clustering)
- Picks the top 10 clips from the last 7 days
- Compiles them in chronological order
- Adds timestamp overlays

**Auto-weekly:** Enable in config and it'll generate every Sunday.

---

## 💬 Discord & Telegram Alerts

Get alerts directly in your chat — no Clawdbot middleman needed.

### Discord Webhook

1. Server Settings → Integrations → Webhooks → New Webhook
2. Copy the webhook URL
3. Add to `config.yaml`:

```yaml
notification:
  discord:
    enabled: true
    webhook_url: "https://discord.com/api/webhooks/..."
    tank_name: "Gerald's Tank"
```

### Telegram Bot

1. Message @BotFather → /newbot → get token
2. Message @userinfobot → get your chat ID
3. Add to `config.yaml`:

```yaml
notification:
  telegram:
    enabled: true
    bot_token: "123456:ABC-DEF..."
    chat_id: "123456789"
    tank_name: "Gerald's Tank"
```

Alerts include AI analysis, clip info, and fun personality messages.

---

## 📱 Social Sharing

Generate GIFs from any clip for easy sharing:

```bash
python -m src.highlights --gif clips/feeding_frenzy.mp4
```

Options:
- Default: 5 seconds, 480px wide, 15fps
- Output saved to `./highlights/`

Perfect for Twitter, TikTok, Instagram stories.

---

## 📁 Project Structure

```
fish-watcher/
├── run.py              # Main watcher entry point
├── dashboard.py        # Web dashboard
├── stream.py           # Live stream server
├── test_camera.py      # Camera test utility
├── config.yaml         # All settings
├── src/                # Core modules
│   ├── watcher.py      # Main watcher loop
│   ├── detector.py     # Alert detection algorithms
│   ├── buffer.py       # Rolling frame buffer
│   ├── recorder.py     # Clip recording
│   ├── notifier.py     # Clawdbot/webhook notifications
│   ├── vision.py       # Claude vision analysis
│   ├── reports.py      # Health reports
│   ├── tank_mood.py    # Tank personality/vibe 🆕
│   ├── highlights.py   # Highlight reel generator 🆕
│   ├── discord_notifier.py   # Discord webhooks 🆕
│   └── telegram_notifier.py  # Telegram bot alerts 🆕
└── clawdbot/
    ├── SKILL.md        # Clawdbot skill definition
    ├── controller.py   # Clawdbot control interface
    └── setup_wizard.py # Interactive setup
```

---

## 🔢 Fish Counter

Real-time fish counting with bounding boxes:

```bash
# Live camera
python -m src.fish_counter 0

# From image
python -m src.fish_counter tank_photo.jpg
```

Uses background subtraction + blob detection. The stable count smooths out noise.

---

## ⚙️ Configuration Reference

| Setting | Default | Description |
|---------|---------|-------------|
| `recording.pre_roll` | 10 | Seconds before trigger |
| `recording.post_roll` | 30 | Seconds after trigger |
| `detection.motion_sensitivity` | 50 | 0-100, higher = more sensitive |
| `detection.no_motion_threshold` | 300 | Seconds before "no motion" alert |
| `alerts.cooldown` | 60 | Min seconds between same alert |
| `vision.enabled` | true | Use Claude for clip analysis |

See `config.yaml` for all options.

---

## 📋 Requirements

- Python 3.10+
- OpenCV, NumPy, Flask, PyYAML
- Camera (USB, IP, or phone)
- ~100MB disk/day for clips
- (Optional) Anthropic API key for vision

---

## 📜 License

MIT — do whatever you want with it.

---

<p align="center">
Built with 🐟 by <a href="https://twitter.com/ashen_one">@ashen_one</a>
</p>

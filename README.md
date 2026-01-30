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

## Quick Start (2 minutes)

### 1. Clone & Install

```bash
git clone https://github.com/oh-ashen-one/fish-watcher.git
cd fish-watcher
pip install -r requirements.txt
```

### 2. Test Your Camera

```bash
python test_camera.py
```

This will:
- Find all connected cameras
- Show you which device number to use
- Save a test snapshot so you can verify it's pointing at your tank

### 3. Configure (Optional)

Edit `config.yaml` if needed:

```yaml
camera:
  type: "usb"
  device: 0  # Change if test_camera.py shows a different number
```

### 4. Run It

```bash
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

## Requirements

- Python 3.10+
- USB webcam, IP camera, or phone with webcam app
- ~100MB disk space per day of clips

---

## License

MIT - do whatever you want with it.

---

Built with 🐟 by [@ashen_one](https://twitter.com/ashen_one)

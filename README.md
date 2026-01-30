# 🐟 Fish Watcher

AI-powered fish tank monitoring that watches your aquarium 24/7 and alerts you when something's wrong.

## Features

- **Motion Detection** - Alerts when fish stop moving (potential health issue)
- **Activity Spike Detection** - Catches unusual behavior like erratic swimming
- **Water Color Monitoring** - Detects cloudiness or color changes
- **Surface Activity** - Alerts if fish are gasping at surface
- **Smart Clip Recording** - Captures 10 seconds BEFORE the event + 30 seconds after
- **Clawdbot Integration** - Sends alerts with video clips to your AI assistant

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure your camera

Edit `config.yaml`:

```yaml
camera:
  type: "usb"      # or "ip" for IP cameras
  device: 0        # USB device index, or URL for IP cam
```

For IP cameras (phone as webcam):
- Install DroidCam, Iriun, or similar on your phone
- Set the URL in config:
```yaml
camera:
  type: "ip"
  url: "http://192.168.1.100:4747/video"
```

### 3. Run it

```bash
python run.py
```

Or with a custom config:
```bash
python run.py --config my-config.yaml
```

## Configuration

See `config.yaml` for all options:

| Setting | Description | Default |
|---------|-------------|---------|
| `recording.pre_roll` | Seconds to capture before trigger | 10 |
| `recording.post_roll` | Seconds to record after trigger | 30 |
| `detection.motion_sensitivity` | 0-100, higher = more sensitive | 50 |
| `detection.no_motion_threshold` | Seconds of no motion before alert | 300 |
| `alerts.cooldown` | Seconds between same alert type | 60 |

## How It Works

```
Camera Feed → Rolling Buffer (always keeps last 10 sec)
     ↓
Detectors analyze each frame
     ↓
Alert triggered? → Save clip (10s before + 30s after)
     ↓
Notify Clawdbot → AI analyzes clip → Message sent to you
```

## Detection Types

| Alert | What It Means |
|-------|---------------|
| `no_motion` | Fish haven't moved in 5+ minutes |
| `motion_spike` | Unusual activity (3x normal) |
| `color_change` | Water color shifted (cloudiness/algae) |
| `surface_activity` | Fish at surface for 30+ seconds |

## Clips

Clips are saved to `./clips/` with format:
```
20260129_183045_no_motion.mp4
```

## Clawdbot Integration

Fish Watcher writes alerts to `~/clawd/fish-watcher-pending-alert.json`. Your Clawdbot agent can pick these up during heartbeats and:

1. Analyze the clip with vision
2. Send you a Telegram message with the video
3. Provide context ("Gerald hasn't moved in 8 minutes, might be sleeping or check on him")

## Roadmap

- [ ] Individual fish tracking
- [ ] Feeding detection
- [ ] Health indicator recognition (fin rot, spots)
- [ ] Daily/weekly reports
- [ ] Cool moment detection (not just problems)
- [ ] Web dashboard

## License

MIT

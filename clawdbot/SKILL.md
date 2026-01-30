# Fish Watcher - Clawdbot Skill

AI-powered fish tank monitoring with Telegram control.

## Setup (via Telegram)

When user mentions fish tank monitoring, fish watcher, or wants to set up camera monitoring:

1. Check if fish-watcher is installed:
   ```bash
   ls ~/clawd/repos/fish-watcher 2>/dev/null || ls ~/fish-watcher 2>/dev/null
   ```

2. If not installed, offer to install:
   ```bash
   cd ~/clawd/repos && git clone https://github.com/oh-ashen-one/fish-watcher.git
   cd fish-watcher && pip install -r requirements.txt
   ```

3. Run camera detection:
   ```bash
   cd ~/clawd/repos/fish-watcher && python test_camera.py
   ```

4. Guide user through Telegram:
   - "I found X cameras. Which one is pointed at your tank?"
   - Show test snapshot if possible
   - Update config.yaml with chosen device

5. Start the watcher:
   ```bash
   cd ~/clawd/repos/fish-watcher && python run.py &
   ```

## Commands (Natural Language)

These are conversational, not slash commands:

| User Says | Action |
|-----------|--------|
| "set up fish watcher" / "monitor my tank" | Start setup wizard |
| "is fish watcher running?" / "tank status" | Check process status |
| "start watching my tank" | Start watcher daemon |
| "stop fish watcher" | Stop watcher daemon |
| "show me the tank" / "how are my fish?" | Capture current frame |
| "fish report" / "how's the tank today?" | Generate daily report |
| "name my fish" | Start fish naming wizard |
| "show recent clips" | List/send recent alert clips |

## Monitoring Alerts

Check for pending alerts during heartbeats:

```bash
cat ~/clawd/fish-watcher-pending-alert.json 2>/dev/null
```

If alert exists:
1. Read the alert data
2. Get the clip path
3. Send clip to user via Telegram with your analysis
4. Delete the pending alert file

Example alert response:
```
🚨 Fish Tank Alert

Gerald hasn't moved in 8 minutes. Looking at the clip... 
he seems to be resting near the filter. Probably fine, 
but keep an eye on him.

[Sends video clip]
```

## Daily Reports

At configured time (default 8 PM), generate and send daily report:

```python
from fish_watcher.reports import ReportGenerator
rg = ReportGenerator(data_dir="~/clawd/repos/fish-watcher/data")
print(rg.generate_daily_report())
```

## Process Management

Check if running:
```bash
pgrep -f "fish-watcher.*run.py" || pgrep -f "python.*watcher"
```

Start (background):
```bash
cd ~/clawd/repos/fish-watcher && nohup python run.py > fish-watcher.log 2>&1 &
```

Stop:
```bash
pkill -f "fish-watcher.*run.py"
```

## File Locations

| File | Purpose |
|------|---------|
| `~/clawd/repos/fish-watcher/config.yaml` | Configuration |
| `~/clawd/repos/fish-watcher/clips/` | Saved video clips |
| `~/clawd/repos/fish-watcher/data/` | Stats and reports |
| `~/clawd/fish-watcher-pending-alert.json` | Pending alert for Clawdbot |
| `~/clawd/fish-watcher-alerts.json` | Alert history |

## Sending Clips via Telegram

When sending a clip, use the message tool with the clip file:

```
The clip is at: /path/to/clip.mp4
Send it with your alert message.
```

## Config Updates via Chat

User: "make it more sensitive"
→ Update config.yaml: `motion_sensitivity: 70` (was 50)

User: "alert me faster when fish stop moving"  
→ Update config.yaml: `no_motion_threshold: 180` (was 300)

User: "my fish are named Gerald, Nemo, and Dory"
→ Update config.yaml fish profiles

Always confirm changes: "Done - sensitivity increased to 70. I'll catch more subtle movements now."

## Cool Moments

When `is_cool_moment: true` in alert, frame it positively:

```
✨ Cool Moment!

Your fish are having a party! Caught this feeding 
frenzy moment. Look at them go!

[Sends video clip]
```

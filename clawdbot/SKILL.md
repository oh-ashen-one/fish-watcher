# Fish Watcher - Clawdbot Skill

AI-powered fish tank monitoring with Telegram control.

---

## ⏰ TIMESTAMPS ON EVERYTHING (MANDATORY)

**Every single image, screenshot, clip, alert, or visual output MUST include a timestamp.**

**Format:** `Jan 29, 8:14 PM` (human-readable, date + time)

**Where timestamps go:**
- Screenshots → in the message, right after the 🐟 status line
- Alerts → at the top of the alert message
- Video clips → in the message when sending
- Daily reports → header of the report
- Cool moments → in the message
- AI overlay views → in the message
- Test snapshots during setup → in the message

**No exceptions.** The timestamp proves the content is live/current, not cached or stale.

---

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

5. Ask about fish:
   - "How many fish do you have?"
   - For each fish: "What's fish 1's name? Give me a quick description"
   - Example: "Gerald - blue betta, likes to hide in the castle"
   - Save to config.yaml fish profiles
   - **Research each species** to understand normal behavior, compatibility, care needs

6. Tank details ("etc" step):
   - Tank size (gallons/liters)
   - Freshwater or saltwater
   - What they're fed
   - Feeding schedule
   - Any other relevant info
   - Save to config.yaml tank section

7. Stream password:
   - "Set a password for your live stream (so only you can watch):"
   - User provides password
   - Save to config.yaml: `stream.password: <their password>`
   - Confirm: "Got it! Your stream will be at `localhost:5555/?p=<password>`"

8. Start the watcher:
   ```bash
   cd ~/clawd/repos/fish-watcher && python run.py &
   ```

## Example Setup Conversation

```
User: "set up fish watcher"

AI: 🐟 Fish Watcher Setup
    I found 1 camera (Device 0, 640x480)
    Is this the one pointing at your tank?

User: "yes"

AI: 📸 Test snapshot captured — Jan 29, 8:10 PM
    [sends image]
    Does this show your fish tank?

User: "yeah that's it"

AI: 🐟 Tell me about your fish!
    How many fish do you have in this tank?

User: "3"

AI: 🐟 Fish 1 of 3
    What's this fish's name? And give me a quick description.
    Example: 'Gerald - blue betta, likes to hide in the castle'

User: "Gerald - blue betta, he's the boss"

AI: 🐟 Fish 2 of 3
    What's this fish's name and description?

User: "Nemo - clownfish, very active"

AI: 🐟 Fish 3 of 3
    What's this fish's name and description?

User: "Dory - blue tang, a bit shy"

AI: 🐟 Got it! I'll remember:
    • Gerald - blue betta, he's the boss
    • Nemo - clownfish, very active
    • Dory - blue tang, a bit shy
    
    Quick research note: Bettas can be territorial - I'll watch 
    for any aggression between Gerald and the others.

    🏠 A few more questions about your tank setup:
    Tank size? Freshwater/saltwater? What do you feed them?

User: "20 gallon freshwater, feed them tropical flakes twice a day"

AI: ✅ Got it!
    • 20 gallon freshwater
    • Tropical flakes, twice daily
    
    Ready to start watching?

User: "yes"

AI: 🎉 Fish Watcher is running!
    I'll be keeping an eye on Gerald, Nemo, and Dory! 🐟
```

---

## Status Indicator (Always Show!)

**When the user prompts you about fish/tank in ANY way:**
1. Capture a current screenshot FIRST
2. Include a status line with the 🐟 emoji to confirm it's operational
3. THEN respond to their actual question

**Format:**
```
🐟 Fish Watcher Active — [timestamp] [screenshot]

[Your response to their question]
```

**Timestamp format:** `Jan 29, 8:14 PM` (human-readable, includes date)

This gives instant visual confirmation that the system is running and the camera is working. Even for simple questions, grab a quick frame so they see their fish. The timestamp proves the image is live, not cached.

**Examples:**
- User: "hey, how are my fish?"
  → Capture screenshot, then: "🐟 Fish Watcher Active — Jan 29, 8:14 PM\n[screenshot]\n\nEveryone's looking good! Gerald is near the filter, Nemo is zooming around as usual."

- User: "anything happening in the tank?"
  → Capture screenshot, then: "🐟 Fish Watcher Active — Jan 29, 8:15 PM\n[screenshot]\n\nAll quiet! No alerts in the last 2 hours."

---

## Commands (Natural Language)

These are conversational, not slash commands:

| User Says | Action |
|-----------|--------|
| "set up fish watcher" / "monitor my tank" | Start setup wizard |
| "is fish watcher running?" / "tank status" | Capture frame + Check process status |
| "start watching my tank" | Start watcher daemon |
| "stop fish watcher" | Stop watcher daemon |
| "show me the tank" / "how are my fish?" | Capture current frame + status |
| "show me the AI view" / "tracking view" | Capture with AI overlay (boxes, names, stats) |
| "fish report" / "how's the tank today?" | Capture frame + Generate daily report |
| "name my fish" | Start fish naming wizard |
| "show recent clips" | List/send recent alert clips |
| **"watch live" / "live feed" / "stream"** | **Start live camera stream** |
| **"stop stream"** | **Stop live stream server** |

---

## 🎥 Live Camera Stream (Secure, Local-Only)

The stream is **local-only** and **token-protected**. Only the user with the unique link can view it.

**When user asks to watch live:**

1. Start the stream server:
   ```bash
   cd ~/clawd/repos/fish-watcher && python stream.py &
   ```

2. Get password from config:
   ```bash
   grep password ~/clawd/repos/fish-watcher/config.yaml
   ```

3. Send the user their **private** link:
   ```
   🐟 Live Feed Active — Jan 29, 8:20 PM
   
   📺 Your private stream:
   http://localhost:5555/?p=<PASSWORD>
   
   🔐 Password-protected — only you can view.
   Open in browser to watch your tank live!
   ```

4. For **remote access** (e.g., user is on phone/away):
   ```bash
   ngrok http 5555
   ```
   Then send: `https://<ngrok-url>/?p=<PASSWORD>`

**Security:**
- Server binds to 127.0.0.1 only (no direct external access)
- Password set during onboarding (saved in config.yaml)
- Password required for all endpoints — wrong password = 403 Forbidden
- Only the user with the password can view

**Stream features:**
- MJPEG stream (works in any browser)
- Timestamp overlay on every frame (top-left corner)
- 60 FPS smooth streaming
- Low latency

**To stop:**
```bash
pkill -f "stream.py"
```

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
🚨 Fish Tank Alert — Jan 29, 8:22 PM

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

## Species-Aware Alerts

After setup, **research each fish species** to provide informed alerts:

**What to research:**
- Normal behavior patterns (active vs. sedentary)
- Temperature and pH preferences
- Compatibility with tank mates
- Common health issues to watch for
- Lifespan and expected behavior at different ages
- Signs of stress specific to that species

**Use this info when alerting:**

Instead of generic:
> "Fish not moving for 5 minutes"

Say species-aware:
> "🚨 Jan 29, 3:42 PM — Gerald (your betta) hasn't moved in 8 minutes. 
> Bettas usually rest on leaves or near the surface - is he in his 
> usual spot? If he's at the bottom looking pale, that could indicate 
> stress or illness."

**Compatibility warnings:**
If user has incompatible species, mention during setup:
> "Heads up - bettas can be aggressive with other fish, especially 
> colorful ones. Keep an eye on how Gerald treats Nemo."

**Feeding context:**
If user feeds twice daily and no activity during normal feeding time:
> "🐟 Jan 29, 6:00 PM — It's feeding time and I didn't see the usual 
> feeding frenzy. Did you already feed them, or should I remind you?"

---

## Cool Moments

When `is_cool_moment: true` in alert, frame it positively:

```
✨ Cool Moment — Jan 29, 6:05 PM

Your fish are having a party! Caught this feeding 
frenzy moment. Look at them go!

[Sends video clip]
```

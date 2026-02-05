# Changelog

All notable changes to Fish Watcher will be documented here.

## [1.2.0] - 2026-02-05

### Added
- **Multi-Tank Support** (`run_multi.py`) — Monitor multiple tanks simultaneously
  - Each tank runs in its own thread
  - Separate clips/data directories per tank
  - Independent detection settings
  - Example config: `tanks.example.yaml`
- `TankConfig`, `TankWatcher`, `MultiTankWatcher` classes
- **Docker Support** — Dockerfile and docker-compose.yml
  - Easy deployment with `docker-compose up`
  - Multi-tank mode with `--profile multi`
- **GitHub Actions CI** — Automated linting, testing, and Docker builds

### Changed
- Bumped version to 1.2.0
- Updated README with multi-tank and Docker documentation

## [1.1.0] - 2026-02-05

### Added
- **Web Dashboard** (`dashboard.py`) — View status, clips, and live stream from any browser
  - Health score overview
  - Clips browser with inline video player
  - Live stream page
  - REST API endpoints (`/api/status`, `/api/clips`, `/api/alerts`)
  - Password protection
- **Claude Vision Analysis** (`src/vision.py`) — AI-powered clip analysis
  - Automatically analyzes clips when alerts trigger
  - Provides summary, health concerns, observations, recommendations
  - Supports Anthropic API or `claude` CLI fallback
  - Configurable via `vision.enabled` in config

### Changed
- Bumped version to 1.1.0
- Updated requirements.txt with `anthropic` package
- Notifier now includes vision analysis in alert data

## [1.0.0] - 2026-01-29

### Added
- Initial release
- 24/7 fish tank monitoring
- Health & emergency detection (no motion, floating, erratic swimming, etc.)
- Tank issue detection (cloudiness, algae, color changes)
- Behavior analysis (clustering, hiding, low activity)
- Cool moment capture (feeding frenzy, interesting activity)
- Rolling buffer with pre-roll recording
- Clip recording with timestamp
- Daily and weekly health reports
- Clawdbot integration with setup wizard
- Live streaming with password protection
- Fish profiles for personalized alerts
- Configurable detection sensitivity

# Technical Debt Report: fish-watcher
**Repository**: oh-ashen-one/fish-watcher
**Analysis Date**: 2026-02-07
**Tool**: technical-debt-manager (claude-code-templates)
**Total LOC**: ~5,534 (Python)
**Total Commits**: 22

## Executive Summary

| Severity | Count | Action |
|----------|-------|--------|
| 🔴 Critical | 0 | — |
| 🟠 High | 3 | Next sprint |
| 🟡 Medium | 5 | Next month |
| 🟢 Low | 3 | Backlog |

**Overall Health: 6.5/10** — Solid MVP with clear areas for improvement before scaling.

---

## Findings by Category

### 1. Code Quality Debt 🟠 HIGH

**Large Functions (22 functions > 50 lines)**
The codebase has significant function complexity:
- `fish_counter.py:count_fish_in_image` — **105 lines** (worst offender)
- `tank_mood.py:analyze_mood` — **88 lines**
- `discord_notifier.py:notify` — **87 lines**
- `highlights.py:generate_reel` — **85 lines**
- `detector.py:process` — 4 variants, each 55-79 lines

**Impact**: Hard to test, hard to debug, high merge conflict risk.
**Fix**: Extract helper functions. Target < 40 lines per function.
**Effort**: 3-4 days

**`detector.py` is the hottest file** — 510 lines, 4 separate `process()` methods, most changed file after README. This is where bugs will cluster.

---

### 2. Test Debt 🟠 HIGH

**Test Coverage: ~0%**
- Only 1 test file exists: `test_camera.py` (113 lines) — appears to be a utility, not a test suite
- **Zero unit tests** for core logic
- No pytest configuration
- No CI test step

**Critical untested paths:**
- `detector.py` — anomaly detection (core feature)
- `fish_counter.py` — fish counting accuracy
- `vision.py` — AI vision analysis
- `notifier.py` — alert delivery

**Impact**: Any refactoring is high risk. Bugs in detection = false alerts or missed issues.
**Fix**: Add pytest + basic unit tests for detector, fish_counter, vision.
**Effort**: 5-7 days for 60% coverage on critical paths

---

### 3. Error Handling 🟡 MEDIUM

**13 bare `except:` blocks** (out of 42 try/except)
- Bare excepts swallow ALL errors including KeyboardInterrupt, SystemExit
- Makes debugging impossible — errors silently disappear
- 31% of error handling is "catch everything and ignore"

**Fix**: Replace bare `except:` with `except Exception as e:` + logging.
**Effort**: 1 day

---

### 4. Type Hint Debt 🟡 MEDIUM

**Type hint coverage: 48.6%** (84/173 functions)
- Half the codebase has no return type annotations
- Makes IDE support weaker, refactoring riskier

**Fix**: Add type hints to public functions, especially in `src/`.
**Effort**: 2 days

---

### 5. Documentation Debt 🟡 MEDIUM

- README exists and is well-maintained (most changed file: 10 commits)
- CHANGELOG exists ✅
- **Missing**: API documentation for the dashboard/stream endpoints
- **Missing**: Architecture overview (how detector → notifier → discord flows)
- No docstrings on many core functions

**Fix**: Add architecture diagram + docstrings on core classes.
**Effort**: 1-2 days

---

### 6. Dependency Debt 🟢 LOW

**Dependencies look healthy:**
- `opencv-python-headless>=4.8.0` — reasonable floor
- `anthropic>=0.20.0` — marked optional ✅
- `flask>=3.0.0`, `fastapi>=0.109.0` — recent versions
- No pinned exact versions (flexible but could cause reproducibility issues)
- **No lock file** (no `requirements.lock` or `poetry.lock`)

**No hardcoded secrets found** ✅

**Fix**: Add `pip freeze > requirements.lock` for reproducible builds.
**Effort**: 30 minutes

---

### 7. Design Debt 🟡 MEDIUM

- **Two web frameworks**: Flask (`stream.py`) AND FastAPI (`dashboard.py`) — should pick one
- `detector.py` has 4 different `process()` methods across what appears to be different classes — could benefit from a shared interface/base class
- `clawdbot/controller.py` at 362 lines is a large controller — could extract command handlers

**Fix**: Consolidate on FastAPI, extract detector base class.
**Effort**: 3-4 days

---

### 8. Infrastructure Debt 🟡 MEDIUM

- Docker support exists ✅ (`Dockerfile`, `docker-compose.yml`)
- **No CI/CD tests** — only CI file but no test step visible
- No linting in CI (ruff cache exists but not enforced)

**Fix**: Add ruff + pytest to CI pipeline.
**Effort**: 1 day

---

## Top 5 Priority Actions

| # | Item | Severity | Effort | Impact |
|---|------|----------|--------|--------|
| 1 | Add unit tests for detector + fish_counter | 🟠 HIGH | 5 days | Prevents bugs in core feature |
| 2 | Refactor `detector.py` (510 LOC, 4 process methods) | 🟠 HIGH | 3 days | Reduces hotspot complexity |
| 3 | Fix 13 bare except blocks | 🟡 MEDIUM | 1 day | Stops silent error swallowing |
| 4 | Consolidate Flask/FastAPI to one framework | 🟡 MEDIUM | 2 days | Reduces maintenance burden |
| 5 | Add requirements.lock + CI test step | 🟢 LOW | 1 day | Reproducible builds + safety net |

---

## What's Good ✅

- No hardcoded secrets
- Docker setup ready
- Clean project structure (src/ separation)
- Good README maintenance
- YAML-based configuration
- Reasonable dependencies (not bloated)
- .ruff_cache present (linting used at some point)

---

*Generated by technical-debt-manager agent • fish-watcher repo audit*

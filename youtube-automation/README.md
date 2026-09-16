# YouTube Shorts Automation — AI-Generated Cars ASMR
### Google Flow → Local Video Pipeline

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Core Rule — One Job, One Video](#2-core-rule--one-job-one-video)
3. [Video Target Specification](#3-video-target-specification)
4. [Technology Stack](#4-technology-stack)
5. [Project Structure](#5-project-structure)
6. [Configuration Reference](#6-configuration-reference)
7. [Authentication Model](#7-authentication-model)
8. [Job State Machine](#8-job-state-machine)
9. [Module Responsibilities](#9-module-responsibilities)
10. [Build Phases](#10-build-phases)
11. [Phase 1 Acceptance Criteria](#11-phase-1-acceptance-criteria)
12. [Output Directory Layout](#12-output-directory-layout)
13. [Logging Specification](#13-logging-specification)
14. [Error Handling & Debug Artifacts](#14-error-handling--debug-artifacts)
15. [Prompt System](#15-prompt-system)
16. [Generation Monitoring Rules](#16-generation-monitoring-rules)
17. [Download Handling Rules](#17-download-handling-rules)
18. [What Is Explicitly NOT Built Yet](#18-what-is-explicitly-not-built-yet)
19. [Future Full-System Architecture](#19-future-full-system-architecture)
20. [Development Methodology](#20-development-methodology)
21. [Quick Start (Phase 1)](#21-quick-start-phase-1)

---

## 1. Project Overview

This is a **local Python automation system** for a YouTube Shorts channel whose content is entirely **AI-generated automotive ASMR videos**.

The automation pipeline uses **Google Flow** (accessed through a real browser via Playwright) to generate short cinematic videos. No unofficial APIs, no hacked endpoints — only real browser interaction with the visible Google Flow UI.

**End-state daily output target:**

```
10 jobs/day  →  10 prompts  →  10 individual videos  →  10 Shorts uploaded
```

The system is built **incrementally**. Each phase must be proven to work before the next phase begins. This document is the single source of truth for the entire project.

---

## 2. Core Rule — One Job, One Video

> **ONE prompt → ONE Google Flow generation → ONE video**

This rule is absolute and must never be violated by the automation system.

- The system must never request multiple variations for a single job.
- The system must never submit more than one generation per job execution.
- The eventual daily output of 10 videos is achieved by running **10 independent jobs**, not by requesting 10 variations in one job.

---

## 3. Video Target Specification

| Parameter       | Target Value                          |
|-----------------|---------------------------------------|
| Duration        | 10 seconds                            |
| Aspect Ratio    | 9:16 (vertical, Shorts format)        |
| Format          | MP4                                   |
| Content style   | Photorealistic, cinematic             |
| Subject         | AI-generated automotive ASMR          |
| Photography     | Macro/product, shallow depth of field |
| Lighting        | Cinematic chiaroscuro                 |
| Voiceover       | None (visual ASMR only)               |
| Sound           | Natural ambient / physical ASMR       |

> **Important:** Do not hardcode unsupported duration or aspect ratio values.
> Detect what options the current Flow UI actually exposes, and configure accordingly.
> The UI changes over time. Always inspect before assuming.

---

## 4. Technology Stack

| Layer              | Technology                  | Notes                                      |
|--------------------|-----------------------------|--------------------------------------------|
| Language           | Python 3.11+                | Minimum version requirement                |
| Browser automation | Playwright                  | Do **not** use Selenium                    |
| Browser            | Chromium (via Playwright)   | Headless=False during development          |
| Config             | YAML (`config/config.yaml`) | No hardcoded settings in code              |
| Job tracking       | SQLite                      | Phase 3+ only                              |
| Post-processing    | FFmpeg                      | Phase 3+ only                              |
| Logging            | Python `logging` + Rich     | Structured output, no credentials in logs  |

---

## 5. Project Structure

```
youtube-automation/
│
├── app/                          # Application source code
│   ├── main.py                   # Entry point: python -m app.main
│   │
│   ├── browser/
│   │   ├── browser_manager.py    # Launch, profile, lifecycle
│   │   └── flow_client.py        # All Google Flow UI interactions
│   │
│   ├── generation/
│   │   └── generation_job.py     # Job state machine + job record
│   │
│   ├── storage/
│   │   └── file_manager.py       # Output paths, saving files
│   │
│   └── utils/
│       └── logger.py             # Logging setup (Rich + file handler)
│
├── config/
│   └── config.yaml               # All runtime settings
│
├── prompts/
│   └── test_prompt.txt           # MVP test prompt (manually written)
│
├── output/                       # Generated videos (git-ignored)
│   └── YYYY-MM-DD/
│       └── job_0001/
│           ├── prompt.txt
│           ├── video.mp4
│           ├── metadata.json     # Phase 2+
│           ├── screenshot.png    # Phase 2+
│           └── status.json       # Phase 2+
│
├── logs/                         # Runtime logs (git-ignored)
│   └── YYYY-MM-DD.log
│
├── debug/                        # Debug screenshots/dumps (git-ignored)
│
├── browser_profile/              # Playwright persistent auth (git-ignored)
│
├── tests/                        # Test scripts (Phase 2+)
│
├── .gitignore
├── requirements.txt
└── README.md                     # This file
```

---

## 6. Configuration Reference

Full annotated `config/config.yaml`:

```yaml
# ──────────────────────────────────────────────
# Google Flow target
# ──────────────────────────────────────────────
flow:
  url: "https://labs.google/fx/tools/flow"
  # Verify this URL is current at runtime.
  # Do not assume it is permanent.

# ──────────────────────────────────────────────
# Browser settings
# ──────────────────────────────────────────────
browser:
  headless: false                   # Always false during development
  profile_directory: "./browser_profile"  # Persistent auth — git-ignored
  slow_mo_ms: 0                     # Set > 0 for step-by-step debug (e.g. 500)
  viewport_width: 1280
  viewport_height: 900
  default_timeout_ms: 30000         # Playwright default element timeout

# ──────────────────────────────────────────────
# Generation parameters
# ──────────────────────────────────────────────
generation:
  target_duration_seconds: 10       # Preferred — use if available in UI
  aspect_ratio: "9:16"              # Preferred — use if available in UI
  videos_per_job: 1                 # MUST always be 1. Never change this.
  timeout_seconds: 900              # Max wait time for generation (15 min)
  poll_interval_seconds: 5          # How often to check generation status

# ──────────────────────────────────────────────
# Storage
# ──────────────────────────────────────────────
storage:
  output_directory: "./output"
  log_directory: "./logs"
  debug_directory: "./debug"
```

---

## 7. Authentication Model

### Philosophy

- **No credentials in source code.** Ever.
- **No credentials in config files.** Ever.
- Authentication is **manual** — the user logs in through the real browser.

### How It Works

1. On first run, the browser opens at the Flow URL.
2. If not logged in, a message tells the user to authenticate in the browser window.
3. The script waits (up to a configurable timeout) for the user to complete login.
4. Once authenticated, Playwright's persistent context stores the session in `browser_profile/`.
5. On subsequent runs, the stored session is reused automatically.
6. If the session expires, the user is prompted to log in again.

### Security Rules

- `browser_profile/` is in `.gitignore` — it will **never** be committed.
- Logs must **never** print cookies, tokens, headers, or any authentication data.
- The system never bypasses CAPTCHA or any security mechanism.

---

## 8. Job State Machine

Every job transitions through these states in order:

```
CREATED
   ↓
BROWSER_READY
   ↓
FLOW_READY
   ↓
PROMPT_SUBMITTED
   ↓
GENERATING
   ↓
COMPLETED
   ↓
DOWNLOADED
```

**Failure states** (terminal — job stops, no automatic retry):

```
AUTH_REQUIRED       ← User must log in manually
GENERATION_FAILED   ← Flow reported an error during generation
TIMEOUT             ← generation.timeout_seconds exceeded
DOWNLOAD_FAILED     ← File did not arrive or could not be saved
```

### Critical Rule

> A job is **only** marked `DOWNLOADED` (success) when the `.mp4` file physically exists
> on disk and its size is greater than zero bytes.
> Never mark success without verifying file presence.

---

## 9. Module Responsibilities

### `app/utils/logger.py`
- Sets up Python's `logging` module with Rich console output.
- Configures a file handler writing to `logs/YYYY-MM-DD.log`.
- Provides a `get_logger(name)` function for module-level loggers.
- **Never** logs cookies, tokens, session data, or credentials.

---

### `app/browser/browser_manager.py`
- Owns the Playwright `Browser` / `BrowserContext` lifecycle.
- Reads `browser.profile_directory` from config.
- Launches Chromium with a persistent context (stores session locally).
- Exposes `launch()` and `close()` methods.
- Captures screenshots on error and saves to `debug/`.

---

### `app/browser/flow_client.py`
- The **only** module that interacts with the Google Flow UI.
- Uses accessible roles, labels, text, and stable attributes — never screen coordinates.
- Has fallback selectors for fragile elements.
- Full planned interface:

```python
open()                           # Navigate to Flow URL
is_authenticated()               # Check if user session is active
wait_for_authentication(timeout) # Block until user logs in
navigate_to_create()             # Open the video creation interface
enter_prompt(text)               # Type the prompt
configure_generation()           # Set 9:16 / 10s if available in UI
submit_generation()              # Click generate — exactly once
wait_for_generation(timeout, poll_interval)  # Poll for completion
download_video(job_dir)          # Trigger download, wait, save to dir
```

- On **any** failure: screenshot → log → raise exception with context.
- Never submits more than one generation per `submit_generation()` call.

---

### `app/generation/generation_job.py`
- Represents a single job record.
- Holds: job ID, state, prompt text, timestamps, output paths.
- Transitions state using a strict state machine (no skipping states).
- Writes `status.json` to the job output directory (Phase 2+).

---

### `app/storage/file_manager.py`
- Computes output path: `output/YYYY-MM-DD/job_NNNN/`
- Creates directories as needed.
- Saves `prompt.txt` alongside the video.
- Verifies downloaded file exists and is non-empty.

---

### `app/main.py`
- Entry point: `python -m app.main`
- Loads `config/config.yaml`.
- Reads `prompts/test_prompt.txt`.
- Creates a `GenerationJob`.
- Calls `BrowserManager.launch()`.
- Calls `FlowClient` methods in sequence.
- Handles all exceptions at the top level.
- Exits with code `0` on success, `1` on failure.

---

## 10. Build Phases

### Phase 1 — Browser Connection (MVP)

**Goal:** Prove Python can open Google Flow in a real browser and maintain an authenticated session.

**Scope:**
- Full project directory structure
- `requirements.txt` + `.gitignore` + `config/config.yaml`
- `app/utils/logger.py` — Rich structured logger
- `app/browser/browser_manager.py` — Chromium persistent profile launch
- `app/browser/flow_client.py` — `open()` + `is_authenticated()` + `wait_for_authentication()`
- `app/generation/generation_job.py` — state machine skeleton
- `app/storage/file_manager.py` — skeleton
- `app/main.py` — wires browser + Flow open + auth check
- `prompts/test_prompt.txt`
- `README.md`

**Phase 1 complete when:** Browser opens Flow, user can log in, session persists across runs.

---

### Phase 2 — Full Generation Pipeline

Builds on a working Phase 1.

**Adds:**
- `navigate_to_create()`, `enter_prompt()`, `configure_generation()`
- `submit_generation()` — exactly once
- `wait_for_generation()` — polls UI, respects timeout
- `download_video()` — real download, saved to job dir
- Full state machine (all states)
- Debug screenshot capture on failures
- `status.json`, `metadata.json` output

**Phase 2 complete when:** `python -m app.main` produces `output/YYYY-MM-DD/job_0001/video.mp4`

---

### Phase 3 — Batch & Scheduling

- Prompt queue / multiple prompt files
- SQLite job tracking database
- Job runner: N jobs/day
- Configurable delay between jobs
- FFmpeg post-processing
- CLI job status dashboard

---

### Phase 4 — Upload & Publishing

- YouTube Data API v3 integration
- OAuth2 for YouTube (separate from Flow session)
- Metadata generation (title, description, tags)
- Upload queue with human approval gate
- Scheduled publishing

---

## 11. Phase 1 Acceptance Criteria

Phase 1 is **complete and proven** only when this exact output is seen:

```
[INFO] Starting Flow automation
[INFO] Config loaded: config/config.yaml
[INFO] Browser launched | Profile: ./browser_profile
[INFO] Navigating to Google Flow: https://labs.google/fx/tools/flow
[INFO] Authentication detected — session active
       (OR: Waiting for manual login — please sign in to Google in the browser window)
[INFO] Flow loaded successfully
[INFO] Phase 1 complete — browser connection verified
[INFO] Session stored to browser_profile/
```

Verified by actually running `python -m app.main` and observing the output.

---

## 12. Output Directory Layout

### Phase 1
```
output/                       # Created but empty in Phase 1
```

### Phase 2 (MVP complete)
```
output/
└── 2026-09-04/
    └── job_0001/
        ├── prompt.txt        # Copy of the prompt used
        └── video.mp4         # Downloaded video — REQUIRED for success
```

### Phase 2+ (extended)
```
output/
└── 2026-09-04/
    └── job_0001/
        ├── prompt.txt
        ├── video.mp4
        ├── metadata.json     # Title, tags, duration, model, timestamp
        ├── screenshot.png    # Final UI state screenshot
        └── status.json       # Final job state record
```

---

## 13. Logging Specification

Format:
```
[LEVEL] YYYY-MM-DD HH:MM:SS | module | Message
```

### Log Levels

| Level   | When to use                                                  |
|---------|--------------------------------------------------------------|
| DEBUG   | Selector attempts, element state checks                      |
| INFO    | State transitions, milestone events                          |
| WARNING | Fallback selector used, unexpected-but-recoverable states    |
| ERROR   | Failures — include full context, but never credentials       |

### Rules

- **Never** log: cookies, auth tokens, session data, passwords, HTTP headers.
- Always log state transitions explicitly.
- On success, log the exact output file path and file size.

---

## 14. Error Handling & Debug Artifacts

On any exception inside `FlowClient`:

1. Capture screenshot → `debug/YYYY-MM-DD_HH-MM-SS_error.png`
2. Log the current URL.
3. Log the page title.
4. Log exception message + traceback.
5. Transition job to the appropriate failure state.
6. Re-raise so `main.py` catches it and exits with code `1`.

`debug/` is git-ignored.

---

## 15. Prompt System

### Phase 1 & 2 — Manual Prompt

Read from `prompts/test_prompt.txt` as plain UTF-8. Whitespace stripped. Full text passed to `FlowClient.enter_prompt()`.

### Test Prompt

```
Create a photorealistic 10-second vertical cinematic ASMR video
of a miniature black-and-silver Hero Splendor motorcycle being
carefully unboxed on a polished dark walnut tabletop.

Use realistic miniature-scale construction, macro-lens photography,
cinematic chiaroscuro lighting, shallow depth of field, realistic
metal, rubber, plastic and chrome materials, natural human hands,
and satisfying physical unboxing actions.

Maintain consistent motorcycle proportions and authentic Hero
Splendor design.

No cartoon appearance, no futuristic modifications, no additional
motorcycles, no distorted components.

The video should feel like premium realistic automotive product ASMR.
```

### Phase 3+ — Prompt Generator

Will generate prompts from a car database + scene database via LLM. Not built yet.

---

## 16. Generation Monitoring Rules

After `submit_generation()`:

1. Confirm the generation indicator has appeared in the UI.
2. Poll every `generation.poll_interval_seconds` seconds.
3. Do NOT click the generate button again while waiting.
4. Detect "complete" through the UI (e.g., download button appears).
5. Detect "error" through the UI (e.g., error message appears).
6. If `generation.timeout_seconds` elapses → state = `TIMEOUT`, stop.
7. If UI error detected → state = `GENERATION_FAILED`, stop.
8. **No automatic retries.** Retries could consume Google Flow credits.

---

## 17. Download Handling Rules

When generation completes:

1. Identify the generated video element in Flow UI.
2. Use Flow's legitimate download action (button / menu).
3. Intercept Playwright download event — do not use default browser download path.
4. Move file to `output/YYYY-MM-DD/job_0001/video.mp4`.
5. Verify: file exists AND `os.path.getsize() > 0`.
6. Save `prompt.txt` alongside.
7. Only then transition to state `DOWNLOADED`.

---

## 18. What Is Explicitly NOT Built Yet

| Feature                         | Phase |
|---------------------------------|-------|
| YouTube API / uploading         | 4     |
| Automatic scheduling            | 3     |
| Automatic publishing            | 4     |
| 10-video batch generation       | 3     |
| LLM prompt generation           | 3     |
| Car database                    | 3     |
| Scene database                  | 3     |
| Analytics                       | 4     |
| Thumbnails                      | 4     |
| Voiceover / background music    | 4     |
| FFmpeg post-processing          | 3     |
| Autonomous Google login         | Never |
| CAPTCHA bypass                  | Never |
| Anti-bot evasion                | Never |

---

## 19. Future Full-System Architecture

```
CAR DATABASE          (Phase 3)
      ↓
SCENE DATABASE        (Phase 3)
      ↓
PROMPT GENERATOR      (Phase 3)
      ↓  (10 independent prompts)
10 INDEPENDENT JOBS   (Phase 3)
      ↓
GOOGLE FLOW BROWSER AUTOMATION   ← Building NOW (Phase 1 & 2)
      ↓
10 INDIVIDUAL VIDEOS
      ↓
LOCAL QUALITY CONTROL    (Phase 3)
      ↓
LOCAL POST-PROCESSING    (Phase 3 — FFmpeg)
      ↓
METADATA GENERATION      (Phase 4)
      ↓
HUMAN APPROVAL           (Phase 4)
      ↓
YOUTUBE UPLOAD           (Phase 4 — YouTube Data API v3)
```

---

## 20. Development Methodology

**Always work in this order:**

1. Implement one component.
2. Run it immediately.
3. Observe what actually happens.
4. Fix any errors.
5. Confirm it works.
6. Only then move to the next component.

**Never:**
- Generate large amounts of untested code in one shot.
- Claim a feature works without running it.
- Hardcode selectors without inspecting the current DOM.
- Skip a phase because it "should work".

**When the Flow UI changes (and it will):**
- Inspect the current page DOM.
- Update selectors to match reality.
- Add fallback selectors for fragile elements.
- Do not guess — look at the actual element.

---

## 21. Quick Start (Phase 1)

### Prerequisites

- Python 3.11 or higher
- pip

### Setup

```bash
# 1. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Playwright's Chromium browser
playwright install chromium

# 4. Run Phase 1 connection test
python -m app.main
```

### First Run Behaviour

1. A **visible** Chromium browser window opens.
2. Google Flow loads (or Google sign-in appears).
3. You log in manually through the browser window.
4. The script detects authentication and continues.
5. Session is saved to `browser_profile/` (git-ignored).
6. Future runs reuse the session automatically.

### Notes on Google Flow

- Live web application: `https://labs.google/fx/tools/flow`
- UI **changes without notice** — never treat selectors as permanent.
- May require a **Google One / Labs subscription** for access.
- Generation typically takes 2–10 minutes per video.
- System waits up to 15 minutes by default (`timeout_seconds: 900`).

---

*Last updated: 2026-09-04 | Current phase: 1 (Browser Connection MVP)*

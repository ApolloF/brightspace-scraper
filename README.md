# Brightspace RUG Sync Tool

A local Python CLI utility to sync your **Brightspace RUG calendar** (using your private iCal link) and **course files** (using browser automation via Playwright to bypass SSO/MFA).

---

## Features

- **Session Persistence (`auth_state.json`):** Logs in interactively via a headed browser window on the first run, saves cookies/session, and uses them headlessly for future syncs.
- **Calendar Parsing:** Downloads the private iCal calendar feed, parses upcoming deadlines, classes, and exams, and formats them into a clean, markdown file `calendar_summary.md` (which can be easily read by local AI models or IDE agents).
- **Course Downloader:** Discovers active course offerings, recursively traverses their Table of Contents modules, and downloads materials (PDFs, Word docs, PowerPoint presentations, etc.) into the `downloads/` folder, skipping files that have already been downloaded to minimize network overhead.

---

## Setup Instructions

### 1. Configure the Environment File
A default `.env` file has been created. Edit the `.env` file in the project root folder and configure your private iCal URL:

```env
BRIGHTSPACE_BASE_URL=https://brightspace.rug.nl
CALENDAR_ICAL_URL=https://brightspace.rug.nl/d2l/le/calendar/feed/user/feed.ics?token=your_private_token
DOWNLOADS_DIR=downloads
```

> **How to get your private iCal URL:**
> 1. Log in to Brightspace on your browser.
> 2. Go to the **Calendar** tool.
> 3. Click **Settings** (gear icon) in the calendar page.
> 4. Go to **Subscribe** (or look for a button to subscribe to your feed).
> 5. Select **All Calendars and Tasks** or similar, and copy the URL generated. It should end with `feed.ics?token=...`.
> 6. Paste this URL into the `CALENDAR_ICAL_URL` variable in your `.env`.

### 2. Verify Your Environment
The virtual environment has already been set up and dependencies installed. You can activate it using PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

---

## CLI Usage

Run the utility using the `sync.py` entry point:

### 1. Login (Interactive Session Generation)
Opens a headed browser window. Log in using your University of Groningen credentials and complete any multi-factor authentication (MFA). Once the home dashboard is reached, the browser will close and save your login session to `auth_state.json`.

```powershell
python sync.py login
```

### 2. Sync Calendar
Downloads the private iCal calendar feed and generates `calendar_summary.md` in your workspace.

```powershell
python sync.py calendar
```

### 3. Sync Course Files
Walks active courses and downloads all course documents. If it detects a missing or expired session, it will automatically prompt you to log in first.

```powershell
python sync.py files
```

### 4. Sync Everything
Runs calendar synchronization followed by the course files downloader:

```powershell
python sync.py all
```

---

## Pushing to GitHub

Since GitHub CLI is not installed locally, you can push this repository to GitHub manually:

1. Go to [github.com](https://github.com) and log in.
2. Click **New** to create a new repository.
3. Name the repository (e.g. `brightspace-sync`) and leave it **Private** (recommended since it syncs university materials). Do **NOT** initialize it with a README, gitignore, or license (as we already have them).
4. Copy the remote repository URL (e.g. `https://github.com/your-username/brightspace-sync.git`).
5. Open your terminal in the workspace and run:

```powershell
# Set default branch to main
git branch -M main

# Add the remote URL
git remote add origin <paste-your-copied-github-url>

# Push the code
git push -u origin main
```

# Brightspace & Rooster RUG Sync Tool

A robust local Python CLI utility to sync your University of Groningen (RUG) Brightspace courses and Rooster timetables into a personalized, group-filtered schedule, write it to local `.ics` and `.md` files, and automatically upload/synchronize it with Google Calendar.

---

## Features

- **Session Persistence (`auth_state.json`):** Logs in interactively via a headed browser window on the first run, saving cookies/session state. Future syncs run headlessly to bypass SSO/MFA.
- **Personalized Timetables (Rooster RUG):** 
  - Scans your Brightspace course enrollments and retrieves group numbers (e.g. `Werkcolleges` -> `10`, `Werkgroepen` -> `5`) that you are enrolled in.
  - Downloads the official Rooster timetables for all active courses.
  - Automatically filters out classes/events meant for other groups (e.g., if you are in group 10, it filters out events tagged with `gr.17`, `group 5`, etc.), leaving only your personalized schedule.
- **Valence API Deadlines:** Scrapes upcoming deadlines, assignments, and quiz schedules directly from Brightspace using the official Valence API.
- **Unified Calendar Generator:** Merges Rooster events and Brightspace deadlines into a tagged, RFC-5545 compliant `.ics` calendar file (`downloads/personalized_schedule.ics`).
- **Google Calendar Sync:** Performs 2-way incremental synchronization of your unified schedule into a dedicated Google Calendar (defaults to `"Brightspace Sync"`). It uses private extended properties to update modified events and delete obsolete ones.
- **Course Downloader:** Recursively traverses active course modules, downloads documents (PDFs, Word docs, PowerPoint presentations, etc.), and scrapes direct file download links hidden inside module HTML description texts (e.g. *Werkcolleges Tiggelaar*). Skips already-downloaded files to optimize performance.

---

## Setup Instructions

### 1. Prerequisites and Installation
Ensure you have Python 3.10+ installed. In your terminal, run:

```powershell
# Activate the virtual environment
.venv\Scripts\Activate.ps1

# Install any updated dependencies (if needed)
pip install -r requirements.txt
```

### 2. Configure the Environment File
Create/edit the `.env` file in the root folder (based on `.env.template`):

```env
BRIGHTSPACE_BASE_URL=https://brightspace.rug.nl
DOWNLOADS_DIR=downloads
GOOGLE_CALENDAR_NAME=Brightspace Sync
```

### 3. Set Up Google Calendar Integration (Optional)
To use the Google Calendar synchronization, you need to set up Google Cloud OAuth Credentials:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g., `Brightspace Sync`).
3. Search for **Google Calendar API** in the API Library and click **Enable**.
4. Go to the **OAuth consent screen** tab:
   - Choose **External** user type.
   - Enter App details (e.g. App Name: `Brightspace Sync`, and your email).
   - In **Test Users**, add your Google email address (the calendar account you want to sync to).
5. Go to the **Credentials** tab:
   - Click **Create Credentials** -> **OAuth client ID**.
   - Select application type **Desktop App**.
   - Name it (e.g., `Brightspace Sync CLI`) and click **Create**.
6. Download the JSON credentials file, rename it to `credentials.json`, and place it in the root folder of this workspace.

---

## CLI Usage

Run the utility using the `sync.py` entry point:

### 1. Interactive Session Login
Run this command on your first run or when your session expires. It opens a headed browser window. Log in using your RUG credentials and complete any MFA. Once the home dashboard is reached, the browser will save your login session to `auth_state.json`.

```powershell
python sync.py login
```

### 2. Sync and Personalize Schedule
Fetches groups from Brightspace, downloads Rooster timetables, filters them to match your groups, fetches Brightspace deadlines, and merges them into `downloads/personalized_schedule.ics` and a readable summary `calendar_summary.md`.

```powershell
python sync.py schedule
```

### 3. Sync Course Files
Walks active courses and downloads all files, including links inside HTML descriptions.

```powershell
python sync.py files
```

### 4. Sync to Google Calendar
Syncs the generated schedule from `downloads/personalized_schedule.ics` to your Google Calendar account. The first time you run this, a browser window will open asking you to log in to your Google Account and authorize the app. The credentials will be cached in `token.json` for future runs.

```powershell
python sync.py sync-gcal
```

### 5. Run Everything (Sync All)
Syncs the schedule, course files, and updates Google Calendar in one command:

```powershell
python sync.py all
```

---

## Pushing to GitHub

Since GitHub CLI is not installed locally, you can push this repository to GitHub manually:

1. Go to [github.com](https://github.com) and log in.
2. Click **New** to create a new repository.
3. Name the repository `brightspace-scraper` (or something similar). Keep it **Private** (highly recommended, as it syncs university materials). Do **NOT** initialize it with a README, gitignore, or license.
4. Copy the remote repository URL (e.g. `https://github.com/ApolloF/brightspace-scraper.git`).
5. Open your terminal in the workspace and run:

```powershell
# Set default branch name to main
git branch -M main

# Add the remote URL
git remote add origin <paste-your-copied-github-url>

# Push the code to the main branch
git push -u origin main
```

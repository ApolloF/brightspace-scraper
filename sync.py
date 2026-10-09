import sys
import io
import asyncio
from brightspace_sync.auth import login, check_auth, AUTH_STATE_PATH, BRIGHTSPACE_BASE_URL
from brightspace_sync.calendar import (
    sync_calendar, 
    fetch_active_courses, 
    fetch_brightspace_calendar_events, 
    generate_merged_calendar, 
    write_calendar_summary,
    write_weekly_schedule_todo_summary
)
from brightspace_sync.downloader import sync_files
from brightspace_sync.rooster import scan_brightspace_groups, sync_personalized_schedule
from brightspace_sync.gcal import sync_to_google_calendar
import os
from playwright.async_api import async_playwright

DOWNLOADS_DIR = os.getenv("DOWNLOADS_DIR", "downloads")
# Reconfigure standard output streams to handle Unicode characters safely on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Default course and group presets for Year 2 Semester 1a Bedrijfskunde (BDK)
Y2S1_COURSES = [
    {"id": "EBB054A05", "name": "Management- en Organisatietheorie", "code": "EBB054A05"},
    {"id": "EBB050A05", "name": "Kwalitatieve onderzoeksmethoden", "code": "EBB050A05"},
    {"id": "EBB046A05", "name": "Financial Management BDK", "code": "EBB046A05"}
]

Y2S1_GROUPS = {
    "EBB054A05": ["Werkcollege 3 - Groepje 3", "Werkcollege 3 - Donderdag 13.00-15.00 in 5416.0059", "gr.03", "gr03", "group 3", "3"],
    "EBB050A05": ["3.8", "Werkcollege 3", "gr.03", "gr03", "group 3", "3"],
    "EBB046A05": ["group 1", "gr01", "gr.01", "1"]
}

def print_help():
    print("=" * 60)
    print("Brightspace RUG Sync Tool CLI")
    print("=" * 60)
    print("Usage:")
    print("  python sync.py login          - Open interactive browser to log in and save session")
    print("  python sync.py schedule       - Sync personalized schedule (Rooster + Brightspace)")
    print("  python sync.py schedule y2s1  - Sync Year 2 Semester 1a schedule (Group 1)")
    print("  python sync.py summary        - Generate weekly schedule & to-do summary")
    print("  python sync.py calendar       - Legacy: Sync iCal calendar feed to local 'calendar_summary.md'")
    print("  python sync.py files          - Sync course files (downloads new/modified materials)")
    print("  python sync.py sync-gcal      - Synchronize the personalized schedule to Google Calendar")
    print("  python sync.py all            - Run schedule sync, files sync, and Google Calendar sync")
    print("  python sync.py help           - Show this help message")
    print("=" * 60)

async def run_personalized_schedule(force_y2s1=False):
    courses = []
    course_groups = {}
    bs_events = []
    
    # 1. Determine whether to use Brightspace session or direct Year 2 Semester 1 preset
    print("Checking Brightspace session status...")
    is_authenticated = False
    try:
        is_authenticated = await check_auth()
    except Exception:
        is_authenticated = False
        
    if is_authenticated and not force_y2s1:
        async with async_playwright() as p:
            request_context = await p.request.new_context(
                base_url=BRIGHTSPACE_BASE_URL,
                storage_state=AUTH_STATE_PATH
            )
            
            print("Fetching active courses from Brightspace...")
            courses = await fetch_active_courses(request_context)
            if courses:
                print("Scanning Brightspace group memberships...")
                course_groups = await scan_brightspace_groups(request_context, courses)
                print("Scraping deadlines and assignments from Brightspace...")
                bs_events = await fetch_brightspace_calendar_events(request_context, courses)
    else:
        if not is_authenticated:
            print("[INFO] No active Brightspace session. Using Year 2 Semester 1a courses (Rooster RUG direct mode).")
        else:
            print("[INFO] Targeting Year 2 Semester 1a courses directly.")
        courses = Y2S1_COURSES
        course_groups = Y2S1_GROUPS

    # 2. Retrieve and filter Rooster RUG timetables
    print(f"Retrieving and group-filtering Rooster RUG schedule for {len(courses)} course(s)...")
    rooster_events, web_url, direct_url = sync_personalized_schedule(course_groups, courses)
    if not rooster_events:
        print("[ERROR] No events retrieved from Rooster RUG timetable.")
        return False
        
    # 3. Merge and save
    print("Merging events and generating unified schedule...")
    cal = generate_merged_calendar(rooster_events, bs_events)
    
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    ics_path = os.path.join(DOWNLOADS_DIR, "personalized_schedule.ics")
    try:
        with open(ics_path, "wb") as f:
            f.write(cal.to_ical())
        print(f"Personalized schedule successfully saved to '{ics_path}'!")
    except Exception as e:
        print(f"[ERROR] Failed to save '{ics_path}': {e}")
        return False
        
    # 4. Write calendar summary & weekly schedule / to-do guide
    summary_path = "calendar_summary.md"
    todo_path = "weekly_schedule_todo.md"
    write_calendar_summary(rooster_events, bs_events, summary_path)
    write_weekly_schedule_todo_summary(rooster_events, bs_events, todo_path)
    
    print("=" * 60)
    print("SCHEDULE SYNC COMPLETION SUMMARY")
    print("=" * 60)
    print(f"Total Personalized Events: {len(rooster_events) + len(bs_events)}")
    print(f"ICS Calendar File        : {ics_path}")
    print(f"Calendar Summary         : {summary_path}")
    print(f"Weekly Schedule & To-Do  : {todo_path}")
    print(f"Personalized Rooster URL :\n  {web_url}\n")
    print(f"Personalized Direct iCal :\n  {direct_url}\n")
    print("=" * 60)
    return True


async def main():
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
        
    cmd = sys.argv[1].lower()
    
    if cmd == "login":
        await login()
    elif cmd == "schedule":
        force_y2s1 = len(sys.argv) > 2 and sys.argv[2].lower() in ("y2s1", "y2", "semester1a", "s1a")
        await run_personalized_schedule(force_y2s1=force_y2s1)
    elif cmd == "summary":
        await run_personalized_schedule(force_y2s1=True)
    elif cmd == "calendar":
        sync_calendar()
    elif cmd == "files":
        print("Checking session status...")
        is_authenticated = await check_auth()
        if not is_authenticated:
            print("No active session or session has expired. Launching login browser...")
            await login()
            is_authenticated = await check_auth()
            if not is_authenticated:
                print("[ERROR] Authentication check failed after login. Sync aborted.")
                sys.exit(1)
        targets = sys.argv[2:] if len(sys.argv) > 2 else None
        await sync_files(target_courses=targets)
    elif cmd == "sync-gcal":
        gcal_name = os.getenv("GOOGLE_CALENDAR_NAME", "Brightspace Sync")
        ics_path = os.path.join(DOWNLOADS_DIR, "personalized_schedule.ics")
        sync_to_google_calendar(ics_path, gcal_name)
    elif cmd == "all":
        print("\n=== STEP 1: Syncing Personalized Schedule (Rooster + Brightspace) ===")
        schedule_success = await run_personalized_schedule()
        
        print("\n=== STEP 2: Syncing Course Files ===")
        print("Checking session status...")
        is_authenticated = await check_auth()
        if not is_authenticated:
            print("No active session or session has expired. Launching login browser...")
            await login()
            is_authenticated = await check_auth()
            if not is_authenticated:
                print("[ERROR] Authentication check failed after login. Sync aborted.")
                sys.exit(1)
        await sync_files()
        
        if schedule_success:
            print("\n=== STEP 3: Synchronizing to Google Calendar ===")
            gcal_name = os.getenv("GOOGLE_CALENDAR_NAME", "Brightspace Sync")
            ics_path = os.path.join(DOWNLOADS_DIR, "personalized_schedule.ics")
            sync_to_google_calendar(ics_path, gcal_name)
    elif cmd in ("help", "--help", "-h"):
        print_help()
    else:
        print(f"Unknown command: {cmd}")
        print_help()
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)

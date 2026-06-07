import sys
import io
import asyncio
from brightspace_sync.auth import login, check_auth, AUTH_STATE_PATH, BRIGHTSPACE_BASE_URL
from brightspace_sync.calendar import sync_calendar, fetch_active_courses, fetch_brightspace_calendar_events, generate_merged_calendar, write_calendar_summary
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


def print_help():
    print("=" * 60)
    print("Brightspace RUG Sync Tool CLI")
    print("=" * 60)
    print("Usage:")
    print("  python sync.py login      - Open interactive browser to log in and save session")
    print("  python sync.py schedule   - Sync personalized schedule (Rooster + Brightspace deadlines) to local .ics and .md")
    print("  python sync.py calendar   - Legacy: Sync iCal calendar feed to local 'calendar_summary.md'")
    print("  python sync.py files      - Sync course files (downloads new/modified materials)")
    print("  python sync.py sync-gcal  - Synchronize the personalized schedule to Google Calendar")
    print("  python sync.py all        - Run schedule sync, files sync, and Google Calendar sync")
    print("  python sync.py help       - Show this help message")
    print("=" * 60)

async def run_personalized_schedule():
    print("Checking Brightspace session status...")
    is_authenticated = await check_auth()
    if not is_authenticated:
        print("No active session or session has expired. Launching login browser...")
        await login()
        is_authenticated = await check_auth()
        if not is_authenticated:
            print("[ERROR] Authentication check failed after login. Sync aborted.")
            return False
            
    async with async_playwright() as p:
        request_context = await p.request.new_context(
            base_url=BRIGHTSPACE_BASE_URL,
            storage_state=AUTH_STATE_PATH
        )
        
        # 1. Fetch active courses
        print("Fetching active courses...")
        courses = await fetch_active_courses(request_context)
        if not courses:
            print("[Warning] No active courses found. Schedule sync aborted.")
            return False
            
        # 2. Scan groups
        print("Scanning Brightspace group memberships...")
        course_groups = await scan_brightspace_groups(request_context, courses)
        
        # 3. Retrieve and filter Rooster RUG timetables
        print("Retrieving and group-filtering Rooster RUG schedule...")
        rooster_events, web_url, direct_url = sync_personalized_schedule(course_groups, courses)
        
        # 4. Scrape Brightspace calendar events
        print("Scraping deadlines and assignments from Brightspace...")
        bs_events = await fetch_brightspace_calendar_events(request_context, courses)
        
        # 5. Merge and save
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
            
        # Write summary
        write_calendar_summary(rooster_events, bs_events, "calendar_summary.md")
        
        print("=" * 60)
        print("SCHEDULE SYNC COMPLETION SUMMARY")
        print("=" * 60)
        print(f"Personalized Rooster RUG Web URL:\n  {web_url}\n")
        print(f"Personalized Direct iCal Feed URL:\n  {direct_url}\n")
        print("You can copy the direct iCal URL above and subscribe to it in your calendar app.")
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
        await run_personalized_schedule()
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
        await sync_files()
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

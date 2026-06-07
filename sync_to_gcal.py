import os
from dotenv import load_dotenv
from brightspace_sync.gcal import sync_to_google_calendar

# Load configurations
load_dotenv()

def main():
    calendar_name = os.getenv("GOOGLE_CALENDAR_NAME", "Brightspace Sync")
    downloads_dir = os.getenv("DOWNLOADS_DIR", "downloads")
    ics_path = os.path.join(downloads_dir, "personalized_schedule.ics")
    
    print("=" * 60)
    print("GOOGLE CALENDAR SYNC RUNNER")
    print("=" * 60)
    print(f"Calendar Name: '{calendar_name}'")
    print(f"ICS Source   : '{ics_path}'")
    print("=" * 60)
    
    if not os.path.exists(ics_path):
        print(f"[ERROR] Source file '{ics_path}' does not exist.")
        print("Please run `python sync.py schedule` first to build your personalized schedule.")
        return
        
    success = sync_to_google_calendar(ics_path, calendar_name)
    if success:
        print("[SUCCESS] Schedule has been successfully synchronized to your Google Calendar!")
    else:
        print("[FAILED] Synchronization failed. Check error logs above.")

if __name__ == "__main__":
    main()

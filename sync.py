import sys
import io
import asyncio
from brightspace_sync.auth import login, check_auth
from brightspace_sync.calendar import sync_calendar
from brightspace_sync.downloader import sync_files

# Reconfigure standard output streams to handle Unicode characters safely on Windows console
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def print_help():
    print("=" * 60)
    print("Brightspace RUG Sync Tool CLI")
    print("=" * 60)
    print("Usage:")
    print("  python sync.py login      - Open interactive browser to log in and save session")
    print("  python sync.py calendar   - Sync iCal calendar feed to local 'calendar_summary.md'")
    print("  python sync.py files      - Sync course files (downloads new/modified materials)")
    print("  python sync.py all        - Run calendar sync followed by course files sync")
    print("  python sync.py help       - Show this help message")
    print("=" * 60)

async def main():
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
        
    cmd = sys.argv[1].lower()
    
    if cmd == "login":
        await login()
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
    elif cmd == "all":
        print("\n=== STEP 1: Syncing iCal Calendar ===")
        sync_calendar()
        
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

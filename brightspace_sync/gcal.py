import os
import json
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from icalendar import Calendar

# Google Calendar API Scopes
SCOPES = ['https://www.googleapis.com/auth/calendar']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

def get_gcal_credentials():
    """
    Retrieves the Google OAuth2 credentials.
    Loads existing token if present; otherwise runs local web server flow.
    """
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            print(f"[Warning] Failed to load '{TOKEN_FILE}': {e}")
            
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("Refreshing Google API access token...")
                creds.refresh(Request())
            except Exception as e:
                print(f"[Warning] Refresh failed: {e}. Re-authenticating...")
                creds = None
                
        if not creds:
            if not os.path.exists(CREDENTIALS_FILE):
                print("=" * 60)
                print("[ERROR] Google Calendar OAuth client credentials file 'credentials.json' is missing!")
                print("To sync to Google Calendar, you must place your 'credentials.json' in the project root.")
                print("Refer to README.md or the walkthrough for instructions on how to create this file.")
                print("=" * 60)
                return None
                
            print("Starting Google OAuth2 authentication flow...")
            print("A browser window will open for you to log in and authorize the application.")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save the credentials for the next run
        try:
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
            print(f"Google API credentials saved to '{TOKEN_FILE}'.")
        except Exception as e:
            print(f"[Warning] Failed to save '{TOKEN_FILE}': {e}")
            
    return creds

def get_or_create_calendar(service, calendar_name):
    """
    Finds a calendar with the specified name in the user's list,
    or creates a new secondary calendar if it doesn't exist.
    """
    print(f"Finding Google Calendar with name '{calendar_name}'...")
    page_token = None
    while True:
        calendar_list = service.calendarList().list(pageToken=page_token).execute()
        for calendar_entry in calendar_list.get('items', []):
            if calendar_entry.get('summary') == calendar_name:
                print(f"Found existing calendar '{calendar_name}' (ID: {calendar_entry['id']})")
                return calendar_entry['id']
        page_token = calendar_list.get('nextPageToken')
        if not page_token:
            break
            
    print(f"Calendar '{calendar_name}' not found. Creating a new one...")
    calendar = {
        'summary': calendar_name,
        'timeZone': 'Europe/Amsterdam'
    }
    created_calendar = service.calendars().insert(body=calendar).execute()
    print(f"Created calendar '{calendar_name}' successfully (ID: {created_calendar['id']})")
    return created_calendar['id']

def format_gcal_time(dt):
    """
    Converts datetime or date objects to Google Calendar API event time structures.
    """
    if isinstance(dt, datetime.datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return {'dateTime': dt.isoformat()}
    elif isinstance(dt, datetime.date):
        return {'date': dt.isoformat()}
    return None

def parse_ics_events(ics_path):
    """
    Parses a local .ics file and extracts events in a simple list of dicts.
    """
    if not os.path.exists(ics_path):
        print(f"[ERROR] Unified schedule file '{ics_path}' not found.")
        return []
        
    with open(ics_path, 'rb') as f:
        gcal = Calendar.from_ical(f.read())
        
    events = []
    for component in gcal.walk():
        if component.name == "VEVENT":
            summary = str(component.get("summary", "Untitled Event"))
            description = str(component.get("description", ""))
            location = str(component.get("location", ""))
            uid = str(component.get("uid", ""))
            
            dtstart = component.get("dtstart").dt if component.get("dtstart") else None
            dtend = component.get("dtend").dt if component.get("dtend") else None
            
            events.append({
                "summary": summary,
                "description": description,
                "location": location,
                "uid": uid,
                "dtstart": dtstart,
                "dtend": dtend
            })
    return events

def sync_events_to_gcal(service, calendar_id, ics_events):
    """
    Syncs the parsed events list to Google Calendar.
    Performs incremental inserts, updates, and deletes.
    """
    print("Fetching existing events from Google Calendar...")
    
    # We query events that have privateExtendedProperty 'source=brightspace-sync'
    gcal_events = []
    page_token = None
    while True:
        events_result = service.events().list(
            calendarId=calendar_id,
            privateExtendedProperty="source=brightspace-sync",
            maxResults=2500,
            pageToken=page_token
        ).execute()
        
        gcal_events.extend(events_result.get('items', []))
        page_token = events_result.get('nextPageToken')
        if not page_token:
            break
            
    print(f"Found {len(gcal_events)} synced event(s) in Google Calendar.")
    
    # Index Google Calendar events by their original iCal UID
    gcal_map = {}
    for item in gcal_events:
        props = item.get('extendedProperties', {}).get('private', {})
        uid = props.get('uid')
        if uid:
            gcal_map[uid] = item
            
    # Track which Google Calendar events are still active (seen)
    seen_gcal_uids = set()
    
    inserted = 0
    updated = 0
    skipped = 0
    
    for ev in ics_events:
        uid = ev["uid"]
        summary = ev["summary"]
        description = ev["description"]
        location = ev["location"]
        dtstart = ev["dtstart"]
        dtend = ev["dtend"] or dtstart
        
        start_g = format_gcal_time(dtstart)
        end_g = format_gcal_time(dtend)
        
        # Google Calendar Event Payload
        event_body = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': start_g,
            'end': end_g,
            'extendedProperties': {
                'private': {
                    'source': 'brightspace-sync',
                    'uid': uid
                }
            }
        }
        
        if uid in gcal_map:
            # Event exists. Check if we need to update it
            seen_gcal_uids.add(uid)
            existing = gcal_map[uid]
            
            # Simple difference check
            # We compare summary, location, description, and times
            # Note: Google Calendar API dates are returned as dicts
            needs_update = False
            
            # Helper to check if time definitions are equal
            def times_equal(t1, t2):
                if not t1 or not t2:
                    return False
                if 'dateTime' in t1 and 'dateTime' in t2:
                    # Parse and compare as datetimes (handles timezone differences)
                    try:
                        d1 = datetime.datetime.fromisoformat(t1['dateTime'].replace('Z', '+00:00'))
                        d2 = datetime.datetime.fromisoformat(t2['dateTime'].replace('Z', '+00:00'))
                        return d1 == d2
                    except Exception:
                        return t1['dateTime'] == t2['dateTime']
                elif 'date' in t1 and 'date' in t2:
                    return t1['date'] == t2['date']
                return False
                
            if existing.get('summary') != summary:
                needs_update = True
            elif existing.get('location', '') != location:
                needs_update = True
            elif existing.get('description', '') != description:
                needs_update = True
            elif not times_equal(existing.get('start'), start_g):
                needs_update = True
            elif not times_equal(existing.get('end'), end_g):
                needs_update = True
                
            if needs_update:
                service.events().update(
                    calendarId=calendar_id,
                    eventId=existing['id'],
                    body=event_body
                ).execute()
                updated += 1
            else:
                skipped += 1
        else:
            # Event is new, insert it
            service.events().insert(
                calendarId=calendar_id,
                body=event_body
            ).execute()
            inserted += 1
            
    # Delete stale events (events in GCal but no longer in our .ics file)
    deleted = 0
    for uid, existing in gcal_map.items():
        if uid not in seen_gcal_uids:
            service.events().delete(
                calendarId=calendar_id,
                eventId=existing['id']
            ).execute()
            deleted += 1
            
    print(f"Sync complete: {inserted} inserted, {updated} updated, {skipped} skipped, {deleted} deleted.")

def sync_to_google_calendar(ics_path, calendar_name="Brightspace Sync"):
    """
    Main function to run the iCal to Google Calendar sync process.
    """
    creds = get_gcal_credentials()
    if not creds:
        print("[ERROR] Google credentials could not be initialized. Sync aborted.")
        return False
        
    try:
        service = build('calendar', 'v3', credentials=creds)
        calendar_id = get_or_create_calendar(service, calendar_name)
        
        ics_events = parse_ics_events(ics_path)
        if not ics_events:
            print("[Warning] No events found in unified schedule. Sync aborted.")
            return False
            
        print(f"Loaded {len(ics_events)} event(s) from '{ics_path}'. Starting sync...")
        sync_events_to_gcal(service, calendar_id, ics_events)
        return True
    except Exception as e:
        print(f"[ERROR] Google Calendar synchronization failed: {e}")
        return False

import os
import datetime
import urllib.request
import urllib.parse
import json
import re
from icalendar import Calendar, Event
from dotenv import load_dotenv

# Load configuration
load_dotenv()
CALENDAR_ICAL_URL = os.getenv("CALENDAR_ICAL_URL")
BRIGHTSPACE_BASE_URL = os.getenv("BRIGHTSPACE_BASE_URL", "https://brightspace.rug.nl").rstrip("/")
DOWNLOADS_DIR = os.getenv("DOWNLOADS_DIR", "downloads")

def parse_event_time(dt_prop):
    """
    Parses datetime properties from iCal, handling both datetime and date-only values.
    Returns (datetime_obj, is_all_day).
    """
    if not dt_prop:
        return None, False
    
    dt = dt_prop.dt
    if isinstance(dt, datetime.datetime):
        # Convert timezone-aware datetimes to UTC or preserve them
        return dt, False
    elif isinstance(dt, datetime.date):
        # All-day event
        # Convert to a datetime at midnight
        dt_datetime = datetime.datetime.combine(dt, datetime.time.min, tzinfo=datetime.timezone.utc)
        return dt_datetime, True
    return None, False

def format_event_row(event, now):
    """
    Formats a single event for the Markdown report.
    """
    start_dt = event["start_dt"]
    is_all_day = event["is_all_day"]
    summary = event["summary"]
    description = event["description"]
    location = event.get("location", "")
    
    # Calculate days relative to today
    today = now.date()
    event_date = start_dt.date()
    delta = (event_date - today).days
    
    if delta == 0:
        time_str = "TODAY"
    elif delta == 1:
        time_str = "TOMORROW"
    elif delta == -1:
        time_str = "YESTERDAY"
    elif delta > 0:
        time_str = f"In {delta} days"
    else:
        time_str = f"{abs(delta)} days ago"
        
    date_formatted = event_date.strftime("%A, %b %d, %Y")
    
    if is_all_day:
        time_detail = "All Day"
    else:
        time_detail = start_dt.strftime("%H:%M")
        if start_dt.tzinfo:
            # Show offset/tzname
            time_detail += f" ({start_dt.tzname() or 'UTC'})"

    status = "🔴" if delta < 0 else ("🟡" if delta == 0 or delta == 1 else "🟢")
    
    markdown = f"### {status} {summary}\n"
    markdown += f"* **Date:** {date_formatted} ({time_str})\n"
    markdown += f"* **Time:** {time_detail}\n"
    if location and location.strip():
        markdown += f"* **Location:** {location.strip()}\n"
    if description and description.strip() != "None":
        clean_desc = description.replace("<br/>", "\n").replace("<br>", "\n").strip()
        # Remove any HTML tags from description for clean display
        clean_desc = re.sub('<[^<]+?>', '', clean_desc)
        markdown += f"* **Description:**\n  ```text\n  {clean_desc}\n  ```\n"
    markdown += "\n"
    return markdown

def sync_calendar():
    """
    Downloads and parses the iCal feed, saving upcoming events to calendar_summary.md.
    """
    if not CALENDAR_ICAL_URL:
        print("[ERROR] CALENDAR_ICAL_URL environment variable is not set in `.env`.")
        print("Please configure your private iCal link in your `.env` file first.")
        return False
        
    print(f"Downloading calendar from private feed...")
    try:
        req = urllib.request.Request(
            CALENDAR_ICAL_URL,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            ics_data = response.read()
    except Exception as e:
        print(f"[ERROR] Failed to download calendar: {e}")
        return False

    print("Parsing iCal data...")
    try:
        gcal = Calendar.from_ical(ics_data)
    except Exception as e:
        print(f"[ERROR] Failed to parse iCal file: {e}")
        return False
        
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Gather events
    events = []
    for component in gcal.walk():
        if component.name == "VEVENT":
            summary = str(component.get("summary", "Untitled Event"))
            description = str(component.get("description", ""))
            
            start_dt, is_all_day = parse_event_time(component.get("dtstart"))
            end_dt, _ = parse_event_time(component.get("dtend"))
            
            if not start_dt:
                continue
                
            events.append({
                "summary": summary,
                "description": description,
                "start_dt": start_dt,
                "end_dt": end_dt,
                "is_all_day": is_all_day
            })
            
    # Sort chronologically
    events.sort(key=lambda e: e["start_dt"])
    
    # Filter: Show events from 7 days ago to 60 days in the future
    start_filter = now - datetime.timedelta(days=7)
    end_filter = now + datetime.timedelta(days=60)
    
    filtered_events = [
        e for e in events 
        if start_filter <= e["start_dt"] <= end_filter
    ]
    
    past_events = [e for e in filtered_events if e["start_dt"] < now]
    upcoming_events = [e for e in filtered_events if e["start_dt"] >= now]
    
    # Generate markdown file
    md_content = f"# Brightspace Calendar Summary\n"
    md_content += f"*Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (Local Time)*\n\n"
    
    md_content += "## 📅 Upcoming Deadlines & Events (Next 60 Days)\n\n"
    if not upcoming_events:
        md_content += "*No upcoming events found.*\n\n"
    else:
        for event in upcoming_events:
            md_content += format_event_row(event, now)
            
    md_content += "## 🕒 Recent Deadlines & Events (Past 7 Days)\n\n"
    if not past_events:
        md_content += "*No recent past events found.*\n\n"
    else:
        for event in past_events:
            md_content += format_event_row(event, now)
            
    output_path = "calendar_summary.md"
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"Calendar successfully synced! Summary written to '{output_path}'.")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to write '{output_path}': {e}")
        return False


# --- NEW CUSTOM ENDPOINTS FOR PERSONALIZED SCHEDULE MERGING ---

async def fetch_active_courses(request_context):
    """
    Fetches user active course enrollments for the current year from Brightspace.
    """
    courses = []
    url = "/d2l/api/lp/1.26/enrollments/myenrollments/"
    while url:
        response = await request_context.get(url)
        if response.status != 200:
            print("[Warning] Failed to fetch enrollments for calendar sync.")
            return []
        data = await response.json()
        for item in data.get("Items", []):
            org_unit = item.get("OrgUnit", {})
            access = item.get("Access", {})
            if org_unit.get("Type", {}).get("Id") == 3 and access.get("CanAccess", True):
                code = org_unit.get("Code", "")
                courses.append({
                    "id": org_unit.get("Id"),
                    "name": org_unit.get("Name"),
                    "code": code
                })
        url = data.get("Next")
        if url and url.startswith(BRIGHTSPACE_BASE_URL):
            url = url[len(BRIGHTSPACE_BASE_URL):]
    return courses

async def fetch_brightspace_calendar_events(request_context, courses):
    """
    Scrapes user calendar events from the Brightspace Valence API for all courses.
    Returns a list of parsed event dictionaries.
    """
    # Look for events from 30 days ago to 180 days in the future
    now = datetime.datetime.now(datetime.timezone.utc)
    start_dt = now - datetime.timedelta(days=30)
    end_dt = now + datetime.timedelta(days=180)
    
    start_str = urllib.parse.quote(start_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"))
    end_str = urllib.parse.quote(end_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"))
    
    # Map orgUnitId to course details for tagging
    course_map = {c["id"]: c for c in courses}
    
    bs_events = []
    
    for c in courses:
        cal_url = f"/d2l/api/le/1.26/{c['id']}/calendar/events/myEvents/?startDateTime={start_str}&endDateTime={end_str}"
        response = await request_context.get(cal_url)
        if response.status != 200:
            continue
            
        data = await response.json()
        events = data.get("Objects", []) if isinstance(data, dict) else data
        for ev in events:
            title = ev.get("Title", "Untitled Assignment")
            description = ev.get("Description", "")
            
            # Brightspace date format: '2026-06-05T15:00:00.000Z'
            start_dt_str = ev.get("StartDateTime")
            end_dt_str = ev.get("EndDateTime")
            
            # Parse datetime
            def parse_bs_date(date_str):
                if not date_str:
                    return None
                try:
                    # e.g. "2026-06-05T15:00:00.000Z"
                    clean_str = date_str.replace("Z", "+00:00")
                    # some endpoints don't return milliseconds or return varying precision
                    if '.' in clean_str:
                        return datetime.datetime.strptime(clean_str.split('.')[0] + "+00:00", "%Y-%m-%dT%H:%M:%S%z")
                    return datetime.datetime.strptime(clean_str, "%Y-%m-%dT%H:%M:%S%z")
                except Exception as e:
                    print(f"Error parsing date string '{date_str}': {e}")
                    return None
                    
            event_start = parse_bs_date(start_dt_str)
            event_end = parse_bs_date(end_dt_str) or event_start
            
            if not event_start:
                continue
                
            # Determine if all day
            is_all_day = (event_start == event_end) or ("all day" in title.lower())
            
            # Create a clean course code tag
            raw_code = c.get("code", "")
            clean_code = raw_code.split('.')[0] if '.' in raw_code else raw_code
            
            bs_events.append({
                "summary": f"[Brightspace][{clean_code}] {title}",
                "description": description,
                "location": "Brightspace",
                "uid": f"bs-{ev.get('CalendarEventId')}@brightspace.rug.nl",
                "course_code": clean_code,
                "dtstart": event_start,
                "dtend": event_end,
                "is_all_day": is_all_day,
                "categories": ["Brightspace", clean_code]
            })
            
    return bs_events

def generate_merged_calendar(rooster_events, bs_events):
    """
    Constructs an RFC-5545 compliant Calendar object containing all tagged and filtered events.
    """
    cal = Calendar()
    cal.add('prodid', '-//Brightspace & Rooster RUG Sync//EN')
    cal.add('version', '2.0')
    
    # Process Rooster RUG events
    for ev in rooster_events:
        event = Event()
        
        # Tag summary with course code
        summary = ev["summary"]
        code = ev["course_code"]
        if code and not summary.startswith(f"[{code}]"):
            summary = f"[{code}] {summary}"
            
        event.add('summary', summary)
        
        # Datetimes
        event.add('dtstart', ev["dtstart"])
        event.add('dtend', ev["dtend"] or ev["dtstart"])
        
        # Description & Location
        event.add('description', ev["description"])
        event.add('location', ev["location"])
        event.add('uid', ev["uid"])
        
        # Categories for filtering
        categories = ["Rooster"]
        if code:
            categories.append(code)
        event.add('categories', categories)
        
        cal.add_component(event)
        
    # Process Brightspace events
    for ev in bs_events:
        event = Event()
        event.add('summary', ev["summary"])
        event.add('dtstart', ev["dtstart"])
        event.add('dtend', ev["dtend"])
        event.add('description', ev["description"])
        event.add('location', ev["location"])
        event.add('uid', ev["uid"])
        event.add('categories', ev["categories"])
        cal.add_component(event)
        
    return cal

def write_calendar_summary(rooster_events, bs_events, output_path):
    """
    Generates a human-readable calendar_summary.md file for the combined schedule.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Merge and unify event structures
    all_events = []
    
    for ev in rooster_events:
        # Check if all day
        dtstart = ev["dtstart"]
        dtend = ev["dtend"]
        is_all_day = False
        if dtstart and dtend:
            # If start is a date object, or if it spans exactly midnight to midnight
            if not isinstance(dtstart, datetime.datetime) or (dtstart.time() == datetime.time.min and dtend.time() == datetime.time.min and (dtend - dtstart).days >= 1):
                is_all_day = True
                
        summary = ev["summary"]
        code = ev["course_code"]
        if code and not summary.startswith(f"[{code}]"):
            summary = f"[{code}] {summary}"
            
        # Ensure timezone-aware datetime for start_dt
        start_dt = dtstart
        if not isinstance(start_dt, datetime.datetime):
            start_dt = datetime.datetime.combine(start_dt, datetime.time.min, tzinfo=datetime.timezone.utc)
        elif start_dt.tzinfo is None or start_dt.tzinfo.utcoffset(start_dt) is None:
            start_dt = start_dt.replace(tzinfo=datetime.timezone.utc)
            
        # Ensure timezone-aware datetime for end_dt
        end_dt = dtend if dtend else start_dt
        if not isinstance(end_dt, datetime.datetime):
            end_dt = datetime.datetime.combine(end_dt, datetime.time.min, tzinfo=datetime.timezone.utc)
        elif end_dt.tzinfo is None or end_dt.tzinfo.utcoffset(end_dt) is None:
            end_dt = end_dt.replace(tzinfo=datetime.timezone.utc)
             
        all_events.append({
            "summary": summary,
            "description": ev["description"],
            "location": ev["location"],
            "start_dt": start_dt,
            "end_dt": end_dt,
            "is_all_day": is_all_day
        })
        
    for ev in bs_events:
        # Ensure timezone-aware datetime for Brightspace events as well
        start_dt = ev["dtstart"]
        if start_dt.tzinfo is None or start_dt.tzinfo.utcoffset(start_dt) is None:
            start_dt = start_dt.replace(tzinfo=datetime.timezone.utc)
            
        end_dt = ev["dtend"]
        if end_dt.tzinfo is None or end_dt.tzinfo.utcoffset(end_dt) is None:
            end_dt = end_dt.replace(tzinfo=datetime.timezone.utc)
            
        all_events.append({
            "summary": ev["summary"],
            "description": ev["description"],
            "location": ev["location"],
            "start_dt": start_dt,
            "end_dt": end_dt,
            "is_all_day": ev["is_all_day"]
        })
        
    # Sort chronologically
    all_events.sort(key=lambda e: e["start_dt"])
    
    # Filter: Show events from 7 days ago to 60 days in the future
    start_filter = now - datetime.timedelta(days=7)
    end_filter = now + datetime.timedelta(days=60)
    
    filtered_events = [
        e for e in all_events 
        if start_filter <= e["start_dt"] <= end_filter
    ]
    
    past_events = [e for e in filtered_events if e["start_dt"] < now]
    upcoming_events = [e for e in filtered_events if e["start_dt"] >= now]
    
    md_content = f"# Brightspace & Rooster Personalized Calendar Summary\n"
    md_content += f"*Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (Local Time)*\n\n"
    
    md_content += "## 📅 Upcoming Deadlines & Events (Next 60 Days)\n\n"
    if not upcoming_events:
        md_content += "*No upcoming events found.*\n\n"
    else:
        for event in upcoming_events:
            md_content += format_event_row(event, now)
            
    md_content += "## 🕒 Recent Deadlines & Events (Past 7 Days)\n\n"
    if not past_events:
        md_content += "*No recent past events found.*\n\n"
    else:
        for event in past_events:
            md_content += format_event_row(event, now)
            
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"Calendar summary written to '{output_path}'.")
    except Exception as e:
        print(f"[Warning] Failed to write calendar summary: {e}")

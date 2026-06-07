import os
import datetime
import urllib.request
from icalendar import Calendar
from dotenv import load_dotenv

# Load configuration
load_dotenv()
CALENDAR_ICAL_URL = os.getenv("CALENDAR_ICAL_URL")

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
        # If the start_dt is timezone-aware, we can display the offset/name
        if start_dt.tzinfo:
            time_detail += f" ({start_dt.tzname() or 'UTC'})"

    status = "🔴" if delta < 0 else ("🟡" if delta == 0 or delta == 1 else "🟢")
    
    markdown = f"### {status} {summary}\n"
    markdown += f"* **Date:** {date_formatted} ({time_str})\n"
    markdown += f"* **Time:** {time_detail}\n"
    if description and description.strip() != "None":
        # Strip simple HTML if any, or limit length
        clean_desc = description.replace("<br/>", "\n").replace("<br>", "\n").strip()
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

if __name__ == "__main__":
    sync_calendar()

import os
import json
import re
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from icalendar import Calendar

BRIGHTSPACE_BASE_URL = os.getenv("BRIGHTSPACE_BASE_URL", "https://brightspace.rug.nl").rstrip("/")
AUTH_STATE_PATH = "auth_state.json"

def extract_numbers(s):
    """
    Extracts all integers from a string.
    """
    return [int(x) for x in re.findall(r'\d+', s)]

def matches_group(summary, user_groups):
    """
    Checks if an event summary matches any of the user's groups.
    If the event is a group-specific class (e.g. gr.17, group 5, or mentorgroep 10-19),
    returns True if the user is in that group, or False if they are in a different group.
    If it's a general event (like a lecture/HC), returns True.
    """
    summary_lower = summary.lower()
    
    # If the summary doesn't mention "gr.", "groep", "group", or "werkgroep" / "wg",
    # it is assumed to be a general event (e.g., lecture/HC) that everyone attends.
    if not any(x in summary_lower for x in ["gr.", "group", "groep", "wg", "werkgroep"]):
        return True
        
    # 1. Check for ranges, e.g. "mentorgroep 01-09" or "groep 10-19"
    range_match = re.search(r'(?:mentorgroep|gr\.?|group|groep|wg|werkgroep)\s*(\d+)\s*-\s*(\d+)', summary_lower)
    if range_match:
        start_g = int(range_match.group(1))
        end_g = int(range_match.group(2))
        for ug in user_groups:
            ug_nums = extract_numbers(ug)
            if ug_nums and any(start_g <= n <= end_g for n in ug_nums):
                return True
        return False
        
    # 2. Check for specific group number/identifier, e.g. "gr.10" or "group 144" or "gr.9a"
    gr_match = re.search(r'(?:gr\.?|group|groep|wg|werkgroep)\s*([a-zA-Z0-9\.]+)', summary_lower)
    if gr_match:
        event_grp = gr_match.group(1).strip()
        # Clean leading zeros for pure numeric strings (e.g. '05' -> '5')
        event_grp_clean = event_grp.lstrip('0') if event_grp.isdigit() else event_grp
        
        for ug in user_groups:
            ug_lower = ug.lower()
            # Extract alphanumeric tokens from the user group name
            ug_tokens = re.findall(r'[a-zA-Z0-9\.]+', ug_lower)
            ug_tokens_clean = [t.lstrip('0') if t.isdigit() else t for t in ug_tokens]
            
            if event_grp_clean in ug_tokens_clean or event_grp in ug_tokens:
                return True
        return False
        
    return True

async def get_user_identifier(request_context):
    """
    Retrieves the user's Unique ID / Identifier from Brightspace.
    """
    try:
        response = await request_context.get("/d2l/api/lp/1.26/users/whoami")
        if response.status == 200:
            data = await response.json()
            return data.get("Identifier")
    except Exception as e:
        print(f"[Warning] Failed to fetch whoami identifier: {e}")
    return None

async def get_user_groups_for_course(request_context, course_id, user_id):
    """
    Fetches all group names the user belongs to for a specific Brightspace course offering.
    """
    url = f"/d2l/api/lp/1.26/{course_id}/groupcategories/"
    try:
        response = await request_context.get(url)
        if response.status != 200:
            return []
            
        categories = await response.json()
        user_group_names = []
        
        for cat in categories:
            cat_id = cat.get("GroupCategoryId")
            groups_url = f"/d2l/api/lp/1.26/{course_id}/groupcategories/{cat_id}/groups/"
            groups_res = await request_context.get(groups_url)
            if groups_res.status == 200:
                groups = await groups_res.json()
                for group in groups:
                    enrollments = group.get("Enrollments", [])
                    # Compare user ID
                    if user_id in enrollments or str(user_id) in enrollments or any(str(x) == str(user_id) for x in enrollments):
                        user_group_names.append(group.get("Name"))
                        
        return user_group_names
    except Exception as e:
        print(f"  [Warning] Failed to fetch groups for course ID {course_id}: {e}")
        return []

def get_academic_year():
    """
    Determines the current academic year string.
    Since we are in June 2026, the academic year for courses we sync is 2025-2026.
    """
    # For simplicity and robustness, we can dynamic-detect or default to 2025-2026
    # Let's inspect the current local time month.
    # Academic years run from September of year X to September of year X+1.
    now = datetime.now()
    if now.month >= 9:
        return f"{now.year}-{now.year + 1}"
    else:
        return f"{now.year - 1}-{now.year}"

async def scan_brightspace_groups(request_context, courses):
    """
    Scans Brightspace for the user's groups in each course.
    Returns a dict mapping course_code to list of user group names.
    """
    user_id = await get_user_identifier(request_context)
    if not user_id:
        print("[Warning] Could not retrieve user ID from Brightspace. Group filtering may be disabled.")
        return {}
        
    print(f"Brightspace User ID identified: {user_id}")
    course_groups = {}
    
    for c in courses:
        code = c.get("code", "")
        # Clean course code (e.g. "EBP023A05.2025-2026.1" -> "EBP023A05")
        clean_code = code.split('.')[0] if '.' in code else code
        print(f"Scanning groups for course: {c['name']} ({clean_code})...")
        
        groups = await get_user_groups_for_course(request_context, c["id"], user_id)
        if groups:
            course_groups[clean_code] = groups
            print(f"  -> User belongs to groups: {groups}")
        else:
            print("  -> No group enrollments found.")
            
    return course_groups

def get_te_course_code(all_te_courses, course_code):
    """
    Finds the exact course code object from the TimeEdit database for the course code.
    Returns the TimeEdit identifier string (e.g. "course-EBP023A05") or None.
    """
    # The rooster.rug.nl courses list holds items like:
    # {"code": "EBP023A05", "name": {"en": "", "nl": "Financial Accounting BDK"}}
    # So we search for exact code matches, or case insensitive match.
    for c in all_te_courses:
        code_te = c.get("code", "")
        if code_te.lower() == course_code.lower():
            return f"course-{code_te}"
            
    return None

def sync_personalized_schedule(course_groups, courses):
    """
    Downloads full calendars from rooster.rug.nl for all user courses,
    applies group-filtering locally, and collects the list of excluded series.
    Returns (filtered_events, web_schedule_url, direct_ical_url).
    """
    year = get_academic_year()
    print(f"Using academic year for Rooster RUG: {year}")
    
    # 1. Fetch complete TimeEdit course list
    catalog_url = f"https://rooster.rug.nl/api/course/{year}"
    try:
        req = urllib.request.Request(catalog_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as res:
            all_te_courses = json.loads(res.read().decode("utf-8"))
    except Exception as e:
        print(f"[ERROR] Failed to fetch course list from Rooster RUG: {e}")
        return [], "", ""
        
    # 2. Map course codes to TimeEdit codes
    te_codes = []
    mapped_courses = {} # clean_code -> course details
    
    for c in courses:
        raw_code = c.get("code", "")
        clean_code = raw_code.split('.')[0] if '.' in raw_code else raw_code
        te_code = get_te_course_code(all_te_courses, clean_code)
        if te_code:
            te_codes.append(te_code)
            mapped_courses[clean_code] = te_code
            
    if not te_codes:
        print("[ERROR] No course mappings found on Rooster RUG timetable.")
        return [], "", ""
        
    print(f"Mapped {len(te_codes)} course(s) to TimeEdit codes: {te_codes}")
    
    # 3. Fetch calendar events for each course individually
    events_raw = []
    series_map = {}
    
    for c in courses:
        raw_code = c.get("code", "")
        clean_code = raw_code.split('.')[0] if '.' in raw_code else raw_code
        te_code = mapped_courses.get(clean_code)
        if not te_code:
            continue
            
        course_ical_url = f"https://rooster.rug.nl/api/ical2/en/current/{te_code}"
        print(f"Downloading schedule for {clean_code} from {course_ical_url}...")
        try:
            ical_req = urllib.request.Request(course_ical_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(ical_req, timeout=15) as ical_res:
                ics_data = ical_res.read()
        except Exception as e:
            print(f"[Warning] Failed to download schedule for {clean_code}: {e}")
            continue
            
        gcal = Calendar.from_ical(ics_data)
        for component in gcal.walk():
            if component.name == "VEVENT":
                summary = str(component.get("summary", "Untitled Event"))
                description = str(component.get("description", ""))
                location = str(component.get("location", ""))
                uid = str(component.get("uid", ""))
                dtstart = component.get("dtstart").dt if component.get("dtstart") else None
                dtend = component.get("dtend").dt if component.get("dtend") else None
                
                series_id = uid.split("/")[0] if "/" in uid else ""
                
                events_raw.append({
                    "summary": summary,
                    "description": description,
                    "location": location,
                    "uid": uid,
                    "series_id": series_id,
                    "course_code": clean_code,
                    "dtstart": dtstart,
                    "dtend": dtend
                })
                
                if not series_id:
                    continue
                    
                user_groups = course_groups.get(clean_code, [])
                match = matches_group(summary, user_groups)
                
                if clean_code not in series_map:
                    series_map[clean_code] = {}
                    
                if series_id not in series_map[clean_code]:
                    series_map[clean_code][series_id] = []
                series_map[clean_code][series_id].append(match)
                
    # Determine the actual list of excluded series IDs
    excludes = []
    for course_code, series_dict in series_map.items():
        for series_id, match_list in series_dict.items():
            # If all events in this series are non-matches for the user's group, exclude it!
            if not any(match_list):
                excludes.append(series_id)
                
    print(f"Identified {len(excludes)} series ID(s) to exclude: {excludes}")
    
    # 5. Filter the events list locally
    filtered_events = []
    excludes_set = set(excludes)
    
    for ev in events_raw:
        if ev["series_id"] in excludes_set:
            continue
        filtered_events.append(ev)
        
    print(f"Filtered {len(events_raw)} events down to {len(filtered_events)} personalized events.")
    
    # 6. Generate the URLs
    # Format excluded series for the query parameter
    # e.g., excludes are `#SPLUSC7D11A` -> URL-encoded as `%2523SPLUSC7D11A` and joined by `%2526`
    # Wait, the Rooster UI url is:
    # https://rooster.rug.nl/#/en/current/schedule/{joined_codes}/dataView=ical&excludeSeries={joined_excludes}
    # where codes are joined by `&` and excludes are encoded and joined by `&` (double URL encoded)
    
    joined_te_codes = "&".join(te_codes)
    joined_excludes = "&".join(excludes)
    # Double encode for the hash route
    double_encoded_excludes = urllib.parse.quote(joined_excludes).replace("&", "%26")
    
    web_schedule_url = f"https://rooster.rug.nl/#/en/current/schedule/{joined_te_codes}/dataView=ical&excludeSeries={double_encoded_excludes}"
    
    # Direct iCal feed URL from Rooster RUG:
    # https://rooster.rug.nl/api/ical2/en/current/{joined_codes}?excludes={excludes}
    direct_ical_url = f"https://rooster.rug.nl/api/ical2/en/current/{joined_te_codes}"
    if excludes:
        # The excludes parameter is URL encoded
        direct_ical_url += f"?excludes={urllib.parse.quote(joined_excludes)}"
        
    return filtered_events, web_schedule_url, direct_ical_url

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
    If the event is a group-specific class (e.g. gr.17, group 5, tutorial gr01, tut. training gr.01a),
    returns True if the user is in that group, or False if they are in a different group.
    If it's a general event (like a lecture/HC/Q&A/exam), returns True.
    """
    summary_lower = summary.lower()
    
    # Check if the summary mentions a tutorial or group indicator
    is_group_event = any(x in summary_lower for x in ["gr.", "group", "groep", "wg", "werkgroep", "tutorial", "tut."]) or bool(re.search(r'\bgr\d+', summary_lower))
    if not is_group_event:
        return True
        
    # 1. Check for ranges, e.g. "mentorgroep 01-09" or "groep 10-19"
    range_match = re.search(r'(?:mentorgroep|gr\.?|group|groep|wg|werkgroep|tutorial|tut\.?)\s*(\d+)\s*-\s*(\d+)', summary_lower)
    if range_match:
        start_g = int(range_match.group(1))
        end_g = int(range_match.group(2))
        for ug in user_groups:
            ug_nums = extract_numbers(ug)
            if ug_nums and any(start_g <= n <= end_g for n in ug_nums):
                return True
        return False
        
    # 2. Check for specific group number/identifier, e.g. "gr.10", "tutorial gr01", "tut. training gr.01a"
    gr_match = re.search(r'(?:gr\.?|group|groep|wg|werkgroep)\s*([a-zA-Z0-9\.\+]+)', summary_lower)
    if not gr_match:
        gr_match = re.search(r'(?:tutorial|tut\.?)\s*(?:training\s*)?(?:gr\.?\s*)?([a-zA-Z0-9\.\+]+)', summary_lower)
        
    if gr_match:
        event_grp = gr_match.group(1).strip()
        # Clean leading zeros for pure numeric strings (e.g. '05' -> '5')
        event_grp_clean = event_grp.lstrip('0') if event_grp.isdigit() else event_grp
        event_num_match = re.search(r'(\d+)', event_grp)
        event_base_num = event_num_match.group(1).lstrip('0') if event_num_match else None
        
        for ug in user_groups:
            ug_lower = ug.lower()
            # If ug contains a dot like "3.8", the primary tutorial class group is the prefix before the dot
            ug_base = ug_lower.split('.')[0].strip() if '.' in ug_lower else ug_lower
            ug_tokens = re.findall(r'[a-zA-Z0-9\.]+', ug_lower)
            ug_tokens_clean = [t.lstrip('0') if t.isdigit() else t for t in ug_tokens]
            ug_nums = [str(n) for n in extract_numbers(ug_base)]
            
            if (event_grp_clean in ug_tokens_clean or 
                event_grp in ug_tokens or
                (event_base_num and event_base_num in ug_nums)):
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
    Determines the active academic year string for Rooster RUG.
    Checks ROOSTER_ACADEMIC_YEAR env var first, then checks app-config.js,
    then defaults to current academic year.
    """
    env_year = os.getenv("ROOSTER_ACADEMIC_YEAR")
    if env_year:
        return env_year
        
    try:
        cfg_url = "https://rooster.rug.nl/app-config.js"
        req = urllib.request.Request(cfg_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as res:
            cfg_text = res.read().decode("utf-8")
            match = re.search(r'"currentYear"\s*:\s*"([^"]+)"', cfg_text)
            if match:
                return match.group(1)
    except Exception:
        pass
        
    now = datetime.now()
    return f"{now.year}-{now.year + 1}" if now.month >= 9 else f"{now.year - 1}-{now.year}"


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
    for c in all_te_courses:
        code_te = c.get("code", "")
        if code_te.lower() == course_code.lower():
            return f"course-{code_te}"
            
    return None

def fetch_maat_schedule(year, courses, course_groups):
    """
    Fetches the schedule from the new RUG MAAT API for 2026-2027 and newer.
    Applies group filtering for tutorials and returns standard event dictionaries.
    """
    try:
        from zoneinfo import ZoneInfo
        tz_ams = ZoneInfo("Europe/Amsterdam")
    except ImportError:
        tz_ams = timezone.utc

    # 1. Search course offerings to find exact MAAT codes
    course_offering_codes = []
    course_name_map = {}
    for c in courses:
        clean_code = c.get("code", "").split('.')[0]
        search_url = f"https://rooster.rug.nl/maat/api/{year}/course-offerings/search"
        payload = json.dumps({"searchText": clean_code, "academicYear": year, "limit": 20}).encode("utf-8")
        req = urllib.request.Request(search_url, data=payload, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=15) as res:
                data = json.loads(res.read().decode("utf-8"))
                for res_item in data.get("results", []):
                    if res_item.get("courseCode") == clean_code:
                        co_code = res_item.get("code")
                        course_offering_codes.append(co_code)
                        course_name_map[clean_code] = res_item.get("displayNameEn") or c.get("name")
                        break
        except Exception as e:
            print(f"[Warning] Failed to search MAAT course offering for {clean_code}: {e}")
            
    if not course_offering_codes:
        print("[ERROR] No course offerings found in MAAT.")
        return [], "", ""
        
    print(f"Discovered MAAT course offering codes: {course_offering_codes}")
    
    # 2. Generate schedule
    gen_url = f"https://rooster.rug.nl/maat/api/{year}/schedule/generate"
    gen_payload = json.dumps({"objects": [], "courseOfferingCodes": course_offering_codes}).encode("utf-8")
    gen_req = urllib.request.Request(gen_url, data=gen_payload, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(gen_req, timeout=20) as res:
            gen_data = json.loads(res.read().decode("utf-8"))
            raw_results = gen_data.get("results", [])
    except Exception as e:
        print(f"[ERROR] Failed to generate MAAT schedule: {e}")
        return [], "", ""
        
    print(f"Retrieved {len(raw_results)} total events from MAAT schedule.")
    
    # 3. Filter and parse events
    filtered_events = []
    for ev in raw_results:
        cos = ev.get("courseOfferings", [])
        if not cos:
            continue
        c_item = cos[0]
        clean_code = c_item.get("courseCode", "")
        c_name = course_name_map.get(clean_code, c_item.get("displayNameEn", ""))
        
        desc = ev.get("description", "").strip()
        act = ev.get("activityType", {}).get("displayNameEn", "").strip()
        
        # Check if tutorial/group event
        is_tut = "tutorial" in act.lower() or "tutorial" in desc.lower() or "werkcollege" in desc.lower() or "tut." in desc.lower()
        user_groups = course_groups.get(clean_code, [])
        if is_tut and user_groups:
            # Check group match against description e.g. "Tutorial gr.03"
            if not matches_group(desc, user_groups):
                continue
                
        # Parse datetime into local timezone (Europe/Amsterdam)
        st = ev.get("start")
        et = ev.get("end") or st
        dtstart = datetime(st[0], st[1], st[2], st[3], st[4], tzinfo=tz_ams)
        dtend = datetime(et[0], et[1], et[2], et[3], et[4], tzinfo=tz_ams)
        
        rooms = ", ".join([r.get("code", "") for r in ev.get("rooms", []) if r.get("code")])
        
        filtered_events.append({
            "summary": f"[{clean_code}] {c_name} {desc}",
            "description": f"{act}: {desc}",
            "location": rooms,
            "uid": f"maat-{ev.get('id')}@rug.nl",
            "course_code": clean_code,
            "dtstart": dtstart,
            "dtend": dtend,
            "categories": ["Rooster", clean_code]
        })
        
    filtered_events.sort(key=lambda x: x["dtstart"])
    print(f"Filtered down to {len(filtered_events)} personalized {year} events via MAAT.")
    
    # 4. Save schedule in MAAT to obtain direct iCal subscription feed URL
    direct_ical_url = ""
    try:
        save_url = f"https://rooster.rug.nl/maat/api/{year}/schedule"
        save_payload = json.dumps({"objects": [], "courseOfferingCodes": course_offering_codes}).encode("utf-8")
        save_req = urllib.request.Request(save_url, data=save_payload, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(save_req, timeout=10) as s_res:
            sched_uuid = json.loads(s_res.read().decode("utf-8"))
            direct_ical_url = f"https://rooster.rug.nl/maat/api/{year}/schedule/{sched_uuid}"
    except Exception as e:
        print(f"[Warning] Failed to generate MAAT iCal link: {e}")
        
    joined_co = ",".join(course_offering_codes)
    web_schedule_url = f"https://rooster.rug.nl/{year}?courseOffering={joined_co}"
    return filtered_events, web_schedule_url, direct_ical_url

def sync_personalized_schedule(course_groups, courses):
    """
    Downloads full calendars from rooster.rug.nl for all user courses,
    applies group-filtering locally, and returns (filtered_events, web_schedule_url, direct_ical_url).
    Automatically routes to MAAT API for 2026-2027 and newer, or TimeEdit for older years.
    """
    year = get_academic_year()
    print(f"Using academic year for Rooster RUG: {year}")
    
    # Route to MAAT API for 2026-2027+
    if year >= "2026-2027":
        print("Using RUG MAAT timetable system for 2026-2027+...")
        events, web_url, direct_url = fetch_maat_schedule(year, courses, course_groups)
        if events:
            return events, web_url, direct_url
        print("[Warning] MAAT returned no events. Falling back to TimeEdit...")
    
    # Legacy TimeEdit flow
    catalog_url = f"https://rooster.rug.nl/api/course/{year}"
    try:
        req = urllib.request.Request(catalog_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as res:
            all_te_courses = json.loads(res.read().decode("utf-8"))
    except Exception as e:
        print(f"[ERROR] Failed to fetch course list from Rooster RUG: {e}")
        return [], "", ""
        
    # Map course codes to TimeEdit codes
    te_codes = []
    mapped_courses = {}
    
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
    
    # Fetch calendar events for each course individually
    events_raw = []
    series_map = {}
    
    for c in courses:
        raw_code = c.get("code", "")
        clean_code = raw_code.split('.')[0] if '.' in raw_code else raw_code
        te_code = mapped_courses.get(clean_code)
        if not te_code:
            continue
            
        course_ical_url = f"https://rooster.rug.nl/api/ical2/en/{year}/{te_code}"
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
            if not any(match_list):
                excludes.append(series_id)
                
    print(f"Identified {len(excludes)} series ID(s) to exclude: {excludes}")
    
    filtered_events = []
    excludes_set = set(excludes)
    
    for ev in events_raw:
        if ev["series_id"] in excludes_set:
            continue
        user_groups = course_groups.get(ev["course_code"], [])
        if not matches_group(ev["summary"], user_groups):
            continue
        filtered_events.append(ev)
        
    print(f"Filtered {len(events_raw)} events down to {len(filtered_events)} personalized events.")
    
    joined_te_codes = "&".join(te_codes)
    joined_excludes = "&".join(excludes)
    double_encoded_excludes = urllib.parse.quote(joined_excludes).replace("&", "%26")
    
    web_schedule_url = f"https://rooster.rug.nl/#/en/{year}/schedule/{joined_te_codes}/dataView=ical&excludeSeries={double_encoded_excludes}"
    
    direct_ical_url = f"https://rooster.rug.nl/api/ical2/en/{year}/{joined_te_codes}"
    if excludes:
        direct_ical_url += f"?excludes={urllib.parse.quote(joined_excludes)}"
        
    return filtered_events, web_schedule_url, direct_ical_url


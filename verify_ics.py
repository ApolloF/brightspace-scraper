from icalendar import Calendar
from collections import defaultdict
import datetime

with open('downloads/personalized_schedule.ics', 'rb') as f:
    cal = Calendar.from_ical(f.read())

events = list(cal.walk('VEVENT'))
print(f"Total VEVENTs: {len(events)}")

by_course = defaultdict(list)
by_type = defaultdict(int)

for e in sorted(events, key=lambda x: str(x.get('dtstart').dt)):
    start = e.get('dtstart').dt
    end = e.get('dtend').dt
    summary = str(e.get('summary'))
    loc = str(e.get('location'))
    desc = str(e.get('description'))
    
    course = "Other"
    if "Management" in summary or "MOT" in summary or "EBB054A05" in desc:
        course = "Management- en Organisatietheorie (EBB054A05)"
    elif "Kwalitatieve" in summary or "KOM" in summary or "EBB050A05" in desc:
        course = "Kwalitatieve onderzoeksmethoden (EBB050A05)"
    elif "Financial Management" in summary or "FM" in summary or "EBB046A05" in desc:
        course = "Financial Management BDK (EBB046A05)"
        
    by_course[course].append((start, end, summary, loc, desc))
    
    if "Tutorial" in summary or "Werkcollege" in summary:
        by_type["Tutorial/Werkcollege"] += 1
    elif "Lecture" in summary or "Hoorcollege" in summary:
        by_type["Lecture/Hoorcollege"] += 1
    elif "Exam" in summary or "Tentamen" in summary or "Midterm" in summary:
        by_type["Exam/Midterm"] += 1
    else:
        by_type["Other"] += 1

print("\n=== EVENT BREAKDOWN BY TYPE ===")
for k, v in by_type.items():
    print(f"  {k}: {v}")

print("\n=== DETAILED EVENT LIST PER COURSE ===")
for course, evs in by_course.items():
    print(f"\n--- {course} ({len(evs)} events) ---")
    for s, e, summ, loc, desc in evs:
        print(f"  {s} to {e.strftime('%H:%M')} | {summ} | Loc: {loc}")

# Check for time overlaps/conflicts
print("\n=== CHECKING FOR TIME CONFLICTS ===")
conflicts = []
sorted_evs = sorted(events, key=lambda x: x.get('dtstart').dt)
for i in range(len(sorted_evs)):
    for j in range(i + 1, len(sorted_evs)):
        s1 = sorted_evs[i].get('dtstart').dt
        e1 = sorted_evs[i].get('dtend').dt
        s2 = sorted_evs[j].get('dtstart').dt
        e2 = sorted_evs[j].get('dtend').dt
        if s2 < e1:
            conflicts.append((sorted_evs[i], sorted_evs[j]))

if conflicts:
    print(f"[WARNING] Found {len(conflicts)} conflict(s):")
    for c1, c2 in conflicts:
        print(f"  Conflict between '{c1.get('summary')}' ({c1.get('dtstart').dt}) and '{c2.get('summary')}' ({c2.get('dtstart').dt})")
else:
    print("Zero scheduling conflicts found! Schedule is completely collision-free.")

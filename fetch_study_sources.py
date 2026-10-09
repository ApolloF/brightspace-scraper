import asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright
from brightspace_sync.auth import BRIGHTSPACE_BASE_URL,AUTH_STATE_PATH
from brightspace_sync.calendar import fetch_active_courses
async def main():
 async with async_playwright() as p:
  ctx=await p.request.new_context(base_url=BRIGHTSPACE_BASE_URL,storage_state=AUTH_STATE_PATH)
  courses=[c for c in await fetch_active_courses(ctx) if c['code'].split('.')[0] in ['EBB050A05','EBB046A05','EBB054A05']]
  out=[]
  for c in courses:
   entry={'course':c,'sources':{}}
   for label,path in [('calendar','calendar/events/myEvents/?startDateTime=2026-09-01T00:00:00.000Z&endDateTime=2026-11-01T00:00:00.000Z'),('assignments','dropbox/folders/'),('quizzes','quizzes/')]:
    r=await ctx.get(f"/d2l/api/le/1.26/{c['id']}/{path}")
    entry['sources'][label]={'status':r.status,'data':await r.json() if r.status==200 else None}
    print(c['name'],label,r.status)
   out.append(entry)
  Path('downloads/course-deadlines.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
  await ctx.dispose()
asyncio.run(main())


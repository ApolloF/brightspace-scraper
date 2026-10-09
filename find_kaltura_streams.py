"""
Inspect and capture video stream URLs from the 4 Kaltura/video topics:
- 5977053 (Week 5 - Module 5.1)
- 5977054 (Week 5 - Module 5.2)
- 5981787 (Week 6 - Module 6.1)
- 5981789 (Week 6 - Module 6.2)
"""

import asyncio
import re
from playwright.async_api import async_playwright

TOPICS = [
    ("5977053", "Module 5.1"),
    ("5977054", "Module 5.2"),
    ("5981787", "Module 6.1"),
    ("5981789", "Module 6.2"),
]

async def inspect_topic(context, tid, label):
    page = await context.new_page()
    captured = []
    
    def on_res(r):
        u = r.url
        ct = r.headers.get("content-type", "").lower()
        if any(k in u.lower() for k in [".mp4", ".m3u8", "playmanifest", "manifest", "/flavor/", "serveflavor"]) or "video/" in ct or "mpegurl" in ct:
            if u not in captured:
                captured.append(u)
                print(f"  [STREAM SNIFFER] {u[:120]}")

    page.on("response", on_res)

    url = f"https://brightspace.rug.nl/d2l/le/lessons/523940/topics/{tid}"
    print(f"\nNavigating to {label} (Topic {tid})...")
    await page.goto(url, wait_until="domcontentloaded", timeout=45000)
    await page.wait_for_timeout(6000)

    # Find entryId from frame URLs
    entry_id = None
    for f in page.frames:
        m = re.search(r'entryid/([0-9a-zA-Z_]+)', f.url, re.IGNORECASE)
        if m:
            entry_id = m.group(1)
            print(f"  [FOUND ENTRY ID in frame URL] {entry_id} (Frame: {f.url[:80]})")

    # If not triggered, click buttons inside all frames
    if not captured:
        print("  Clicking play elements in frames...")
        for f in page.frames:
            try:
                # also check for entryId inside HTML
                content = await f.content()
                m_html = re.search(r'["\']entry_id["\']\s*:\s*["\']([0-9a-zA-Z_]+)["\']', content)
                if not entry_id and m_html:
                    entry_id = m_html.group(1)
                    print(f"  [FOUND ENTRY ID in frame HTML] {entry_id}")

                btns = await f.query_selector_all("button, .play, .play-icon, video, .largePlayBtn, [title*='Play' i]")
                for b in btns:
                    try:
                        await b.click(timeout=1000)
                        await page.wait_for_timeout(1000)
                    except:
                        pass
            except:
                pass
        await page.wait_for_timeout(5000)

    print(f"  Results for {label}: EntryID={entry_id}, Captured streams={len(captured)}")
    await page.close()
    return entry_id, captured

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch(headless=True)
        ctx = await b.new_context(storage_state='auth_state.json')
        for tid, label in TOPICS:
            await inspect_topic(ctx, tid, label)
        await b.close()

if __name__ == "__main__":
    asyncio.run(main())

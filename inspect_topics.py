"""
Inspect the 6 Brightspace topics to identify titles, content types (video vs PDF/slides), and download URLs.
"""

import asyncio
from playwright.async_api import async_playwright

TOPICS = [
    ("Week 5", "5977053"),
    ("Week 5", "5977054"),
    ("Week 5", "5977056"),
    ("Week 6", "5981791"),
    ("Week 6", "5981787"),
    ("Week 6", "5981789"),
]

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch(headless=True)
        ctx = await b.new_context(storage_state='auth_state.json')
        
        for week, tid in TOPICS:
            page = await ctx.new_page()
            media = []
            def on_res(r):
                u = r.url
                ct = r.headers.get("content-type", "").lower()
                if any(ext in u.lower() for ext in [".mp4", ".m3u8", ".pdf", "playmanifest", "viewfile", "download"]) or "video/" in ct or "pdf" in ct:
                    if u not in media:
                        media.append((ct, u))
            page.on("response", on_res)

            url = f"https://brightspace.rug.nl/d2l/le/lessons/523940/topics/{tid}"
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(4000)
                title = await page.title()
                h1 = await page.evaluate("() => document.querySelector('h1, .d2l-page-title')?.innerText || ''")
                
                # Check for iframes and links
                doc_links = await page.evaluate('''() => {
                    const res = [];
                    document.querySelectorAll('a, iframe, embed, object, d2l-labs-media-player').forEach(el => {
                        const s = el.src || el.href || '';
                        if (s) res.push(s);
                    });
                    return res;
                }''')

                print(f"[{week}] Topic {tid}:")
                print(f"  Title: {title.strip()} | H1: {h1.strip()}")
                print(f"  Media sniffed ({len(media)}):")
                for ct, u in media[:5]:
                    print(f"    - {ct}: {u[:110]}")
                print(f"  Document/Player links ({len(doc_links)}):")
                for l in doc_links[:5]:
                    print(f"    - {l[:110]}")

            except Exception as e:
                print(f"[{week}] Topic {tid} error: {e}")
            finally:
                await page.close()

        await b.close()

if __name__ == "__main__":
    asyncio.run(main())

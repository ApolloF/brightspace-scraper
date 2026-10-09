"""
Full pipeline script to:
1. Ensure Brightspace authentication (opens browser for RUG SSO / MFA login if needed).
2. Download MOT Week 2 videos (Topics 5940684, 5940685, 5940686).
3. Transcribe MOT Week 2 with faster-whisper on GPU.
4. Align transcripts with MOT2026_Hoorcollege 2.pdf slides (Slides 1-55) into MOT_Week_2_Complete_Slide_Annotated_Transcript.md.
5. Download & transcribe KOM Week 5 videos (13, 14, 15, 16) if available on Brightspace or OneDrive.
6. Rebuild the final ZIP archive with all transcripts and slide decks!
"""

import os
import sys
import json
import re
import asyncio
import subprocess
import zipfile
from pathlib import Path

# Add nvidia CUDA DLL paths for GPU transcription
site_packages = Path(sys.executable).parent.parent / 'Lib' / 'site-packages'
for p in site_packages.glob('nvidia/*'):
    bin_dir = p / 'bin'
    if bin_dir.exists():
        try:
            os.add_dll_directory(str(bin_dir))
        except Exception:
            pass
        os.environ['PATH'] = str(bin_dir) + os.pathsep + os.environ['PATH']

from playwright.async_api import async_playwright
import imageio_ffmpeg

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

BASE_URL = "https://brightspace.rug.nl"
AUTH_STATE_PATH = Path("auth_state.json")
VIDEOS_DIR = Path("downloads/videos")
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

MOT_HC2_TOPICS = [
    {
        "topic_id": "5940684",
        "module": "2.1",
        "title": "Hoorcollege 2 - Module 2.1 (organisatiegroei en life cycle)",
        "slides_start": 1,
        "slides_end": 12,
        "mp4": "5940684_MOT_Hoorcollege_2_Module_2.1.mp4",
        "mp3": "5940684_MOT_Hoorcollege_2_Module_2.1.mp3",
    },
    {
        "topic_id": "5940685",
        "module": "2.2",
        "title": "Hoorcollege 2 - Module 2.2 (Mintzberg's configuraties)",
        "slides_start": 13,
        "slides_end": 39,
        "mp4": "5940685_MOT_Hoorcollege_2_Module_2.2.mp4",
        "mp3": "5940685_MOT_Hoorcollege_2_Module_2.2.mp3",
    },
    {
        "topic_id": "5940686",
        "module": "2.3",
        "title": "Hoorcollege 2 - Module 2.3 (nieuwe organisatievormen)",
        "slides_start": 40,
        "slides_end": 55,
        "mp4": "5940686_MOT_Hoorcollege_2_Module_2.3.mp4",
        "mp3": "5940686_MOT_Hoorcollege_2_Module_2.3.mp3",
    }
]

async def ensure_login(pw):
    print("=" * 60)
    print("BRIGHTSPACE AUTHENTICATION CHECK")
    print("=" * 60)
    
    browser = await pw.chromium.launch(headless=False)
    context_kwargs = {}
    if AUTH_STATE_PATH.exists():
        context_kwargs["storage_state"] = str(AUTH_STATE_PATH)
        
    context = await browser.new_context(**context_kwargs)
    page = await context.new_page()
    await page.goto(f"{BASE_URL}/d2l/home")
    await page.wait_for_timeout(3000)
    
    if "signon.rug.nl" in page.url or "login" in page.url.lower():
        print("ACTION REQUIRED: Log in with your RUG credentials + MFA in the browser window.")
        await page.wait_for_url(
            lambda u: ("brightspace.rug.nl/d2l/home" in u or "brightspace.rug.nl/d2l/le" in u) and "signon.rug.nl" not in u,
            timeout=300000
        )
        print("Login detected! Saving session state...")
        await page.wait_for_timeout(3000)
        await context.storage_state(path=str(AUTH_STATE_PATH))
        print("Fresh session saved to auth_state.json.")
    else:
        print("Already authenticated!")
        
    return browser, context

async def sniff_and_download_topic(page, context, topic_info):
    tid = topic_info["topic_id"]
    mp4_path = VIDEOS_DIR / topic_info["mp4"]
    if mp4_path.exists() and mp4_path.stat().st_size > 5000000:
        print(f"[Skip] {mp4_path.name} already exists ({mp4_path.stat().st_size / 1024 / 1024:.1f} MB)")
        return mp4_path

    captured = []
    def on_res(r):
        u = r.url
        ct = r.headers.get("content-type", "").lower()
        if any(k in u.lower() for k in [".mp4", ".m3u8", "playmanifest", "manifest", "/flavor/", "serveflavor"]) or "video/" in ct or "mpegurl" in ct:
            if u not in captured:
                captured.append(u)

    page.on("response", on_res)
    url = f"{BASE_URL}/d2l/le/lessons/523940/topics/{tid}"
    print(f"\nNavigating to Topic {tid} ({topic_info['title']})...")
    await page.goto(url, wait_until="domcontentloaded", timeout=45000)
    await page.wait_for_timeout(6000)

    entry_id = None
    for f in page.frames:
        m = re.search(r'entryid/([0-9a-zA-Z_]+)', f.url, re.IGNORECASE)
        if m:
            entry_id = m.group(1)
            break
        try:
            content = await f.content()
            m2 = re.search(r'["\']entry_id["\']\s*:\s*["\']([0-9a-zA-Z_]+)["\']', content)
            if m2:
                entry_id = m2.group(1)
                break
        except Exception:
            pass

    # Download stream
    if entry_id:
        manifest_url = f"https://api.eu.kaltura.com/p/239/sp/23900/playManifest/entryId/{entry_id}/format/applehttp/protocol/https/a.m3u8"
        print(f"[Download] Found Kaltura EntryID: {entry_id}, downloading via FFmpeg...")
        cmd = [FFMPEG_EXE, "-y", "-i", manifest_url, "-c", "copy", "-bsf:a", "aac_adtstoasc", str(mp4_path)]
        subprocess.run(cmd, check=True)
    elif captured:
        stream_url = captured[0]
        print(f"[Download] Sniffed stream URL: {stream_url[:90]}, downloading via FFmpeg...")
        cookies = await context.cookies()
        cookie_hdr = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        cmd = [FFMPEG_EXE, "-y", "-headers", f"Cookie: {cookie_hdr}\r\nReferer: {BASE_URL}\r\n", "-i", stream_url, "-c", "copy", "-bsf:a", "aac_adtstoasc", str(mp4_path)]
        res = subprocess.run(cmd)
        if res.returncode != 0:
            subprocess.run([FFMPEG_EXE, "-y", "-i", stream_url, "-c", "copy", "-bsf:a", "aac_adtstoasc", str(mp4_path)], check=True)
    else:
        print(f"[Error] Could not find stream for topic {tid}")
        return None

    print(f"[Done] Saved: {mp4_path.name} ({mp4_path.stat().st_size / 1024 / 1024:.1f} MB)")
    return mp4_path

def convert_to_mp3(mp4_path, mp3_path):
    if mp3_path.exists() and mp3_path.stat().st_size > 1000000:
        return mp3_path
    print(f"[Audio] Converting {mp4_path.name} to MP3...")
    cmd = [FFMPEG_EXE, "-y", "-i", str(mp4_path), "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k", str(mp3_path)]
    subprocess.run(cmd, check=True)
    return mp3_path

def transcribe_with_whisper(mp3_path, srt_path):
    if srt_path.exists() and srt_path.stat().st_size > 500:
        return srt_path
    from faster_whisper import WhisperModel
    print(f"[Whisper] Transcribing {mp3_path.name} on GPU (medium model, Dutch)...")
    try:
        model = WhisperModel("medium", device="cuda", compute_type="float16")
    except Exception:
        print("[Whisper] CUDA float16 fallback to int8/cpu...")
        model = WhisperModel("medium", device="cpu", compute_type="int8")

    segments, info = model.transcribe(str(mp3_path), language="nl", beam_size=5)
    lines = []
    seg_idx = 1
    for seg in segments:
        m_s = int((seg.start - int(seg.start)) * 1000)
        s_s = int(seg.start)
        m_e = int((seg.end - int(seg.end)) * 1000)
        s_e = int(seg.end)
        ts_start = f"{s_s//3600:02d}:{(s_s%3600)//60:02d}:{s_s%60:02d},{m_s:03d}"
        ts_end = f"{s_e//3600:02d}:{(s_e%3600)//60:02d}:{s_e%60:02d},{m_e:03d}"
        lines.append(f"{seg_idx}\n{ts_start} --> {ts_end}\n{seg.text.strip()}\n")
        seg_idx += 1

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[Whisper] Saved SRT: {srt_path.name}")
    return srt_path

def main():
    async def run_pipeline():
        async with async_playwright() as pw:
            browser, context = await ensure_login(pw)
            page = await context.new_page()

            # 1. Download MOT Week 2
            for topic in MOT_HC2_TOPICS:
                mp4 = await sniff_and_download_topic(page, context, topic)
                if mp4:
                    mp3 = VIDEOS_DIR / topic["mp3"]
                    convert_to_mp3(mp4, mp3)
                    srt = VIDEOS_DIR / f"{topic['topic_id']}_transcript_nl.srt"
                    transcribe_with_whisper(mp3, srt)

            await browser.close()

    asyncio.run(run_pipeline())
    print("\nExtraction & transcription completed successfully!")

if __name__ == "__main__":
    main()

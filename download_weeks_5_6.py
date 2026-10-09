"""
Download, convert to MP3, and transcribe in Dutch using GPU:
Week 5:
  - https://brightspace.rug.nl/d2l/le/lessons/523940/topics/5977053
  - https://brightspace.rug.nl/d2l/le/lessons/523940/topics/5977054
  - https://brightspace.rug.nl/d2l/le/lessons/523940/topics/5977056
Week 6:
  - https://brightspace.rug.nl/d2l/le/lessons/523940/topics/5981791
  - https://brightspace.rug.nl/d2l/le/lessons/523940/topics/5981787
  - https://brightspace.rug.nl/d2l/le/lessons/523940/topics/5981789
"""

import os
import sys
import json
import re
import time
import asyncio
import subprocess
import urllib.parse
from pathlib import Path

# Add nvidia CUDA DLL directories for faster-whisper GPU
site_packages = Path(sys.executable).parent.parent / 'Lib' / 'site-packages'
for p in site_packages.glob('nvidia/*'):
    bin_dir = p / 'bin'
    if bin_dir.exists():
        try:
            os.add_dll_directory(str(bin_dir))
        except Exception:
            pass
        os.environ['PATH'] = str(bin_dir) + os.pathsep + os.environ['PATH']

from faster_whisper import WhisperModel
from playwright.async_api import async_playwright
import imageio_ffmpeg

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

BASE_URL = "https://brightspace.rug.nl"
AUTH_STATE_PATH = "auth_state.json"
OUTPUT_DIR = Path("downloads/videos")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TOPICS = [
    # Week 5
    {
        "course_id": "523940",
        "topic_id": "5977053",
        "week": "Week 5",
        "default_name": "MOT Hoorcollege 5 - Topic 5977053",
        "url": f"{BASE_URL}/d2l/le/lessons/523940/topics/5977053"
    },
    {
        "course_id": "523940",
        "topic_id": "5977054",
        "week": "Week 5",
        "default_name": "MOT Hoorcollege 5 - Topic 5977054",
        "url": f"{BASE_URL}/d2l/le/lessons/523940/topics/5977054"
    },
    {
        "course_id": "523940",
        "topic_id": "5977056",
        "week": "Week 5",
        "default_name": "MOT Hoorcollege 5 - Topic 5977056",
        "url": f"{BASE_URL}/d2l/le/lessons/523940/topics/5977056"
    },
    # Week 6
    {
        "course_id": "523940",
        "topic_id": "5981791",
        "week": "Week 6",
        "default_name": "MOT Hoorcollege 6 - Topic 5981791",
        "url": f"{BASE_URL}/d2l/le/lessons/523940/topics/5981791"
    },
    {
        "course_id": "523940",
        "topic_id": "5981787",
        "week": "Week 6",
        "default_name": "MOT Hoorcollege 6 - Topic 5981787",
        "url": f"{BASE_URL}/d2l/le/lessons/523940/topics/5981787"
    },
    {
        "course_id": "523940",
        "topic_id": "5981789",
        "week": "Week 6",
        "default_name": "MOT Hoorcollege 6 - Topic 5981789",
        "url": f"{BASE_URL}/d2l/le/lessons/523940/topics/5981789"
    }
]

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()


def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\n\r\t]', '_', name)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned[:120] if cleaned else "video"


def format_timestamp_srt(seconds: float) -> str:
    millis = int((seconds - int(seconds)) * 1000)
    total_seconds = int(seconds)
    secs = total_seconds % 60
    mins = (total_seconds // 60) % 60
    hours = total_seconds // 3600
    return f"{hours:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def convert_video_to_mp3(video_path: Path, mp3_path: Path):
    if mp3_path.exists() and mp3_path.stat().st_size > 1000000:
        print(f"[Audio] MP3 already exists: {mp3_path.name}")
        return
    print(f"[Audio] Converting {video_path.name} to MP3...")
    cmd = [
        FFMPEG_EXE,
        "-y",
        "-i", str(video_path),
        "-vn",
        "-ar", "44100",
        "-ac", "2",
        "-b:a", "192k",
        str(mp3_path)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg audio conversion failed: {res.stderr.decode('utf-8', errors='replace')}")
    print(f"[Audio] Created: {mp3_path.name} ({mp3_path.stat().st_size / 1024 / 1024:.2f} MB)")


async def ensure_authenticated(context):
    print("=" * 60)
    print("Checking Brightspace session status...")
    page = await context.new_page()
    await page.goto(f"{BASE_URL}/d2l/home", wait_until="domcontentloaded", timeout=45000)
    await page.wait_for_timeout(3000)

    url = page.url
    print(f"[Auth Check] Current page URL: {url}")
    
    if "signon.rug.nl" in url or "login" in url.lower():
        print("=" * 60)
        print("ACTION REQUIRED: Please log in using the browser window on your screen.")
        print("Enter your RUG credentials and complete MFA verification.")
        print("The script will automatically continue once login finishes.")
        print("=" * 60)

        await page.wait_for_url(lambda u: "brightspace.rug.nl/d2l/home" in u or "brightspace.rug.nl/d2l/le" in u, timeout=300000)
        print("[Auth] Login detected! Saving session state...")
        await page.wait_for_timeout(3000)
        await context.storage_state(path=AUTH_STATE_PATH)
        print(f"[Auth] Saved fresh session state to {AUTH_STATE_PATH}.")
    else:
        print("[Auth] Already logged in!")

    await page.close()


async def download_file_with_cookies(url: str, dest_path: Path, context):
    print(f"[Download] Direct media: {url[:100]}...")
    cookies = await context.cookies()
    cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "Cookie": cookie_str,
        "Referer": BASE_URL
    }
    req_ctx = await context.request.get(url, headers=headers)
    if req_ctx.status == 200:
        content = await req_ctx.body()
        with open(dest_path, "wb") as f:
            f.write(content)
        print(f"[Download] Saved {dest_path.name} ({len(content) / 1024 / 1024:.2f} MB)")
        return True
    return False


def download_hls_stream(m3u8_url: str, dest_path: Path, cookies_list=None):
    print(f"[Download] HLS stream via FFmpeg: {m3u8_url[:100]}...")
    cmd = [FFMPEG_EXE, "-y"]
    if cookies_list:
        cookie_header = "; ".join([f"{c['name']}={c['value']}" for c in cookies_list])
        cmd.extend(["-headers", f"Cookie: {cookie_header}\r\nReferer: {BASE_URL}\r\n"])
    
    cmd.extend([
        "-i", m3u8_url,
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        str(dest_path)
    ])

    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        cmd_no_hdr = [FFMPEG_EXE, "-y", "-i", m3u8_url, "-c", "copy", "-bsf:a", "aac_adtstoasc", str(dest_path)]
        proc = subprocess.run(cmd_no_hdr, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            err = proc.stderr.decode("utf-8", errors="replace")
            raise RuntimeError(f"FFmpeg stream download failed: {err}")
    
    print(f"[Download] Successfully saved {dest_path.name} ({dest_path.stat().st_size / 1024 / 1024:.2f} MB)")


async def process_topic(context, topic_info):
    topic_id = topic_info["topic_id"]
    topic_url = topic_info["url"]
    topic_title = topic_info["default_name"]

    print(f"\n" + "=" * 60)
    print(f"Processing Topic: {topic_id} ({topic_info['week']})")
    print(f"URL: {topic_url}")
    print("=" * 60)

    # Check if files already exist
    existing_videos = list(OUTPUT_DIR.glob(f"{topic_id}_*.mp4"))
    if existing_videos and existing_videos[0].stat().st_size > 1000000:
        dest_video = existing_videos[0]
        dest_mp3 = dest_video.with_suffix(".mp3")
        print(f"[Info] Video already downloaded: {dest_video.name}")
        convert_video_to_mp3(dest_video, dest_mp3)
        return dest_video, dest_mp3

    page = await context.new_page()
    captured_urls = []

    async def handle_response(response):
        url = response.url
        ct = response.headers.get("content-type", "").lower()
        if any(v_ext in url.lower() for v_ext in [".mp4", ".m3u8", ".mpd", "playmanifest", "master.m3u8", "index.m3u8"]) or \
           "video/" in ct or "application/vnd.apple.mpegurl" in ct or "application/x-mpegurl" in ct:
            if url not in captured_urls and not url.endswith(".css") and not url.endswith(".js"):
                captured_urls.append(url)
                print(f"[Media Sniffer] Detected: {url[:100]}... (Type: {ct})")

    page.on("response", handle_response)

    print(f"[Browser] Navigating...")
    await page.goto(topic_url, wait_until="load", timeout=60000)
    await page.wait_for_timeout(5000)

    try:
        dom_title = await page.evaluate("""() => {
            const h = document.querySelector('h1, .d2l-page-title, [class*="title" i]');
            if (h && h.innerText) return h.innerText.trim();
            return document.title;
        }""")
        if dom_title and "inloggen" not in dom_title.lower() and "brightspace" not in dom_title.lower():
            topic_title = sanitize_filename(dom_title)
    except Exception:
        pass

    safe_base_name = f"{topic_id}_{topic_title}"
    print(f"[Info] Resolved name: '{safe_base_name}'")

    media_candidates = []
    for frame in page.frames:
        try:
            frame_media = await frame.evaluate("""() => {
                const results = [];
                document.querySelectorAll('video').forEach(v => {
                    if (v.src) results.push(v.src);
                    v.querySelectorAll('source').forEach(s => { if (s.src) results.push(s.src); });
                });
                document.querySelectorAll('audio').forEach(a => {
                    if (a.src) results.push(a.src);
                    a.querySelectorAll('source').forEach(s => { if (s.src) results.push(s.src); });
                });
                document.querySelectorAll('iframe').forEach(i => {
                    if (i.src) results.push(i.src);
                });
                return results;
            }""")
            for m in frame_media:
                if m not in media_candidates:
                    media_candidates.append(m)
        except Exception:
            pass

    if not captured_urls:
        print("[Browser] Looking for play buttons...")
        for frame in page.frames:
            try:
                play_buttons = await frame.query_selector_all("button, .play, .vjs-play-control, [aria-label*='Play' i], [title*='Play' i], video")
                for btn in play_buttons[:3]:
                    try:
                        await btn.click(timeout=1500)
                        await page.wait_for_timeout(1500)
                    except Exception:
                        pass
            except Exception:
                pass
        await page.wait_for_timeout(4000)

    all_media = []
    for u in captured_urls + media_candidates:
        if u and u not in all_media:
            all_media.append(u)

    print(f"[Found Media] Candidates: {len(all_media)}")
    selected_url = None
    for m in all_media:
        if ".m3u8" in m and not any(sub in m.lower() for sub in ["thumbnail", "segment", "audio_"]):
            selected_url = m
            break
    if not selected_url:
        for m in all_media:
            if ".mp4" in m:
                selected_url = m
                break
    if not selected_url and all_media:
        selected_url = all_media[0]

    if not selected_url:
        print(f"[ERROR] Could not find media stream for topic {topic_id}!")
        await page.close()
        return None, None

    print(f"[Selected Media] {selected_url}")
    dest_video = OUTPUT_DIR / f"{safe_base_name}.mp4"
    dest_mp3 = OUTPUT_DIR / f"{safe_base_name}.mp3"

    cookies_list = await context.cookies()
    if ".m3u8" in selected_url or "manifest" in selected_url.lower():
        download_hls_stream(selected_url, dest_video, cookies_list)
    elif selected_url.startswith("http"):
        success = await download_file_with_cookies(selected_url, dest_video, context)
        if not success:
            download_hls_stream(selected_url, dest_video, cookies_list)

    await page.close()

    if not dest_video.exists() or dest_video.stat().st_size == 0:
        print(f"[ERROR] Video download failed for {safe_base_name}")
        return None, None

    convert_video_to_mp3(dest_video, dest_mp3)
    return dest_video, dest_mp3


def transcribe_file(model: WhisperModel, mp3_path: Path):
    base_name = mp3_path.stem
    txt_path = OUTPUT_DIR / f"{base_name}_transcript_nl.txt"
    srt_path = OUTPUT_DIR / f"{base_name}_transcript_nl.srt"

    if txt_path.exists() and txt_path.stat().st_size > 1000 and srt_path.exists():
        print(f"[Whisper] Transcript already exists: {txt_path.name}")
        return

    print("\n" + "=" * 60)
    print(f"[Whisper] Transcribing on RTX 4090 GPU: {mp3_path.name}")
    print("=" * 60)

    start_t = time.time()
    segments, info = model.transcribe(
        str(mp3_path),
        language="nl",
        task="transcribe",
        beam_size=5,
        vad_filter=False
    )

    print(f"[Whisper] Detected language: {info.language} ({info.duration / 60:.1f} min)")

    with open(srt_path, "w", encoding="utf-8") as f_srt, open(txt_path, "w", encoding="utf-8") as f_txt:
        f_txt.write(f"Transscriptie (Nederlands): {base_name}\n")
        f_txt.write(f"Duur: {info.duration / 60:.1f} minuten\n")
        f_txt.write("=" * 60 + "\n\n")

        for idx, seg in enumerate(segments, start=1):
            start_str = format_timestamp_srt(seg.start)
            end_str = format_timestamp_srt(seg.end)
            text_cleaned = seg.text.strip()

            f_srt.write(f"{idx}\n{start_str} --> {end_str}\n{text_cleaned}\n\n")
            f_txt.write(f"[{start_str} - {end_str}] {text_cleaned}\n")

            if idx % 25 == 0:
                print(f"  Segment {idx} [{start_str}]: {text_cleaned[:60]}...")

    elapsed = time.time() - start_t
    print(f"[Whisper] Finished {base_name} in {elapsed:.1f}s ({elapsed / 60:.1f} min)!")


async def main():
    print("=" * 60)
    print("Brightspace Weeks 5 & 6 Downloader & Transcriber")
    print("=" * 60)

    force_headed = "--headed" in sys.argv
    is_headless = not force_headed

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=is_headless)
        context_args = {}
        if os.path.exists(AUTH_STATE_PATH):
            context_args["storage_state"] = AUTH_STATE_PATH

        context = await browser.new_context(**context_args)

        # Check if auth valid; if not valid and we are headless, prompt user
        page = await context.new_page()
        try:
            await page.goto(f"{BASE_URL}/d2l/home", wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(3000)
            url = page.url
        except Exception:
            url = ""
        await page.close()

        if "signon.rug.nl" in url or "login" in url.lower() or not url:
            if is_headless:
                print("\n" + "=" * 60)
                print("[AUTH REQUIRED] The saved Brightspace session has expired.")
                print("Please run this command in your PowerShell / terminal to log in:")
                print("    .venv\\Scripts\\python download_weeks_5_6.py --headed")
                print("=" * 60)
                await browser.close()
                return

            await ensure_authenticated(context)

        downloaded_mp3s = []
        for topic_info in TOPICS:
            try:
                dest_video, dest_mp3 = await process_topic(context, topic_info)
                if dest_mp3 and dest_mp3.exists():
                    downloaded_mp3s.append(dest_mp3)
            except Exception as e:
                print(f"[ERROR] Failed topic {topic_info['topic_id']}: {e}")
                import traceback
                traceback.print_exc()

        await browser.close()

    if downloaded_mp3s:
        print("\n" + "=" * 60)
        print("Starting Dutch GPU transcription on RTX 4090...")
        print("=" * 60)
        model = WhisperModel("medium", device="cuda", compute_type="float16")
        for mp3 in downloaded_mp3s:
            try:
                transcribe_file(model, mp3)
            except Exception as e:
                print(f"[ERROR] Transcription failed for {mp3.name}: {e}")
                import traceback
                traceback.print_exc()

    print("\n" + "=" * 60)
    print("All tasks finished successfully for Weeks 5 & 6!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

"""
Download Brightspace course videos, convert them to MP3, and transcribe in Dutch using faster-whisper.
Target topics:
  - https://brightspace.rug.nl/d2l/le/lessons/523940/topics/5940698
  - https://brightspace.rug.nl/d2l/le/lessons/523940/topics/5940699
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
from playwright.async_api import async_playwright
import imageio_ffmpeg
from faster_whisper import WhisperModel

# Ensure UTF-8 and auto-flushing output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

BASE_URL = "https://brightspace.rug.nl"
AUTH_STATE_PATH = "auth_state.json"
OUTPUT_DIR = Path("downloads/videos")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_TOPICS = [
    {
        "course_id": "523940",
        "topic_id": "5940698",
        "url": f"{BASE_URL}/d2l/le/lessons/523940/topics/5940698"
    },
    {
        "course_id": "523940",
        "topic_id": "5940699",
        "url": f"{BASE_URL}/d2l/le/lessons/523940/topics/5940699"
    }
]

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()


def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\n\r\t]', '_', name)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned[:100] if cleaned else "video"


def format_timestamp_srt(seconds: float) -> str:
    millis = int((seconds - int(seconds)) * 1000)
    total_seconds = int(seconds)
    secs = total_seconds % 60
    mins = (total_seconds // 60) % 60
    hours = total_seconds // 3600
    return f"{hours:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def convert_video_to_mp3(video_path: Path, mp3_path: Path):
    print(f"\n[Audio] Converting {video_path.name} to MP3...")
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
    print(f"[Audio] Created: {mp3_path} ({mp3_path.stat().st_size / 1024 / 1024:.2f} MB)")


def transcribe_audio_dutch(mp3_path: Path, output_base: Path):
    print(f"\n[Whisper] Transcribing {mp3_path.name} in Dutch...")
    
    device = "cuda"
    compute_type = "float16"
    try:
        model = WhisperModel("medium", device=device, compute_type=compute_type)
        print("[Whisper] Loaded 'medium' model on NVIDIA RTX 4090 GPU (float16).")
    except Exception as e:
        print(f"[Whisper] GPU init failed ({e}), falling back to CPU (int8)...")
        device = "cpu"
        compute_type = "int8"
        model = WhisperModel("medium", device=device, compute_type=compute_type)

    start_t = time.time()
    segments, info = model.transcribe(
        str(mp3_path),
        language="nl",
        task="transcribe",
        beam_size=5,
        vad_filter=True
    )

    txt_path = output_base.with_name(f"{output_base.name}_transcript_nl.txt")
    srt_path = output_base.with_name(f"{output_base.name}_transcript_nl.srt")

    segment_list = []
    print(f"[Whisper] Detected language: {info.language} (probability: {info.language_probability:.2f})")
    print("[Whisper] Processing speech segments...")

    with open(srt_path, "w", encoding="utf-8") as f_srt, open(txt_path, "w", encoding="utf-8") as f_txt:
        f_txt.write(f"Transscriptie (Nederlands): {mp3_path.name}\n")
        f_txt.write("=" * 60 + "\n\n")

        for idx, seg in enumerate(segments, start=1):
            segment_list.append(seg)
            start_str = format_timestamp_srt(seg.start)
            end_str = format_timestamp_srt(seg.end)
            text_cleaned = seg.text.strip()
            
            f_srt.write(f"{idx}\n{start_str} --> {end_str}\n{text_cleaned}\n\n")
            f_txt.write(f"[{start_str} - {end_str}] {text_cleaned}\n")

    elapsed = time.time() - start_t
    print(f"[Whisper] Done in {elapsed:.1f}s! Generated:")
    print(f"  - TXT: {txt_path}")
    print(f"  - SRT: {srt_path}")


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
    print(f"[Download] Downloading direct media from: {url}")
    cookies = await context.cookies()
    cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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
    else:
        print(f"[Download] HTTP {req_ctx.status} fetching direct file.")
        return False


def download_hls_stream(m3u8_url: str, dest_path: Path, cookies_list=None):
    print(f"[Download] Downloading stream via FFmpeg: {m3u8_url}")
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
    
    print(f"[Download] Successfully saved stream to {dest_path.name} ({dest_path.stat().st_size / 1024 / 1024:.2f} MB)")


async def process_topic(context, topic_info):
    course_id = topic_info["course_id"]
    topic_id = topic_info["topic_id"]
    topic_url = topic_info["url"]

    print(f"\n" + "=" * 60)
    print(f"Processing Topic: {topic_id} ({topic_url})")
    print("=" * 60)

    # 1. Valence API check
    api_url = f"/d2l/api/le/1.26/{course_id}/content/topics/{topic_id}"
    topic_title = f"Topic_{topic_id}"
    media_candidates = []

    try:
        api_res = await context.request.get(f"{BASE_URL}{api_url}")
        if api_res.status == 200:
            topic_data = await api_res.json()
            raw_title = topic_data.get("Title")
            if raw_title:
                topic_title = sanitize_filename(raw_title)
            print(f"[API] Topic Title: {topic_data.get('Title')} (Type: {topic_data.get('TypeIdentifier')})")
            
            raw_url = topic_data.get("Url", "")
            if raw_url:
                full_raw_url = urllib.parse.urljoin(BASE_URL, raw_url)
                print(f"[API] Target Url: {full_raw_url}")
                if any(ext in full_raw_url.lower() for ext in [".mp4", ".m3u8", ".mp3", ".webm"]):
                    media_candidates.append(full_raw_url)
    except Exception as e:
        print(f"[API] Note: {e}")

    # 2. Browser Navigation & Sniffing
    page = await context.new_page()
    captured_urls = []

    async def handle_response(response):
        url = response.url
        ct = response.headers.get("content-type", "").lower()
        if any(v_ext in url.lower() for v_ext in [".mp4", ".m3u8", ".mpd", "playmanifest", "master.m3u8", "index.m3u8"]) or \
           "video/" in ct or "application/vnd.apple.mpegurl" in ct or "application/x-mpegurl" in ct:
            if url not in captured_urls and not url.endswith(".css") and not url.endswith(".js"):
                captured_urls.append(url)
                print(f"[Media Sniffer] Detected: {url} (Type: {ct})")

    page.on("response", handle_response)

    print(f"[Browser] Navigating to {topic_url}...")
    await page.goto(topic_url, wait_until="load", timeout=60000)
    await page.wait_for_timeout(5000)

    # Resolve Title from DOM
    try:
        dom_title = await page.evaluate("""() => {
            const h = document.querySelector('h1, .d2l-page-title, d2l-navigation-band, [class*="title" i]');
            if (h && h.innerText) return h.innerText.trim();
            return document.title;
        }""")
        if dom_title and topic_title == f"Topic_{topic_id}":
            topic_title = sanitize_filename(dom_title)
    except Exception:
        pass

    print(f"[Info] Topic Title resolved: '{topic_title}'")
    safe_base_name = f"{topic_id}_{topic_title}"

    # Check all frames
    print(f"[Browser] Inspecting {len(page.frames)} frames...")
    for idx, frame in enumerate(page.frames):
        try:
            f_url = frame.url
            if f_url and f_url != "about:blank":
                print(f"  Frame {idx}: {f_url[:120]}")
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

    # If no media yet, search and click play buttons
    if not captured_urls:
        print("[Browser] Looking for play buttons...")
        for frame in page.frames:
            try:
                play_buttons = await frame.query_selector_all("button, .play, .vjs-play-control, [aria-label*='Play' i], [title*='Play' i], video, .kWidgetIframeContainer")
                for btn in play_buttons[:3]:
                    try:
                        await btn.click(timeout=1500)
                        await page.wait_for_timeout(1500)
                    except Exception:
                        pass
            except Exception:
                pass
        await page.wait_for_timeout(4000)

    # Combine candidates
    all_media = []
    for u in captured_urls + media_candidates:
        if u and u not in all_media:
            # Skip pure wrapper iframes if direct stream is found
            all_media.append(u)

    print(f"\n[Found Media] Total candidates found: {len(all_media)}")
    for idx, m in enumerate(all_media, start=1):
        print(f"  {idx}. {m}")

    selected_url = None
    # 1. Prefer m3u8 playlist or mp4 direct link
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
        print(f"[ERROR] Could not find any video stream or file for topic {topic_id}!")
        await page.close()
        return False

    print(f"\n[Selected Media] Using: {selected_url}")
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
        return False

    # 3. Convert to MP3
    convert_video_to_mp3(dest_video, dest_mp3)

    # 4. Transcribe in Dutch
    transcribe_audio_dutch(dest_mp3, OUTPUT_DIR / safe_base_name)
    return True


async def main():
    print("=" * 60)
    print("Brightspace Video Downloader & Dutch Transcriber")
    print("=" * 60)

    # If --headless is passed or session is known valid, can run headless
    force_headed = "--headed" in sys.argv
    force_headless = "--headless" in sys.argv
    is_headless = force_headless or (not force_headed and os.path.exists(AUTH_STATE_PATH))

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=not force_headed and is_headless)
        context_args = {}
        if os.path.exists(AUTH_STATE_PATH):
            context_args["storage_state"] = AUTH_STATE_PATH

        context = await browser.new_context(**context_args)

        # Check if auth valid; if not valid and we are headless, we tell user
        page = await context.new_page()
        try:
            await page.goto(f"{BASE_URL}/d2l/home", wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(3000)
            url = page.url
        except Exception:
            url = ""
        await page.close()

        if "signon.rug.nl" in url or "login" in url.lower() or not url:
            if is_headless and not force_headed:
                print("\n" + "=" * 60)
                print("[AUTH REQUIRED] The saved Brightspace session has expired.")
                print("Because automated background tools cannot display GUI windows on your desktop,")
                print("please run this command in your VS Code terminal:")
                print("    .venv\\Scripts\\python download_and_transcribe.py --headed")
                print("or:")
                print("    python sync.py login")
                print("=" * 60)
                await browser.close()
                return

            # If headed mode, wait for user login
            await ensure_authenticated(context)

        # Process both topics
        for topic_info in TARGET_TOPICS:
            try:
                await process_topic(context, topic_info)
            except Exception as e:
                print(f"[ERROR] Failed processing topic {topic_info['topic_id']}: {e}")
                import traceback
                traceback.print_exc()

        await browser.close()

    print("\n" + "=" * 60)
    print("All tasks completed! Check 'downloads/videos/' for files.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

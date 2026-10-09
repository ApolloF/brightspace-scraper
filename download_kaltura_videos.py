"""
Download remaining 3 Kaltura videos (5.2, 6.1, 6.2), convert to MP3, and transcribe all 4 videos for Weeks 5 & 6.
"""

import os
import sys
import time
import subprocess
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
import imageio_ffmpeg

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

VIDEOS_DIR = Path("downloads/videos")
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

VIDEOS = [
    {
        "id": "5977053",
        "entry_id": "0_2jwo11s6",
        "module": "5.1",
        "title": "Hoorcollege 5 - Module 5.1 (Organisatieverandering)",
        "mp4": "5977053_M&OT Hoorcollege 5 - Module 5.1 (Organisatieverandering).mp4",
        "mp3": "5977053_M&OT Hoorcollege 5 - Module 5.1 (Organisatieverandering).mp3",
    },
    {
        "id": "5977054",
        "entry_id": "0_qz2zkc9s",
        "module": "5.2",
        "title": "Hoorcollege 5 - Module 5.2 (Crisis)",
        "mp4": "5977054_M&OT Hoorcollege 5 - Module 5.2 (Crisis).mp4",
        "mp3": "5977054_M&OT Hoorcollege 5 - Module 5.2 (Crisis).mp3",
    },
    {
        "id": "5981787",
        "entry_id": "0_pkxntnv8",
        "module": "6.1",
        "title": "Hoorcollege 6 - Module 6.1 (IORs & OI)",
        "mp4": "5981787_M&OT Hoorcollege 6 - Module 6.1 (IORs & OI).mp4",
        "mp3": "5981787_M&OT Hoorcollege 6 - Module 6.1 (IORs & OI).mp3",
    },
    {
        "id": "5981789",
        "entry_id": "0_ojn4n5fm",
        "module": "6.2",
        "title": "Hoorcollege 6 - Module 6.2 (ACAP)",
        "mp4": "5981789_M&OT Hoorcollege 6 - Module 6.2 (ACAP).mp4",
        "mp3": "5981789_M&OT Hoorcollege 6 - Module 6.2 (ACAP).mp3",
    }
]

def format_timestamp_srt(seconds: float) -> str:
    millis = int((seconds - int(seconds)) * 1000)
    total_seconds = int(seconds)
    secs = total_seconds % 60
    mins = (total_seconds // 60) % 60
    hours = total_seconds // 3600
    return f"{hours:02d}:{mins:02d}:{secs:02d},{millis:03d}"

def download_video(item):
    mp4_path = VIDEOS_DIR / item["mp4"]
    # Check if already downloaded under old long name
    old_files = list(VIDEOS_DIR.glob(f"{item['id']}_*.mp4"))
    for old in old_files:
        if old.stat().st_size > 5000000:
            print(f"[Download] Reusing existing video: {old.name}")
            if old != mp4_path:
                old.replace(mp4_path)
            return mp4_path

    if mp4_path.exists() and mp4_path.stat().st_size > 5000000:
        print(f"[Download] Already exists: {mp4_path.name}")
        return mp4_path

    manifest_url = f"https://api.eu.kaltura.com/p/239/sp/23900/playManifest/entryId/{item['entry_id']}/format/applehttp/protocol/https/a.m3u8"
    print(f"\n[Download] Downloading {item['title']} via FFmpeg...")
    cmd = [
        FFMPEG_EXE,
        "-y",
        "-i", manifest_url,
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        str(mp4_path)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0:
        raise RuntimeError(f"Download failed for {item['title']}: {res.stderr.decode('utf-8', errors='replace')}")
    print(f"[Download] Successfully saved {mp4_path.name} ({mp4_path.stat().st_size / 1024 / 1024:.2f} MB)")
    return mp4_path

def convert_to_mp3(mp4_path: Path, mp3_path: Path):
    # Check if old mp3 exists
    old_files = list(VIDEOS_DIR.glob(f"{mp4_path.stem[:7]}*.mp3"))
    for old in old_files:
        if old.stat().st_size > 1000000:
            print(f"[Audio] Reusing existing MP3: {old.name}")
            if old != mp3_path:
                old.replace(mp3_path)
            return mp3_path

    if mp3_path.exists() and mp3_path.stat().st_size > 1000000:
        print(f"[Audio] Already exists: {mp3_path.name}")
        return mp3_path

    print(f"[Audio] Converting {mp4_path.name} to MP3...")
    cmd = [
        FFMPEG_EXE,
        "-y",
        "-i", str(mp4_path),
        "-vn",
        "-ar", "44100",
        "-ac", "2",
        "-b:a", "192k",
        str(mp3_path)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0:
        raise RuntimeError(f"MP3 conversion failed: {res.stderr.decode('utf-8', errors='replace')}")
    print(f"[Audio] Created {mp3_path.name} ({mp3_path.stat().st_size / 1024 / 1024:.2f} MB)")
    return mp3_path

def extract_frames(mp4_path: Path, output_folder: Path):
    output_folder.mkdir(parents=True, exist_ok=True)
    existing = list(output_folder.glob("*.jpg"))
    if len(existing) > 50:
        print(f"[Frames] {output_folder.name} already has {len(existing)} frames.")
        return
    print(f"[Frames] Extracting frames (1 per 5s) from {mp4_path.name}...")
    cmd = [
        FFMPEG_EXE,
        "-y",
        "-i", str(mp4_path),
        "-vf", "fps=1/5",
        "-q:v", "3",
        str(output_folder / "f_%04d.jpg")
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(f"[Frames] Saved {len(list(output_folder.glob('*.jpg')))} frames.")

def transcribe_audio(model: WhisperModel, mp3_path: Path, title: str):
    txt_path = VIDEOS_DIR / f"{mp3_path.stem}_transcript_nl.txt"
    srt_path = VIDEOS_DIR / f"{mp3_path.stem}_transcript_nl.srt"

    if txt_path.exists() and txt_path.stat().st_size > 1000 and srt_path.exists():
        print(f"[Whisper] Already transcribed: {txt_path.name}")
        return

    print("\n" + "=" * 60)
    print(f"[Whisper] Transcribing on GPU: {title}")
    print("=" * 60)

    start_t = time.time()
    segments, info = model.transcribe(
        str(mp3_path),
        language="nl",
        task="transcribe",
        beam_size=5,
        vad_filter=False
    )

    print(f"[Whisper] Language: {info.language} ({info.duration / 60:.1f} min)")

    with open(srt_path, "w", encoding="utf-8") as f_srt, open(txt_path, "w", encoding="utf-8") as f_txt:
        f_txt.write(f"Transscriptie (Nederlands): {title}\n")
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
    print(f"[Whisper] Done in {elapsed:.1f}s ({elapsed / 60:.1f} min)!")

def main():
    print("=" * 60)
    print("Downloading & Processing Weeks 5 & 6 Video Lectures")
    print("=" * 60)

    # 1. Download & Convert to MP3
    ready_items = []
    for item in VIDEOS:
        mp4_path = download_video(item)
        mp3_path = VIDEOS_DIR / item["mp3"]
        convert_to_mp3(mp4_path, mp3_path)
        
        # Extract frames for slide alignment
        frames_folder = Path("scratch") / f"v_{item['module']}_fps1"
        extract_frames(mp4_path, frames_folder)
        
        ready_items.append((mp3_path, item["title"]))

    # 2. Transcribe on RTX 4090 GPU
    print("\n" + "=" * 60)
    print("Loading faster-whisper on NVIDIA GeForce RTX 4090 (CUDA float16)...")
    print("=" * 60)
    model = WhisperModel("medium", device="cuda", compute_type="float16")

    for mp3_path, title in ready_items:
        transcribe_audio(model, mp3_path, title)

    print("\n" + "=" * 60)
    print("All downloads, conversions, and transcriptions complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()

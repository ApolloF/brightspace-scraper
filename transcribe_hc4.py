"""
Transcribe Hoorcollege 4 lectures in Dutch using faster-whisper on RTX 4090 (CUDA float16).
Also extracts video frames every 5 seconds for slide transition detection.
"""

import os
import sys
import time
from pathlib import Path

# Add nvidia CUDA DLL directories
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
import subprocess

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

VIDEOS_DIR = Path("downloads/videos")
FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

HC4_FILES = [
    {
        "id": "5970124",
        "module": "4.1",
        "mp3": "5970124_M&OT Hoorcollege 4 - Module 4.1 (Besluitvorming) - Management- en Organisatietheorie [Semester 1a].mp3",
        "mp4": "5970124_M&OT Hoorcollege 4 - Module 4.1 (Besluitvorming) - Management- en Organisatietheorie [Semester 1a].mp4",
        "name": "Hoorcollege 4 - Module 4.1 (Besluitvorming)"
    },
    {
        "id": "5970125",
        "module": "4.2",
        "mp3": "5970125_M&OT Hoorcollege 4 - Module 4.2 (Leren & Bias) - Management- en Organisatietheorie [Semester 1a].mp3",
        "mp4": "5970125_M&OT Hoorcollege 4 - Module 4.2 (Leren & Bias) - Management- en Organisatietheorie [Semester 1a].mp4",
        "name": "Hoorcollege 4 - Module 4.2 (Leren & Bias)"
    },
    {
        "id": "5970126",
        "module": "4.3",
        "mp3": "5970126_M&OT Hoorcollege 4 - Module 4.3 (Conflict) - Management- en Organisatietheorie [Semester 1a].mp3",
        "mp4": "5970126_M&OT Hoorcollege 4 - Module 4.3 (Conflict) - Management- en Organisatietheorie [Semester 1a].mp4",
        "name": "Hoorcollege 4 - Module 4.3 (Conflict)"
    },
    {
        "id": "5970127",
        "module": "4.4",
        "mp3": "5970127_M&OT Hoorcollege 4 - Module 4.4 (Macht & Politiek) - Management- en Organisatietheorie [Semester 1a].mp3",
        "mp4": "5970127_M&OT Hoorcollege 4 - Module 4.4 (Macht & Politiek) - Management- en Organisatietheorie [Semester 1a].mp4",
        "name": "Hoorcollege 4 - Module 4.4 (Macht & Politiek)"
    }
]


def format_timestamp_srt(seconds: float) -> str:
    millis = int((seconds - int(seconds)) * 1000)
    total_seconds = int(seconds)
    secs = total_seconds % 60
    mins = (total_seconds // 60) % 60
    hours = total_seconds // 3600
    return f"{hours:02d}:{mins:02d}:{secs:02d},{millis:03d}"


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
    print(f"[Frames] Saved {len(list(output_folder.glob('*.jpg')))} frames to {output_folder.name}")


def transcribe(model: WhisperModel, item: dict):
    mp3_path = VIDEOS_DIR / item["mp3"]
    base_name = mp3_path.stem
    txt_path = VIDEOS_DIR / f"{base_name}_transcript_nl.txt"
    srt_path = VIDEOS_DIR / f"{base_name}_transcript_nl.srt"

    print("\n" + "=" * 60)
    print(f"Transcribing: {item['name']}")
    print(f"File: {mp3_path.name}")
    print("=" * 60)

    start_t = time.time()
    segments, info = model.transcribe(
        str(mp3_path),
        language="nl",
        task="transcribe",
        beam_size=5,
        vad_filter=False
    )

    print(f"Duration: {info.duration / 60:.1f} min. Transcribing...")

    with open(srt_path, "w", encoding="utf-8") as f_srt, open(txt_path, "w", encoding="utf-8") as f_txt:
        f_txt.write(f"Transscriptie (Nederlands): {item['name']}\n")
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
    print(f"Finished {item['name']} in {elapsed:.1f}s ({elapsed / 60:.1f} min)!")


def main():
    print("=" * 60)
    print("Loading faster-whisper on NVIDIA GeForce RTX 4090 (CUDA float16)...")
    model = WhisperModel("medium", device="cuda", compute_type="float16")
    print("Model ready!")

    for item in HC4_FILES:
        # Extract frames
        mp4_path = VIDEOS_DIR / item["mp4"]
        frames_folder = Path("scratch") / f"v_{item['module']}_fps1"
        extract_frames(mp4_path, frames_folder)

        # Transcribe
        transcribe(model, item)

    print("\n" + "=" * 60)
    print("All Hoorcollege 4 lectures transcribed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()

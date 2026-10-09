"""
Transcribe downloaded MP3 files into Dutch text and SRT subtitles using faster-whisper.
"""

import sys
import time
from pathlib import Path
from faster_whisper import WhisperModel

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

OUTPUT_DIR = Path("downloads/videos")


def format_timestamp_srt(seconds: float) -> str:
    millis = int((seconds - int(seconds)) * 1000)
    total_seconds = int(seconds)
    secs = total_seconds % 60
    mins = (total_seconds // 60) % 60
    hours = total_seconds // 3600
    return f"{hours:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def transcribe_file(model: WhisperModel, mp3_path: Path):
    base_name = mp3_path.stem
    # Remove extra .mp4 if present in stem
    clean_name = base_name.replace(".mp4", "")
    txt_path = OUTPUT_DIR / f"{clean_name}_transcript_nl.txt"
    srt_path = OUTPUT_DIR / f"{clean_name}_transcript_nl.srt"

    print(f"\n" + "=" * 60)
    print(f"Transcribing: {mp3_path.name}")
    print(f"Destination TXT: {txt_path.name}")
    print(f"Destination SRT: {srt_path.name}")
    print("=" * 60)

    start_t = time.time()
    segments, info = model.transcribe(
        str(mp3_path),
        language="nl",
        task="transcribe",
        beam_size=5,
        vad_filter=False
    )

    print(f"Detected language: {info.language} (duration: {info.duration / 60:.1f} min)")
    print("Processing audio segments...")

    with open(srt_path, "w", encoding="utf-8") as f_srt, open(txt_path, "w", encoding="utf-8") as f_txt:
        f_txt.write(f"Transscriptie (Nederlands): {clean_name}\n")
        f_txt.write(f"Duur: {info.duration / 60:.1f} minuten\n")
        f_txt.write("=" * 60 + "\n\n")

        for idx, seg in enumerate(segments, start=1):
            start_str = format_timestamp_srt(seg.start)
            end_str = format_timestamp_srt(seg.end)
            text_cleaned = seg.text.strip()

            f_srt.write(f"{idx}\n{start_str} --> {end_str}\n{text_cleaned}\n\n")
            f_txt.write(f"[{start_str} - {end_str}] {text_cleaned}\n")

            if idx % 10 == 0:
                print(f"  Segment {idx} [{start_str}]: {text_cleaned[:50]}...")

    elapsed = time.time() - start_t
    print(f"Completed {clean_name} in {elapsed:.1f}s ({elapsed / 60:.1f} min)!")


def main():
    mp3_files = sorted(list(OUTPUT_DIR.glob("*.mp3")))
    if not mp3_files:
        print("No MP3 files found in downloads/videos/")
        return

    print(f"Found {len(mp3_files)} MP3 files to transcribe.")
    print("Loading faster-whisper 'medium' model (int8)...")
    model = WhisperModel("medium", device="cpu", compute_type="int8", cpu_threads=8)
    print("Model loaded successfully.\n")

    for mp3 in mp3_files:
        transcribe_file(model, mp3)

    print("\n" + "=" * 60)
    print("All transcriptions successfully completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()

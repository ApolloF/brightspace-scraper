"""
Detect slide transitions across Weeks 5 & 6 video frames and correlate with transcripts.
"""

import os, numpy as np
from PIL import Image

def find_peaks(folder, threshold=3.5, step_sec=5):
    files = sorted([f for f in os.listdir(folder) if f.endswith('.jpg')])
    prev = None
    diffs = []
    for i, f in enumerate(files):
        img = Image.open(os.path.join(folder, f)).convert('L').resize((320, 180))
        arr = np.array(img, dtype=np.float32)
        if prev is not None:
            mae = np.mean(np.abs(arr - prev))
            if mae > threshold:
                sec = i * step_sec
                m, s = divmod(sec, 60)
                diffs.append((i, sec, f"{m:02d}:{s:02d}", mae, f))
        prev = arr
    return diffs

for mod in ['5.1', '5.2', '6.1', '6.2']:
    folder = f'scratch/v_{mod}_fps1'
    peaks = find_peaks(folder, threshold=3.2)
    print(f"\n=== Module {mod} (Total frames: {len(os.listdir(folder))}, Peaks: {len(peaks)}) ===")
    for p in peaks:
        print(f"  Frame {p[0]:03d} at {p[2]} ({p[1]}s) - diff: {p[3]:.1f}")

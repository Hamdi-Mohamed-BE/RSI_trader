"""Assemble the explainer MP4 + poster + WebVTT captions from captured frames and voice clips (ffmpeg).

    python tools/video/render_video.py <work_dir>
Outputs static/video/calyx-how-it-works.mp4, calyx-how-it-works-poster.jpg, calyx-how-it-works.en.vtt
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "static" / "video"
FPS = 30
LEAD, TAIL = 0.35, 0.75


def ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def vtt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def cues_for(line: str, start: float, duration: float) -> list[tuple[float, float, str]]:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", line) if s.strip()]
    chunks: list[str] = []
    for sentence in sentences:  # keep cues short enough for two caption lines
        words, current = sentence.split(), ""
        for word in words:
            if len(current) + len(word) + 1 > 84 and current:
                chunks.append(current)
                current = word
            else:
                current = f"{current} {word}".strip()
        if current:
            chunks.append(current)
    total = sum(len(c) for c in chunks)
    cues, t = [], start
    for chunk in chunks:
        d = duration * len(chunk) / total
        cues.append((t, t + d, chunk))
        t += d
    return cues


def main(work: str) -> None:
    work_dir = Path(work)
    spec = json.loads((HERE / "script.json").read_text(encoding="utf-8"))
    durations = json.loads((work_dir / "voice" / "durations.json").read_text())
    clips_dir = work_dir / "clips"
    shutil.rmtree(clips_dir, ignore_errors=True)
    clips_dir.mkdir(parents=True)
    cues: list[tuple[float, float, str]] = []
    t = 0.0
    concat = []
    for i, (scene, speech) in enumerate(zip(spec["scenes"], durations)):
        length = LEAD + speech + TAIL
        frames = int(round(length * FPS))
        image = work_dir / "shots" / f"{scene['shot']}.png"
        clip = clips_dir / f"clip_{i:02d}.mp4"
        zoom = "min(1+0.00012*on,1.06)" if i % 2 == 0 else "max(1.06-0.00012*on,1.0)"
        vf = (f"scale=3840:2160,zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps={FPS},"
              f"fade=t=in:st=0:d=0.3,fade=t=out:st={length - 0.3:.3f}:d=0.3,format=yuv420p")
        af = f"adelay={int(LEAD * 1000)}|{int(LEAD * 1000)},apad,atrim=0:{length:.3f},aformat=sample_rates=48000:channel_layouts=stereo"
        ffmpeg("-loop", "1", "-i", str(image), "-i", str(work_dir / "voice" / f"scene_{i:02d}.mp3"),
               "-vf", vf, "-af", af, "-frames:v", str(frames), "-c:v", "libx264", "-preset", "medium", "-crf", "20",
               "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-t", f"{length:.3f}", str(clip))
        cues += cues_for(scene["line"], t + LEAD, speech)
        concat.append(f"file '{clip.as_posix()}'")
        t += length
        print(f"clip {i:02d} {length:5.2f}s", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    listing = clips_dir / "concat.txt"
    listing.write_text("\n".join(concat) + "\n", encoding="utf-8")
    mp4 = OUT / "calyx-how-it-works.mp4"
    joined = clips_dir / "joined.mp4"
    ffmpeg("-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(joined))
    # web delivery: re-encode once at a lower bitrate (slides + slow zoom compress well)
    ffmpeg("-i", str(joined), "-c:v", "libx264", "-preset", "slow", "-crf", "26", "-tune", "stillimage",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(mp4))
    ffmpeg("-i", str(work_dir / "shots" / "01-title.png"), "-vf", "scale=1280:720", "-q:v", "3", str(OUT / "calyx-how-it-works-poster.jpg"))
    vtt = ["WEBVTT", ""]
    for n, (start, end, text) in enumerate(cues, 1):
        vtt += [str(n), f"{vtt_time(start)} --> {vtt_time(end)}", text, ""]
    (OUT / "calyx-how-it-works.en.vtt").write_text("\n".join(vtt), encoding="utf-8")
    print(f"video {t:.1f}s -> {mp4}")


if __name__ == "__main__":
    main(sys.argv[1])

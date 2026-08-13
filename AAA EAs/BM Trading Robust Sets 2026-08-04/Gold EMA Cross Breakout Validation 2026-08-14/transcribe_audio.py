from __future__ import annotations

import argparse
from pathlib import Path

from faster_whisper import WhisperModel


def stamp(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    return f"{total // 60:02d}:{total % 60:02d}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("audio", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    model = WhisperModel("base.en", device="cpu", compute_type="int8", cpu_threads=8)
    segments, info = model.transcribe(
        str(args.audio),
        beam_size=3,
        vad_filter=True,
        condition_on_previous_text=True,
    )
    lines = [f"# language={info.language} probability={info.language_probability:.4f}"]
    for segment in segments:
        text = segment.text.strip()
        if text:
            lines.append(f"[{stamp(segment.start)} - {stamp(segment.end)}] {text}")
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {args.output} ({len(lines) - 1} segments)")


if __name__ == "__main__":
    main()

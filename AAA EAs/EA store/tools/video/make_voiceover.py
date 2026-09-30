"""Voice each scene line with free Microsoft Edge neural TTS (adapted, copied from clipper/tools/make_voiceover.py).

    python tools/video/make_voiceover.py <work_dir>
Writes <work_dir>/voice/scene_NN.mp3 and <work_dir>/voice/durations.json. Requires `edge-tts` + ffprobe.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def main(work: str) -> None:
    spec = json.loads((HERE / "script.json").read_text(encoding="utf-8"))
    out = Path(work) / "voice"
    out.mkdir(parents=True, exist_ok=True)
    durations = []
    for i, scene in enumerate(spec["scenes"]):
        clip = out / f"scene_{i:02d}.mp3"
        if not clip.exists():
            subprocess.run([sys.executable, str(HERE / "edge_tts_threaded.py"), "--voice", spec["voice"], "--rate", spec["rate"],
                            "--text", scene["line"], "--write-media", str(clip)], check=True)
        durations.append(duration(clip))
        print(f"scene {i:02d}: {durations[-1]:5.2f}s", flush=True)
    (out / "durations.json").write_text(json.dumps(durations), encoding="utf-8")
    print(f"total speech {sum(durations):.1f}s")


if __name__ == "__main__":
    main(sys.argv[1])

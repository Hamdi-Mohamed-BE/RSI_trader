from __future__ import annotations

import argparse
import time

import soundcard as sc
import soundfile as sf


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--seconds", type=float, default=1100.0)
    parser.add_argument("--samplerate", type=int, default=48000)
    args = parser.parse_args()

    speaker = sc.default_speaker()
    loopback = sc.get_microphone(speaker.name, include_loopback=True)
    frames_per_chunk = args.samplerate
    deadline = time.monotonic() + args.seconds

    with sf.SoundFile(args.output, mode="w", samplerate=args.samplerate, channels=2, subtype="PCM_16") as output:
        with loopback.recorder(samplerate=args.samplerate, channels=2, blocksize=frames_per_chunk) as recorder:
            while time.monotonic() < deadline:
                output.write(recorder.record(numframes=frames_per_chunk))


if __name__ == "__main__":
    main()

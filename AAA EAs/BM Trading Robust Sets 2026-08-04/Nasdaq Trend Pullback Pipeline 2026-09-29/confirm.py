"""Confirm the unchanged Nasdaq baseline; never initializes the live MT5 API."""
from pathlib import Path
import hashlib
import importlib.util
import json
import msvcrt

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'Market Style Bots Raw 2026-09-29'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    spec = importlib.util.spec_from_file_location('frozen_native_runner', SOURCE / 'run.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    # Only output scope changes. CFG, source, executable, parameters and costs do not.
    runner.ROOT = ROOT
    build = json.loads((SOURCE / 'BUILD.json').read_text())
    assert all(sha(ROOT / name) == expected for name, expected in build.items())
    assert all(sha(SOURCE / name) == expected for name, expected in build.items())
    provenance = {
        'source_root': str(SOURCE),
        'source_runner_sha256': sha(SOURCE / 'run.py'),
        'protocol_sha256': sha(ROOT / 'PROTOCOL.md'),
        'wrapper_sha256': sha(Path(__file__)),
        'original_build': build,
        'mode': 'unchanged_raw_confirmation_only',
        'gold_modified': False,
    }
    runner.save(ROOT / 'PROVENANCE.json', provenance)
    bot = next(b for b in runner.CFG['bots'] if b['name'] == 'nasdaq-trend')
    # Share the existing lease as well as port/process guards with prior runners.
    with (SOURCE / 'tester.lock').open('a+b') as lease:
        lease.seek(0)
        msvcrt.locking(lease.fileno(), msvcrt.LK_NBLCK, 1)
        for window in ['3y', '5y']:
            for control in [False, True]:
                runner.case(bot, window, 4, control)
    runner.status('COMPLETE Nasdaq unchanged raw confirmation')


if __name__ == '__main__':
    main()

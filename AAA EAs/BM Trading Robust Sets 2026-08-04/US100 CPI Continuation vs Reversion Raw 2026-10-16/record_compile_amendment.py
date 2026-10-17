"""Record a compiler-only identifier repair before ANY tester process exists."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

R = Path(__file__).resolve().parent

def main():
    freeze = R / 'FROZEN.json'
    out = R / 'native/cpi-raw-20261016'
    assert not (out / 'owned-process.json').exists(), 'Cannot amend after a tester process has started'
    assert not (out / 'results.json').exists()
    previous = json.loads(freeze.read_text())
    old = (out / 'OrbSearch.mq5').read_text()
    import build_engine
    cases = json.loads((R / 'CASES.json').read_text())
    new = build_engine.build(cases)
    import re
    # Strings/CSV headers retain the name "mode"; only the identifier changed.
    def strip(s):
        return re.sub(r'//[^\n]*', '', re.sub(r'"(?:\\.|[^"\\])*"', '"STRING"', s))
    assert re.sub(r'\bmode\b', 'strategy_mode', strip(old)) == strip(new)
    record = dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(), reason='Compiler reported two global-name shadowing warnings; rename identifier mode to strategy_mode only',
                  prior_freeze=previous, prior_generated_source_sha256=hashlib.sha256(old.encode()).hexdigest(),
                  new_engine_sha256=hashlib.sha256((R / 'engine.mq5').read_bytes()).hexdigest(),
                  tester_started=False, results_inspected=False, parameters_or_logic_changed=False)
    (R / 'COMPILER-ONLY-AMENDMENT.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    previous['locked']['engine_sha256'] = record['new_engine_sha256']
    previous['frozen_at_utc'] = datetime.now(timezone.utc).isoformat()
    freeze.write_text(json.dumps(previous, indent=2), encoding='utf-8')
    manifest = json.loads((out / 'manifest.json').read_text())
    manifest['engine_sha256'] = hashlib.sha256(new.encode()).hexdigest()
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('Compiler-only amendment recorded before any tester run; trading rules unchanged')

if __name__ == '__main__':
    main()

from pathlib import Path
import hashlib
import run_grid as g

# Identical strategy; only additional audit events. Keep original reports intact.
g.ROOT=Path(__file__).resolve().parent/'Audit Replay'
g.SOURCE=g.ROOT/'EA'/f'{g.NAME}.mq5'
g.HASH=hashlib.sha256(g.SOURCE.read_bytes()).hexdigest()
g.EXPERT=Path('AAA Research')/'XAU Doubling Grid Diagnostic 20260913'
g.compile_ea()
out=[g.run(p) for p in g.WINDOWS]
g.save(g.ROOT/'results.json',{'source_sha256':g.HASH,'rows':out})

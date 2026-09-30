"""Re-run the frozen joint-week study with News Pulse excluded. Offline only."""
from pathlib import Path
import json, random, sys
ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "FTMO Fourteen EA Study 2026-09-27"
sys.path.insert(0, str(SOURCE))
import study as s

def main():
    checks = s.unit_tests()
    data = s.read(SOURCE / "prepared.json")
    keys = [x["slug"] for x in s.read(SOURCE / "FROZEN.json")["entries"]
            if x["slug"] != "news-pulse-xau"]
    assert len(keys) == 13
    data["placements"] = []
    data["rows"] = {k: data["rows"][k] for k in keys}
    assert not any(r["news"] for rows in data["rows"].values() for r in rows)
    s.c.START, s.c.END = s.START, s.END
    s.ph.HORIZONS = [30, 60, 120, 180]
    weeks = s.c.pool(data, s.POOL_START, s.WEEKS)
    rng = random.Random(20260927)
    samples = [[rng.randrange(s.WEEKS) for _ in range(26)] for _ in range(1000)]
    out = dict(news_enabled=False, keys=keys, checks=checks, paths=1000,
               source_hash=s.sha(SOURCE / "prepared.json"), cases=[])
    rows = [dict(r) for k in keys for r in data["rows"][k]]
    for risk in (50., 70.):
        ns = s.engine(risk)
        for stress in (False, True):
            paths = []
            for sample in samples:
                rr, pp = s.c.sample_rows(data, keys, s.POOL_START, weeks, sample,
                                        s.START, s.START + 180*s.DAY)
                assert not pp and not any(r["news"] for r in rr)
                paths.append(ns["replay"](rr, [], s.START, s.START+180*s.DAY,
                                         stress=stress, guards=True))
            hist = ns["replay"](rows, [], s.BEGIN, s.END, stress=stress,
                                guards=True, challenge=False, detail=True)
            hist["risk"] = risk
            s.reconcile(hist)
            case = dict(risk=risk, stress=stress, guards=True,
                        summary=s.ph.summarize(paths, ns),
                        historical_continuous=hist, historical_details=s.describe(hist))
            out["cases"].append(case)
            s.save(ROOT / "NO_NEWS_RESULTS.json", out)
            print(json.dumps(dict(risk=risk, stress=stress, trades=hist["trades"],
                                  balance=hist["balance"], summary=case["summary"])), flush=True)
    print("Complete: 4,000 paired scenarios; original results untouched.", flush=True)

if __name__ == "__main__":
    main()

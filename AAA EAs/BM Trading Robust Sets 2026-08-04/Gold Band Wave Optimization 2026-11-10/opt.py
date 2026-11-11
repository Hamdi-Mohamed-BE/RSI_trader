"""Gold Band Wave optimisation (PLAN.md, frozen 2026-11-10 before results) on the shared engine (../research_opt_engine.py). Run from AAA EAs/EA store:  uv run python "<this>" """
import importlib.util
from pathlib import Path
from types import SimpleNamespace

H = Path(__file__).resolve().parent; PACKAGE = H.parent
spec = importlib.util.spec_from_file_location('engine', PACKAGE / 'research_opt_engine.py'); E = importlib.util.module_from_spec(spec); spec.loader.exec_module(E)
R = lambda **k: {a: str(v) for a, v in k.items()}  # noqa: E731
S = SimpleNamespace(
    H=H, EX5=H / 'EA/Gold Band Wave Research EA.ex5', SYM='XAUUSD', FIRST='2019-01-01', RAW=PACKAGE / 'Gold Band Wave Raw 2026-11-10/native/nw-XAUUSD-GBW-all', RAW_END='2026-11-10',
    EXPERT_DIR='CalyxGbwOpt', MIN_TRADES=100, PERIOD=lambda c: {'60': 'H1', '1440': 'D1'}.get(str(int(float(c['InpGbwTF']))), 'H4'),
    BASE=dict(InpRiskPercent='1.0', InpMagic='91110001', InpTrendPeriod='200', InpShortBB='20', InpLongBB='50', InpBBDeviation='2.0', InpSignalPeriod='9', InpATRPeriod='14', InpStopATR='2.0',
              InpRandomDirection='false', InpSeed='1', InpDeviationPoints='50', InpGbwTF='240', InpGbwDirection='2', InpGbwExitOnCross='true', InpGbwTargetR='0', InpGbwBreakEvenR='0', InpGbwTrailATR='0'),
    STAGES=[
        ('timeframe', [R(InpGbwTF=v) for v in (60, 240, 1440)]),
        ('bands', [R(InpShortBB=s, InpLongBB=l) for s in (10, 20, 30) for l in (40, 50, 100)]),
        ('deviation', [R(InpBBDeviation=v) for v in (1.5, 2.0, 2.5)]),
        ('signal', [R(InpSignalPeriod=v) for v in (5, 9, 14, 21)]),
        ('trend', [R(InpTrendPeriod=v) for v in (0, 100, 200)]),
        ('stop', [R(InpStopATR=v) for v in (1, 1.5, 2, 3, 4)]),
        ('target', [R(InpGbwTargetR=v) for v in (0, 1, 2, 3, 4, 6)]),
        ('exit', [R(InpGbwExitOnCross=v) for v in ('true', 'false')]),
        ('management', [R(InpGbwBreakEvenR=0, InpGbwTrailATR=0), R(InpGbwBreakEvenR=1)] + [R(InpGbwTrailATR=v) for v in (2, 3, 4)]),
        ('direction', [R(InpGbwDirection=v) for v in (0, 1, 2)])],
    NEIGHBOUR={'InpShortBB': (10, 20, 30), 'InpLongBB': (40, 50, 100), 'InpBBDeviation': (1.5, 2.0, 2.5), 'InpSignalPeriod': (5, 9, 14, 21), 'InpTrendPeriod': (0, 100, 200),
               'InpStopATR': (1, 1.5, 2, 3, 4), 'InpGbwTargetR': (1, 2, 3, 4, 6), 'InpGbwTrailATR': (2, 3, 4)})

if __name__ == '__main__':
    E.run_study(S)

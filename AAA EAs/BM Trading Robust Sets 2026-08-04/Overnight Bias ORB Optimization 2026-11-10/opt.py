"""Overnight Bias ORB optimisation (PLAN.md, frozen 2026-11-10 before results) on the shared engine (../research_opt_engine.py). Run from AAA EAs/EA store:  uv run python "<this>" """
import importlib.util
from pathlib import Path
from types import SimpleNamespace

H = Path(__file__).resolve().parent; PACKAGE = H.parent
spec = importlib.util.spec_from_file_location('engine', PACKAGE / 'research_opt_engine.py'); E = importlib.util.module_from_spec(spec); spec.loader.exec_module(E)
R = lambda **k: {a: str(v) for a, v in k.items()}  # noqa: E731
S = SimpleNamespace(
    H=H, EX5=H / 'EA/Overnight Bias ORB Research EA.ex5', SYM='USTEC', FIRST='2019-07-16', RAW=PACKAGE / 'Video ORB VWAP Ideas Raw 2026-11-09/native/nw-USTEC-ONB-all', RAW_END='2026-11-10',
    EXPERT_DIR='CalyxOnbOpt', MIN_TRADES=100, PERIOD=lambda c: 'M15',
    BASE=dict(InpStrategy='4', InpUseBias='true', InpRandomDirection='false', InpSeed='1', InpRiskPercent='1.0', InpServerUtcOffsetHours='0', InpMagic='91109001', InpDeviationPoints='50',
              InpOnbORMinutes='15', InpOnbOvernightStart='0', InpOnbBiasFrac='0.3333333333', InpOnbAdxMin='20', InpOnbStopMult='0.3', InpOnbTargetR='3', InpOnbEntryEnd='915', InpOnbFlatMin='930',
              InpOnbBreakEvenR='0', InpOnbTrailStartR='0', InpOnbTrailDistR='0.5', InpOnbDirection='2', InpOnbDayMask='31', InpOnbMaxTrades='1'),
    STAGES=[
        ('opening_range', [R(InpOnbORMinutes=v) for v in (15, 30, 45, 60)]),
        ('bias', [R(InpOnbBiasFrac=v) for v in (0.25, 0.3333333333, 0.4, 0.5)] + [R(InpUseBias='false')]),
        ('overnight_start', [R(InpOnbOvernightStart=v) for v in (0, 120, 240)]),
        ('adx', [R(InpOnbAdxMin=v) for v in (0, 15, 20, 25, 30)]),
        ('stop', [R(InpOnbStopMult=v) for v in (0.15, 0.2, 0.25, 0.3, 0.4, 0.5)]),
        ('target', [R(InpOnbTargetR=v) for v in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 0)]),
        ('management', [R(InpOnbBreakEvenR=0, InpOnbTrailStartR=0), R(InpOnbBreakEvenR=0.5), R(InpOnbBreakEvenR=1)] + [R(InpOnbTrailStartR=s, InpOnbTrailDistR=d) for s in (1, 1.5, 2) for d in (0.5, 1)]),
        ('entry_end', [R(InpOnbEntryEnd=v) for v in (720, 840, 900, 915)]),
        ('flat', [R(InpOnbFlatMin=v) for v in (900, 930, 955)]),
        ('direction', [R(InpOnbDirection=v) for v in (0, 1, 2)]),
        ('trades', [R(InpOnbMaxTrades=v) for v in (1, 2)]),
        ('weekdays', [R(InpOnbDayMask=v) for v in (31, 15, 30, 14)])],
    NEIGHBOUR={'InpOnbORMinutes': (15, 30, 45, 60), 'InpOnbBiasFrac': (0.25, 0.3333333333, 0.4, 0.5), 'InpOnbAdxMin': (0, 15, 20, 25, 30), 'InpOnbStopMult': (0.15, 0.2, 0.25, 0.3, 0.4, 0.5),
               'InpOnbTargetR': (1, 1.5, 2, 2.5, 3, 4, 5, 6), 'InpOnbEntryEnd': (720, 840, 900, 915), 'InpOnbFlatMin': (900, 930, 955), 'InpOnbTrailStartR': (1, 1.5, 2), 'InpOnbBreakEvenR': (0.5, 1)})

if __name__ == '__main__':
    E.run_study(S)

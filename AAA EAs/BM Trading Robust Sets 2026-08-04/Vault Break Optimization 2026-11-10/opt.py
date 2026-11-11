"""Vault Break optimisation (PLAN.md, frozen 2026-11-10 before results) on the shared engine (../research_opt_engine.py). Run from AAA EAs/EA store:  uv run python "<this>" """
import importlib.util, sys
from pathlib import Path
from types import SimpleNamespace

H = Path(__file__).resolve().parent; PACKAGE = H.parent
spec = importlib.util.spec_from_file_location('engine', PACKAGE / 'research_opt_engine.py'); E = importlib.util.module_from_spec(spec); spec.loader.exec_module(E)
R = lambda **k: {a: str(v) for a, v in k.items()}  # noqa: E731
S = SimpleNamespace(
    H=H, EX5=H / 'EA/Vault Break Research EA.ex5', SYM='USTEC', FIRST='2019-07-16', RAW=PACKAGE / 'Video ORB VWAP Ideas Raw 2026-11-09/native/nw-USTEC-VAULT-all', RAW_END='2026-11-10',
    EXPERT_DIR='CalyxVaultOpt', MIN_TRADES=100, PERIOD=lambda c: {'15': 'M15', '60': 'H1'}.get(str(int(float(c['InpVaultTF']))), 'M30'),
    BASE=dict(InpStrategy='2', InpUseBias='true', InpRandomDirection='false', InpSeed='1', InpRiskPercent='1.0', InpServerUtcOffsetHours='0', InpMagic='91109001', InpDeviationPoints='50',
              InpVaultTF='30', InpVaultAnchorMin='60', InpVaultBarrierAtr='0.3', InpVaultUseVwap='true', InpVaultEntryStart='660', InpVaultEntryEnd='900', InpVaultFlatMin='930', InpVaultMaxTrades='3',
              InpVaultStopMode='0', InpVaultStopPoints='75', InpVaultStopAtr='0.3', InpVaultTargetMode='0', InpVaultTargetPoints='40', InpVaultTargetR='1', InpVaultBreakEvenR='0', InpVaultTrailStartR='0',
              InpVaultTrailDistR='0.5', InpVaultDirection='0', InpVaultAdxMin='0', InpVaultDayMask='31'),
    STAGES=[
        ('timeframe', [R(InpVaultTF=v) for v in (15, 30, 60)]),
        ('direction', [R(InpVaultDirection=v) for v in (0, 1, 2)]),
        ('barrier', [R(InpVaultBarrierAtr=v) for v in (0.1, 0.2, 0.3, 0.4, 0.5)] + [R(InpVaultUseVwap='false')]),
        ('window', [R(InpVaultEntryStart=s, InpVaultEntryEnd=e) for s in (600, 630, 660, 720) for e in (840, 900, 915)]),
        ('stop', [R(InpVaultStopMode=0, InpVaultStopPoints=v) for v in (40, 60, 75, 100, 150)] + [R(InpVaultStopMode=1, InpVaultStopAtr=v) for v in (0.15, 0.2, 0.3, 0.4, 0.5)]),
        ('target', [R(InpVaultTargetMode=0, InpVaultTargetPoints=v) for v in (20, 30, 40, 60, 80)] + [R(InpVaultTargetMode=1, InpVaultTargetR=v) for v in (0.5, 1, 1.5, 2, 3, 4, 6)] + [R(InpVaultTargetMode=2)]),
        ('management', [R(InpVaultBreakEvenR=0, InpVaultTrailStartR=0), R(InpVaultBreakEvenR=0.5), R(InpVaultBreakEvenR=1)] + [R(InpVaultTrailStartR=s, InpVaultTrailDistR=d) for s in (1, 1.5, 2) for d in (0.5, 1)]),
        ('trades', [R(InpVaultMaxTrades=v) for v in (1, 2, 3, 5)]),
        ('flat', [R(InpVaultFlatMin=v) for v in (900, 930, 955)]),
        ('adx', [R(InpVaultAdxMin=v) for v in (0, 20, 25)]),
        ('weekdays', [R(InpVaultDayMask=v) for v in (31, 15, 30, 14)])],
    NEIGHBOUR={'InpVaultBarrierAtr': (0.1, 0.2, 0.3, 0.4, 0.5), 'InpVaultEntryStart': (600, 630, 660, 720), 'InpVaultEntryEnd': (840, 900, 915), 'InpVaultStopPoints': (40, 60, 75, 100, 150),
               'InpVaultStopAtr': (0.15, 0.2, 0.3, 0.4, 0.5), 'InpVaultTargetPoints': (20, 30, 40, 60, 80), 'InpVaultTargetR': (0.5, 1, 1.5, 2, 3, 4, 6), 'InpVaultMaxTrades': (1, 2, 3, 5),
               'InpVaultFlatMin': (900, 930, 955), 'InpVaultTrailStartR': (1, 1.5, 2), 'InpVaultBreakEvenR': (0.5, 1)})

if __name__ == '__main__':
    E.run_study(S)

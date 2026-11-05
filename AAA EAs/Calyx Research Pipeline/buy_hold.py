"""Buy-and-hold benchmark for every new EA idea (owner 2026-11-05: "for all new EA ideas always compare to just buying and holding").

Pipeline stage 3 / 4 / 6 (PIPELINE.md, policy block buy_hold_benchmark). Run the benchmark EA natively on the SAME asset, windows and deposit as the
strategy, then put both in the report:

    run(study_folder, symbol, windows)   native Model 4 runs of Benchmarks/Calyx Buy Hold Benchmark EA at 1x notional -> {window: row}
    compare(strategy, benchmark)         one comparison row: return, equity DD, return / DD, verdict

The EA holds the CFD with real spread, commission and swap. `price_return_pct` is the same position before commission and swap (gross), so a
result dragged down by CFD financing is visible. Long only: on an FX pair "buy and hold" is an arbitrary direction, and the report must say so.
It is a required comparison, not an automatic reject: the owner decides what a lag means, and a strategy that lags can still earn its place by
risking far less. A strategy with a higher return but also a much bigger drawdown has not beaten it, so both figures are always shown.
Run from AAA EAs/EA store when calling run(); compare() needs no MT5."""
from __future__ import annotations

import gzip
import html
import importlib.util
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
EA_SOURCE = HERE / 'Benchmarks' / 'Calyx Buy Hold Benchmark EA.mq5'
PACKAGE = HERE.parent / 'BM Trading Robust Sets 2026-08-04'
DEPOSIT = 10000.0
VARIANT = 'BUYHOLD'


def _ratio(ret: float | None, dd: float | None) -> float | None:
    return round(ret / dd, 2) if ret is not None and dd else None


def compare(strategy: dict, benchmark: dict) -> dict:
    """strategy / benchmark: dicts with return_pct and max_dd_pct (the same drawdown definition for both). Returns one report row."""
    sr, sd, br, bd = strategy['return_pct'], strategy['max_dd_pct'], benchmark['return_pct'], benchmark['max_dd_pct']
    beats_return, beats_ratio = sr > br, (_ratio(sr, sd) or 0) > (_ratio(br, bd) or 0)
    verdict = ('BEATS on return and return/DD' if beats_return and beats_ratio else 'BEATS on return only, at a worse return/DD' if beats_return
               else 'LAGS on return, better return/DD' if beats_ratio else 'LAGS on return and return/DD')
    return dict(strategy_return_pct=sr, strategy_dd_pct=sd, strategy_return_dd=_ratio(sr, sd), hold_return_pct=br, hold_dd_pct=bd,
                hold_return_dd=_ratio(br, bd), excess_return_pct=round(sr - br, 2), verdict=verdict)


def _harness(study: Path):
    os.environ['EA_STORE_DISABLE_MT5'] = '1'
    spec = importlib.util.spec_from_file_location('baseline', PACKAGE / 'No Wick Candle Raw 2026-09-25/run_nw.py')
    b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
    b.ROOT = study; b.OUT = study / 'buy-hold-native'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(parents=True, exist_ok=True)
    return b


def _compiled(b) -> Path:
    ex5 = EA_SOURCE.with_suffix('.ex5')
    if ex5.exists() and ex5.stat().st_mtime >= EA_SOURCE.stat().st_mtime: return ex5
    log = EA_SOURCE.with_suffix('.compile.log'); editor = PACKAGE / '_Backtests/MT5-DMC-20260811/MetaEditor64.exe'
    subprocess.run(f'"{editor}" /portable /compile:"{EA_SOURCE}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=120)
    raw = log.read_bytes(); text = raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')
    assert '0 errors, 0 warnings' in text, text[-2000:]
    return ex5


def run(study: Path | str, symbol: str, windows: dict[str, tuple[str, str]], period: str = 'H1') -> dict:
    """windows: {name: (start, end_exclusive)} as ISO dates. Requires the isolated tester to be free."""
    study = Path(study); b = _harness(study); assert not b.isolated_running(), 'Tester is occupied'
    dest = b.TESTER / 'MQL5/Experts/CalyxBuyHold'; dest.mkdir(parents=True, exist_ok=True); shutil.copy2(_compiled(b), dest / 'buy-hold.ex5')
    dot = lambda s: s.replace('-', '.')  # noqa: E731
    b.CONFIG.update(periods={k: dot(a) for k, (a, _) in windows.items()}, deposit=int(DEPOSIT), currency='USD', model=4, execution_delay_ms=150, profile='Calyx Research Empty',
                    timeout_seconds=14400, expert_dir='CalyxBuyHold', expert_file='buy-hold.ex5', controls={}, period=period, common_inputs={'InpNotionalMultiple': '1.0', 'InpMagic': '99000001'},
                    variants={VARIANT: {'label': f'{symbol} buy and hold', 'inputs': {}}})
    out = {}
    for name, (_, end) in windows.items():
        b.CONFIG['end_date'] = dot(end)
        for attempt in range(4):                         # the tester agent can time out at startup when the CPU is busy; a failed run leaves no ok receipt
            try:
                b.run_case(symbol, VARIANT, name); break
            except SystemExit:
                if attempt == 3: raise
                time.sleep(60)
        out[name] = load(study, symbol, name)
    return out


def load(study: Path | str, symbol: str, window: str) -> dict:
    d = Path(study) / 'buy-hold-native' / f'nw-{symbol}-{VARIANT}-{window}'
    T = json.loads(gzip.open(d / 'trades.json.gz').read())
    spec = re.search(r'BUYHOLD_SPEC symbol=\S+ lots=([\d.]+) lot_notional=([\d.]+) equity=([\d.]+)', gzip.open(d / 'journal.txt.gz').read().decode('utf-8', 'replace'))
    assert spec and len(T) == 1, f'{d.name}: benchmark did not open exactly one position'
    notional = float(spec[1]) * float(spec[2]) / float(spec[3])
    assert 0.8 <= notional <= 1.2, f'{d.name}: position is {notional:.2f}x notional, expected about 1x'
    net, gross = sum(t['net_profit'] for t in T), sum(t['gross_profit'] for t in T)
    return dict(symbol=symbol, window=window, return_pct=round(100 * net / DEPOSIT, 2), price_return_pct=round(100 * gross / DEPOSIT, 2), swap_pct=round(100 * sum(t['swap'] for t in T) / DEPOSIT, 2),
                commission_pct=round(100 * sum(t['commission'] for t in T) / DEPOSIT, 2), max_dd_pct=relative_equity_dd(d / f'{d.name}.htm.gz'), trades=len(T))


def relative_equity_dd(report_gz: Path) -> float | None:
    """MT5 'Equity Drawdown Relative' (the largest % drawdown). The parser's max_drawdown_pct is the 'Maximal' figure, which understates it."""
    h = gzip.decompress(Path(report_gz).read_bytes()); s = h.decode('utf-16') if h[:2] in (b'\xff\xfe', b'\xfe\xff') else h.decode('utf-8', 'ignore')
    m = re.search(r'Equity Drawdown Relative:?\s*([\d.]+)%', html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s))))
    return float(m[1]) if m else None

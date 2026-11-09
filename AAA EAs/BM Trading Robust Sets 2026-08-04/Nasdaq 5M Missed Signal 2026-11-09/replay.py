"""Owner 2026-11-09: why did the Nasdaq 5M not trade today (Monday 2026-11-09)? The Friday trade was held over the weekend and closed near breakeven.
Replays the production EX5 with the canonical SET and DI OFF (owner setting), native Model 4, $10k, 1%, 2026-11-02 -> 2026-11-10 (data to the latest the tester
has). Prints every trade and every N5EMA journal line, so we can see whether a 09:30 NY signal existed today and what blocked it.
Run from AAA EAs/EA store: uv run python "<this>" """
import gzip, hashlib, importlib.util, json, re, shutil, sys, time
import os
os.environ['EA_STORE_DISABLE_MT5'] = '1'
from pathlib import Path

H = Path(__file__).resolve().parent; PACKAGE = H.parent
EX5 = PACKAGE / 'Nasdaq 5M DI ATR Deployment 2026-09-28/EA/Nasdaq 5M DI Wide ATR EA.ex5'
SET = PACKAGE / 'Selected Portfolio Settings 2026-09-01/11 Nasdaq 5M - DI ATR6 STOP ATR6 TRAIL NO TP - 1PCT.set'


def main():
    assert hashlib.sha256(EX5.read_bytes()).hexdigest().startswith('fe9f391db5af'), 'not the production EX5'
    spec = importlib.util.spec_from_file_location('baseline', PACKAGE / 'No Wick Candle Raw 2026-09-25/run_nw.py'); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
    b.ROOT = H; b.OUT = H / 'native'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True); assert not b.isolated_running(), 'Tester is occupied'
    raw = SET.read_bytes(); text = raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')
    inputs = {k.strip(): v.strip().split('||')[0] for k, v in (l.split('=', 1) for l in text.splitlines() if '=' in l and not l.startswith(';'))}
    inputs.update(InpRequireDIAgreement='false', InpRiskPercent='1.0', InpAdaptivePortfolioControls='false')
    dest = b.TESTER / 'MQL5/Experts/CalyxMissed'; dest.mkdir(parents=True, exist_ok=True); shutil.copy2(EX5, dest / 'nas5m.ex5')
    b.CONFIG.update(periods={'week': '2026.11.02'}, end_date='2026.11.10', deposit=10000, currency='USD', model=4, execution_delay_ms=150, profile='Calyx Research Empty', timeout_seconds=3600,
                    expert_dir='CalyxMissed', expert_file='nas5m.ex5', controls={}, variants={'DIOFF': {'label': 'DIOFF', 'inputs': {}}}, common_inputs=inputs, period='M5')
    started = time.time(); meta = None
    for attempt in range(4):
        try:
            meta = b.run_case('USTEC', 'DIOFF', 'week'); break
        except SystemExit:
            time.sleep(60)
    d = b.OUT / 'nw-USTEC-DIOFF-week'
    T = json.loads(gzip.open(d / 'trades.json.gz').read()) if (d / 'trades.json.gz').exists() else []
    print('RUN', 'ok' if meta and meta.get('ok') else 'FAILED')
    for t in T: print('TRADE', t['side'], t['open_time'], '->', t['close_time'], 'open', t['open_price'], 'close', t['close_price'], 'net', round(t['net_profit'], 2), '|', t.get('entry_comment'), '|', t.get('exit_comment'))
    lines = []
    for log in b.log_files():
        if log.stat().st_mtime < started - 5: continue
        raw = log.read_bytes(); s = raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8', errors='replace')
        lines += [l for l in s.splitlines() if re.search(r'N5EMA|2026\.11\.09 1[3-6]:|position|order|deal|stop loss|history|last bar|real ticks', l, re.I)]
    (H / 'JOURNAL.txt').write_text('\n'.join(lines), encoding='utf-8'); print('journal lines', len(lines))
    for l in [l for l in lines if 'N5EMA' in l or 'deal' in l.lower()][-40:]: print('LOG', l[-220:])


if __name__ == '__main__':
    main()

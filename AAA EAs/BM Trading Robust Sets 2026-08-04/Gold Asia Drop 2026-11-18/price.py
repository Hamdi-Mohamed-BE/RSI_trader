"""Owner 2026-11-18: "today gold fell like 2% during the Asia session, which EA would have caught it". Read-only: XAUUSD M15 bars 2026-11-16 -> now from the
ISOLATED research terminal (_Backtests/MT5-DMC-20260811, portable; server time = UTC). The terminal is shut down afterwards. Output PRICE.json."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import MetaTrader5 as mt5

H = Path(__file__).resolve().parent; TERM = H.parent / '_Backtests/MT5-DMC-20260811/terminal64.exe'
assert mt5.initialize(path=str(TERM), portable=True, timeout=120000), mt5.last_error()
try:
    info = mt5.terminal_info(); assert info and 'MT5-DMC-20260811' in info.path
    mt5.symbol_select('XAUUSD', True)
    r = mt5.copy_rates_range('XAUUSD', mt5.TIMEFRAME_M15, datetime(2026, 11, 16, tzinfo=timezone.utc), datetime.now(timezone.utc) + timedelta(hours=1))
    assert r is not None and len(r), mt5.last_error()
    bars = [dict(t=datetime.fromtimestamp(int(x['time']), timezone.utc).strftime('%Y-%m-%d %H:%M'), o=float(x['open']), h=float(x['high']), l=float(x['low']), c=float(x['close'])) for x in r]
    tick = mt5.symbol_info_tick('XAUUSD')
finally:
    mt5.shutdown()
day = [b for b in bars if b['t'].startswith('2026-11-18')]; prev = [b for b in bars if b['t'].startswith('2026-11-17')]
asia = [b for b in day if b['t'][11:] < '08:00']
out = dict(last_bar=bars[-1]['t'], prev_close=prev[-1]['c'] if prev else None, day_open=day[0]['o'] if day else None,
           asia_high=max(b['h'] for b in asia) if asia else None, asia_low=min(b['l'] for b in asia) if asia else None,
           asia_close=asia[-1]['c'] if asia else None, day_high=max(b['h'] for b in day) if day else None, day_low=min(b['l'] for b in day) if day else None, last=day[-1]['c'] if day else None)
if asia:
    hi = max(asia, key=lambda b: b['h']); lo = min(asia, key=lambda b: b['l'])
    out.update(asia_high_time=hi['t'], asia_low_time=lo['t'], asia_drop_pct=round(100 * (lo['l'] / hi['h'] - 1), 2), open_to_asia_low_pct=round(100 * (lo['l'] / day[0]['o'] - 1), 2))
out['hourly'] = [dict(hour=b['t'], o=b['o'], h=b['h'], l=b['l'], c=b['c']) for b in day if b['t'].endswith(':00')]
(H / 'PRICE.json').write_text(json.dumps(dict(summary=out, bars=bars), indent=1), encoding='utf-8')
print(json.dumps(out, indent=1))

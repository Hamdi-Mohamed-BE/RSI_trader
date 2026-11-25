"""Owner 2026-11-24: "I have connected an FTMO account, compare its results for the last 2 months to Exness, and rerun the full simulation pass rate".
READ-ONLY export from the owner's running FTMO terminal (C:\\Program Files\\MetaTrader 5, FTMO-Server4): copy_ticks_range / copy_rates_range only,
no orders, no settings. FTMO server clock = UTC+3 while the US is on DST, else UTC+2 (v2; v1 wrongly used the EU dates). All times are converted to UTC
so the isolated research terminal (server = UTC) sees the same wall clock as the Exness data.
Output (binary, little endian) in %APPDATA%\\MetaQuotes\\Terminal\\Common\\Files\\CalyxFTMO\\:
  <SYM>_ticks.bin : int64 time_msc_utc, double bid, double ask   (24 bytes per tick; consecutive duplicates dropped)
  <SYM>_m1.bin    : int64 time_utc, double open, high, low, close, int64 tick_volume, int32 spread   (60 bytes per bar)
python export_ftmo.py ticks <start> <end>   |   python export_ftmo.py bars <start> <end>   (dates YYYY-MM-DD, UTC)"""
import os, struct, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import MetaTrader5 as mt5
import numpy as np

TERM = r'C:\Program Files\MetaTrader 5\terminal64.exe'
SYMS = {'US100.cash': 'US100', 'XAUUSD': 'XAUUSD', 'USDJPY': 'USDJPY', 'UK100.cash': 'UK100'}
OUT = Path(os.environ['APPDATA']) / 'MetaQuotes/Terminal/Common/Files/CalyxFTMO'
SWITCH = int(datetime(2026, 11, 1, 6, tzinfo=timezone.utc).timestamp())   # US DST end 2026 (server +3 -> +2), v2 2026-11-24


def eet_offset(utc_s):
    """FTMO server offset (hours) at a UTC instant. v2 2026-11-24: the server follows US DST (UTC+3 from the 2nd Sunday of March 07:00 UTC to the 1st Sunday of
    November 06:00 UTC, else UTC+2 = New York + 7 h). v1 used the EU rule and was 1 h off in 19 weeks of 2021-2026 (clock_check.py, CLOCK_CHECK.json)."""
    y = datetime.fromtimestamp(utc_s, timezone.utc).year
    def nth_sun(m, n):
        d = datetime(y, m, 1, tzinfo=timezone.utc)
        while d.weekday() != 6: d += timedelta(days=1)
        return d + timedelta(days=7 * (n - 1))
    on = int((nth_sun(3, 2) + timedelta(hours=7)).timestamp()); off = int((nth_sun(11, 1) + timedelta(hours=6)).timestamp())
    return 3 if on <= utc_s < off else 2


def to_utc(server_s):
    """server seconds -> UTC seconds (try +3 then +2 consistently)."""
    s = np.asarray(server_s, dtype=np.int64)
    u3 = s - 3 * 3600
    off = np.array([eet_offset(int(x)) for x in u3]) if s.size < 5000 else np.vectorize(eet_offset)(u3)
    return s - off * 3600


def init():
    assert mt5.initialize(path=TERM, timeout=60000), mt5.last_error()
    a = mt5.account_info(); assert a and a.server.startswith('FTMO'), 'not the FTMO terminal'
    OUT.mkdir(parents=True, exist_ok=True)


def ticks(start, end):
    init()
    try:
        for s, n in SYMS.items():
            mt5.symbol_select(s, True); total = 0; prev = None
            with open(OUT / f'{n}_ticks.bin', 'wb') as f:
                d = start
                while d < end:
                    a = d - timedelta(hours=3); b = d + timedelta(days=1) + timedelta(hours=3)   # server-time window around the UTC day
                    t = None
                    for _ in range(10):
                        t = mt5.copy_ticks_range(s, a, b, mt5.COPY_TICKS_ALL)
                        if t is not None: break
                        time.sleep(1)
                    if t is not None and len(t):
                        ms = t['time_msc'].astype(np.int64); sec = ms // 1000
                        utc_ms = ms - np.where(sec - 3 * 3600 >= SWITCH, 2, 3).astype(np.int64) * 3600 * 1000   # 2026 window only (Sep-Nov)
                        assert d.year == 2026 and d.month >= 4
                        lo, hi = int(d.timestamp() * 1000), int((d + timedelta(days=1)).timestamp() * 1000)
                        k = (utc_ms >= lo) & (utc_ms < hi) & (t['bid'] > 0) & (t['ask'] > 0)
                        utc_ms, bid, ask = utc_ms[k], t['bid'][k], t['ask'][k]
                        o = np.argsort(utc_ms, kind='stable'); utc_ms, bid, ask = utc_ms[o], bid[o], ask[o]
                        keep = np.ones(len(bid), bool); keep[1:] = (bid[1:] != bid[:-1]) | (ask[1:] != ask[:-1])
                        if prev is not None and len(keep): keep[0] = (bid[0], ask[0]) != prev
                        rec = np.zeros(int(keep.sum()), dtype=[('t', '<i8'), ('b', '<f8'), ('a', '<f8')])
                        rec['t'], rec['b'], rec['a'] = utc_ms[keep], bid[keep], ask[keep]
                        f.write(rec.tobytes()); total += len(rec)
                        if len(rec): prev = (rec['b'][-1], rec['a'][-1])
                    d += timedelta(days=1)
            print(n, 'ticks', total, flush=True)
    finally:
        mt5.shutdown()


def bars(start, end):
    init()
    try:
        for s, n in SYMS.items():
            mt5.symbol_select(s, True); r = None
            for _ in range(10):
                r = mt5.copy_rates_range(s, mt5.TIMEFRAME_M1, start - timedelta(hours=3), end + timedelta(hours=3))
                if r is not None and len(r): break
                time.sleep(2)
            tu = to_utc(r['time'].astype(np.int64)); k = (tu >= int(start.timestamp())) & (tu < int(end.timestamp()))
            rec = np.zeros(int(k.sum()), dtype=[('t', '<i8'), ('o', '<f8'), ('h', '<f8'), ('l', '<f8'), ('c', '<f8'), ('v', '<i8'), ('s', '<i4')])
            rec['t'] = tu[k]; rec['o'] = r['open'][k]; rec['h'] = r['high'][k]; rec['l'] = r['low'][k]; rec['c'] = r['close'][k]
            rec['v'] = r['tick_volume'][k]; rec['s'] = r['spread'][k]
            (OUT / f'{n}_m1.bin').write_bytes(rec.tobytes())
            print(n, 'M1 bars', len(rec), datetime.fromtimestamp(int(rec['t'][0]), timezone.utc), '->', datetime.fromtimestamp(int(rec['t'][-1]), timezone.utc), flush=True)
    finally:
        mt5.shutdown()


if __name__ == '__main__':
    a = datetime.fromisoformat(sys.argv[2]).replace(tzinfo=timezone.utc); b = datetime.fromisoformat(sys.argv[3]).replace(tzinfo=timezone.utc)
    {'ticks': ticks, 'bars': bars}[sys.argv[1]](a, b)

"""Public market-data download only. Does not import MT5 or use private keys."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import hashlib
import io
import json
import time
import zipfile
import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'Data'
DATA.mkdir(exist_ok=True)
BASE = 'https://data.binance.vision/data/spot'
START = pd.Timestamp('2025-03-31', tz='UTC')
END = pd.Timestamp('2026-10-02', tz='UTC')


def fetch(kind, stamp):
    name = f'BTCUSDT-1m-{stamp}.zip'
    url = f'{BASE}/{kind}/klines/BTCUSDT/1m/{name}'
    p = DATA / name
    for attempt in range(3):
        try:
            checksum = requests.get(url + '.CHECKSUM', timeout=30)
            if checksum.status_code == 404:
                return None
            checksum.raise_for_status()
            expected = checksum.text.split()[0]
            if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != expected:
                r = requests.get(url, timeout=60)
                r.raise_for_status()
                assert hashlib.sha256(r.content).hexdigest() == expected, 'Checksum mismatch'
                p.write_bytes(r.content)
            with zipfile.ZipFile(p) as z:
                names = z.namelist()
                assert len(names) == 1
                raw = z.read(names[0])
            frame = pd.read_csv(io.BytesIO(raw), header=None)
            assert frame.shape[1] == 12
            ts = pd.to_numeric(frame[0], errors='raise')
            unit = 'us' if ts.median() > 10**14 else 'ms'
            frame = frame[[0, 1, 2, 3, 4, 5, 8]].copy()
            frame.columns = ['time', 'open', 'high', 'low', 'close', 'volume', 'trades']
            frame['time'] = pd.to_datetime(ts, unit=unit, utc=True)
            info = dict(url=url, sha256=expected, checksum_verified=True, rows=len(frame),
                        timestamp_unit=unit, first=str(frame.time.min()), last=str(frame.time.max()))
            return frame, info
        except Exception:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def main():
    jobs = [('daily', '2025-03-31')]
    for month in pd.date_range('2025-04-01', '2026-09-01', freq='MS'):
        jobs.append(('monthly', month.strftime('%Y-%m')))
    frames, sources = [], []
    missing = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        tasks = {pool.submit(fetch, *job): job for job in jobs}
        for task in as_completed(tasks):
            job = tasks[task]
            result = task.result()
            if result is None:
                missing.append(job)
                print('MONTH NOT PUBLISHED', job, flush=True)
            else:
                frames.append(result[0]); sources.append(result[1])
                print('VERIFIED', job, len(result[0]), flush=True)
    daily = [('daily', '2026-10-01')]
    for kind, stamp in missing:
        assert kind == 'monthly'
        begin = pd.Timestamp(stamp + '-01')
        last = begin + pd.offsets.MonthEnd(0)
        daily.extend(('daily', d.strftime('%Y-%m-%d')) for d in pd.date_range(begin, last))
    with ThreadPoolExecutor(max_workers=6) as pool:
        tasks = {pool.submit(fetch, *job): job for job in daily}
        for task in as_completed(tasks):
            job = tasks[task]
            result = task.result()
            assert result is not None, f'Missing daily archive: {job}'
            frames.append(result[0]); sources.append(result[1])
            print('VERIFIED', job, len(result[0]), flush=True)
    frame = pd.concat(frames, ignore_index=True).sort_values('time')
    frame = frame[(frame.time >= START) & (frame.time < END)].reset_index(drop=True)
    assert not frame.time.duplicated().any(), 'Duplicate bar timestamps'
    assert (frame.close > 0).all() and (frame.low > 0).all()
    assert (frame.high >= frame[['open', 'close', 'low']].max(axis=1)).all()
    assert (frame.low <= frame[['open', 'close', 'high']].min(axis=1)).all()
    grid = pd.date_range(START, END, freq='min', inclusive='left')
    missing_times = grid.difference(pd.DatetimeIndex(frame.time))
    # pandas can retain datetime64[us]; do not assume its integer storage is ns.
    off_grid = frame.time[(frame.time.dt.second != 0) | (frame.time.dt.microsecond != 0)]
    assert len(off_grid) == 0
    np.savez_compressed(DATA / 'BTCUSDT-1m.npz',
                        time=frame.time.dt.tz_localize(None).to_numpy(dtype='datetime64[ns]').astype('int64'),
                        **{col:frame[col].to_numpy() for col in frame.columns if col!='time'})
    manifest = dict(instrument='Binance spot BTCUSDT', interval='1m', timezone='UTC',
                    start=str(START), end_exclusive=str(END), rows=len(frame),
                    expected_rows=len(grid), missing_count=len(missing_times),
                    missing_times=[str(t) for t in missing_times],
                    data_sha256=hashlib.sha256((DATA / 'BTCUSDT-1m.npz').read_bytes()).hexdigest(),
                    archives=sorted(sources, key=lambda s:s['first']))
    (ROOT / 'DATA MANIFEST.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('DATA READY', len(frame), 'missing', len(missing_times), flush=True)


if __name__ == '__main__':
    main()

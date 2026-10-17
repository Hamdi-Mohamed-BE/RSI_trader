import hashlib
import json
import os
from pathlib import Path

os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'
import numpy as np
import pandas as pd
import torch
from chronos import Chronos2Pipeline

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'AAA Final/XAU weakness/data/XAUUSD.._M15_1000d.csv'
REVISION = '29ec3766d36d6f73f0696f85560a422f50e8498c'


def stats(frame):
    p = frame.net.to_numpy()
    equity = np.r_[0., p.cumsum()]
    return dict(trades=len(p), win_rate=float(np.mean(p > 0)) if len(p) else None,
                pf=float(p[p > 0].sum() / -p[p < 0].sum()) if np.any(p < 0) else None,
                net_usd_per_oz=float(p.sum()), mean=float(p.mean()) if len(p) else None,
                realized_dd_usd_per_oz=float(np.max(np.maximum.accumulate(equity)-equity)))


def score(frame, direction):
    out = frame.copy()
    out['side'] = direction
    spread = np.where(out.side > 0, out.entry_spread, out.exit_spread)
    out['net'] = out.side * (out.exit - out.entry) - spread - .27
    return out


def main():
    torch.set_num_threads(4)
    torch.manual_seed(42)
    df = pd.read_csv(SOURCE)
    df['time'] = pd.to_datetime(df.time, utc=True)
    assert df.time.is_monotonic_increasing and not df.time.duplicated().any()
    assert np.isfinite(df[['open', 'high', 'low', 'close', 'spread']]).all().all()
    assert (df.high >= df[['open', 'close', 'low']].max(axis=1)).all()
    close = df.close.to_numpy(dtype=np.float32)
    indices = [i for i in range(255, len(df)-4)
               if pd.Timestamp('2026-02-01', tz='UTC') <= df.time.iloc[i+1] < pd.Timestamp('2026-08-01', tz='UTC')
               and df.time.iloc[i+1].minute == 0
               and (df.time.iloc[i:i+5].diff().dropna() == pd.Timedelta(minutes=15)).all()]
    manifest = {'source': str(SOURCE), 'sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                'bars': len(df), 'origins': len(indices), 'model': 'amazon/chronos-2',
                'revision': REVISION, 'context': 256, 'validation_end': '2026-05-01', 'test_end': '2026-08-01'}
    if (ROOT/'forecasts.csv').exists():
        assert json.loads((ROOT/'manifest.json').read_text()) == manifest, 'Forecast cache differs from protocol/source'
    (ROOT/'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest), flush=True)
    cache = ROOT/'forecasts.csv'
    if not cache.exists():
        pipe = Chronos2Pipeline.from_pretrained('amazon/chronos-2', revision=REVISION, device_map='cpu')
        print('Model loaded', flush=True)
        rows = []
        for start in range(0, len(indices), 32):
            ids = indices[start:start+32]
            context = torch.tensor(np.stack([close[i-255:i+1] for i in ids]))[:, None, :]
            with torch.inference_mode():
                quantiles, _ = pipe.predict_quantiles(context, prediction_length=4,
                                                     quantile_levels=[.1, .5, .9], cross_learning=False)
            for j, i in enumerate(ids):
                assert len(quantiles) == len(ids) and quantiles[j].shape == (1, 4, 3)
                q = quantiles[j].cpu().numpy().reshape(4, 3)
                assert np.isfinite(q).all()
                for h in (1, 2, 4):
                    rows.append(dict(time=str(df.time.iloc[i+1]), horizon=h*15,
                                     last=float(close[i]), actual=float(close[i+h]),
                                     low=float(q[h-1,0]), median=float(q[h-1,1]), high=float(q[h-1,2]),
                                     entry=float(df.open.iloc[i+1]), exit=float(close[i+h]),
                                     entry_spread=float(df.spread.iloc[i+1])*.01,
                                     exit_spread=float(df.spread.iloc[i+h])*.01,
                                     momentum=float(close[i]-close[i-1])))
            if start % 320 == 0:
                print(f'Forecasted {start+len(ids)}/{len(indices)} origins', flush=True)
        pd.DataFrame(rows).to_csv(cache, index=False)
    forecasts = pd.read_csv(cache)
    forecasts['time'] = pd.to_datetime(forecasts.time, utc=True)
    forecasts['strength'] = abs(forecasts['median']-forecasts['last']) / (forecasts.high-forecasts.low).clip(lower=.001)
    val = forecasts[forecasts.time < '2026-05-01']
    test = forecasts[forecasts.time >= '2026-05-01']
    candidates = []
    for h in (15, 30, 60):
        for threshold in (0., .1, .25, .5):
            f = val[(val.horizon == h) & (val.strength >= threshold)]
            f = score(f, np.sign(f['median']-f['last']))
            f = f[f.side != 0]
            candidates.append(dict(horizon=h, threshold=threshold, **stats(f)))
    eligible = [x for x in candidates if x['trades'] >= 100]
    chosen = max(eligible, key=lambda x: x['mean'])
    results = {'validation_candidates': candidates, 'frozen_choice': chosen, 'test': []}
    for h in (15, 30, 60):
        f = test[test.horizon == h]
        delta = f.actual-f['last']
        for name, direction in [('Chronos', np.sign(f['median']-f['last'])),
                                ('Always long', np.ones(len(f))), ('Momentum', np.sign(f.momentum)),
                                ('Mean reversion', -np.sign(f.momentum))]:
            scored = score(f, direction)
            scored = scored[scored.side != 0]
            results['test'].append(dict(model=name, horizon=h,
                direction_accuracy=float(np.mean(direction[delta != 0] == np.sign(delta[delta != 0]))), **stats(scored)))
        results.setdefault('forecast_quality', []).append(dict(horizon=h,
            mae=float(abs(f['median']-f.actual).mean()), naive_mae=float(abs(delta).mean()),
            interval_coverage=float(((f.actual >= f.low) & (f.actual <= f.high)).mean())))
    f = test[(test.horizon == chosen['horizon']) & (test.strength >= chosen['threshold'])]
    f = score(f, np.sign(f['median']-f['last']))
    f = f[f.side != 0]
    f.to_csv(ROOT/'heldout_trades.csv', index=False)
    results['selected_test'] = stats(f)
    results['selected_test']['coverage'] = len(f)/len(test[test.horizon == chosen['horizon']])
    results['monthly'] = {str(month): stats(g) for month, g in f.groupby(f.time.dt.strftime('%Y-%m'))}
    stressed = f.copy()
    stressed['net'] -= .50
    results['cost_stress'] = stats(stressed)
    daily = f.groupby(f.time.dt.date).net.agg(['sum', 'count']).to_numpy()
    rng = np.random.default_rng(42)
    samples = daily[rng.integers(0, len(daily), (3000, len(daily)))].sum(axis=1)
    results['mean_net_day_bootstrap_95pct'] = np.quantile(samples[:,0]/samples[:,1], [.025,.975]).tolist()
    (ROOT/'results.json').write_text(json.dumps(results, indent=2))
    lines = ['CHRONOS-2 GOLD M15 PILOT', 'Held-out: May-July 2026; validation: February-April 2026',
             'Fixed one-ounce exposure. Costs are bar-spread proxies plus $0.27/oz round trip.',
             'Not a live fill simulation. No account balance or margin assumptions.', '',
             'Unfiltered held-out comparisons:',
             pd.DataFrame(results['test']).to_string(index=False), '', 'Forecast accuracy:',
             pd.DataFrame(results['forecast_quality']).to_string(index=False), '',
             'Rule chosen using validation only:', json.dumps(chosen, indent=2),
             'Held-out selected rule:', json.dumps(results['selected_test'], indent=2),
             'Monthly:', json.dumps(results['monthly'], indent=2),
             'Additional $0.50/oz cost stress:', json.dumps(results['cost_stress'], indent=2),
             '95% day-block bootstrap interval for mean net P/L per trade:',
             str(results['mean_net_day_bootstrap_95pct']), '',
             'Limits: one broker archive, three test months, hourly origins on M15 bars,',
             'compressed overnight/weekend history, unverified archive timezone, estimated costs,',
             'no event-specific attribution, no assurance of exclusion from pretraining data.']
    (ROOT/'REPORT.txt').write_text('\n'.join(lines))
    print(json.dumps(results, indent=2), flush=True)


if __name__ == '__main__':
    main()

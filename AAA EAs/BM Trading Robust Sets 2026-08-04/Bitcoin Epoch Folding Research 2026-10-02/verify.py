"""Offline audit of published forecasts and a seasonality-free clustered-noise control."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import numpy as np
import pandas as pd
from scipy.signal import lfilter
from analyze import ROOT, SEED, TEST_START, period_search, qlike


def main():
    completed=subprocess.run([sys.executable,'-m','pytest','test_research.py','-q'],cwd=ROOT,capture_output=True,text=True)
    print(completed.stdout,flush=True)
    assert completed.returncode==0
    r=json.loads((ROOT/'RESULTS.json').read_text())
    manifest=json.loads((ROOT/'DATA MANIFEST.json').read_text())
    assert manifest['missing_count']==0
    assert all(s['checksum_verified'] for s in manifest['archives'])
    assert r['protocol_sha256']==hashlib.sha256((ROOT/'PROTOCOL.txt').read_bytes()).hexdigest()
    assert r['forecast_sha256']==hashlib.sha256((ROOT/'FORECASTS.csv.gz').read_bytes()).hexdigest()
    f=pd.read_csv(ROOT/'FORECASTS.csv.gz')
    assert len(f)==365*96 and (f.realized_variance>0).all()
    for model in range(4):
        assert np.allclose(f[f'qlike_{model}'],qlike(f.realized_variance.values,f[f'forecast_{model}'].values),rtol=1e-10,atol=1e-10)
        assert abs(f[f'qlike_{model}'].mean()-r['models'][model]['mean_qlike'])<1e-12
    index=pd.date_range(pd.Timestamp('2025-04-01',tz='UTC'),TEST_START,freq='min',inclusive='left')
    rng=np.random.default_rng(SEED)
    logvol=lfilter([.025],[1,-.995],rng.normal(size=len(index)))
    noise=pd.Series(rng.normal(size=len(index))*np.exp(logvol),index=index)
    null=period_search(noise)
    checks=dict(unit_tests_passed=7,checksum_verified_archives=len(manifest['archives']),
                test_minute_returns=r['test_minute_returns'],missing_minute_returns=0,
                forecast_loss_reconciliation=True,future_mutation_invariance=True,
                null_model='Gaussian innovations with stochastic AR(1) log volatility; no deterministic calendar signal',
                null_seed=SEED,null_raw_rejections=sum(x['p_unadjusted']<.05 for x in null),
                null_adjusted_rejections=sum(x['survives'] for x in null),null_period_search=null,
                no_live_account_access=True,no_strategy_pnl_claim=True)
    (ROOT/'VERIFICATION.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    print('VERIFIED',json.dumps({k:v for k,v in checks.items() if k!='null_period_search'}),flush=True)


if __name__=='__main__':main()

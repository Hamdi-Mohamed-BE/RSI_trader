"""Offline release of explicitly selected targets. Does not open any MT5 terminal.

Preserves historical source/SETs; only copies and changes the target default.
Research evidence remains labelled standalone, not a guarded FTMO simulation.
"""
from pathlib import Path
import csv, gzip, hashlib, io, json, os, re, shutil, subprocess, sys
from datetime import datetime, timezone, date, timedelta

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
STORE = BASE.parent / 'EA store'
RESEARCH = BASE / 'Gold Target Sensitivity 2026-10-02'
TESTER = BASE / '_Backtests/MT5-DMC-20260811'
SPECS = {
    'xau-trend-progression': ('T', '0.6', 'Trend Progression Research 2026-09-02/EA/Trend Progression EA.mq5',
                              'Trend Progression Research 2026-09-02/Sets/TrendProgression-xauusd--h4--optimized--locked.set'),
    'xau-slow-trend': ('S', '1', 'Slow Multi Asset Trend Research 2026-09-06/EA/Calyx Slow Trend EA.mq5',
                     'Selected Portfolio Settings 2026-09-01/17 XAU Slow Trend H4 - LOCKED 6R - HARD 1PCT.set'),
}

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2), encoding='utf-8')
def read(p):
    raw=p.read_bytes()
    return raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig').replace('\r\n','\n')
def inputs(p): return dict(l.split('=',1) for l in read(p).splitlines() if '=' in l and not l.startswith(';'))
def backup(p):
    dest=ROOT/'before'/p.relative_to(BASE.parent)
    if dest.exists() or not p.exists(): return
    dest.parent.mkdir(parents=True, exist_ok=True)
    if p.is_dir(): shutil.copytree(p,dest)
    else: shutil.copy2(p,dest)

def prepare():
    for p in [BASE/'_Auto Deploy/Install-BMTradingPortfolio.ps1',
              BASE/'FTMO Thirteen EA Deployment 2026-09-27/package',
              BASE/'FTMO Thirteen EA Deployment 2026-09-27/PACKAGE.json',
              STORE/'app/catalog.py', STORE/'data/evidence-cache/v1/portfolio',
              STORE/'data/evidence-cache/v1/manifest.json', STORE/'data/portfolio-consistency-audit.json']:
        backup(p)
    manifest={'version':'GOLD-TARGETS-20261002', 'selection':'Explicit user choice; failed strict cross-window PF screen',
              'live_terminal_changed':False, 'profiles':{}, 'research_root':str(RESEARCH.relative_to(BASE))}
    for slug,(kind,rr,src,settings) in SPECS.items():
        backup(STORE/f'data/evidence-cache/v1/products/{slug}')
        backup(STORE/f'data/evidence-cache/v1/source-runs/{slug}')
        source=BASE/src; dest=ROOT/'EA'/source.name; dest.parent.mkdir(exist_ok=True)
        text,n=re.subn(r'(input\s+double\s+InpRewardRisk\s*=\s*)[\d.]+',r'\g<1>'+rr,read(source))
        assert n==1,source
        dest.write_text(text,encoding='utf-8')
        # Preserve the exact recommended settings, including management and magic.
        values=inputs(BASE/settings); values['InpRewardRisk']=rr; values['InpTesterOnly']='false' if 'InpTesterOnly' in values else values.get('InpTesterOnly','')
        if values.get('InpTesterOnly')=='': values.pop('InpTesterOnly',None)
        setpath=ROOT/'Sets'/(slug+'-normal.set'); setpath.parent.mkdir(exist_ok=True)
        setpath.write_text(''.join(f'{k}={v}\n' for k,v in values.items()),encoding='utf-8')
        log=dest.with_suffix('.log')
        subprocess.run(f'"{TESTER/"metaeditor64.exe"}" /portable /compile:"{dest}" /log:"{log}"',timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
        assert '0 errors, 0 warnings' in read(log),read(log)
        assert dest.with_suffix('.ex5').is_file()
        ftmo=dict(values); ftmo['InpRewardRisk']='0.6' if kind=='T' else '0.5'
        fset=ROOT/'Sets'/(slug+'-ftmo-target.set')
        fset.write_text(''.join(f'{k}={v}\n' for k,v in ftmo.items()),encoding='utf-8')
        manifest['profiles'][slug]={'expert':str(dest.with_suffix('.ex5').relative_to(BASE)),
            'expert_sha':sha(dest.with_suffix('.ex5')), 'source_sha':sha(dest),
            'original_source_sha':sha(source), 'original_settings_sha':sha(BASE/settings),
            'strategy_change':'InpRewardRisk default only; all function bodies unchanged',
            'normal':{'settings':str(setpath.relative_to(BASE)), 'settings_sha':sha(setpath),'inputs':values},
            'ftmo':{'settings':str(fset.relative_to(BASE)), 'settings_sha':sha(fset),'inputs':ftmo}}
        print('PREPARED',slug,'normal',rr,'FTMO',ftmo['InpRewardRisk'],flush=True)
    write(ROOT/'SELECTION.json',manifest)

def publish():
    assert os.getenv('EA_STORE_DISABLE_MT5')=='1'
    sys.path[:0]=[str(STORE),str(STORE/'tools')]
    import precompute_evidence_cache as P
    from app.trade_metrics import enrich_trades
    results=load(RESEARCH/'RESULTS.json'); selection=load(ROOT/'SELECTION.json'); checks=[]
    def stamp(epoch): return datetime.fromtimestamp(float(epoch),timezone.utc).isoformat().replace('+00:00','')
    for slug,(kind,rr,_,_) in SPECS.items():
        product=next(p for p in P.get_sellable_catalog() if p.slug==slug)
        for mode,target in [('standard',rr)]+([('dynamic','0.5')] if kind=='S' else []):
            for period in P.PERIOD_MONTHS:
                r=next(r for r in results[kind][period] if float(r['parameters']['rr'])==float(target))
                folder=RESEARCH/'native'/r['native_batch']; ledger=folder/(str(r['native_index'])+'-trades.csv.gz')
                data=list(csv.DictReader(io.StringIO(gzip.decompress(ledger.read_bytes()).decode())))
                trades=[]
                for n,v in enumerate(data,1):
                    trades.append(dict(number=n,position_id=int(v['position_id']),ea=product.label,symbol='XAUUSD',
                        side='buy' if int(v['side'])>0 else 'sell', volume=float(v['volume']),
                        open_time=stamp(v['open_epoch']),close_time=stamp(v['close_epoch']),
                        open_price=float(v['open_price']),close_price=float(v['close_price']),
                        initial_sl=float(v['initial_sl']),initial_tp=float(v['initial_tp']),
                        gross_profit=float(v['gross_profit']),commission=float(v['commission']),swap=float(v['swap']),
                        fee=float(v['fee']),net_profit=float(v['net_profit']),total_costs=float(v['commission'])+float(v['swap'])+float(v['fee']),
                        actual_risk=float(v['actual_risk']),requested_risk=float(v['requested_risk']),
                        exit_reason=int(v['exit_reason']),cache_slug=slug,cache_mode=mode,cache_period=period,
                        source='Native MT5 position ledger; costs included'))
                trades=enrich_trades(trades,slug)
                for t in trades:
                    t['risk_cash']=t['actual_risk'];t['realized_r']=t['net_profit']/t['actual_risk'] if t['actual_risk'] else None
                    t['estimated_r']=t['realized_r']; t['estimated_risk_cash']=t['actual_risk']; t['r_is_estimate']=False
                start=date.fromisoformat(r['start'].replace('.','-'));end=date.fromisoformat(r['end'].replace('.','-'))
                stats,series=P.portfolio_metrics(trades,start,end)
                # Website daily Sharpe takes inclusive from/to; the tester end is exclusive.
                stats['to']=str(end-timedelta(days=1)); stats['end_exclusive']=str(end)
                series[-1]['time']=end.isoformat()+'T00:00:00'
                stats.update(profit_factor=r['net']['profit_factor'],win_rate_pct=r['net']['win_rate_pct'],
                    max_drawdown_pct=r['net']['equity_dd_pct'],max_equity_drawdown_pct=r['net']['equity_dd_pct'],
                    max_closed_balance_drawdown_pct=r['stats']['balance_dd_pct'],sharpe_ratio=None,
                    max_closed_balance_drawdown_cash=stats['max_drawdown_cash'],max_drawdown_cash=None,
                    recovery_factor=None,
                    sharpe_annualized=r['stats']['sharpe'], max_win_streak=r['stats']['max_win_streak'],max_loss_streak=r['stats']['max_loss_streak'],
                    avg_win_streak=r['stats']['avg_win_streak'],avg_loss_streak=r['stats']['avg_loss_streak'])
                assert stats['trades']==r['stats']['trades'] and abs(stats['net_profit']-r['stats']['net'])<.011
                profile='normal' if mode=='standard' else 'ftmo'
                fingerprint=P.source_fingerprint(product,mode,start,end)
                fingerprint.update(ledger_sha256=sha(ledger),research_parameters_sha=r['parameters_sha'],
                    research_ledger=str(ledger.relative_to(BASE)),
                    research_report_sha=r['report_sha'],research_manifest_sha=sha(folder/'manifest.json'),
                    production_selection_sha=sha(ROOT/'SELECTION.json'),identity='Original strategy functions, target-only wrapper; fresh account. Production magic differs for Slow; no trade-logic change.')
                notice=(f'User-selected {target}R target. Separate $10,000 Exness XAUUSD H4 research account, nominal 1% equity risk, 1:2000 leverage, 150 ms delay and recorded costs. '
                        'Native Model 4 every tick; real ticks begin January 2026, earlier ticks generated. 365-day no-entry warm-up. '
                        'Retrospective target sensitivity; failed strict 1y/5y PF >=1.20 screen, not untouched validation. '
                        'Ceil/minimum-lot sizing may exceed selected risk. Closed-balance curve; max equity DD measured natively. '
                        'End date exclusive. '+('FTMO TARGET COMPARISON ONLY: these are NOT guarded $50 FTMO results or pass/payout forecasts.' if mode=='dynamic' else 'Not a shared-account or FTMO test.'))
                payload=dict(label=product.label,period=f'{start} to {end}',period_key=period,mode=mode,currency='USD',
                    series=series,stats=stats,available_from=str(start),available_to=str(end),end_exclusive=str(end),
                    evidence_label=f'{target}R · {period} · standalone target sensitivity', evidence_status='Research evidence',
                    notice=notice,source='native-mt5-target-sensitivity',history_quality='Mixed real/generated ticks; real history from Jan 2026',
                    cached_trade_count=len(trades),trade_coverage_from=min(t['open_time'] for t in trades),trade_coverage_to=max(t['close_time'] for t in trades),
                    source_fingerprint=fingerprint,target_r=float(target),deployment_profile=profile,generated_at=datetime.now(timezone.utc).isoformat())
                P.write_json(P.product_trades_path(slug,mode,period),trades)
                fingerprint['cached_trades_sha256']=sha(P.product_trades_path(slug,mode,period))
                P.write_json(P.product_cache_path(slug,mode,period),payload)
                # Optimizer report is not a scalar report: prevent old report reuse.
                _,meta=P.source_paths(product,mode,period)
                P.write_json(meta,fingerprint)
                checks.append(dict(slug=slug,mode=mode,period=period,stats=stats,ledger_sha256=sha(ledger)))
                print('PUBLISHED',slug,mode,period,len(trades),flush=True)
    write(ROOT/'WEBSITE_PUBLICATION.json',{'checks':checks,'public_server_verified':False,'live_mt5_changed':False})

if __name__=='__main__': {'prepare':prepare,'publish':publish}[sys.argv[1]]()

"""Nasdaq 5M carry fix (PLAN.md, frozen before results). Run from AAA EAs/EA store:
  uv run python "<this>" ea       copy + patch the production source, compile (no tester)
  uv run python "<this>" native   parity (production EX5) + modes 0-3 DI OFF, Model 4 (one tester job at a time)
  uv run python "<this>" report   -> RESULTS.json / RESULTS.md, FINALIST.json
  uv run python "<this>" dion     the chosen mode and PROD with DI ON"""
import gzip, hashlib, importlib.util, json, os, shutil, subprocess, sys, time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; PACKAGE = H.parent; PIPE = PACKAGE.parent / 'Calyx Research Pipeline'; sys.path.insert(0, str(PIPE))
import buy_hold, data_split, robustness  # noqa: E402
PROD_DIR = PACKAGE / 'Nasdaq 5M DI ATR Deployment 2026-09-28/EA'; PROD_EX5 = PROD_DIR / 'Nasdaq 5M DI Wide ATR EA.ex5'
SRC = H / 'EA/carry/Nasdaq 5M Carry Research EA.mq5'; SYM = 'USTEC'
START, END = '2019-07-16', '2026-11-10'; SPLIT = data_split.research_split(START, END)
WINDOWS = {k: (SPLIT[n]['start'], SPLIT[n]['end_exclusive']) for k, n in (('dev', 'development'), ('val', 'validation'), ('oos', 'oos'))}
WINDOWS.update(all=(START, END), last_year=('2025-11-10', END), last_6m=('2026-05-10', END))
MODES = {'PROD': '0', 'LATE': '1', 'REPLACE': '2', 'FLIP_ONLY': '3'}
dot = lambda s: s.replace('-', '.')  # noqa: E731


def harness():
    spec = importlib.util.spec_from_file_location('baseline', PACKAGE / 'No Wick Candle Raw 2026-09-25/run_nw.py'); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
    b.ROOT = H; b.OUT = H / 'native'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True)
    return b


def edge_inputs(di):
    m = json.loads((PACKAGE / '_00 Live profiles/Packages/Edge10/Package.json').read_text(encoding='utf-8-sig'))
    i = {k: str(v) for k, v in next(x for x in m['entries'] if x['key'] == 'nasdaq-5m-candle-momentum')['inputs'].items() if not k.startswith('InpPortfolio')}
    i.update(InpRiskPercent='1.0', InpAdaptivePortfolioControls='false', InpRequireDIAgreement='true' if di else 'false'); return i


def sub1(text, old, new):
    assert text.count(old) == 1, (old[:90], text.count(old)); return text.replace(old, new)


def build_ea():
    assert hashlib.sha256(PROD_EX5.read_bytes()).hexdigest().startswith('fe9f391db5af')
    (H / 'EA/carry').mkdir(parents=True, exist_ok=True); (H / '_Shared').mkdir(exist_ok=True)
    for n in ('SafeRegimeFilter.mqh', 'DynamicTrailingSessionFilter.mqh'): shutil.copy2(PROD_DIR / n, H / 'EA/carry' / n)
    shutil.copy2(PACKAGE / '_Shared/CalyxAdaptivePortfolio.mqh', H / '_Shared/CalyxAdaptivePortfolio.mqh')
    raw = (PROD_DIR / 'Nasdaq 5M DI Wide ATR EA.mq5').read_bytes(); s = raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig').replace('\r\n', '\n')
    s = sub1(s, 'input group "Risk and execution"\n', '''input group "Carry research (0 = production)"
input int    InpCarryMode=0;               // 0 skip the day, 1 late entry after the old trade closes, 2 replace, 3 replace only if opposite
input int    InpLateCutoffMinuteNY=930;    // mode 1: no late entry after this New York minute (15:30)

input group "Risk and execution"
''')
    s = sub1(s, 'void ProcessNewBar()\n  {\n', '''int g_pending_dir=0,g_pending_key=0;

bool TryLateEntry(const MqlRates &bar)
  {
   if(g_pending_dir==0) return false;
   MqlDateTime ny; TimeToStruct(ServerToNewYork(bar.time),ny);
   int key=ny.year*10000+ny.mon*100+ny.day,close_minute=ny.hour*60+ny.min+PeriodSeconds(InpSignalTimeframe)/60;
   if(key!=g_pending_key || close_minute>InpLateCutoffMinuteNY || AlreadyTradedOnNewYorkDate(g_pending_key)) { g_pending_dir=0; return false; }
   ulong ticket=0;
   if(SelectOurPosition(ticket) || !InpEnableTrading) return false;
   double ema=0.0,atr=0.0;
   if(!ReadIndicatorValue(g_ema_handle,1,ema) || !ReadIndicatorValue(g_atr_handle,1,atr)) return false;
   if((g_pending_dir>0 && bar.close<=ema) || (g_pending_dir<0 && bar.close>=ema)) return false;   // the signal side must still hold: wait
   int direction=g_pending_dir; g_pending_dir=0;
   SendEntry(direction,atr,bar,SelectedRewardRisk(bar,atr));
   return true;
  }

void ProcessNewBar()
  {
''')
    s = sub1(s, '''   if(!IsNewYorkTime(rates[1].time,InpSignalHourNY,InpSignalMinuteNY)) return;
   int date_key=NewYorkDateKey(rates[1].time);
   ulong ticket=0;
   if(SelectOurPosition(ticket) || AlreadyTradedOnNewYorkDate(date_key) || !InpEnableTrading) return;
''', '''   if(InpCarryMode==1 && TryLateEntry(rates[1])) return;
   if(!IsNewYorkTime(rates[1].time,InpSignalHourNY,InpSignalMinuteNY)) return;
   int date_key=NewYorkDateKey(rates[1].time);
   ulong ticket=0;
   bool held=SelectOurPosition(ticket);
   if((held && InpCarryMode==0) || AlreadyTradedOnNewYorkDate(date_key) || !InpEnableTrading) return;
   int held_direction=(held ? (PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY ? 1 : -1) : 0);
''')
    s = sub1(s, '''   if(!DIAgrees(direction)) return;
   SendEntry(direction,atr,rates[1],SelectedRewardRisk(rates[1],atr));
  }''', '''   if(!DIAgrees(direction)) return;
   if(held)
     {
      if(InpCarryMode==1) { g_pending_dir=direction; g_pending_key=date_key; return; }
      if(InpCarryMode==3 && held_direction==direction) return;
      g_trade.SetExpertMagicNumber((ulong)InpMagic);
      g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
      if(!g_trade.PositionClose(ticket,(ulong)InpMaximumDeviationPoints)) { Print("N5EMA carry close failed: ",g_trade.ResultRetcodeDescription()); return; }
      if(SelectOurPosition(ticket)) return;
     }
   SendEntry(direction,atr,rates[1],SelectedRewardRisk(rates[1],atr));
  }''')
    SRC.write_text(s, encoding='utf-8'); editor = harness().TESTER / 'MetaEditor64.exe'; log = SRC.with_suffix('.compile.log'); started = time.time()
    subprocess.run(f'"{editor}" /portable /compile:"{SRC}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=300)
    r = log.read_bytes(); text = r.decode('utf-16' if r.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'); assert '0 errors, 0 warnings' in text, text[-2500:]
    assert SRC.with_suffix('.ex5').stat().st_mtime >= started - 2; print('COMPILED', flush=True)


def setup(b, di):
    dest = b.TESTER / 'MQL5/Experts/CalyxCarry'; dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC.with_suffix('.ex5'), dest / 'carry.ex5'); shutil.copy2(PROD_EX5, dest / 'prod.ex5')
    b.CONFIG.update(periods={'all': dot(START)}, end_date=dot(END), deposit=10000, currency='USD', model=4, execution_delay_ms=150, profile='Calyx Research Empty', timeout_seconds=21600,
                    expert_dir='CalyxCarry', expert_file='carry.ex5', controls={}, variants={}, common_inputs=edge_inputs(di), period='M5')


def run(b, key, inputs, expert='carry.ex5'):
    b.CONFIG['expert_file'] = expert; b.CONFIG['variants'][key] = {'label': key, 'inputs': inputs}
    for attempt in range(4):
        try:
            return b.run_case(SYM, key, 'all')
        except SystemExit:
            print('RETRY' if attempt < 3 else 'CASE FAILED', key, flush=True); time.sleep(60)


def ledger(key):
    return json.loads(gzip.open(H / 'native' / f'nw-{SYM}-{key}-all' / 'trades.json.gz').read())


def native():
    b = harness(); assert not b.isolated_running(), 'Tester is occupied'; setup(b, False)
    run(b, 'PRODEX5', {}, 'prod.ex5'); run(b, 'PROD', dict(InpCarryMode='0'))
    sig = lambda T: [(t['open_time'], t['close_time'], t['side'], t['volume'], t['net_profit']) for t in sorted(T, key=lambda t: t['open_time'])]  # noqa: E731
    same = sig(ledger('PRODEX5')) == sig(ledger('PROD')); print('PARITY', same, len(ledger('PROD')), flush=True); assert same, 'research EA differs from production'
    for key, mode in MODES.items():
        if key != 'PROD': run(b, key, dict(InpCarryMode=mode)); print('DONE', key, flush=True)
    print('NATIVE DONE', flush=True)


def ny(server_iso):
    """Exness tester time is UTC. New York = UTC-4 from the 2nd Sunday of March 07:00 UTC to the 1st Sunday of November 06:00 UTC, else UTC-5."""
    t = datetime.fromisoformat(server_iso[:19]); y = t.year
    def sunday(m, n):
        d = datetime(y, m, 1); d += timedelta(days=(6 - d.weekday()) % 7); return d + timedelta(days=7 * (n - 1))
    dst = sunday(3, 2) + timedelta(hours=7) <= t < sunday(11, 1) + timedelta(hours=6)
    return t - timedelta(hours=4 if dst else 5)


def rows_of(key):
    bal = 1e4; rows = []
    for t in sorted(ledger(key), key=lambda t: t['close_time']):
        rows.append(dict(o=t['open_time'], c=t['close_time'], r=t['net_profit'] / (0.01 * bal), net=t['net_profit'], side=t['side'], exit=t.get('exit_comment') or '')); bal += t['net_profit']
    return rows


def stats(rows, a, b_):
    x = [r for r in rows if a <= r['o'][:10] < b_]; gw = sum(r['r'] for r in x if r['r'] > 0); gl = -sum(r['r'] for r in x if r['r'] < 0); eq = peak = dd = 0.0; days = defaultdict(float)
    for r in x:
        eq += r['r']; peak = max(peak, eq); dd = max(dd, peak - eq); days[r['c'][:10]] += r['r']
    months = (datetime.fromisoformat(b_) - datetime.fromisoformat(a)).days / 30.4375; tot = sum(r['r'] for r in x)
    return dict(trades=len(x), per_month=round(len(x) / months, 2), per_weekday=round(len(x) / (months * 21.74), 3), total_r=round(tot, 2), mean_r=round(tot / max(1, len(x)), 4),
                pf=round(gw / gl, 3) if gl else None, win=round(100 * sum(r['r'] > 0 for r in x) / max(1, len(x)), 1), closed_dd_r=round(dd, 2), ret_dd=round(tot / dd, 2) if dd else None,
                without_best5=round(tot - sum(sorted(days.values(), reverse=True)[:5]), 2))


def held_days(rows):
    """Days on which a trade opened on an earlier day was still open at the 09:35 New York check."""
    n = 0
    for r in rows:
        o, c = ny(r['o']), ny(r['c']); d = (o + timedelta(days=1)).replace(hour=9, minute=35, second=0)
        while d < c:
            if d.weekday() < 5: n += 1
            d += timedelta(days=1)
    return n


def report():
    out = dict(split=WINDOWS, modes={})
    for k in MODES:
        try:
            rows = rows_of(k)
        except FileNotFoundError:
            continue
        d = H / 'native' / f'nw-{SYM}-{k}-all'
        out['modes'][k] = dict(windows={w: stats(rows, *v) for w, v in WINDOWS.items()}, held_days=held_days(rows), equity_dd_relative_pct=buy_hold.relative_equity_dd(d / f'{d.name}.htm.gz'),
                               three_way=robustness.three_monte_carlo([r['r'] for r in rows], runs=1000, seed=20261104), carry_closes=sum('carry' in r['exit'].lower() for r in rows))
    P = out['modes']['PROD']['windows']; ok = []
    for k, v in out['modes'].items():
        w = v['windows']; tw = v['three_way']
        v['qualifies'] = k != 'PROD' and (w['dev']['ret_dd'] or -9) > (P['dev']['ret_dd'] or 0) and w['val']['total_r'] >= P['val']['total_r'] and w['oos']['total_r'] >= P['oos']['total_r']
        if v['qualifies']: ok.append(k)
    out['finalist'] = max(ok, key=lambda k: out['modes'][k]['windows']['dev']['ret_dd']) if ok else None
    (H / 'FINALIST.json').write_text(json.dumps(out['finalist']), encoding='utf-8'); (H / 'RESULTS.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8')
    print(json.dumps({k: dict(all=v['windows']['all'], dev=v['windows']['dev']['total_r'], val=v['windows']['val']['total_r'], oos=v['windows']['oos']['total_r'], held=v['held_days'], q=v['qualifies']) for k, v in out['modes'].items()}, default=str)[:5000]); print('FINALIST', out['finalist'])


def dion():
    # Owner 2026-11-09: "try DI on and OFF too" -> every mode is also run with DI ON (same choice rule, applied separately), not only the finalist.
    b = harness(); assert not b.isolated_running(), 'Tester is occupied'; setup(b, True)
    for k, mode in MODES.items(): run(b, k + '_DION', dict(InpCarryMode=mode)); print('DONE', k + '_DION', flush=True)
    out = dict(split=WINDOWS, modes={})
    for k in MODES:
        rows = rows_of(k + '_DION'); d = H / 'native' / f'nw-{SYM}-{k}_DION-all'
        out['modes'][k] = dict(windows={w: stats(rows, *v) for w, v in WINDOWS.items()}, held_days=held_days(rows), equity_dd_relative_pct=buy_hold.relative_equity_dd(d / f'{d.name}.htm.gz'),
                               three_way=robustness.three_monte_carlo([r['r'] for r in rows], runs=1000, seed=20261104))
    P = out['modes']['PROD']['windows']; ok = []
    for k, v in out['modes'].items():
        w = v['windows']
        v['qualifies'] = k != 'PROD' and (w['dev']['ret_dd'] or -9) > (P['dev']['ret_dd'] or 0) and w['val']['total_r'] >= P['val']['total_r'] and w['oos']['total_r'] >= P['oos']['total_r']
        if v['qualifies']: ok.append(k)
    out['finalist'] = max(ok, key=lambda k: out['modes'][k]['windows']['dev']['ret_dd']) if ok else None
    (H / 'RESULTS_DION.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); print('FINALIST DI ON', out['finalist'], flush=True)


PCT = dict(InpStopMode='2', InpInitialStopATR='4.0', InpInitialStopPercent='0.60')   # the installers' OLD stop (Calyx-InstallChoices.ps1 Set-CalyxNasdaqVersion)


def pct():
    """Owner 2026-11-09 (after the first results): DI OFF, the old 0.60% stop, alone and with the two best carry modes. Compared with the ATR6 runs above."""
    b = harness(); assert not b.isolated_running(), 'Tester is occupied'; setup(b, False)
    for k in ('PROD', 'REPLACE', 'FLIP_ONLY'): run(b, 'PCT_' + k, dict(PCT, InpCarryMode=MODES[k])); print('DONE PCT_' + k, flush=True)
    out = {}
    for k in ('PROD', 'REPLACE', 'FLIP_ONLY', 'PCT_PROD', 'PCT_REPLACE', 'PCT_FLIP_ONLY'):
        rows = rows_of(k); d = H / 'native' / f'nw-{SYM}-{k}-all'
        out[k] = dict(windows={w: stats(rows, *v) for w, v in WINDOWS.items()}, held_days=held_days(rows) if not k.endswith(('REPLACE', 'FLIP_ONLY')) else None,
                      equity_dd_relative_pct=buy_hold.relative_equity_dd(d / f'{d.name}.htm.gz'), native_return_pct=round(sum(r['net'] for r in rows) / 100, 2),
                      three_way=robustness.three_monte_carlo([r['r'] for r in rows], runs=1000, seed=20261104))
    (H / 'RESULTS_PCT.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); print('PCT DONE', flush=True)


if __name__ == '__main__':
    {'ea': build_ea, 'native': native, 'report': report, 'dion': dion, 'pct': pct}[sys.argv[1]]()

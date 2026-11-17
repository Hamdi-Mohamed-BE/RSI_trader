"""RULES.md. Run from AAA EAs/EA store:  uv run python "<this>" build | parity | main | report   (report needs: uv run --with numpy)"""
import gzip, hashlib, importlib.util, json, os, shutil, subprocess, sys, time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; B = H.parent; PIPE = B.parent / 'Calyx Research Pipeline'; sys.path.insert(0, str(PIPE))
import buy_hold, data_split, robustness  # noqa: E402
NAS_DIR = B / 'Nasdaq 5M Carry Replace Deployment 2026-11-09/EA'; NAS_SRC = NAS_DIR / 'Nasdaq 5M DI Wide ATR EA.mq5'; NAS_EX5 = NAS_DIR / 'Nasdaq 5M DI Wide ATR EA.ex5'
ONB_DIR = B / 'Video ORB VWAP Ideas Raw 2026-11-09/EA'; ONB_SRC = ONB_DIR / 'Video Ideas Raw EA.mq5'; ONB_EX5 = ONB_DIR / 'Video Ideas Raw EA.ex5'
EA = H / 'EA'; NAS_LOC = EA / 'Nasdaq 5M Market Clock Research.mq5'; ONB_LOC = EA / 'ONB Market Clock Research.mq5'
START, END = '2019-07-16', '2026-11-16'
MARKET = {'UK100': dict(clock=1, open=480, label='London 08:00'), 'DE30': dict(clock=2, open=540, label='Frankfurt 09:00')}
spec = importlib.util.spec_from_file_location('carry', B / 'Nasdaq 5M Carry Fix 2026-11-09/carry.py'); C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)

EU_FN = '''
int CalyxLastSunday(const int year,const int month)
  {
   int days=(month==3 || month==10 ? 31 : 30);
   MqlDateTime t; TimeToStruct(%s(year,month,days,0),t);
   return days-t.day_of_week;
  }
int CalyxMarketUtcOffsetHours(const datetime utc_time)   // 1 London (UTC+0/+1), 2 Frankfurt (UTC+1/+2), EU DST
  {
   MqlDateTime p; TimeToStruct(utc_time,p);
   datetime a=%s(p.year,3,CalyxLastSunday(p.year,3),1),b=%s(p.year,10,CalyxLastSunday(p.year,10),1);
   int dst=(utc_time>=a && utc_time<b ? 1 : 0);
   return (InpMarketClock==1 ? 0 : 1)+dst;
  }
'''


def sub1(t, a, b):
    assert t.count(a) == 1, (a[:80], t.count(a)); return t.replace(a, b)


def build():
    assert hashlib.sha256(NAS_EX5.read_bytes()).hexdigest().startswith('2488443f62a8')
    EA.mkdir(exist_ok=True)
    for n in ('SafeRegimeFilter.mqh', 'DynamicTrailingSessionFilter.mqh'): shutil.copy2(NAS_DIR / n, EA / n)
    t = NAS_SRC.read_text(encoding='utf-8')
    t = sub1(t, 'input int    InpSignalMinuteNY=30;', 'input int    InpSignalMinuteNY=30;\ninput int    InpMarketClock=0;      // RESEARCH 2026-11-16: 0 New York (production), 1 London, 2 Frankfurt; all "NY" times become this clock')
    t = sub1(t, 'int NewYorkUtcOffsetHours(const datetime utc_time)\n  {\n', EU_FN % ('BuildUtcTime', 'BuildUtcTime', 'BuildUtcTime') + '\nint NewYorkUtcOffsetHours(const datetime utc_time)\n  {\n   if(InpMarketClock!=0) return CalyxMarketUtcOffsetHours(utc_time);\n')
    NAS_LOC.write_text('// RESEARCH COPY (2026-11-16) of Nasdaq 5M DI Wide ATR EA 2488443f62a8: adds InpMarketClock only. NEVER attach to a live chart.\n' + t, encoding='utf-8')
    o = ONB_SRC.read_text(encoding='utf-8')
    o = sub1(o, 'input int    InpServerUtcOffsetHours=0;', 'input int    InpServerUtcOffsetHours=0;\ninput int    InpMarketClock=0;      // RESEARCH 2026-11-16: 0 New York, 1 London, 2 Frankfurt\ninput int    InpOpenMin=570;        // ONB cash open in that clock (NY 570 = 09:30); every ONB minute is relative to it')
    o = sub1(o, 'int NyOffset(const datetime utc)\n  {\n', EU_FN % ('MakeUtc', 'MakeUtc', 'MakeUtc') + '\nint NyOffset(const datetime utc)\n  {\n   if(InpMarketClock!=0) return CalyxMarketUtcOffsetHours(utc);\n')
    o = sub1(o, 'if(!g_setup && close_min>=585)', 'if(!g_setup && close_min>=InpOpenMin+15)')
    o = sub1(o, 'TodayNy(t1,570),true),sn=iBarShift(_Symbol,PERIOD_M15,TodayNy(t1,0),false);', 'TodayNy(t1,InpOpenMin),true),sn=iBarShift(_Symbol,PERIOD_M15,TodayNy(t1,0),false);')
    o = sub1(o, 'if(!g_setup || g_done || close_min<600 || close_min>915 || HasPos()) return;', 'if(!g_setup || g_done || close_min<InpOpenMin+30 || close_min>InpOpenMin+345 || HasPos()) return;')
    o = sub1(o, 'int flat=(InpStrategy==1 || InpStrategy==3 ? 955 : 930);', 'int flat=(InpStrategy==1 || InpStrategy==3 ? 955 : (InpStrategy==4 ? InpOpenMin+360 : 930));')
    ONB_LOC.write_text('// RESEARCH COPY (2026-11-16) of Video Ideas Raw EA: adds InpMarketClock / InpOpenMin for ONB only. NEVER attach to a live chart.\n' + o, encoding='utf-8')
    b = harness()
    for src in (NAS_LOC, ONB_LOC):
        log = src.with_suffix('.compile.log'); started = time.time()
        subprocess.run(f'"{b.TESTER / "MetaEditor64.exe"}" /portable /compile:"{src}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=300)
        r = log.read_bytes(); txt = r.decode('utf-16' if r.startswith(b'\xff\xfe') else 'utf-8-sig'); assert '0 errors, 0 warnings' in txt, txt[-1500:]
        assert src.with_suffix('.ex5').stat().st_mtime >= started - 2
    print('BUILT', flush=True)


def harness(out='native'):
    spec2 = importlib.util.spec_from_file_location('baseline', B / 'No Wick Candle Raw 2026-09-25/run_nw.py'); b = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(b)
    b.ROOT = H; b.OUT = H / out; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True); return b


def stage(b):
    dest = b.TESTER / 'MQL5/Experts/CalyxTwoEU'; dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(NAS_EX5, dest / 'nas-prod.ex5'); shutil.copy2(NAS_LOC.with_suffix('.ex5'), dest / 'nas-loc.ex5')
    shutil.copy2(ONB_EX5, dest / 'onb-prod.ex5'); shutil.copy2(ONB_LOC.with_suffix('.ex5'), dest / 'onb-loc.ex5')


def case(b, sym, key, expert, inputs, period, start, end, tf):
    if (b.OUT / f'nw-{sym}-{key}-{period}' / 'trades.json.gz').exists(): return
    b.CONFIG.update(model=4, end_date=end.replace('-', '.'), periods={period: start.replace('-', '.')}, deposit=10000, currency='USD', execution_delay_ms=150,
                    profile='Calyx Research Empty', timeout_seconds=14400, period=tf, expert_dir='CalyxTwoEU', expert_file=expert, controls={}, common_inputs={},
                    variants={key: {'label': key, 'inputs': inputs}})
    for attempt in range(3):
        try: b.run_case(sym, key, period); break
        except SystemExit: print('RETRY', sym, key, flush=True); time.sleep(30)
    print('DONE', sym, key, period, flush=True)


NAS_IN = lambda: C.edge_inputs(False)  # noqa: E731
ONB_IN = dict(InpStrategy='4', InpUseBias='true', InpRandomDirection='false', InpSeed='1', InpRiskPercent='1.0', InpServerUtcOffsetHours='0')


def parity():
    b = harness('parity'); assert not b.isolated_running(), 'Tester is occupied'; stage(b)
    case(b, 'USTEC', 'NASPROD', 'nas-prod.ex5', NAS_IN(), '6m', '2026-05-16', END, 'M5')
    case(b, 'USTEC', 'NASLOC0', 'nas-loc.ex5', dict(NAS_IN(), InpMarketClock='0'), '6m', '2026-05-16', END, 'M5')
    case(b, 'USTEC', 'ONBPROD', 'onb-prod.ex5', ONB_IN, '6m', '2026-05-16', END, 'M15')
    case(b, 'USTEC', 'ONBLOC0', 'onb-loc.ex5', dict(ONB_IN, InpMarketClock='0', InpOpenMin='570'), '6m', '2026-05-16', END, 'M15')
    k = lambda p: [(t['open_time'], t['close_time'], t['side'], t['net_profit']) for t in sorted(json.loads(gzip.open(H / 'parity' / f'nw-USTEC-{p}-6m' / 'trades.json.gz').read()), key=lambda t: t['open_time'])]  # noqa: E731
    res = {'NAS': dict(n=len(k('NASPROD')), identical=k('NASPROD') == k('NASLOC0')), 'ONB': dict(n=len(k('ONBPROD')), identical=k('ONBPROD') == k('ONBLOC0'))}
    (H / 'PARITY.json').write_text(json.dumps(res, indent=1), encoding='utf-8'); print('PARITY', res, flush=True); assert all(v['identical'] for v in res.values())


def main():
    b = harness(); assert not b.isolated_running(), 'Tester is occupied'; stage(b)
    for sym, m in MARKET.items():
        hh, mm = divmod(m['open'], 60)
        case(b, sym, 'NAS_NY', 'nas-prod.ex5', NAS_IN(), 'all', START, END, 'M5')
        case(b, sym, 'NAS_LOC', 'nas-loc.ex5', dict(NAS_IN(), InpMarketClock=str(m['clock']), InpSignalHourNY=str(hh), InpSignalMinuteNY=str(mm)), 'all', START, END, 'M5')
        case(b, sym, 'ONB_NY', 'onb-prod.ex5', ONB_IN, 'all', START, END, 'M15')
        case(b, sym, 'ONB_LOC', 'onb-loc.ex5', dict(ONB_IN, InpMarketClock=str(m['clock']), InpOpenMin=str(m['open'])), 'all', START, END, 'M15')
    W = {'all': (START, END)}
    for sym in MARKET:
        try:
            if not buy_hold.load(H, sym, 'all'): raise ValueError
        except Exception:
            try: buy_hold.run(H, sym, W)
            except Exception as e: print('BUYHOLD FAILED', sym, repr(e)[:200], flush=True)
    print('MAIN DONE', flush=True)


def rows(sym, key):
    T = sorted(json.loads(gzip.open(H / 'native' / f'nw-{sym}-{key}-all' / 'trades.json.gz').read()), key=lambda t: t['close_time']); bal = 1e4; out = []
    for t in T: out.append(dict(o=t['open_time'][:10], c=t['close_time'][:10], r=t['net_profit'] / (0.01 * bal), net=t['net_profit'])); bal += t['net_profit']
    return out


def stats(x, a, b):
    x = [r for r in x if a <= r['o'] < b]; w = sum(r['r'] for r in x if r['r'] > 0); l = -sum(r['r'] for r in x if r['r'] < 0); eq = pk = dd = 0.0
    for r in x: eq += r['r']; pk = max(pk, eq); dd = max(dd, pk - eq)
    months = (datetime.fromisoformat(b) - datetime.fromisoformat(a)).days / 30.4375
    return dict(trades=len(x), per_month=round(len(x) / months, 1), per_day=round(len(x) / months / 21, 2), r=round(sum(r['r'] for r in x), 1), pf=round(w / l, 2) if l else None,
                win=round(100 * sum(1 for r in x if r['r'] > 0) / max(1, len(x)), 1), dd_r=round(dd, 1))


def report():
    sp = data_split.research_split(START, END)
    W = {'all': (START, END), 'dev': (sp['development']['start'], sp['development']['end_exclusive']), 'val': (sp['validation']['start'], sp['validation']['end_exclusive']),
         'oos': (sp['oos']['start'], sp['oos']['end_exclusive']), 'last3y': ('2023-11-16', END), 'last12m': ('2025-11-16', END), 'last2m': ('2026-09-16', END)}
    out = dict(windows=W)
    for sym in list(MARKET) + list(US):
        for key in ('NAS_NY', 'NAS_LOC', 'ONB_NY', 'ONB_LOC'):  # missing combinations are skipped
            try: A = rows(sym, key)
            except FileNotFoundError: continue
            run = json.loads((H / 'native' / f'nw-{sym}-{key}-all' / 'run.json').read_text())['metrics']
            years = defaultdict(float)
            for r in A: years[r['o'][:4]] += r['r']
            mc = robustness.three_monte_carlo([r['r'] for r in A], runs=1000, seed=20261104) if len(A) >= 30 else None
            out[f'{sym} {key}'] = dict(native=dict(ret=run['return_pct'], pf=run['profit_factor'], mt5_dd=run['max_drawdown_pct'], trades=run['trades']),
                                      win={k: stats(A, *v) for k, v in W.items()}, years={y: round(v, 1) for y, v in sorted(years.items())},
                                      mc=dict(resample=mc['resample']['red_pct'], randomize=mc['randomize']['both']['red_pct'], clumped=mc['reshuffle']['real_drawdown_worse_than_pct']) if mc else None)
        try: x = buy_hold.load(H, sym, 'all'); out[f'{sym} buy&hold'] = dict(ret=x['return_pct'], dd=x['max_dd_pct'])
        except Exception as e: out[f'{sym} buy&hold'] = repr(e)[:80]
    (H / 'RESULTS.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); print(json.dumps(out, indent=1, default=str)[:9000])


US = ('US30', 'US500')


def main_us():
    b = harness(); assert not b.isolated_running(), 'Tester is occupied'; stage(b)
    for sym in US:
        case(b, sym, 'NAS_NY', 'nas-prod.ex5', NAS_IN(), 'all', START, END, 'M5')
        case(b, sym, 'ONB_NY', 'onb-prod.ex5', ONB_IN, 'all', START, END, 'M15')
    for sym in US:
        try: buy_hold.load(H, sym, 'all')
        except Exception:
            try: buy_hold.run(H, sym, {'all': (START, END)})
            except Exception as e: print('BUYHOLD FAILED', sym, repr(e)[:200], flush=True)
    print('US DONE', flush=True)


def controls():
    b = harness('controls'); assert not b.isolated_running(), 'Tester is occupied'; stage(b)
    def m1(key, inputs):
        if (b.OUT / f'nw-US500-{key}-all' / 'trades.json.gz').exists(): return
        b.CONFIG.update(model=1, end_date=END.replace('-', '.'), periods={'all': START.replace('-', '.')}, deposit=10000, currency='USD', execution_delay_ms=150,
                        profile='Calyx Research Empty', timeout_seconds=7200, period='M15', expert_dir='CalyxTwoEU', expert_file='onb-prod.ex5', controls={}, common_inputs={},
                        variants={key: {'label': key, 'inputs': inputs}})
        for attempt in range(3):
            try: b.run_case('US500', key, 'all'); break
            except SystemExit: time.sleep(30)
        print('DONE', key, flush=True)
    m1('ONB_M1', ONB_IN); m1('NOBIAS', dict(ONB_IN, InpUseBias='false'))
    for s in range(1, 21): m1(f'RNDDIR{s}', dict(ONB_IN, InpRandomDirection='true', InpSeed=str(s)))
    def tot(key):
        T = sorted(json.loads(gzip.open(b.OUT / f'nw-US500-{key}-all' / 'trades.json.gz').read()), key=lambda t: t['close_time']); bal = 1e4; r = 0.0
        for t in T: r += t['net_profit'] / (0.01 * bal); bal += t['net_profit']
        return round(r, 1), len(T)
    main_r = tot('ONB_M1'); rd = [tot(f'RNDDIR{s}')[0] for s in range(1, 21)]
    res = dict(onb_m1=main_r, nobias=tot('NOBIAS'), random_direction=rd, p=round((sum(1 for v in rd if v >= main_r[0]) + 1) / 21, 3))
    (H / 'CONTROLS_US500.json').write_text(json.dumps(res, indent=1), encoding='utf-8'); print('CONTROLS', res, flush=True)


if __name__ == '__main__':
    {'build': build, 'parity': parity, 'main': main, 'us_run': main_us, 'controls': controls}.get(sys.argv[1], report)()

"""Nasdaq Overnight Protocol clip study (PLAN.md, frozen before results). Run from AAA EAs/EA store:
  uv run python "<this>" ea        copy + patch the production source, compile (no tester)
  uv run python "<this>" native    parity + every variant, Model 1 (one tester job at a time)
  uv run python "<this>" report    -> RESULTS.json, RESULTS.md, FINALISTS.json
  uv run python "<this>" confirm   Model 4 + three-way Monte Carlo on PROD and the finalists -> CONFIRM.json, CONFIRM.md"""
import gzip, importlib.util, json, os, shutil, subprocess, sys, time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; PACKAGE = H.parent; PIPE = PACKAGE.parent / 'Calyx Research Pipeline'; sys.path.insert(0, str(PIPE))
import buy_hold, data_split, robustness  # noqa: E402
PROD = PACKAGE / 'Nasdaq Overnight Negative Day EA'; SRC = H / 'EA/overnight/Nasdaq Overnight Lab EA.mq5'; SYM = 'USTEC'
START, END = '2019-07-16', '2026-11-01'; SPLIT = data_split.research_split(START, END)
WINDOWS = {k: (SPLIT[n]['start'], SPLIT[n]['end_exclusive']) for k, n in (('dev', 'development'), ('val', 'validation'), ('oos', 'oos'))}; WINDOWS['last_year'] = ('2025-11-01', END); WINDOWS['all'] = (START, END)
assert WINDOWS['oos'] == ('2024-11-01', '2026-11-01')
dot = lambda s: s.replace('-', '.')  # noqa: E731

LAB_BASE = dict(InpLabEnabled='true', InpLabRedMode='1', InpLabEntryType='0', InpLabEntryStart='960', InpLabEntryEnd='970', InpLabExit='569', InpLabTF='15', InpLabRSIPeriod='14', InpLabRSILevel='0', InpLabSwingBars='2', InpLabAtrPeriod='14', InpLabStopAtr='0', InpLabTargetAtr='0', InpLabLockAt='0', InpLabLockTo='-0.5', InpLabDirection='1', InpLabSeed='1')
CLIP = dict(InpNegativeDayDefinition='1', InpLabEntryType='1', InpLabEntryStart='0', InpLabEntryEnd='480', InpLabExit='480', InpLabRSILevel='30', InpLabStopAtr='1', InpLabTargetAtr='1', InpLabLockAt='0.5')
def clip(tf, **k): return dict(CLIP, InpLabTF=str(tf), **k)  # noqa: E302,E704
VARIANTS = {'LABPROD': {}, 'BASIC': dict(CLIP, InpLabRedMode='0', InpLabEntryType='0', InpLabEntryEnd='10', InpLabRSILevel='0'),
            'CLIP_M5': clip(5), 'CLIP_M15': clip(15), 'NORED_M5': clip(5, InpLabRedMode='0'), 'NORED_M15': clip(15, InpLabRedMode='0'), 'NORSI_M5': clip(5, InpLabRSILevel='0'), 'NORSI_M15': clip(15, InpLabRSILevel='0'),
            'MIRROR_M5': clip(5, InpLabRedMode='3', InpLabDirection='-1'), 'MIRROR_M15': clip(15, InpLabRedMode='3', InpLabDirection='-1'), 'RAND_M5': clip(5, InpLabDirection='0'), 'RAND_M15': clip(15, InpLabDirection='0'),
            'X08': dict(InpLabExit='480'), 'X04': dict(InpLabExit='240'), 'E00': dict(InpLabEntryStart='0', InpLabEntryEnd='10'), 'EU': dict(InpLabEntryStart='90', InpLabEntryEnd='100', InpLabExit='240'),
            'O2C': dict(InpNegativeDayDefinition='1'), 'OVS40': dict(InpLabRSILevel='40'), 'OVS30': dict(InpLabRSILevel='30'),
            'ATR1': dict(InpLabStopAtr='1', InpLabTargetAtr='1', InpLabLockAt='0.5'), 'ATR3': dict(InpLabStopAtr='3'), 'LOCK': dict(InpLabLockAt='0.5')}
CONTROLS = {'CLIP_M5': ('MIRROR_M5', 'RAND_M5'), 'CLIP_M15': ('MIRROR_M15', 'RAND_M15'), 'NORED_M5': ('RAND_M5',), 'NORED_M15': ('RAND_M15',), 'NORSI_M5': ('RAND_M5',), 'NORSI_M15': ('RAND_M15',)}
NOT_CANDIDATES = {'PROD', 'LABPROD', 'MIRROR_M5', 'MIRROR_M15', 'RAND_M5', 'RAND_M15'}


def harness():
    spec = importlib.util.spec_from_file_location('baseline', PACKAGE / 'No Wick Candle Raw 2026-09-25/run_nw.py'); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
    b.ROOT = H; b.OUT = H / 'native'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True)
    return b


def prod_inputs():
    c = json.loads((PACKAGE / 'Current14 Plus ORB05 Portfolio 2026-10-08/Package.json').read_text(encoding='utf-8-sig')); i = {k: str(v) for k, v in next(x for x in c['entries'] if x['key'] == 'nasdaq-overnight')['inputs'].items()}
    i.update(InpRiskPercent='1.0', InpAdaptivePortfolioControls='false'); return i


def sub1(text, old, new):
    assert text.count(old) == 1, (old[:90], text.count(old)); return text.replace(old, new)


def build_ea():
    (H / 'EA/overnight').mkdir(parents=True, exist_ok=True); (H / 'EA/_Shared').mkdir(exist_ok=True)
    for n in ('SafeRegimeFilter.mqh', 'DynamicTrailingSessionFilter.mqh'): shutil.copy2(PROD / n, H / 'EA/overnight' / n)
    shutil.copy2(PACKAGE / '_Shared/CalyxAdaptivePortfolio.mqh', H / 'EA/_Shared/CalyxAdaptivePortfolio.mqh')
    raw = (PROD / 'Nasdaq Overnight Negative Day EA.mq5').read_bytes(); s = raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig').replace('\r\n', '\n')
    s = sub1(s, 'input group "Broker clock"\n', '''input group "Research lab (off = production path)"
input bool   InpLabEnabled=false;
input int    InpLabRedMode=1;       // 0 none, 1 session down, 3 session up (by InpNegativeDayDefinition)
input int    InpLabEntryType=0;     // 0 timed market entry, 1 RSI then swing break
input int    InpLabEntryStart=960;  // New York minute of day
input int    InpLabEntryEnd=970;
input int    InpLabExit=569;
input ENUM_TIMEFRAMES InpLabTF=PERIOD_M15;
input int    InpLabRSIPeriod=14;
input double InpLabRSILevel=0;      // 0 off; long needs RSI below it, short above 100 minus it
input int    InpLabSwingBars=2;     // bars each side of the swing, 0 = no swing condition
input int    InpLabAtrPeriod=14;
input double InpLabStopAtr=0;       // 0 = InpEmergencyStopPercent
input double InpLabTargetAtr=0;
input double InpLabLockAt=0;        // +R that moves the stop, 0 off
input double InpLabLockTo=-0.5;     // R level the stop moves to
input int    InpLabDirection=1;     // 1 long, -1 short mirror, 0 random direction at the long trigger
input int    InpLabSeed=1;

input group "Broker clock"
''')
    s = sub1(s, 'void ProcessStrategy()\n{\n', '''int g_lab_rsi=INVALID_HANDLE,g_lab_atr=INVALID_HANDLE,g_lab_done=0,g_lab_checked=0;
bool g_lab_ok=false,g_lab_armed=false,g_lab_locked=false;
datetime g_lab_bar=0;
double g_lab_R=0.0;

double LabValue(const int handle)
{
   double v[1];
   if(handle==INVALID_HANDLE || CopyBuffer(handle,0,1,1,v)!=1) return -1.0;
   return v[0];
}

bool LabSession(const MqlDateTime &now_ny,MqlDateTime &session)
{
   int minute=now_ny.hour*60+now_ny.min;
   session=now_ny;
   if(minute>=InpCashCloseHour*60+InpCashCloseMinute && now_ny.day_of_week>=1 && now_ny.day_of_week<=5) return true;
   datetime t=StructToTime(now_ny);
   for(int i=0;i<7;i++)
   {
      t-=86400; TimeToStruct(t,session);
      if(session.day_of_week>=1 && session.day_of_week<=5) return true;
   }
   return false;
}

bool LabNightOk(const MqlDateTime &session)
{
   if(InpLabRedMode==0) return true;
   double ret=0.0; int bars=0;
   if(!NegativeDayReturn(session,ret,bars)) return false;
   if(InpLabRedMode==3) return ret>0.0;
   return ret<0.0;
}

double LabSwing(const int side)
{
   for(int i=InpLabSwingBars+2;i<300;i++)
   {
      double level=(side>0?iHigh(_Symbol,InpLabTF,i):iLow(_Symbol,InpLabTF,i));
      if(level<=0.0) return 0.0;
      bool ok=true;
      for(int j=1;j<=InpLabSwingBars && ok;j++)
      {
         double a=(side>0?iHigh(_Symbol,InpLabTF,i-j):iLow(_Symbol,InpLabTF,i-j)),b=(side>0?iHigh(_Symbol,InpLabTF,i+j):iLow(_Symbol,InpLabTF,i+j));
         if(side>0 ? (a>=level || b>level) : (a<=level || b<level)) ok=false;
      }
      if(ok) return level;
   }
   return 0.0;
}

void LabEnter(const int dir)
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0) return;
   double price=(dir>0?tick.ask:tick.bid),atr=0.0;
   if(InpLabStopAtr>0.0 || InpLabTargetAtr>0.0) { atr=LabValue(g_lab_atr); if(atr<=0.0) return; }
   double dist=(InpLabStopAtr>0.0?InpLabStopAtr*atr:price*MathAbs(InpEmergencyStopPercent)/100.0);
   int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   double stop=NormalizeDouble(price-dir*dist,digits),target=(InpLabTargetAtr>0.0?NormalizeDouble(price+dir*InpLabTargetAtr*atr,digits):0.0);
   double lots=LotsForRisk(price,price-dist);
   if(lots<=0.0) return;
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(InpMaxDeviationPoints);
   bool ok=(dir>0?trade.Buy(lots,_Symbol,0.0,stop,target,"Overnight lab"):trade.Sell(lots,_Symbol,0.0,stop,target,"Overnight lab"));
   if(ok) { g_lab_R=dist; g_lab_locked=false; }
   else Print("Overnight lab entry failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
}

void LabManage(const MqlDateTime &now_ny)
{
   ulong ticket=0; datetime opened=0;
   if(!SelectOurPosition(ticket,opened)) return;
   if(now_ny.day_of_week>=1 && now_ny.day_of_week<=5)
   {
      MqlDateTime e=now_ny; e.hour=InpLabExit/60; e.min=InpLabExit%60; e.sec=0;
      datetime exit_time=NewYorkToServer(e);
      if(TimeCurrent()>=exit_time && opened<exit_time)
      {
         trade.SetExpertMagicNumber((ulong)InpMagic);
         trade.SetTypeFillingBySymbol(_Symbol);
         trade.SetDeviationInPoints(InpMaxDeviationPoints);
         if(!trade.PositionClose(ticket)) Print("Overnight lab exit failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
         return;
      }
   }
   if(InpLabLockAt<=0.0 || g_lab_locked || g_lab_R<=0.0) return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   bool is_long=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY);
   double open=PositionGetDouble(POSITION_PRICE_OPEN),gain=(is_long?tick.bid-open:open-tick.ask);
   if(gain<InpLabLockAt*g_lab_R) return;
   double stop=NormalizeDouble(is_long?open+InpLabLockTo*g_lab_R:open-InpLabLockTo*g_lab_R,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
   trade.SetExpertMagicNumber((ulong)InpMagic);
   if(trade.PositionModify(ticket,stop,PositionGetDouble(POSITION_TP))) g_lab_locked=true;
}

void LabEntry(const MqlDateTime &now_ny)
{
   if(!InpEnableTrading || now_ny.day_of_week<1 || now_ny.day_of_week>5) return;
   int minute=now_ny.hour*60+now_ny.min;
   if(minute<InpLabEntryStart || minute>=InpLabEntryEnd) return;
   ulong ticket=0; datetime opened=0;
   if(SelectOurPosition(ticket,opened)) return;
   MqlDateTime session;
   if(!LabSession(now_ny,session)) return;
   int key=DateKey(session);
   if(g_lab_done==key) return;
   if(g_lab_checked!=key) { g_lab_checked=key; g_lab_ok=LabNightOk(session); g_lab_armed=false; g_lab_bar=0; }
   if(!g_lab_ok) return;
   int side=(InpLabDirection==0?1:InpLabDirection);
   if(InpLabEntryType==0)
   {
      g_lab_done=key;
      if(InpLabRSILevel>0.0)
      {
         double rsi=LabValue(g_lab_rsi);
         if(rsi<=0.0 || (side>0 ? rsi>=InpLabRSILevel : rsi<=100.0-InpLabRSILevel)) return;
      }
      LabEnter(side);
      return;
   }
   datetime bar=iTime(_Symbol,InpLabTF,0);
   if(bar==g_lab_bar) return;
   g_lab_bar=bar;
   MqlDateTime w=now_ny; w.hour=InpLabEntryStart/60; w.min=InpLabEntryStart%60; w.sec=0;
   if(iTime(_Symbol,InpLabTF,1)<NewYorkToServer(w)) return;
   if(InpLabRSILevel<=0.0) g_lab_armed=true;
   else
   {
      double rsi=LabValue(g_lab_rsi);
      if(rsi>0.0 && (side>0 ? rsi<InpLabRSILevel : rsi>100.0-InpLabRSILevel)) g_lab_armed=true;
   }
   if(!g_lab_armed) return;
   if(InpLabSwingBars>0)
   {
      double level=LabSwing(side),close=iClose(_Symbol,InpLabTF,1);
      if(level<=0.0 || (side>0 ? close<=level : close>=level)) return;
   }
   g_lab_done=key;
   LabEnter(InpLabDirection==0 ? ((MathRand()&1)==1?1:-1) : side);
}

void ProcessStrategy()
{
   if(InpLabEnabled)
   {
      datetime lab_now=TimeCurrent();
      if(lab_now<=0) return;
      MqlDateTime lab_ny; TimeToStruct(ServerToNewYork(lab_now),lab_ny);
      LabManage(lab_ny);
      LabEntry(lab_ny);
      return;
   }
''')
    s = sub1(s, '   EventSetTimer(15);\n', '''   if(InpLabEnabled)
   {
      MathSrand(InpLabSeed);
      if(InpLabRSILevel>0.0) { g_lab_rsi=iRSI(_Symbol,InpLabTF,InpLabRSIPeriod,PRICE_CLOSE); if(g_lab_rsi==INVALID_HANDLE) return INIT_FAILED; }
      if(InpLabStopAtr>0.0 || InpLabTargetAtr>0.0) { g_lab_atr=iATR(_Symbol,InpLabTF,InpLabAtrPeriod); if(g_lab_atr==INVALID_HANDLE) return INIT_FAILED; }
   }
   EventSetTimer(15);
''')
    SRC.write_text(s, encoding='utf-8'); editor = harness().TESTER / 'MetaEditor64.exe'; log = SRC.with_suffix('.compile.log'); started = time.time()
    subprocess.run(f'"{editor}" /portable /compile:"{SRC}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=300)
    r = log.read_bytes(); text = r.decode('utf-16' if r.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'); assert '0 errors, 0 warnings' in text, text[-2500:]; assert SRC.with_suffix('.ex5').stat().st_mtime >= started - 2; print('COMPILED', flush=True)


def setup(b, model, window):
    inputs = prod_inputs(); dest = b.TESTER / 'MQL5/Experts/CalyxOvernightLab'; dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC.with_suffix('.ex5'), dest / 'overnight-lab.ex5'); shutil.copy2(PROD / 'Nasdaq Overnight Negative Day EA.ex5', dest / 'overnight-prod.ex5')
    b.CONFIG.update(periods={window: dot(START)}, end_date=dot(END), deposit=10000, currency='USD', model=model, execution_delay_ms=150, profile='Calyx Research Empty', timeout_seconds=14400, expert_dir='CalyxOvernightLab', expert_file='overnight-lab.ex5', controls={}, variants={}, common_inputs=inputs, period='M1')
    return inputs


def run(b, key, window, cfg, expert='overnight-lab.ex5'):
    b.CONFIG['expert_file'] = expert; b.CONFIG['variants'][key] = {'label': key, 'inputs': cfg}
    for attempt in range(4):
        try:
            return b.run_case(SYM, key, window)
        except SystemExit:
            print('RETRY' if attempt < 3 else 'CASE FAILED', key, flush=True); time.sleep(60)


def ledger(key, window='all'):
    return json.loads(gzip.open(H / 'native' / f'nw-{SYM}-{key}-{window}' / 'trades.json.gz').read())


def native():
    b = harness(); assert not b.isolated_running(), 'Tester is occupied'; setup(b, 1, 'all')
    run(b, 'PRODEX5', 'all', {}, 'overnight-prod.ex5'); run(b, 'PROD', 'all', dict(InpLabEnabled='false'))
    sig = lambda T: [(t['open_time'], t['close_time'], t['side'], t['volume'], t['net_profit']) for t in sorted(T, key=lambda t: t['open_time'])]  # noqa: E731
    same = sig(ledger('PRODEX5')) == sig(ledger('PROD')); print('PARITY', same, len(ledger('PROD')), flush=True); assert same, 'research EA differs from production'
    for key, change in VARIANTS.items():
        run(b, key, 'all', dict(LAB_BASE, **change)); print('DONE', key, flush=True)
    print('ALL DONE', datetime.now(timezone.utc).isoformat(), flush=True)


def rows_of(key, window='all'):
    bal = 1e4; rows = []
    for t in sorted(ledger(key, window), key=lambda t: t['close_time']):
        rows.append(dict(o=t['open_time'], c=t['close_time'], r=t['net_profit'] / (0.01 * bal), net=t['net_profit'], side=t['side'])); bal += t['net_profit']
    return rows


def stats(rows, a, b_):
    x = [r for r in rows if a <= r['o'][:10] < b_]; gw = sum(r['r'] for r in x if r['r'] > 0); gl = -sum(r['r'] for r in x if r['r'] < 0); eq = peak = dd = 0.0; days = defaultdict(float)
    for r in x:
        eq += r['r']; peak = max(peak, eq); dd = max(dd, peak - eq); days[r['c'][:10]] += r['r']
    months = (datetime.fromisoformat(b_) - datetime.fromisoformat(a)).days / 30.4375; weekdays = months * 21.74
    best5 = sum(sorted(days.values(), reverse=True)[:5])
    return dict(trades=len(x), per_month=round(len(x) / months, 2), per_weekday=round(len(x) / weekdays, 3), total_r=round(sum(r['r'] for r in x), 2), mean_r=round(sum(r['r'] for r in x) / max(1, len(x)), 4), pf=round(gw / gl, 3) if gl else None, win=round(100 * sum(r['r'] > 0 for r in x) / max(1, len(x)), 1), closed_dd_r=round(dd, 2), ret_dd=round(sum(r['r'] for r in x) / dd, 2) if dd else None, worst_day_r=round(min(days.values()), 2) if days else None, without_best5=round(sum(r['r'] for r in x) - best5, 2))


def report():
    keys = ['PROD'] + list(VARIANTS); out = dict(split=WINDOWS, variants={}, failed=[]); B = json.loads((PACKAGE / 'Nasdaq 5M Candle Rule 2026-11-05/BH_COMPARE.json').read_text(encoding='utf-8'))
    for k in keys:
        d = H / 'native' / f'nw-{SYM}-{k}-all'
        if not (d / 'run.json').exists() or not json.loads((d / 'run.json').read_text(encoding='utf-8')).get('ok'): out['failed'].append(k); continue
        rows = rows_of(k); meta = json.loads((d / 'run.json').read_text(encoding='utf-8')); m = meta['metrics']
        out['variants'][k] = dict(windows={w: stats(rows, *v) for w, v in WINDOWS.items()}, native_return_pct=round(sum(r['net'] for r in rows) / 100, 2), native_pf=m.get('profit_factor'), equity_dd_relative_pct=buy_hold.relative_equity_dd(d / f'{d.name}.htm.gz'), flags=meta.get('journal_flags'))
    V = out['variants']; P = V['PROD']['windows']; passed = []
    for k, v in V.items():
        w = v['windows']; all_ = w['all']; checks = dict(pf=(all_['pf'] or 0) >= 1.15, positive=all(w[x]['total_r'] > 0 for x in ('dev', 'val', 'oos')), dev_ret_dd=(w['dev']['ret_dd'] or -9) > (P['dev']['ret_dd'] or 0), freq=all_['per_month'] >= 2, without_best5=all_['without_best5'] > 0, controls=all(all_['total_r'] > V[c]['windows']['all']['total_r'] for c in CONTROLS.get(k, ()) if c in V))
        v['checks'] = checks; v['improves'] = k not in NOT_CANDIDATES and all(checks.values())
        if v['improves']: passed.append(k)
    finalists = sorted(passed, key=lambda k: -(V[k]['windows']['dev']['ret_dd'] or -9))[:3]; out['finalists'] = finalists; (H / 'FINALISTS.json').write_text(json.dumps(finalists), encoding='utf-8'); out['buy_hold'] = {w: {x: B[w]['hold'][x] for x in ('return_pct', 'max_dd_pct')} for w in ('all', 'dev', 'val', 'oos') if w in B}
    L = [f"Native Model 1 screen, USTEC M1, $10k, 1%, {START} to {END}. Failed runs: {out['failed'] or 'none'}. Buy and hold: {out['buy_hold']}.", '', '| Key | Trades | /month | /weekday | Win % | PF | Total R | Mean R | Closed DD R | Equity DD % | Dev R | Val R | OOS R | Last year R | Without best 5 days | Improves? |', '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for k in sorted(V, key=lambda k: -V[k]['windows']['all']['total_r']):
        v = V[k]; a = v['windows']['all']; w = v['windows']; L.append(f"| {k} | {a['trades']} | {a['per_month']} | {a['per_weekday']} | {a['win']} | {a['pf']} | {a['total_r']:+.1f} | {a['mean_r']:+.3f} | {a['closed_dd_r']} | {v['equity_dd_relative_pct']} | {w['dev']['total_r']:+.1f} | {w['val']['total_r']:+.1f} | {w['oos']['total_r']:+.1f} | {w['last_year']['total_r']:+.1f} | {a['without_best5']:+.1f} | {'YES' if v['improves'] else 'no: ' + ', '.join(c for c, ok in v['checks'].items() if not ok)} |")
    L += ['', f'Finalists for Model 4 and Monte Carlo: {finalists or "none"}']
    (H / 'RESULTS.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); (H / 'RESULTS.md').write_text('\n'.join(L) + '\n', encoding='utf-8'); print('\n'.join(L))


def out_trades_per_year(rows):
    return len(rows) / ((datetime.fromisoformat(END) - datetime.fromisoformat(START)).days / 365.25)


def confirm():
    b = harness(); assert not b.isolated_running(), 'Tester is occupied'; setup(b, 4, 'm4'); finalists = json.loads((H / 'FINALISTS.json').read_text(encoding='utf-8')); out = {}
    for k in ['PROD'] + finalists:
        run(b, k, 'm4', dict(InpLabEnabled='false') if k == 'PROD' else dict(LAB_BASE, **VARIANTS[k])); d = H / 'native' / f'nw-{SYM}-{k}-m4'; rows = rows_of(k, 'm4')
        out[k] = dict(windows={w: stats(rows, *v) for w, v in WINDOWS.items()}, equity_dd_relative_pct=buy_hold.relative_equity_dd(d / f'{d.name}.htm.gz'), three_way=robustness.three_monte_carlo([r['r'] for r in rows], runs=1000, seed=20261104), three_way_1y=robustness.three_monte_carlo([r['r'] for r in rows], runs=1000, seed=20261104, horizon=round(out_trades_per_year(rows))))
    (H / 'CONFIRM.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); print(json.dumps(out, indent=1, default=str)[:6000])


if __name__ == '__main__':
    {'ea': build_ea, 'native': native, 'report': report, 'confirm': confirm}[sys.argv[1]]()

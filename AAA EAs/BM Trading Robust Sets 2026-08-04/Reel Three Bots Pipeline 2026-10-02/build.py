"""Mechanical adaptation of the frozen raw rules; original files never edited."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
RAW=BASE/'Reel Three Bots Raw 2026-10-02'
assert hashlib.sha256((RAW/'EA/ReelRules.mqh').read_bytes()).hexdigest()=='0a93ec07e40adf8deac1e20ee22e64e24a2bccf508e53ef0e8466baa406d0c4e'
def replace_function(text,name,new):
    a=text.index(name+'(');a=text.rfind('\n',0,a)+1;b=text.index('{',a);level=1;i=b+1
    while level:
        if text[i]=='{':level+=1
        if text[i]=='}':level-=1
        i+=1
    return text[:a]+new+'\n'+text[i:]
body=(RAW/'EA/PortfolioModules.mqh').read_text()
body=body.replace('public:\n','public:\n#include "Extensions.mqh"\n',1)
body=replace_function(body,'Market','bool Market(int side,double sl,double tp,string why){return Execute(side,sl,tp,why);}')
body=replace_function(body,'Range','void Range(datetime now){RangeFeature(now);}')
body=replace_function(body,'Donchian','void Donchian(datetime now){DonFeature(now);}')
# ATR native smoothing stays identical. Only frame, period, threshold, close-edge become parameters.
body=body.replace('iATR(m_symbol,PERIOD_H1,200)','iATR(m_symbol,TF(),(int)P(28))')
a=body.index('void AtrCandle(');b=body.index('void Donchian(',a)
atr=body[a:b].replace('PERIOD_H1','TF()').replace('2.5*av[0]','P(20)*av[0]').replace('.25*range','P(21)*range')
atr=atr.replace('if(side==0)return;candidates++;','if(side==0)return;candidates++;lastRuleSide=side;if(Control)side=RandSide(now);')
atr=atr.replace('if(OwnPos(t))','if(CountPositions()>=(int)P(25))')
atr=atr.replace('ulong t;','')
atr=atr.replace('r[0].close*(1-side*.005)','r[0].close*(1-side*P(5)/100)').replace('r[0].close*(1+side*.035)','r[0].close*(1+side*P(5)*P(6)/100)')
atr=atr.replace('double sl=Price','double sl=Price').replace('tp=Price(r[0].close*(1+side*P(5)*P(6)/100))','tp=P(6)>0?Price(r[0].close*(1+side*P(5)*P(6)/100)):0')
body=body[:a]+atr+body[b:]
body=body.replace('datetime now=TimeCurrent();if(BOT==1)','datetime now=TimeCurrent();Manage();if(BOT==1)')
body=body.replace('if(BOT==3){DonchianTrail();Donchian(now);}','if(BOT==3){if((int)P(7)==9)DonchianTrail();Donchian(now);}')
body=body.replace('entries++;if(BOT==1)','entries++;dayEntries++;Capture();if(BOT==3){if(lastRuleSide>0)buyArmed=false;else if(lastRuleSide<0)sellArmed=false;}if(BOT==1)')
body=body.replace('void OnDeinit(const int why){','void OnDeinit(const int why){ReleaseFeatures();')
body=body.replace('SYMBOL_TRADE_STOPS_LEVEL)*_Point','SYMBOL_TRADE_STOPS_LEVEL)*SymbolInfoDouble(m_symbol,SYMBOL_POINT)')
body=replace_function(body,'CancelOrders','void CancelOrders(){for(int i=OrdersTotal()-1;i>=0;i--){ulong t=OrderGetTicket(i);if(t&&OrderGetInteger(ORDER_MAGIC)==InpMagic&&OrderGetString(ORDER_SYMBOL)==m_symbol){if(!trade.OrderDelete(t)||trade.ResultRetcode()!=TRADE_RETCODE_DONE){cancelFails++;PrintFormat("RP_CANCEL_FAIL %u",trade.ResultRetcode());}}}}')
body=body.replace('FileWrite(traceFile,"epoch","balance","equity");','')
# Count the original Donchian trail without changing its decision rule.
body=body.replace('if(!trade.PositionModify(t,want,tp)&&trade.ResultRetcode()!=TRADE_RETCODE_NO_CHANGES)', 'bool changed=trade.PositionModify(t,want,tp);if(changed&&trade.ResultRetcode()==TRADE_RETCODE_DONE)trailCount++;else if(trade.ResultRetcode()!=TRADE_RETCODE_NO_CHANGES)')
(ROOT/'EA/Engine.mqh').write_text(body,encoding='utf-8')
shutil.copy2(BASE/'QuantLab Gold Trio Pipeline 2026-09-30/metrics.py',ROOT/'metrics.py')
config={'date':'2026-10-02','risk':'1% current shared balance; floor volume; skip below minimum','exploratory_failure_override':True,'policy':json.loads((BASE.parent/'Calyx Research Pipeline/pipeline-policy.json').read_text()),'search_space':json.loads((BASE/'OPTIMIZATION SEARCH SPACE.json').read_text()),'controls':{'seeds':[301,307,311,313,317],'gold':'direction randomised conditional on raw trigger','range':'random direction at range-end, same range-stop width and flat'},'end_exclusive':'2026-10-02','original_common_sha':hashlib.sha256((RAW/'EA/ReelRules.mqh').read_bytes()).hexdigest(),'protocol_sha':hashlib.sha256((ROOT/'PROTOCOL.txt').read_bytes()).hexdigest()}
p=ROOT/'run-config.json'
if p.exists():assert json.loads(p.read_text())==config,'Frozen protocol changed'
else:p.write_text(json.dumps(config,indent=2),encoding='utf-8')
print('Search engine generated; frozen protocol and raw source verified.')

# Reuse the audited native execution/export layer, not the older strategy/search.
source=(BASE/'QuantLab Gold Trio Pipeline 2026-09-30/search.py').read_text()
source=source[:source.index('# ---------------- search space')]
a=source.index('FIELDS =');b=source.index('\n\ndef save(',a)
source=source[:a]+'''FIELDS = 'module tf entry offset stop sl rr trail start dist exit session direction filter day max_day hold flat season p1 p2 p3 range_start range_end range_flat maxpos reentry channel_tf atr_period partial stopbuffer adx_min regime_min regime_max'.split()
FAIL_KEYS = ['entry_fail','close_fail','modify_fail','cancel_fail','bad_risk']
MAGIC = 9801000
'''+source[b:]
source=source.replace("RAW = BASE / 'QuantLab Gold Trio Raw 2026-09-30'", "RAW = BASE / 'Reel Three Bots Raw 2026-10-02'")
source=source.replace('CalyxGoldTrioSearch20260930','ReelPipeline20261002').replace('GoldTrioSearch20260930','ReelPipeline20261002').replace('GoldTrioSearch','ReelSearch').replace('gold-trio-search-20260930','reel-search-20261002')
source=source.replace("def to_date(end):\n    return end if end == DATA_END else (datetime.strptime(end, '%Y.%m.%d') - timedelta(days=1)).strftime('%Y.%m.%d')", "def to_date(end):\n    return end")
source=source.replace('warmup=180, slots=None):','warmup=180, slots=None, risk=1, seed=301):')
source=source.replace('    folder = OUT / name','    if optimize and len(cases)==1: optimize=False\n    folder = OUT / name',1)
source=source.replace("slots=slots, logic=sha(EA / 'TrioLogic.mqh'), protocol=sha(ROOT / 'PROTOCOL.md')", "slots=slots, risk=risk, seed=seed, logic={p:sha(EA/p) for p in ['Engine.mqh','Extensions.mqh','Main.mqh']}, protocol=sha(ROOT/'PROTOCOL.txt')")
source=source.replace('TrioLogic.mqh','Main.mqh')
source=source.replace("EA / 'Main.mqh'):","EA / 'Main.mqh', EA/'Engine.mqh', EA/'Extensions.mqh'):")
source=source.replace("tag = 'gts-'", "tag = 'reel-'")
source=source.replace('InpRiskPercent=1, InpSeed=300930','InpRiskPercent=risk, InpFixedRiskUSD=100, InpSeed=seed')
source=source.replace("setname = tag + '.set'", "symbol = 'DE30' if all(c['module']==0 for c in cases) else 'XAUUSD'\n    if optimize: assert len({c['module'] for c in cases})==1,'Do not optimise mixed symbols'\n    setname = tag + '.set'")
source=source.replace('Symbol=XAUUSD','Symbol={symbol}').replace("('XAUUSD', warm, todate)","(symbol, warm, todate)")
source=source.replace("native_metrics['equity_dd_pct'] = _number(_metric(rb, 'Equity Drawdown Relative'))", "native_metrics['equity_dd_pct'] = _number(_metric(rb, 'Equity Drawdown Relative'))\n        native_metrics['history_quality'] = _metric(rb, 'History Quality')")
source=source.replace("clean = not any(net[k] for k in FAIL_KEYS) and stopouts == 0", "clean = not any(net[k] for k in FAIL_KEYS) and stopouts == 0\n        if len(d): assert (d.actual_risk > 0).all() and (d.requested_risk > 0).all(), 'Missing initial risk'\n        tick_notes=sorted(set(re.findall(r'[^\\n]*(?:real ticks begin|real ticks.*%|real ticks absent|generated ticks|ticks discarded)[^\\n]*',journal)))[:20]")
source=source.replace("report_sha=sha(rp), stopouts_in_batch=stopouts", "report_sha=sha(rp), stopouts_in_batch=stopouts, native_metrics=native_metrics, tick_notes=tick_notes")
source=source.replace("parameters=cases[i] if optimize else None", "parameters=cases[i] if optimize or (len(cases)==1 and slots is None) else None")
source=source.replace("parameters_sha=digest(cases[i]) if optimize else None", "parameters_sha=digest(cases[i]) if optimize or (len(cases)==1 and slots is None) else None")
(ROOT/'native_runner.py').write_text(source,encoding='utf-8')

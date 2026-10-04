"""Four-symbol native fault checks. Artificial rejections, NOT performance evidence.
Use only the isolated terminal, a tester-only private EA and the frozen official
calendar. Inject definitive rejection before any real broker submission, repair
at current quotes, manually close a leg and reload acknowledged side masks.
"""
from pathlib import Path
import importlib.util,inspect,json,re,shutil,gzip

R=Path(__file__).resolve().parent;B=R.parent;OLD=B/'News XAU Placement Fix 2026-10-03'
spec=importlib.util.spec_from_file_location('placement_engine',OLD/'run.py')
engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)
engine.R=R;engine.DEST=engine.T/'MQL5/Experts/AAA Research/NewsAll20261003'
engine.SYMBOL='XAUUSD';engine.HOLD=30
# Same independent native report/deal/parser engine, adjusted for asset/hold.
body=inspect.getsource(engine.run).replace('NewsFix20261003','NewsAll20261003').replace('newsfix20261003','newsall20261003')
body=body.replace('Symbol=XAUUSD','Symbol={SYMBOL}').replace('int(parts[1])+30+(delay/1000)+2','int(parts[1])+HOLD+(delay/1000)+2')
exec(body,engine.__dict__)

SHIM=r'''
class NP_FaultTrade : public CTrade
{
 private: int m_buy_failures,m_sell_failures;uint m_forced;
 public:
 NP_FaultTrade(void){m_buy_failures=0;m_sell_failures=0;m_forced=0;}
 uint ResultRetcode(void) const {return m_forced>0 ? m_forced : CTrade::ResultRetcode();}
 string ResultRetcodeDescription(void) const {return m_forced>0 ? "TEST definitive rejection, no request sent" : CTrade::ResultRetcodeDescription();}
 bool BuyStop(const double volume,const double price,const string symbol=NULL,const double sl=0,const double tp=0,const ENUM_ORDER_TYPE_TIME type_time=ORDER_TIME_GTC,const datetime expiration=0,const string comment="")
 {if(m_buy_failures<2){m_buy_failures++;m_forced=TRADE_RETCODE_INVALID_STOPS;Print("FAULT_BUY_REJECT_NO_SEND|",m_buy_failures);return false;}m_forced=0;return CTrade::BuyStop(volume,price,symbol,sl,tp,type_time,expiration,comment);}
 bool SellStop(const double volume,const double price,const string symbol=NULL,const double sl=0,const double tp=0,const ENUM_ORDER_TYPE_TIME type_time=ORDER_TIME_GTC,const datetime expiration=0,const string comment="")
 {if(m_sell_failures<1){m_sell_failures++;m_forced=TRADE_RETCODE_INVALID_PRICE;Print("FAULT_SELL_REJECT_NO_SEND");return false;}m_forced=0;return CTrade::SellStop(volume,price,symbol,sl,tp,type_time,expiration,comment);}
 bool Buy(const double volume,const string symbol=NULL,const double price=0,const double sl=0,const double tp=0,const string comment="")
 {m_forced=0;return CTrade::Buy(volume,symbol,price,sl,tp,comment);}
 bool Sell(const double volume,const string symbol=NULL,const double price=0,const double sl=0,const double tp=0,const string comment="")
 {m_forced=0;return CTrade::Sell(volume,symbol,price,sl,tp,comment);}
};
NP_FaultTrade AAA_Trade;
'''

def main():
 engine.free();snapshot=R/'snapshot';snapshot.mkdir(exist_ok=True)
 for p in (OLD/'snapshot').glob('*.mqh'):shutil.copy2(p,snapshot/p.name)
 shutil.copy2(OLD/'snapshot/Current.set',snapshot/'Current.set')
 common=engine.read(snapshot/'AAA_Final_Common.mqh')
 assert 'CTrade AAA_Trade;' in common
 (snapshot/'AAA_Final_Common.mqh').write_text(common.replace('CTrade AAA_Trade;',SHIM))
 results=[]
 for asset,symbol,hold,setname in [
  ('XAU','XAUUSD',30,'12A News Pulse XAU Two Sided - HARD 1.5 TOTAL.set'),
  ('XAG','XAGUSD',60,'12B News Pulse XAG Two Sided - HARD 1.5 TOTAL.set'),
  ('BTC','BTCUSD',600,'12C News Pulse BTC Two Sided - HARD 1.5 TOTAL.set'),
  ('EURUSD','EURUSD',300,'12D News Pulse EURUSD Event Specific - HARD 1.5 TOTAL.set')]:
  engine.SYMBOL=symbol;engine.HOLD=hold;engine.SET=B/'Selected Portfolio Settings 2026-09-01'/setname
  folder='AAA Final News Pulse XAU Event Specific EA' if asset=='XAU' else 'AAA Final News Pulse Multi Asset Event EA'
  source=B/'AAA Final EAs'/folder/(folder+'.mq5');name='New-'+asset+'-fault'
  body=engine.read(source).replace('\r\n','\n')
  body=re.sub(r'#include "[^"\r\n]*[/\\]([^"/\\]+)"',r'#include "\1"',body)
  body=body.replace('int OnInit()\n{','int OnInit()\n{\n if(!(bool)MQLInfoInteger(MQL_TESTER)) return INIT_FAILED;')
  assert 'if(!(bool)MQLInfoInteger(MQL_TESTER)) return INIT_FAILED;' in body
  body=body.replace('int      g_side_required=0;','bool g_fault_skip_sell=true,g_fault_restored=false;\nint      g_side_required=0;',1)
  anchor='g_event_buy_entry=buy_entry;g_event_sell_entry=sell_entry;';assert anchor in body
  body=body.replace(anchor,'''double test_gap=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*SymbolInfoDouble(_Symbol,SYMBOL_POINT)+10*SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
      g_event_buy_entry=tick.ask+MathMax(g_np_offset,test_gap);g_event_sell_entry=tick.bid-MathMax(g_np_offset,test_gap);''',1)
  anchor='if(allow_sell && (g_side_required & 2)!=0) NP_SendSide(false,g_event_sell_entry,side_risk,expiry,prefix+"S");';assert anchor in body
  body=body.replace(anchor,'''if(allow_sell && (g_side_required & 2)!=0){if(g_fault_skip_sell){g_fault_skip_sell=false;Print("FAULT_SKIP_SELL_ONCE");}else NP_SendSide(false,g_event_sell_entry,side_risk,expiry,prefix+"S");}''',1)
  anchor='if(!complete)\n   {';assert anchor in body
  body=body.replace(anchor,'''if(complete && !g_fault_restored){g_fault_restored=true;NP_ClosePositions();g_side_accepted=0;g_side_inflight=0;g_side_required=0;NP_LoadSideState();NP_ReconcileSides();Print("FAULT_RESTORED|accepted=",g_side_accepted,"|required=",g_side_required);}
   if(!complete)
   {''',1)
  (snapshot/(name+'.mq5')).write_text(body)
  engine.compile_one(name)
  result=engine.run(name,150,'2026.10.02','2026.10.03')
  journal=gzip.decompress((R/'native'/result['tag']/'journal.gz').read_bytes()).decode()
  for marker in ['FAULT_BUY_REJECT_NO_SEND|1','FAULT_BUY_REJECT_NO_SEND|2','NP_FRESH_QUOTE_RETRY|',
   'NP_MARKET_FALLBACK|','FAULT_SKIP_SELL_ONCE','FAULT_SELL_REJECT_NO_SEND','FAULT_RESTORED|accepted=3|required=3']:
   assert marker in journal,(asset,marker)
  assert result['max_same_side_per_event']==1 and result['closure_violations']==0
  assert list(result['audit'][1:3])==['1','1']
  results.append(dict(asset=asset,passed=True,source_sha=engine.sha(source),case=result['tag'],not_performance_evidence=True))
 engine.save(R/'FAULT_CHECK.json',dict(passed=True,not_performance_evidence=True,results=results,
  tested=['two rejected buy pendings -> fresh quote then market buy','missing sell repaired independently',
  'rejected sell pending reanchored at current quote','accepted masks survive manual close/reload','no duplicated side','unchanged timed cleanup']))
 engine.status('PASS: all four native placement-fault cases; not performance evidence')

if __name__=='__main__':main()

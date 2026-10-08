"""Mechanical tester-only parameterisation of the original production source.

All research switches default OFF. Mandatory original-binary ledger parity precedes
search. No production source or compiled EA is modified.
"""
from pathlib import Path
import re,json,hashlib
R=Path(__file__).resolve().parent;B=R.parent
SRC=B/'Nasdaq 5M DI ATR Deployment 2026-09-28/EA/Nasdaq 5M DI Wide ATR EA.mq5'
PRESET=B/'Selected Portfolio Settings 2026-09-01/11 Nasdaq 5M - DI WIDE 0P60PCT ATR6 NO TP - 1PCT.set'
PATTERN=r'^input\s+(\w+)\s+(\w+)\s*=\s*([^;]+);'
EXTRA_TYPES={
 'ResearchAnchor':'int','ResearchADXMinimum':'double','ResearchADXMaximum':'double',
 'ResearchRequireBodyDirection':'bool','ResearchSkipWeekday':'int','ResearchBerlinClose':'bool',
}
DEFAULT_EXTRA={k:0 for k in EXTRA_TYPES}
def literal(value):
 v=value.split('//')[0].strip()
 if v in ('true','false'):return int(v=='true')
 enums={'PERIOD_M1':1,'PERIOD_M5':5,'PERIOD_M15':15,'PERIOD_M30':30,'N5_STOP_ATR':0,'N5_STOP_SIGNAL_CANDLE':1,'N5_STOP_PERCENT':2,'MODE_EMA':1,'DTS_SESSION_ALL':0}
 if v in enums:return enums[v]
 return float(v)
def registry():
 source=SRC.read_text(encoding='utf-8-sig')
 helper=(SRC.parent/'DynamicTrailingSessionFilter.mqh').read_text(encoding='utf-8-sig')
 decls=re.findall(PATTERN,source+'\n'+helper,re.M)
 types={name:kind for kind,name,value in decls}
 raw={name:literal(value) for kind,name,value in decls}
 for line in PRESET.read_text(encoding='utf-8-sig').splitlines():
  if '=' in line and not line.startswith(';'):
   k,v=line.split('=',1)
   if k in raw:raw[k]=literal(v.split('||')[0])
 types.update(EXTRA_TYPES);raw.update(DEFAULT_EXTRA)
 raw['InpRiskPercent']=1;raw['InpAdaptivePortfolioControls']=0
 assert raw['InpRequireDIAgreement']==1 and raw['InpInitialStopPercent']==.6 and raw['InpUseFixedTarget']==0
 return types,raw
TYPES,RAW=registry();FIELDS=list(TYPES)
PRE=r'''
input int InpCase=0;
input string InpTag="dax-pipeline";
input bool InpVerbose=false;
input double InpRiskPct=1.0;
int ResearchAnchor=0,ResearchSkipWeekday=0;
double ResearchADXMinimum=0,ResearchADXMaximum=0;
bool ResearchRequireBodyDirection=false,ResearchBerlinClose=false;
int dax_equity_file=INVALID_HANDLE,dax_quotes_file=INVALID_HANDLE;
datetime dax_minute=0;
long dax_ticks=0;
int dax_failed_entries=0,dax_failed_updates=0,dax_closed_updates=0;
string DaxTag(){return InpTag+"-"+(string)InpCase;}
'''
EXTRA=r'''
datetime ServerToBerlin(const datetime server_time){
 datetime utc=server_time-ServerUtcOffsetSeconds();MqlDateTime x;TimeToStruct(utc,x);
 MqlDateTime march,october;TimeToStruct(BuildUtcTime(x.year,3,31,1),march);TimeToStruct(BuildUtcTime(x.year,10,31,1),october);
 datetime begin=BuildUtcTime(x.year,3,31-march.day_of_week,1),end=BuildUtcTime(x.year,10,31-october.day_of_week,1);
 return utc+(utc>=begin && utc<end?2:1)*3600;
}
bool DaxSignalTime(const datetime server_time){
 if(ResearchAnchor==0)return IsNewYorkTime(server_time,InpSignalHourNY,InpSignalMinuteNY);
 if(ResearchAnchor==5)return IsNewYorkTime(server_time,10,0);
 MqlDateTime b;TimeToStruct(ServerToBerlin(server_time),b);
 if(b.day_of_week<1 || b.day_of_week>5)return false;
 int hour=9,minute=0;
 if(ResearchAnchor==1)hour=8;
 if(ResearchAnchor==3)minute=30;
 if(ResearchAnchor==4)hour=10;
 if(ResearchAnchor==6){hour=8;minute=30;}
 if(ResearchAnchor==7){hour=15;minute=30;}
 return b.hour==hour && b.min==minute;
}
bool DaxQuality(const int direction,const MqlRates &signal){
 if(ResearchRequireBodyDirection && (direction>0?signal.close<=signal.open:signal.close>=signal.open))return false;
 MqlDateTime d;TimeToStruct(ServerToBerlin(signal.time),d);
 if((d.day_of_week==1 && (ResearchSkipWeekday==1 || ResearchSkipWeekday==3)) || (d.day_of_week==5 && (ResearchSkipWeekday==2 || ResearchSkipWeekday==3)))return false;
 if(ResearchADXMinimum>0 || ResearchADXMaximum>0){
  double a=0;if(!ReadIndicatorValue(g_adx_handle,1,a))return false;
  if(ResearchADXMinimum>0 && a<ResearchADXMinimum)return false;
  if(ResearchADXMaximum>0 && a>ResearchADXMaximum)return false;
 }
 return true;
}
void DaxSnapshot(){
 dax_ticks++;datetime now=TimeCurrent();
 if(dax_equity_file==INVALID_HANDLE || now/60==dax_minute)return;
 dax_minute=now/60;FileWrite(dax_equity_file,(long)now,AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY));
}
bool DaxOpenAudit(){
 if(!InpVerbose)return true;
 dax_equity_file=FileOpen(DaxTag()+"-equity.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');
 dax_quotes_file=FileOpen(DaxTag()+"-quotes.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');
 if(dax_equity_file==INVALID_HANDLE || dax_quotes_file==INVALID_HANDLE)return false;
 FileWrite(dax_equity_file,"epoch","balance","equity");
 FileWrite(dax_quotes_file,"deal","position_id","epoch","entry","bid","ask","volume","spread_cash");
 return true;
}
double OnTester(){
 HistorySelect(0,TimeCurrent());
 int out=FileOpen(DaxTag()+"-deals.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');
 if(out==INVALID_HANDLE)return -1e99;
 FileWrite(out,"ticket","position_id","epoch","entry","type","volume","price","profit","commission","swap","fee","reason","initial_sl","initial_tp");
 ulong owned[];
 for(int i=0;i<HistoryDealsTotal();i++){
  ulong deal=HistoryDealGetTicket(i);if(deal==0 || HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic || HistoryDealGetInteger(deal,DEAL_ENTRY)!=DEAL_ENTRY_IN)continue;
  int n=ArraySize(owned);ArrayResize(owned,n+1);owned[n]=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);
 }
 for(int i=0;i<HistoryDealsTotal();i++){
  ulong deal=HistoryDealGetTicket(i);if(deal==0)continue;
  ulong id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);bool ours=false;
  for(int j=0;j<ArraySize(owned);j++)if(owned[j]==id){ours=true;break;}if(!ours)continue;
  ulong order=(ulong)HistoryDealGetInteger(deal,DEAL_ORDER);
  FileWrite(out,deal,id,(long)HistoryDealGetInteger(deal,DEAL_TIME),HistoryDealGetInteger(deal,DEAL_ENTRY),HistoryDealGetInteger(deal,DEAL_TYPE),
   HistoryDealGetDouble(deal,DEAL_VOLUME),HistoryDealGetDouble(deal,DEAL_PRICE),HistoryDealGetDouble(deal,DEAL_PROFIT),HistoryDealGetDouble(deal,DEAL_COMMISSION),
   HistoryDealGetDouble(deal,DEAL_SWAP),HistoryDealGetDouble(deal,DEAL_FEE),HistoryDealGetInteger(deal,DEAL_REASON),HistoryOrderGetDouble(order,ORDER_SL),HistoryOrderGetDouble(order,ORDER_TP));
 }
 FileClose(out);
 out=FileOpen(DaxTag()+"-stats.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');if(out==INVALID_HANDLE)return -1e99;
 ulong selected=0;
 FileWrite(out,"net","equity_dd","balance_dd","failed_entries","failed_updates","market_closed_updates","balance","open_position","last_quote_epoch","ticks","mt5_sharpe","trades");
 FileWrite(out,TesterStatistics(STAT_PROFIT),TesterStatistics(STAT_EQUITY_DDREL_PERCENT),TesterStatistics(STAT_BALANCE_DDREL_PERCENT),
  dax_failed_entries,dax_failed_updates,dax_closed_updates,AccountInfoDouble(ACCOUNT_BALANCE),(int)SelectOurPosition(selected),(long)TimeCurrent(),dax_ticks,TesterStatistics(STAT_SHARPE_RATIO),TesterStatistics(STAT_TRADES));
 FileClose(out);
 if(dax_equity_file!=INVALID_HANDLE){FileWrite(dax_equity_file,(long)TimeCurrent(),AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY));FileFlush(dax_equity_file);}
 return TesterStatistics(STAT_PROFIT);
}
void OnTradeTransaction(const MqlTradeTransaction &trans,const MqlTradeRequest &request,const MqlTradeResult &result){
 if(dax_quotes_file==INVALID_HANDLE || trans.type!=TRADE_TRANSACTION_DEAL_ADD || trans.deal==0)return;
 if(!HistoryDealSelect(trans.deal))return;
 long magic=HistoryDealGetInteger(trans.deal,DEAL_MAGIC),entry=HistoryDealGetInteger(trans.deal,DEAL_ENTRY);
 if(entry==DEAL_ENTRY_IN && magic!=InpMagic)return;
 MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return;
 double qty=HistoryDealGetDouble(trans.deal,DEAL_VOLUME),cash=0;
 ENUM_ORDER_TYPE kind=HistoryDealGetInteger(trans.deal,DEAL_TYPE)==DEAL_TYPE_BUY?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 bool priced=OrderCalcProfit(kind,_Symbol,qty,tick.bid,tick.ask,cash);
 FileWrite(dax_quotes_file,trans.deal,HistoryDealGetInteger(trans.deal,DEAL_POSITION_ID),(long)TimeCurrent(),entry,tick.bid,tick.ask,qty,priced?MathAbs(cash):-1);
}
'''
def build(cases):
 assert cases and all(set(c)==set(FIELDS) for c in cases)
 source=SRC.read_text(encoding='utf-8-sig')
 source=re.sub(r'^input group[^\n]*\n','',source,flags=re.M)
 source=re.sub(r'^input\s+','',source,flags=re.M)
 source=source.replace('#include "..\\..\\_Shared\\CalyxAdaptivePortfolio.mqh"','#include "CalyxAdaptivePortfolio.mqh"')
 source=source.replace('   if(!DTS_InputsValid()) return INIT_PARAMETERS_INCORRECT;','   if(!MQLInfoInteger(MQL_TESTER) || InpCase<0 || InpCase>=ArrayRange(Cases,0)) return INIT_PARAMETERS_INCORRECT;\n   DaxApply();\n   if(!DaxOpenAudit()) return INIT_FAILED;\n   if(!DTS_InputsValid()) return INIT_PARAMETERS_INCORRECT;')
 source=source.replace('InpSignalTimeframe==PERIOD_M5 ||','InpSignalTimeframe==PERIOD_M3 || InpSignalTimeframe==PERIOD_M5 || InpSignalTimeframe==PERIOD_M10 ||')
 source=source.replace('if(!IsNewYorkTime(rates[1].time,InpSignalHourNY,InpSignalMinuteNY)) return;','if(!DaxSignalTime(rates[1].time)) return;')
 source=source.replace('   if(!DIAgrees(direction)) return;','   if(!DaxQuality(direction,rates[1])) return;\n   if(!DIAgrees(direction)) return;')
 source=source.replace('   if(InpRequireDIAgreement)\n','   if(InpRequireDIAgreement || ResearchADXMinimum>0 || ResearchADXMaximum>0)\n')
 source=source.replace('   if(!g_trade.PositionModify(ticket,NormalizePrice(stop),target))\n     {','   if(!g_trade.PositionModify(ticket,NormalizePrice(stop),target))\n     {\n      dax_failed_updates++; if(g_trade.ResultRetcode()==TRADE_RETCODE_MARKET_CLOSED) dax_closed_updates++;')
 source=source.replace('   else Print("N5EMA order rejected: ",g_trade.ResultRetcodeDescription());','   else {dax_failed_entries++; if(InpVerbose) Print("N5EMA order rejected: ",g_trade.ResultRetcodeDescription());}')
 # Suppress only diagnostic text. Execution and retry behaviour are unchanged.
 source=source.replace('      Print("N5EMA','      if(InpVerbose) Print("N5EMA').replace('      PrintFormat("Risk sizing','      if(InpVerbose) PrintFormat("Risk sizing')
 source=source.replace('   MqlDateTime ny;\n   TimeToStruct(ServerToNewYork(server_time),ny);\n   if(ny.day_of_week<1 || ny.day_of_week>5) return false;','   MqlDateTime ny;\n   TimeToStruct(ResearchBerlinClose?ServerToBerlin(server_time):ServerToNewYork(server_time),ny);\n   if(ResearchBerlinClose) return ny.day_of_week>=1 && ny.day_of_week<=5 && (ny.hour>17 || (ny.hour==17 && ny.min>=25));\n   if(ny.day_of_week<1 || ny.day_of_week>5) return false;')
 source=source.replace('   DTS_ManageDynamicTrailing(InpMagic);','   DaxSnapshot();\n   DTS_ManageDynamicTrailing(InpMagic);')
 source=source.replace('   if(g_ema_handle!=INVALID_HANDLE) IndicatorRelease(g_ema_handle);','   if(dax_equity_file!=INVALID_HANDLE) FileClose(dax_equity_file);\n   if(dax_quotes_file!=INVALID_HANDLE) FileClose(dax_quotes_file);\n   if(g_ema_handle!=INVALID_HANDLE) IndicatorRelease(g_ema_handle);')
 table='double Cases[]['+str(len(FIELDS))+']={\n'+',\n'.join('{'+','.join(format(float(c[k]),'.16g') for k in FIELDS)+'}' for c in cases)+'\n};\n'
 apply='void DaxApply(){\n'+''.join(' '+key+'=('+TYPES[key]+')Cases[InpCase]['+str(i)+'];\n' for i,key in enumerate(FIELDS))+' InpRiskPercent=InpRiskPct;\n}\n'
 return PRE+table+source+'\n'+apply+EXTRA
def support(folder):
 for name in ['SafeRegimeFilter.mqh','DynamicTrailingSessionFilter.mqh']:
  text=(SRC.parent/name).read_text(encoding='utf-8-sig')
  if name=='DynamicTrailingSessionFilter.mqh':text=re.sub(r'^input group[^\n]*\n','',text,flags=re.M);text=re.sub(r'^input\s+','',text,flags=re.M)
  (folder/name).write_text(text,encoding='utf-8')
 (folder/'CalyxAdaptivePortfolio.mqh').write_bytes((B/'_Shared/CalyxAdaptivePortfolio.mqh').read_bytes())
def fingerprints():
 return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [SRC,SRC.with_suffix('.ex5'),PRESET,SRC.parent/'SafeRegimeFilter.mqh',SRC.parent/'DynamicTrailingSessionFilter.mqh',B/'_Shared/CalyxAdaptivePortfolio.mqh']}

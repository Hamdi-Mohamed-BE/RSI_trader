#property strict
#property version "3.00"
#property description "3 way gold independently parameterized engines. Research only."
#include <Trade/Trade.mqh>
#include "3WaySignals.mqh"

input int InpEngine=0; // 0=all together, 1=momentum, 2=trend change, 3=breakout
input double InpRiskPerEnginePercent=0.30;
input double InpStopATR=2.0;
input double InpRewardRisk=2.0;
input long InpMagicBase=91330000;
input int InpAuditRun=0;
input int InpDeviationPoints=30;
input int InpDirection=0; // 0=both, 1=long, -1=short
input int InpPullbackEMA=20;
input int InpTrendFastEMA=50;
input int InpTrendSlowEMA=200;
input int InpADXPeriod=14;
input double InpADXMin=25;
input int InpChangeFastEMA=9;
input int InpChangeSlowEMA=21;
input int InpRSIPeriod=14;
input double InpRSIThreshold=50;
input int InpBreakoutBars=20;
input double InpExpansionATR=1.5;
input bool InpRisingATR=true;
input int InpATRPeriod=14;
input int InpManagement=0; // 0=fixed, 1=BE at 1R, 2=closed-H1 ATR trail after 1R, 3=both
input double InpTrailATR=2.0;
input double InpTriggerR=1.0;
input double InpMomentumRiskWeight=1.0;
input double InpChangeRiskWeight=1.0;
input double InpBreakoutRiskWeight=1.0;
// Optional per-engine exit overrides: 0 uses the common setting.
input double InpMomentumStopATR=0;
input double InpChangeStopATR=0;
input double InpBreakoutStopATR=0;
input double InpMomentumRR=0;
input double InpChangeRR=0;
input double InpBreakoutRR=0;
input int InpMomentumATRPeriod=0; // 0 inherits common
input int InpMomentumDirection=2; // 2 inherits common; -1 short, 0 both, 1 long
input int InpMomentumManagement=-1; // -1 inherits common
input double InpMomentumTriggerR=0;
input double InpMomentumTrailATR=0;
input int InpChangeATRPeriod=0; // 0 inherits common
input int InpChangeDirection=2; // 2 inherits common; -1 short, 0 both, 1 long
input int InpChangeManagement=-1; // -1 inherits common
input double InpChangeTriggerR=0;
input double InpChangeTrailATR=0;
input int InpBreakoutATRPeriod=0; // 0 inherits common
input int InpBreakoutDirection=2; // 2 inherits common; -1 short, 0 both, 1 long
input int InpBreakoutManagement=-1; // -1 inherits common
input double InpBreakoutTriggerR=0;
input double InpBreakoutTrailATR=0;
input bool InpExportHistory=true;

CTrade trade;
int h9=INVALID_HANDLE,h20=INVALID_HANDLE,h21=INVALID_HANDLE,h50=INVALID_HANDLE,h200=INVALID_HANDLE;
int hATR=INVALID_HANDLE,hADX=INVALID_HANDLE,hRSI=INVALID_HANDLE;
int hMATR=INVALID_HANDLE,hCATR=INVALID_HANDLE,hBATR=INVALID_HANDLE;
double matr[],catr[],batr[];
int eventFile=INVALID_HANDLE,decisionFile=INVALID_HANDLE,equityFile=INVALID_HANDLE;
string prefix;
datetime firstTick=0,lastTick=0,lastBar=0,lastEq=0;
double initial=0,peakEq=0,minEq=0,maxDD=0,maxDDCash=0,maxOpenRiskPct=0;
int fills=0,errors=0,blocked=0,readFailures=0,maxConcurrent=0;
MqlRates b[];
double e9[],e20[],e21[],e50[],e200[],atr[],adx[],plusDI[],minusDI[],rsi[];

string Stamp(datetime t){return t>0?TimeToString(t,TIME_DATE|TIME_SECONDS):"";}
double TickSize(){return MathMax(_Point,SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE));}
double RoundPrice(double p,bool up){double s=TickSize();return NormalizeDouble((up?MathCeil(p/s-1e-9):MathFloor(p/s+1e-9))*s,_Digits);}
void Event(string event,int engine,int dir,string note,ulong pid=0,double px=0,double sl=0,double tp=0,double volume=0,double risk=0,double beforeEq=0,double requested=0)
{
 if(eventFile<0)return;
 FileWrite(eventFile,Stamp(TimeCurrent()),event,engine,dir,note,pid,px,sl,tp,volume,risk,beforeEq,requested,Stamp(lastBar));
}
bool ReadBuffer(int handle,int buffer,double &a[])
{
 ArraySetAsSeries(a,true);
 return CopyBuffer(handle,buffer,0,3,a)==3;
}
bool ReadData()
{
 if(BarsCalculated(h200)<MathMax(250,InpTrendSlowEMA+50))return false;
 ArraySetAsSeries(b,true);
 if(CopyRates(_Symbol,PERIOD_H1,0,InpBreakoutBars+2,b)!=InpBreakoutBars+2)return false;
 if(b[1].time+3600>TimeCurrent())return false;
 return ReadBuffer(h9,0,e9) && ReadBuffer(h20,0,e20) && ReadBuffer(h21,0,e21) && ReadBuffer(h50,0,e50) && ReadBuffer(h200,0,e200)
     && ReadBuffer(hATR,0,atr) && ReadBuffer(hADX,0,adx) && ReadBuffer(hADX,1,plusDI) && ReadBuffer(hADX,2,minusDI) && ReadBuffer(hRSI,0,rsi)
     && ReadBuffer(hMATR,0,matr) && ReadBuffer(hCATR,0,catr) && ReadBuffer(hBATR,0,batr)
     && atr[1]>0 && atr[2]>0 && matr[1]>0 && catr[1]>0 && batr[1]>0 && batr[2]>0;
}
bool HasEngine(int engine)
{
 for(int i=PositionsTotal()-1;i>=0;i--)
 {
  ulong ticket=PositionGetTicket(i);
  if(ticket>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagicBase+engine)return true;
 }
 return false;
}
void TrackOpenRisk()
{
 double grossRisk=0;int count=0;
 for(int i=PositionsTotal()-1;i>=0;i--)
 {
  ulong ticket=PositionGetTicket(i);if(!ticket)continue;
  long magic=PositionGetInteger(POSITION_MAGIC);
  if(PositionGetString(POSITION_SYMBOL)!=_Symbol || magic<InpMagicBase+1 || magic>InpMagicBase+3)continue;
  count++;
  double pnl=0;ENUM_ORDER_TYPE side=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
  if(OrderCalcProfit(side,_Symbol,PositionGetDouble(POSITION_VOLUME),PositionGetDouble(POSITION_PRICE_OPEN),PositionGetDouble(POSITION_SL),pnl))grossRisk+=MathMax(0,-pnl);
 }
 maxConcurrent=MathMax(maxConcurrent,count);
 double eq=AccountInfoDouble(ACCOUNT_EQUITY);
 if(eq>0)maxOpenRiskPct=MathMax(maxOpenRiskPct,100*grossRisk/eq);
}
void TrackEquity()
{
 double eq=AccountInfoDouble(ACCOUNT_EQUITY);
 peakEq=MathMax(peakEq,eq);minEq=MathMin(minEq,eq);
 maxDDCash=MathMax(maxDDCash,peakEq-eq);
 if(peakEq>0)maxDD=MathMax(maxDD,100*(peakEq-eq)/peakEq);
 if(equityFile>=0 && TimeCurrent()-lastEq>=3600)
 {lastEq=TimeCurrent();FileWrite(equityFile,Stamp(TimeCurrent()),AccountInfoDouble(ACCOUNT_BALANCE),eq,maxDD);}
}
double EngineWeight(int engine){return engine==1?InpMomentumRiskWeight:(engine==2?InpChangeRiskWeight:InpBreakoutRiskWeight);}
double EngineStop(int engine){double v=engine==1?InpMomentumStopATR:(engine==2?InpChangeStopATR:InpBreakoutStopATR);return v>0?v:InpStopATR;}
double EngineRR(int engine){double v=engine==1?InpMomentumRR:(engine==2?InpChangeRR:InpBreakoutRR);return v>0?v:InpRewardRisk;}
int EngineATRPeriod(int engine){int v=engine==1?InpMomentumATRPeriod:(engine==2?InpChangeATRPeriod:InpBreakoutATRPeriod);return v>0?v:InpATRPeriod;}
double EngineATR(int engine){return engine==1?matr[1]:(engine==2?catr[1]:batr[1]);}
int EngineDirection(int engine){int v=engine==1?InpMomentumDirection:(engine==2?InpChangeDirection:InpBreakoutDirection);return v==2?InpDirection:v;}
int EngineManagement(int engine){int v=engine==1?InpMomentumManagement:(engine==2?InpChangeManagement:InpBreakoutManagement);return v<0?InpManagement:v;}
double EngineTrigger(int engine){double v=engine==1?InpMomentumTriggerR:(engine==2?InpChangeTriggerR:InpBreakoutTriggerR);return v>0?v:InpTriggerR;}
double EngineTrail(int engine){double v=engine==1?InpMomentumTrailATR:(engine==2?InpChangeTrailATR:InpBreakoutTrailATR);return v>0?v:InpTrailATR;}
void Manage()
{
 if(EngineManagement(1)==0 && EngineManagement(2)==0 && EngineManagement(3)==0)return;
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
 for(int i=PositionsTotal()-1;i>=0;i--)
 {
  ulong ticket=PositionGetTicket(i);if(!ticket)continue;
  long engine=PositionGetInteger(POSITION_MAGIC)-InpMagicBase;
  if(PositionGetString(POSITION_SYMBOL)!=_Symbol || engine<1 || engine>3)continue;
  int mode=EngineManagement((int)engine);if(mode==0)continue;
  int dir=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1;
  double entry=PositionGetDouble(POSITION_PRICE_OPEN),oldSL=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP);
  // Fixed TP encodes original R even after the SL moves.
  double risk=MathAbs(tp-entry)/EngineRR((int)engine);
  if(risk<=0 || dir*(b[1].close-entry)<EngineTrigger((int)engine)*risk)continue;
  double next=oldSL;
  if(mode==1 || mode==3)next=dir>0?MathMax(next,entry):MathMin(next,entry);
  if(mode==2 || mode==3)
  {
   double candidate=b[1].close-dir*EngineTrail((int)engine)*EngineATR((int)engine);
   next=dir>0?MathMax(next,candidate):MathMin(next,candidate);
  }
  next=RoundPrice(next,dir<0);
  double allowed=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point,2*TickSize());
  double price=dir>0?q.bid:q.ask;
  if(dir*(next-oldSL)<TickSize()*.5 || dir*(price-next)<=allowed)continue;
  if(!trade.PositionModify(ticket,next,tp) || trade.ResultRetcode()!=TRADE_RETCODE_DONE)
  {errors++;Event("manage_error",(int)engine,dir,trade.ResultRetcodeDescription(),ticket,entry,next,tp);continue;}
  Event("trail",(int)engine,dir,"closed H1 ratchet",ticket,entry,next,tp);
 }
}
void Enter(int engine,int dir)
{
 if(!dir || (InpEngine!=0 && InpEngine!=engine) || (EngineDirection(engine)!=0 && dir!=EngineDirection(engine)) || EngineWeight(engine)<=0)return;
 if(HasEngine(engine)){blocked++;Event("occupied",engine,dir,"one position per engine");return;}
 MqlTick quote;if(!SymbolInfoTick(_Symbol,quote) || quote.ask<quote.bid || quote.bid<=0)
 {errors++;Event("error",engine,dir,"invalid quote");return;}
 double entry=dir>0?quote.ask:quote.bid;
 double minDist=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point,2*TickSize());
 double distance=MathMax(EngineStop(engine)*EngineATR(engine),minDist+(quote.ask-quote.bid));
 double sl=RoundPrice(entry-dir*distance,dir<0);
 double tp=RoundPrice(entry+dir*MathAbs(entry-sl)*EngineRR(engine),dir>0);
 ENUM_ORDER_TYPE side=dir>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 double oneLot=0,eq=AccountInfoDouble(ACCOUNT_EQUITY);
 if(eq<=0 || !OrderCalcProfit(side,_Symbol,1,entry,sl,oneLot) || oneLot>=0)
 {errors++;Event("error",engine,dir,"risk calculation failed");return;}
 double requested=eq*InpRiskPerEnginePercent*EngineWeight(engine)/100;
 double volume=RoundedLots(requested/MathAbs(oneLot),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP));
 if(volume<=0){errors++;Event("error",engine,dir,"invalid volume");return;}
 double margin=0;
 if(!OrderCalcMargin(side,_Symbol,volume,entry,margin) || margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE))
 {errors++;Event("error",engine,dir,"insufficient margin",0,entry,sl,tp,volume,MathAbs(oneLot)*volume,eq,requested);return;}
 trade.SetExpertMagicNumber((ulong)(InpMagicBase+engine));
 bool ok=dir>0?trade.Buy(volume,_Symbol,0,sl,tp,"3WG|"+(string)engine):trade.Sell(volume,_Symbol,0,sl,tp,"3WG|"+(string)engine);
 if(!ok || (trade.ResultRetcode()!=TRADE_RETCODE_DONE && trade.ResultRetcode()!=TRADE_RETCODE_DONE_PARTIAL))
 {errors++;Event("error",engine,dir,trade.ResultRetcodeDescription(),0,entry,sl,tp,volume,MathAbs(oneLot)*volume,eq,requested);return;}
 ulong deal=trade.ResultDeal();
 if(!deal || !HistoryDealSelect(deal)){errors++;Event("error",engine,dir,"accepted order missing deal");return;}
 ulong pid=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);
 double fill=HistoryDealGetDouble(deal,DEAL_PRICE),filledVol=HistoryDealGetDouble(deal,DEAL_VOLUME),actual=0;
 if(!OrderCalcProfit(side,_Symbol,filledVol,fill,sl,actual)){errors++;Event("error",engine,dir,"fill risk calculation failed",pid);return;}
 fills++;Event("entry",engine,dir,trade.ResultRetcodeDescription(),pid,fill,sl,tp,filledVol,MathAbs(actual),eq,requested);
 TrackOpenRisk();
}
int OnInit()
{
 if(!MQLInfoInteger(MQL_TESTER)){Print("3 way gold is research-only; live initialization refused.");return INIT_FAILED;}
 if(_Symbol!="XAUUSD" || _Period!=PERIOD_H1 || AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)return INIT_PARAMETERS_INCORRECT;
 if(InpEngine<0 || InpEngine>3 || InpRiskPerEnginePercent<=0 || InpRiskPerEnginePercent>1 || InpStopATR<=0 || InpRewardRisk<=0)return INIT_PARAMETERS_INCORRECT;
 if(InpDirection<-1 || InpDirection>1 || InpPullbackEMA<2 || InpTrendFastEMA<2 || InpTrendFastEMA>=InpTrendSlowEMA || InpTrendSlowEMA>400 || InpADXPeriod<2 || InpADXMin<0 || InpChangeFastEMA<2 || InpChangeFastEMA>=InpChangeSlowEMA || InpRSIPeriod<2 || InpRSIThreshold<50 || InpRSIThreshold>70 || InpBreakoutBars<2 || InpBreakoutBars>100 || InpExpansionATR<0 || InpATRPeriod<2 || InpManagement<0 || InpManagement>3 || InpTrailATR<=0 || InpTriggerR<=0)return INIT_PARAMETERS_INCORRECT;
 if(InpMomentumRiskWeight<0 || InpChangeRiskWeight<0 || InpBreakoutRiskWeight<0 || InpMomentumRiskWeight>2 || InpChangeRiskWeight>2 || InpBreakoutRiskWeight>2)return INIT_PARAMETERS_INCORRECT;
 for(int engine=1;engine<=3;engine++)
 {
  if(EngineATRPeriod(engine)<2 || EngineATRPeriod(engine)>100 || EngineDirection(engine)<-1 || EngineDirection(engine)>1 || EngineManagement(engine)<0 || EngineManagement(engine)>3 || EngineTrigger(engine)<=0 || EngineTrail(engine)<=0)return INIT_PARAMETERS_INCORRECT;
 }
 if(!SignalSelfTest()){Print("3WG SELF TEST FAILED");return INIT_FAILED;}
 h9=iMA(_Symbol,PERIOD_H1,InpChangeFastEMA,0,MODE_EMA,PRICE_CLOSE);h20=iMA(_Symbol,PERIOD_H1,InpPullbackEMA,0,MODE_EMA,PRICE_CLOSE);
 h21=iMA(_Symbol,PERIOD_H1,InpChangeSlowEMA,0,MODE_EMA,PRICE_CLOSE);h50=iMA(_Symbol,PERIOD_H1,InpTrendFastEMA,0,MODE_EMA,PRICE_CLOSE);
 h200=iMA(_Symbol,PERIOD_H1,InpTrendSlowEMA,0,MODE_EMA,PRICE_CLOSE);hATR=iATR(_Symbol,PERIOD_H1,InpATRPeriod);hADX=iADX(_Symbol,PERIOD_H1,InpADXPeriod);hRSI=iRSI(_Symbol,PERIOD_H1,InpRSIPeriod,PRICE_CLOSE);
 hMATR=iATR(_Symbol,PERIOD_H1,EngineATRPeriod(1));hCATR=iATR(_Symbol,PERIOD_H1,EngineATRPeriod(2));hBATR=iATR(_Symbol,PERIOD_H1,EngineATRPeriod(3));
 if(hMATR<0 || hCATR<0 || hBATR<0)return INIT_FAILED;
 if(h9<0 || h20<0 || h21<0 || h50<0 || h200<0 || hATR<0 || hADX<0 || hRSI<0)return INIT_FAILED;
 trade.SetAsyncMode(false);trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(InpDeviationPoints);
 initial=AccountInfoDouble(ACCOUNT_BALANCE);peakEq=initial;minEq=initial;
 prefix="3WGI-"+(string)InpAuditRun+"-"+(string)InpEngine;
 eventFile=FileOpen(prefix+"-events.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');
 decisionFile=FileOpen(prefix+"-decisions.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');
 equityFile=FileOpen(prefix+"-equity.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');
 if(eventFile<0 || decisionFile<0 || equityFile<0)return INIT_FAILED;
 FileWrite(eventFile,"time","event","engine","dir","note","position_id","entry","sl","tp","volume","risk_cash","equity_before","requested_risk_cash","decision_bar");
 FileWrite(decisionFile,"time","closed_bar","c1","c2","e20_1","e20_2","e50","e200","adx","plus","minus","e9_1","e9_2","e21_1","e21_2","rsi","prior20_high","prior20_low","tr","atr1","atr2","momentum","change","breakout","momentum_atr","change_atr","breakout_atr","breakout_atr_prev");
 FileWrite(equityFile,"time","balance","equity","running_max_dd_pct");
 Print("3WG SELF TEST PASS; CONTRACT=",SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE)," leverage=",AccountInfoInteger(ACCOUNT_LEVERAGE)," engine=",InpEngine," broker=",AccountInfoString(ACCOUNT_SERVER));
 return INIT_SUCCEEDED;
}
void OnTick()
{
 if(!firstTick)firstTick=TimeCurrent();lastTick=TimeCurrent();TrackEquity();
 datetime nowBar=iTime(_Symbol,PERIOD_H1,0);
 if(!nowBar || nowBar==lastBar)return;
 if(!ReadData()){readFailures++;return;}
 lastBar=nowBar;
 double hi=b[2].high,lo=b[2].low;
 for(int i=3;i<=InpBreakoutBars+1;i++){hi=MathMax(hi,b[i].high);lo=MathMin(lo,b[i].low);}
 double tr=MathMax(b[1].high-b[1].low,MathMax(MathAbs(b[1].high-b[2].close),MathAbs(b[1].low-b[2].close)));
 int s1=MomentumSignal(b[1].close,b[2].close,e20[1],e20[2],e50[1],e200[1],adx[1],plusDI[1],minusDI[1],InpADXMin);
 int s2=ChangeSignal(e9[1],e9[2],e21[1],e21[2],rsi[1],InpRSIThreshold);
 int s3=BreakoutSignal(b[1].close,hi,lo,tr,batr[1],batr[2],InpExpansionATR,InpRisingATR);
 FileWrite(decisionFile,Stamp(TimeCurrent()),Stamp(b[1].time),b[1].close,b[2].close,e20[1],e20[2],e50[1],e200[1],adx[1],plusDI[1],minusDI[1],e9[1],e9[2],e21[1],e21[2],rsi[1],hi,lo,tr,atr[1],atr[2],s1,s2,s3,matr[1],catr[1],batr[1],batr[2]);
 Manage();Enter(1,s1);Enter(2,s2);Enter(3,s3);TrackOpenRisk();TrackEquity();
}
void KV(int f,string k,double v){FileWrite(f,k,DoubleToString(v,8));}
double OnTester()
{
 TrackEquity();
 int f=FileOpen(prefix+"-summary.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');
 FileWrite(f,"key","value");FileWrite(f,"first_tick",Stamp(firstTick));FileWrite(f,"last_tick",Stamp(lastTick));
 KV(f,"initial_balance",initial);KV(f,"final_balance",AccountInfoDouble(ACCOUNT_BALANCE));KV(f,"native_net_profit",TesterStatistics(STAT_PROFIT));KV(f,"native_trades",TesterStatistics(STAT_TRADES));
 KV(f,"native_equity_dd_pct",TesterStatistics(STAT_EQUITY_DDREL_PERCENT));KV(f,"observed_equity_dd_pct",maxDD);KV(f,"observed_equity_dd_cash",maxDDCash);KV(f,"minimum_equity",minEq);
 KV(f,"max_concurrent_positions",maxConcurrent);KV(f,"max_gross_initial_stop_risk_pct",maxOpenRiskPct);KV(f,"fills",fills);KV(f,"errors",errors);KV(f,"occupied_signals",blocked);KV(f,"data_read_retries",readFailures);FileClose(f);
 int d=FileOpen(prefix+"-deals.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');
 FileWrite(d,"deal","time","time_msc","symbol","position_id","magic","type","entry","reason","volume","price","profit","commission","swap","fee","comment");
 HistorySelect(0,TimeCurrent());
 for(int i=0;i<HistoryDealsTotal();i++)
 {
  ulong t=HistoryDealGetTicket(i);
  FileWrite(d,t,Stamp((datetime)HistoryDealGetInteger(t,DEAL_TIME)),HistoryDealGetInteger(t,DEAL_TIME_MSC),HistoryDealGetString(t,DEAL_SYMBOL),HistoryDealGetInteger(t,DEAL_POSITION_ID),HistoryDealGetInteger(t,DEAL_MAGIC),HistoryDealGetInteger(t,DEAL_TYPE),HistoryDealGetInteger(t,DEAL_ENTRY),HistoryDealGetInteger(t,DEAL_REASON),HistoryDealGetDouble(t,DEAL_VOLUME),HistoryDealGetDouble(t,DEAL_PRICE),HistoryDealGetDouble(t,DEAL_PROFIT),HistoryDealGetDouble(t,DEAL_COMMISSION),HistoryDealGetDouble(t,DEAL_SWAP),HistoryDealGetDouble(t,DEAL_FEE),HistoryDealGetString(t,DEAL_COMMENT));
 }
 FileClose(d);FileFlush(eventFile);FileFlush(decisionFile);FileFlush(equityFile);
 if(InpExportHistory)
 {
 MqlRates history[];
 int total=CopyRates(_Symbol,PERIOD_H1,(datetime)(firstTick-90*86400),lastTick,history);
 int barsFile=FileOpen(prefix+"-h1.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');
 FileWrite(barsFile,"time","open","high","low","close","tick_volume","spread","real_volume");
 for(int i=0;i<total;i++)FileWrite(barsFile,Stamp(history[i].time),history[i].open,history[i].high,history[i].low,history[i].close,history[i].tick_volume,history[i].spread,history[i].real_volume);
 FileClose(barsFile);
 }
 // No optimizer score: these are fixed-rule runs, not parameter selection.
 return TesterStatistics(STAT_PROFIT);
}
void OnDeinit(const int reason)
{
 if(eventFile>=0)FileClose(eventFile);if(decisionFile>=0)FileClose(decisionFile);if(equityFile>=0)FileClose(equityFile);
 if(h9>=0)IndicatorRelease(h9);if(h20>=0)IndicatorRelease(h20);if(h21>=0)IndicatorRelease(h21);if(h50>=0)IndicatorRelease(h50);if(h200>=0)IndicatorRelease(h200);
 if(hMATR>=0)IndicatorRelease(hMATR);if(hCATR>=0)IndicatorRelease(hCATR);if(hBATR>=0)IndicatorRelease(hBATR);
 if(hATR>=0)IndicatorRelease(hATR);if(hADX>=0)IndicatorRelease(hADX);if(hRSI>=0)IndicatorRelease(hRSI);
}

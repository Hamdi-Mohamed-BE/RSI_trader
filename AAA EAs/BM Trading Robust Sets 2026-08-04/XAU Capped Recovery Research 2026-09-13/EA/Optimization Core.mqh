#property strict
#property version "1.00"
#include <Trade/Trade.mqh>
double InpLot=0.01;
double InpMultiplier=1.0;
int InpMaxLegs=3;
double InpStep=10.0;
bool InpATRStep=false;
double InpATRMultiple=1.0;
double InpBasketProfit=20.0;
bool InpOriginalExit=false;
double InpBasketLoss=60.0;
double InpDailyLoss=90.0;
double InpDailyProfit=60.0;
double InpCommissionPerLot=5.50;
int InpLeverageCap=2000;
bool InpStopAtDouble=false;
long InpMagic=84913201;
CTrade trade;
int logFile=-1,equityFile=-1,dealsFile=-1,summaryFile=-1,atrHandle=-1;
int legs=0,maxLegs=0;long basket=0,dayKey=0,entries=0,completed=0,rejected=0,lossDays=0,profitDays=0;
double initial=0,basketBalance=0,dayBalance=0,firstEntry=0,gap=0,commonSL=0;
double peak=0,trough=0,maxDD=0,maxDDCash=0,maxLots=0;
datetime firstTick=0,lastCurve=0,firstDouble=0,insolventAt=0,lastRetry=0;
bool closing=false,dayLocked=false,profitLocked=false,halt=false,stoppedDouble=false;
string closeReason="";

string Stamp(datetime t){return t?TimeToString(t,TIME_DATE|TIME_SECONDS):"";}
long Day(datetime t){MqlDateTime s;TimeToStruct(t,s);return s.year*10000+s.mon*100+s.day;}
double Equity(){return AccountInfoDouble(ACCOUNT_EQUITY);}
double Balance(){return AccountInfoDouble(ACCOUNT_BALANCE);}
int Stats(double &lots,double &weighted,double &swaps)
{
 lots=0;weighted=0;swaps=0;int n=0;
 for(int i=PositionsTotal()-1;i>=0;i--)if(PositionGetTicket(i)>0 && PositionGetInteger(POSITION_MAGIC)==InpMagic && PositionGetString(POSITION_SYMBOL)==_Symbol)
 {double v=PositionGetDouble(POSITION_VOLUME);lots+=v;weighted+=v*PositionGetDouble(POSITION_PRICE_OPEN);swaps+=PositionGetDouble(POSITION_SWAP);n++;}
 return n;
}
void Event(string kind,string note="",double volume=0,double price=0,double trigger=0)
{
 if(logFile<0)return;MqlTick q;ZeroMemory(q);SymbolInfoTick(_Symbol,q);double lot,w,s;int n=Stats(lot,w,s);
 FileWrite(logFile,Stamp(TimeCurrent()),kind,note,basket,legs,firstEntry,gap,volume,price,trigger,q.bid,q.ask,Balance(),Equity(),basketBalance,dayBalance,
           Equity()-basketBalance,Equity()-dayBalance,commonSL,lot,n,dayKey,dayLocked);
}
void Track()
{
 double e=Equity(),lot,w,s;Stats(lot,w,s);peak=MathMax(peak,e);trough=MathMin(trough,e);
 maxDDCash=MathMax(maxDDCash,peak-e);if(peak>0)maxDD=MathMax(maxDD,100*(peak-e)/peak);
 maxLots=MathMax(maxLots,lot);maxLegs=MathMax(maxLegs,legs);
 if(TimeCurrent()/60!=lastCurve/60){lastCurve=TimeCurrent();FileWrite(equityFile,Stamp(TimeCurrent()),Balance(),e,lot,legs,basket,maxDD,maxDDCash);}
 if(e<=0 && lot>0 && insolventAt==0){insolventAt=TimeCurrent();Event("insolvency","terminate immediately; do not allow recovery");halt=true;TesterStop();}
}
double RoundPrice(double p,bool up)
{
 double t=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);if(t<=0)t=_Point;
 return NormalizeDouble((up?MathCeil(p/t-1e-8):MathFloor(p/t+1e-8))*t,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}
double MinDistance(){return MathMax(_Point,SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point);}
double StopEquity(){return MathMax(basketBalance-InpBasketLoss,dayBalance-InpDailyLoss);}
double StopPrice(double lot,double weighted,double swaps,double balance)
{
 if(lot<=0)return 0;
 double c=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);
 return MathMax(commonSL,RoundPrice((StopEquity()-balance-swaps+c*weighted)/(c*lot),true));
}
double TargetPrice(double lot,double weighted,double swaps,double balance)
{
 if(InpOriginalExit)return firstEntry+(legs==1?gap:0);
 double c=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);
 return RoundPrice((basketBalance+InpBasketProfit-balance-swaps+c*weighted)/(c*lot),true);
}
void MarkDayLoss()
{
 if(!dayLocked){dayLocked=true;lossDays++;Event("daily_loss_lock","closed plus floating daily threshold");}
}
void FinishBasket()
{
 completed++;Event("basket_closed",closeReason);
 if(Balance()-dayBalance<=-InpDailyLoss)MarkDayLoss();
 if(firstDouble==0 && Balance()>=initial*2){firstDouble=TimeCurrent();Event("closed_double");if(InpStopAtDouble){stoppedDouble=true;halt=true;TesterStop();}}
 legs=0;firstEntry=0;gap=0;commonSL=0;closing=false;lastRetry=0;
}
void CloseAll(string reason)
{
 closing=true;if(closeReason=="" || reason!="retry")closeReason=reason;
 while(true)
 {
  ulong ticket=0;
  for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);if(t && PositionGetInteger(POSITION_MAGIC)==InpMagic && PositionGetString(POSITION_SYMBOL)==_Symbol && (!ticket || t<ticket))ticket=t;}
  if(!ticket)break;
  if(!trade.PositionClose(ticket) || trade.ResultRetcode()!=TRADE_RETCODE_DONE){Event("close_retry",trade.ResultRetcodeDescription());return;}
  Track();
 }
 FinishBasket();
}
bool SyncStops()
{
 double lot,w,s;int n=Stats(lot,w,s);if(!n)return false;MqlTick q;SymbolInfoTick(_Symbol,q);
 double sl=StopPrice(lot,w,s,Balance()),tp=RoundPrice(TargetPrice(lot,w,s,Balance()),true);
 if(q.bid<=sl+MinDistance()){Event("stop_preempt","budget stop within broker distance",0,q.bid,sl);CloseAll("basket_or_daily_stop");return false;}
 if(q.bid>=tp-MinDistance()){Event("target_preempt","target reached or within broker distance",0,q.bid,tp);CloseAll("target");return false;}
 commonSL=sl;
 for(int i=PositionsTotal()-1;i>=0;i--)
 {
  ulong t=PositionGetTicket(i);if(!t || PositionGetInteger(POSITION_MAGIC)!=InpMagic || PositionGetString(POSITION_SYMBOL)!=_Symbol)continue;
  if(MathAbs(PositionGetDouble(POSITION_SL)-sl)<_Point/2 && MathAbs(PositionGetDouble(POSITION_TP)-tp)<_Point/2)continue;
  if(!trade.PositionModify(t,sl,tp) || (trade.ResultRetcode()!=TRADE_RETCODE_DONE && trade.ResultRetcode()!=TRADE_RETCODE_NO_CHANGES))
  {Event("stop_sync_failed",trade.ResultRetcodeDescription());CloseAll("protective_stop_sync_failure");return false;}
 }
 return true;
}
bool BuyLeg()
{
 MqlTick q;SymbolInfoTick(_Symbol,q);double lot,w,s;Stats(lot,w,s);
 double v=InpLot*MathPow(InpMultiplier,legs),step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
 if(v<SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN) || v>SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX) || MathAbs(v/step-MathRound(v/step))>1e-6)
 {Event("add_rejected","invalid prescribed volume",v);rejected++;lastRetry=TimeCurrent();return false;}
 double projectedBalance=Balance()-v*InpCommissionPerLot;
 double sl=StopPrice(lot+v,w+v*q.ask,s,projectedBalance);
 double effectiveLeverage=MathMin(InpLeverageCap,Equity()>=100000?500:(Equity()>=30000?1000:2000));
 double needed=(w+v*q.ask)*SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE)/effectiveLeverage;
 if(sl>=q.bid-MinDistance() || Equity()-v*InpCommissionPerLot<=needed)
 {Event("add_rejected","risk distance or conservative margin budget",v,q.ask,sl);rejected++;lastRetry=TimeCurrent();return false;}
 double rung=legs?firstEntry-gap*legs:q.ask;
 Event("buy_request","prescribed size; projected basket stop",v,q.ask,rung);
 if(!trade.Buy(v,_Symbol,0,sl,0,"CAP|"+(string)basket+"|"+(string)legs) || trade.ResultRetcode()!=TRADE_RETCODE_DONE)
 {Event("add_rejected",trade.ResultRetcodeDescription(),v,q.ask,sl);rejected++;lastRetry=TimeCurrent();return false;}
 if(legs==0)firstEntry=trade.ResultPrice();legs++;entries++;lastRetry=0;commonSL=sl;
 Event("buy_filled","",trade.ResultVolume(),trade.ResultPrice(),rung);Track();if(halt)return false;
 SyncStops();return true;
}
void OnTick()
{
 if(firstTick==0)firstTick=TimeCurrent();Track();if(halt)return;
 long d=Day(TimeCurrent());
 if(d!=dayKey){dayKey=d;dayBalance=Balance();dayLocked=false;profitLocked=false;Event("day_start");}
 double lot,w,s;int count=Stats(lot,w,s);
 if(count<legs && !closing)
 {Event("native_exit","one or more protective SL/TP positions exited");CloseAll("native_sl_tp");return;}
 if(closing){CloseAll("retry");return;}
 if(Equity()-dayBalance<=-InpDailyLoss)
 {MarkDayLoss();if(count)CloseAll("daily_loss");return;}
 if(!count)
 {
  if(dayLocked)return;
  if(InpDailyProfit>0 && Balance()-dayBalance>=InpDailyProfit)
  {if(!profitLocked){profitLocked=true;profitDays++;Event("daily_profit_lock");}return;}
  if(lastRetry && TimeCurrent()-lastRetry<60)return;
  gap=InpStep;
  if(InpATRStep){double a[1];if(CopyBuffer(atrHandle,0,1,1,a)!=1 || a[0]<=0)return;gap=a[0]*InpATRMultiple;}
  basket++;basketBalance=Balance();closeReason="";BuyLeg();return;
 }
 if(Equity()-basketBalance<=-InpBasketLoss){CloseAll("basket_loss");return;}
 if(!SyncStops() || closing || halt)return;
 MqlTick q;SymbolInfoTick(_Symbol,q);
 if(legs<InpMaxLegs && q.ask<=firstEntry-gap*legs && (!lastRetry || TimeCurrent()-lastRetry>=60))BuyLeg();
}
void Pair(string k,string v){FileWrite(summaryFile,k,v);}
void Num(string k,double v){Pair(k,DoubleToString(v,8));}
int BaseInit()
{
 if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;
 if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING || InpLot<=0 || InpBasketLoss<=0 || InpDailyLoss<=0 || InpBasketProfit<=0 || InpMaxLegs<1 || InpLeverageCap<1)return INIT_PARAMETERS_INCORRECT;
 initial=Balance();peak=initial;trough=initial;
 string prefix="CappedGrid-"+(string)InpMagic;
 logFile=FileOpen(prefix+"-events.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');equityFile=FileOpen(prefix+"-equity.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');
 dealsFile=FileOpen(prefix+"-deals.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');summaryFile=FileOpen(prefix+"-summary.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');
 if(logFile<0 || equityFile<0 || dealsFile<0 || summaryFile<0)return INIT_FAILED;
 FileWrite(logFile,"time","event","note","basket","legs","first_entry","gap","volume","price","trigger","bid","ask","balance","equity","basket_start_balance","day_start_balance","basket_pnl","daily_pnl","common_sl","total_lots","positions","day","day_locked");
 FileWrite(equityFile,"time","balance","equity","total_lots","legs","basket","running_max_dd_pct","running_max_dd_cash");
 FileWrite(dealsFile,"deal","time","time_msc","symbol","position_id","type","entry","reason","volume","price","profit","commission","swap","fee","comment");
 FileWrite(summaryFile,"key","value");
 trade.SetExpertMagicNumber(InpMagic);trade.SetDeviationInPoints(30);trade.SetTypeFillingBySymbol(_Symbol);
 if(InpATRStep){atrHandle=iATR(_Symbol,PERIOD_H1,14);if(atrHandle==INVALID_HANDLE)return INIT_FAILED;}
 Print("CAPPED CONTRACT symbol=",_Symbol," contract=",SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE)," leverage=",AccountInfoInteger(ACCOUNT_LEVERAGE)," so=",AccountInfoDouble(ACCOUNT_MARGIN_SO_SO));
 return INIT_SUCCEEDED;
}
void OnDeinit(const int why)
{
 if(summaryFile<0)return;Track();Event("summary","deinit "+(string)why);
 HistorySelect(0,TimeCurrent());
 for(int i=0;i<HistoryDealsTotal();i++)
 {
  ulong t=HistoryDealGetTicket(i);if(!t)continue;
  FileWrite(dealsFile,t,Stamp((datetime)HistoryDealGetInteger(t,DEAL_TIME)),HistoryDealGetInteger(t,DEAL_TIME_MSC),HistoryDealGetString(t,DEAL_SYMBOL),HistoryDealGetInteger(t,DEAL_POSITION_ID),HistoryDealGetInteger(t,DEAL_TYPE),HistoryDealGetInteger(t,DEAL_ENTRY),HistoryDealGetInteger(t,DEAL_REASON),HistoryDealGetDouble(t,DEAL_VOLUME),HistoryDealGetDouble(t,DEAL_PRICE),HistoryDealGetDouble(t,DEAL_PROFIT),HistoryDealGetDouble(t,DEAL_COMMISSION),HistoryDealGetDouble(t,DEAL_SWAP),HistoryDealGetDouble(t,DEAL_FEE),HistoryDealGetString(t,DEAL_COMMENT));
 }
 Pair("first_tick",Stamp(firstTick));Pair("last_tick",Stamp(TimeCurrent()));Pair("first_closed_double",Stamp(firstDouble));Pair("insolvent_at",Stamp(insolventAt));
 Num("initial_balance",initial);Num("final_balance",Balance());Num("final_equity",Equity());Num("max_equity",peak);Num("min_equity",trough);Num("max_equity_dd_pct",maxDD);Num("max_equity_dd_cash",maxDDCash);Num("max_total_lots",maxLots);Num("max_legs",maxLegs);Num("entries",entries);Num("baskets_closed",completed);Num("rejected",rejected);Num("daily_loss_locks",lossDays);Num("daily_profit_locks",profitDays);Num("stopped_at_double",stoppedDouble);Num("leverage",AccountInfoInteger(ACCOUNT_LEVERAGE));
 FileClose(logFile);FileClose(equityFile);FileClose(dealsFile);FileClose(summaryFile);if(atrHandle>=0)IndicatorRelease(atrHandle);
}



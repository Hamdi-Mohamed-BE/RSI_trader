#property strict
#property version "1.00"
#property description "Tester-only unbounded doubling grid; native margin and stop-out audit"
#include <Trade/Trade.mqh>
input double InpInitialLot=0.02;
input double InpPriceStep=10.0;
input double InpDailyTarget=300.0;
input long InpMagic=84913001;
input int InpDeviationPoints=30;
CTrade trade;
int events=INVALID_HANDLE,curve=INVALID_HANDLE,ledger=INVALID_HANDLE,summary=INVALID_HANDLE;
long basket=0,opened=0,closedBaskets=0,blocked=0,dayKey=0,daysTarget=0;
int legs=0,maxLegs=0;
double firstEntry=0,startBalance=0,dayBalance=0,basketBalance=0,peakEq=0,maxDD=0,maxDDCash=0,minEq=0,maxTotalLots=0,maxSingleLot=0,minMarginLevel=1e100;
datetime firstTick=0,firstClosedDouble=0,firstEquityDouble=0,firstStopout=0,firstBlocked=0,lastRetry=0,lastCurve=0;
bool closing=false,stopRequested=false,dayCapped=false;
uint lastReject=0;

string Stamp(datetime t){return t?TimeToString(t,TIME_DATE|TIME_SECONDS):"";}
long Day(datetime t){MqlDateTime d;TimeToStruct(t,d);return d.year*10000+d.mon*100+d.day;}
double A(ENUM_ACCOUNT_INFO_DOUBLE k){return AccountInfoDouble(k);}
int PositionCount(double &lots)
{
 int n=0;lots=0;
 for(int i=PositionsTotal()-1;i>=0;i--)if(PositionGetTicket(i)>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic){n++;lots+=PositionGetDouble(POSITION_VOLUME);}
 return n;
}
void Event(string kind,string detail,double quote=0,double trigger=0,double volume=0,double fill=0)
{
 if(events==INVALID_HANDLE)return;
 MqlTick q;ZeroMemory(q);SymbolInfoTick(_Symbol,q);double total=0;int count=PositionCount(total);
 FileWrite(events,Stamp(TimeCurrent()),kind,detail,basket,legs,firstEntry,quote,trigger,volume,fill,q.bid,q.ask,
           A(ACCOUNT_BALANCE),A(ACCOUNT_EQUITY),A(ACCOUNT_MARGIN),A(ACCOUNT_MARGIN_FREE),A(ACCOUNT_MARGIN_LEVEL),
           dayKey,dayBalance,A(ACCOUNT_BALANCE)-dayBalance,total,count);
 FileFlush(events);
}
void Track()
{
 double e=A(ACCOUNT_EQUITY),total=0;PositionCount(total);
 peakEq=MathMax(peakEq,e);minEq=MathMin(minEq,e);maxDDCash=MathMax(maxDDCash,peakEq-e);
 if(peakEq>0)maxDD=MathMax(maxDD,100*(peakEq-e)/peakEq);
 maxTotalLots=MathMax(maxTotalLots,total);maxLegs=MathMax(maxLegs,legs);
 if(A(ACCOUNT_MARGIN)>0)minMarginLevel=MathMin(minMarginLevel,A(ACCOUNT_MARGIN_LEVEL));
 if(firstEquityDouble==0 && e>=2*startBalance){firstEquityDouble=TimeCurrent();Event("equity_double","floating equity at least twice initial; not secured");}
 if(curve!=INVALID_HANDLE && TimeCurrent()/60!=lastCurve/60)
 {
  lastCurve=TimeCurrent();MqlTick q;ZeroMemory(q);SymbolInfoTick(_Symbol,q);
  FileWrite(curve,Stamp(TimeCurrent()),A(ACCOUNT_BALANCE),e,A(ACCOUNT_MARGIN),A(ACCOUNT_MARGIN_FREE),A(ACCOUNT_MARGIN_LEVEL),total,legs,basket,q.bid,q.ask,maxDD);
 }
}
void NewDay()
{
 long today=Day(TimeCurrent());if(today==dayKey)return;
 if(dayKey!=0)Event("day_end","end of last observed broker day");
 dayKey=today;dayBalance=A(ACCOUNT_BALANCE);dayCapped=false;Event("day_start","net cash target resets at broker midnight");
}
bool OpenLeg()
{
 MqlTick q;if(!SymbolInfoTick(_Symbol,q) || q.ask<=0)return false;
 double lots=InpInitialLot*MathPow(2,legs),step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
 double trigger=legs>0?firstEntry-InpPriceStep*legs:q.ask;
 if(lots>maximum+1e-8 || MathAbs(lots/step-MathRound(lots/step))>1e-6)
 {
  if(lastReject!=TRADE_RETCODE_INVALID_VOLUME){Event("blocked","prescribed lot exceeds broker size/step",q.ask,trigger,lots);blocked++;if(firstBlocked==0)firstBlocked=TimeCurrent();}
  lastReject=TRADE_RETCODE_INVALID_VOLUME;lastRetry=TimeCurrent();return false;
 }
 Event("buy_request",legs==0?"first leg":"doubling rung",q.ask,trigger,lots);
 bool ok=trade.Buy(lots,_Symbol,0,0,0,"GRID|"+(string)basket+"|"+(string)legs);
 uint rc=trade.ResultRetcode();
 if(!ok || (rc!=TRADE_RETCODE_DONE && rc!=TRADE_RETCODE_DONE_PARTIAL))
 {
  if(lastReject!=rc){Event("blocked",trade.ResultRetcodeDescription(),q.ask,trigger,lots);blocked++;if(firstBlocked==0)firstBlocked=TimeCurrent();}
  lastReject=rc;lastRetry=TimeCurrent();Track();return false;
 }
 double actual=trade.ResultVolume();
 if(legs==0)firstEntry=trade.ResultPrice();
 legs++;opened++;maxSingleLot=MathMax(maxSingleLot,actual);lastReject=0;lastRetry=0;
 Event("buy_filled",rc==TRADE_RETCODE_DONE_PARTIAL?"partial fill":"filled",q.ask,trigger,actual,trade.ResultPrice());Track();
 if(rc==TRADE_RETCODE_DONE_PARTIAL){Event("unsupported","partial fill changes exact doubling ladder");stopRequested=true;TesterStop();}
 return true;
}
void CloseBasket()
{
 // Close oldest first. No new buys while the basket is being closed.
 while(true)
 {
  ulong oldest=0;
  for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);if(t && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic && (oldest==0 || t<oldest))oldest=t;}
  if(oldest==0)break;
  if(!trade.PositionClose(oldest) || trade.ResultRetcode()!=TRADE_RETCODE_DONE){Event("close_error",trade.ResultRetcodeDescription());Track();return;}
  Track();
 }
 closedBaskets++;Event("basket_closed","net basket cash="+DoubleToString(A(ACCOUNT_BALANCE)-basketBalance,2));
 if(firstClosedDouble==0 && A(ACCOUNT_BALANCE)>=2*startBalance){firstClosedDouble=TimeCurrent();Event("closed_double","flat balance at least twice initial; no withdrawals");}
 legs=0;firstEntry=0;closing=false;lastReject=0;lastRetry=0;
}
void OnTick()
{
 if(firstTick==0)firstTick=TimeCurrent();
 NewDay();Track();if(stopRequested)return;
 if(closing){CloseBasket();return;}
 MqlTick q;if(!SymbolInfoTick(_Symbol,q) || q.bid<=0 || q.ask<=0)return;
 double total=0;int count=PositionCount(total);
 if(count==0)
 {
  if(legs>0){Event("unexpected_flat","positions disappeared without strategy basket close");stopRequested=true;TesterStop();return;}
  if(A(ACCOUNT_BALANCE)-dayBalance>=InpDailyTarget)
  {if(!dayCapped){dayCapped=true;daysTarget++;Event("daily_target","no further new baskets today");}return;}
  if(lastRetry && TimeCurrent()-lastRetry<60)return;
  basket++;basketBalance=A(ACCOUNT_BALANCE);OpenLeg();return;
 }
 double target=legs==1?firstEntry+InpPriceStep:firstEntry;
 if(q.bid>=target){Event("exit_trigger",legs==1?"single leg plus price step":"all legs at original entry",q.bid,target);closing=true;CloseBasket();return;}
 double add=firstEntry-InpPriceStep*legs;
 if(q.ask<=add && (lastRetry==0 || TimeCurrent()-lastRetry>=60))OpenLeg();
}
void OnTradeTransaction(const MqlTradeTransaction &trans,const MqlTradeRequest &request,const MqlTradeResult &result)
{
 if(trans.type!=TRADE_TRANSACTION_DEAL_ADD || trans.deal==0 || !HistoryDealSelect(trans.deal))return;
 if(HistoryDealGetString(trans.deal,DEAL_SYMBOL)!=_Symbol)return;
 long reason=HistoryDealGetInteger(trans.deal,DEAL_REASON);
 if(reason==DEAL_REASON_SO && firstStopout==0)
 {firstStopout=(datetime)HistoryDealGetInteger(trans.deal,DEAL_TIME);Event("stop_out","native broker forced-liquidation deal");stopRequested=true;Track();TesterStop();}
}
void WritePair(string key,string value){FileWrite(summary,key,value);}
void WriteNumber(string key,double value){WritePair(key,DoubleToString(value,8));}
void ExportLedger()
{
 HistorySelect(0,TimeCurrent());int n=HistoryDealsTotal();
 for(int i=0;i<n;i++)
 {
  ulong t=HistoryDealGetTicket(i);if(!t)continue;
  FileWrite(ledger,t,Stamp((datetime)HistoryDealGetInteger(t,DEAL_TIME)),HistoryDealGetInteger(t,DEAL_TIME_MSC),HistoryDealGetString(t,DEAL_SYMBOL),
            HistoryDealGetInteger(t,DEAL_POSITION_ID),HistoryDealGetInteger(t,DEAL_TYPE),HistoryDealGetInteger(t,DEAL_ENTRY),HistoryDealGetInteger(t,DEAL_REASON),
            HistoryDealGetDouble(t,DEAL_VOLUME),HistoryDealGetDouble(t,DEAL_PRICE),HistoryDealGetDouble(t,DEAL_PROFIT),HistoryDealGetDouble(t,DEAL_COMMISSION),
            HistoryDealGetDouble(t,DEAL_SWAP),HistoryDealGetDouble(t,DEAL_FEE),HistoryDealGetString(t,DEAL_COMMENT));
 }
}
int OnInit()
{
 if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;
 if(InpInitialLot<=0 || InpPriceStep<=0 || InpDailyTarget<=0 || AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)return INIT_PARAMETERS_INCORRECT;
 startBalance=A(ACCOUNT_BALANCE);peakEq=startBalance;minEq=startBalance;
 string prefix="DoublingGrid-"+(string)InpMagic;
 events=FileOpen(prefix+"-events.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');curve=FileOpen(prefix+"-equity.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');
 ledger=FileOpen(prefix+"-deals.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');summary=FileOpen(prefix+"-summary.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');
 if(events==INVALID_HANDLE || curve==INVALID_HANDLE || ledger==INVALID_HANDLE || summary==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(events,"time","event","detail","basket","legs","first_entry","quote","trigger","lots","fill","bid","ask","balance","equity","margin","free_margin","margin_level","day","day_start_balance","daily_cash_pnl","total_lots","positions");
 FileWrite(curve,"time","balance","equity","margin","free_margin","margin_level","total_lots","legs","basket","bid","ask","running_max_equity_dd_pct");
 FileWrite(ledger,"deal","time","time_msc","symbol","position_id","type","entry","reason","volume","price","profit","commission","swap","fee","comment");
 FileWrite(summary,"key","value");
 trade.SetExpertMagicNumber(InpMagic);trade.SetDeviationInPoints(InpDeviationPoints);trade.SetTypeFillingBySymbol(_Symbol);
 Print("GRID CONTRACT symbol=",_Symbol," contract=",SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE)," min=",SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN)," max=",SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX)," step=",SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP)," leverage=",AccountInfoInteger(ACCOUNT_LEVERAGE)," margin_mode=",AccountInfoInteger(ACCOUNT_MARGIN_MODE)," so_mode=",AccountInfoInteger(ACCOUNT_MARGIN_SO_MODE)," so_call=",A(ACCOUNT_MARGIN_SO_CALL)," so_so=",A(ACCOUNT_MARGIN_SO_SO));
 return INIT_SUCCEEDED;
}
void OnDeinit(const int why)
{
 Track();Event("summary","deinit "+(string)why);ExportLedger();
 WritePair("first_tick",Stamp(firstTick));WritePair("last_tick",Stamp(TimeCurrent()));WritePair("first_closed_double",Stamp(firstClosedDouble));WritePair("first_equity_double",Stamp(firstEquityDouble));
 WritePair("first_stopout",Stamp(firstStopout));WritePair("first_blocked",Stamp(firstBlocked));
 WriteNumber("initial_balance",startBalance);WriteNumber("final_balance",A(ACCOUNT_BALANCE));WriteNumber("final_equity",A(ACCOUNT_EQUITY));
 WriteNumber("max_equity",peakEq);WriteNumber("min_equity",minEq);WriteNumber("max_equity_dd_pct",maxDD);WriteNumber("max_equity_dd_cash",maxDDCash);
 WriteNumber("max_total_lots",maxTotalLots);WriteNumber("max_single_lot",maxSingleLot);WriteNumber("max_legs",maxLegs);WriteNumber("entries",opened);WriteNumber("baskets_closed",closedBaskets);WriteNumber("blocked_events",blocked);WriteNumber("daily_targets_reached",daysTarget);
 WriteNumber("leverage",AccountInfoInteger(ACCOUNT_LEVERAGE));WriteNumber("margin_mode",AccountInfoInteger(ACCOUNT_MARGIN_MODE));WriteNumber("stopout_mode",AccountInfoInteger(ACCOUNT_MARGIN_SO_MODE));WriteNumber("margin_call",A(ACCOUNT_MARGIN_SO_CALL));WriteNumber("stopout",A(ACCOUNT_MARGIN_SO_SO));WriteNumber("contract_size",SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE));
 WriteNumber("min_margin_level",minMarginLevel);WriteNumber("open_legs_at_deinit",legs);
 FileClose(events);FileClose(curve);FileClose(ledger);FileClose(summary);
}

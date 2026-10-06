#property copyright "Calyx independent UK100 three-module research"
#property version "1.00"
#property strict
// Public concept only, not QuantLab's proprietary EA or preset.
// Tester-only: all numeric rules below are independent frozen assumptions.
#include <Trade/Trade.mqh>

input group "Closed H1 signals"
input bool InpEnableDrop=true;
input bool InpEnableMonday=true;
input bool InpEnableTrend=true;
input int InpATRPeriod=14;
input int InpDropLookback=24;
input double InpDropATR=3.0;
input int InpRSIPeriod=2;
input double InpOversoldRSI=10.0;
input double InpMondayDipATR=0.5;
input int InpPullbackEMA=20;
input int InpTrendEMA=50;
input int InpSlowEMA=200;

input group "Shared account and separate module positions"
input double InpRiskPercent=1.0;
input double InpStopATR=2.0;
input double InpDropTargetR=1.0;
input double InpMondayTargetR=1.0;
input double InpTrendTargetR=2.0;
input int InpMaxHoldingHours=48;
input int InpMaxPositions=3;
input int InpLossesBeforePause=3;
input int InpPauseHours=24;

input group "Independent London entry window"
input int InpEntryStartHourLondon=8;
input int InpEntryEndHourLondon=16;
input int InpServerUtcOffsetHours=0;
input long InpBaseMagic=867300;
input int InpDeviationPoints=50;

CTrade trade;
int h_atr=INVALID_HANDLE,h_rsi=INVALID_HANDLE,h_pull=INVALID_HANDLE,h_trend=INVALID_HANDLE,h_slow=INVALID_HANDLE;
datetime last_bar=0,blocked_until=0;
int last_dates[3],opened[3],minlot_skips[3];
int losing_streak=0,pause_count=0,blocked_bars=0,entry_errors=0,close_errors=0;
ulong processed[];

datetime UtcDate(int year,int month,int day,int hour)
{
 MqlDateTime p;ZeroMemory(p);p.year=year;p.mon=month;p.day=day;p.hour=hour;
 return StructToTime(p);
}
int LastSunday(int year,int month)
{
 int day=31;MqlDateTime p;TimeToStruct(UtcDate(year,month,day,0),p);
 return day-p.day_of_week;
}
datetime London(datetime server)
{
 datetime utc=server-InpServerUtcOffsetHours*3600;MqlDateTime p;TimeToStruct(utc,p);
 datetime start=UtcDate(p.year,3,LastSunday(p.year,3),1),end=UtcDate(p.year,10,LastSunday(p.year,10),1);
 return utc+(utc>=start && utc<end ? 3600 : 0);
}
int DateKey(datetime server)
{
 MqlDateTime p;TimeToStruct(London(server),p);return p.year*10000+p.mon*100+p.day;
}
bool EntryWindow()
{
 MqlDateTime p;TimeToStruct(London(TimeCurrent()),p);
 return p.day_of_week>=1 && p.day_of_week<=5 && p.hour>=InpEntryStartHourLondon && p.hour<InpEntryEndHourLondon;
}
bool BrokerSessionOpen()
{
 MqlDateTime p;TimeToStruct(TimeCurrent(),p);int seconds=p.hour*3600+p.min*60+p.sec;
 for(uint i=0;i<20;i++){
  datetime from=0,to=0;if(!SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)p.day_of_week,i,from,to))break;
  int a=(int)((long)from%86400),b=(int)((long)to%86400);
  if(a==b || (a<b && seconds>=a && seconds<b) || (a>b && (seconds>=a || seconds<b)))return true;
 }
 return false;
}
bool Ours()
{
 long magic=PositionGetInteger(POSITION_MAGIC);
 return PositionGetString(POSITION_SYMBOL)==_Symbol && magic>=InpBaseMagic+1 && magic<=InpBaseMagic+3;
}
int OwnCount()
{
 int n=0;for(int i=PositionsTotal()-1;i>=0;i--)if(PositionGetTicket(i)>0 && Ours())n++;return n;
}
bool ModuleOpen(int module)
{
 for(int i=PositionsTotal()-1;i>=0;i--)if(PositionGetTicket(i)>0 && Ours() && PositionGetInteger(POSITION_MAGIC)==InpBaseMagic+module)return true;
 return false;
}
bool PositionAlive(ulong id)
{
 for(int i=PositionsTotal()-1;i>=0;i--)if(PositionGetTicket(i)>0 && Ours() && (ulong)PositionGetInteger(POSITION_IDENTIFIER)==id)return true;
 return false;
}
bool Seen(ulong id)
{
 for(int i=0;i<ArraySize(processed);i++)if(processed[i]==id)return true;return false;
}
bool CanEnter(int module,int date)
{
 return !ModuleOpen(module) && OwnCount()<InpMaxPositions && last_dates[module-1]!=date && TimeCurrent()>=blocked_until;
}
bool Value(int handle,int shift,double &v)
{
 double a[];if(CopyBuffer(handle,0,shift,1,a)!=1 || !MathIsValidNumber(a[0]))return false;
 v=a[0];return true;
}
double TickSize()
{
 double v=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);return v>0 ? v : SymbolInfoDouble(_Symbol,SYMBOL_POINT);
}
double Price(double raw,bool down)
{
 double steps=raw/TickSize();
 return NormalizeDouble((down?MathFloor(steps+1e-9):MathCeil(steps-1e-9))*TickSize(),(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}
double BrokerGap()
{
 return MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*SymbolInfoDouble(_Symbol,SYMBOL_POINT)+TickSize();
}
double Lots(ENUM_ORDER_TYPE type,double entry,double stop,double cash)
{
 double loss=0;if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,loss) || MathAbs(loss)<=0)return 0;
 double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
 if(step<=0 || minimum<=0)return 0;
 double lots=MathFloor((MathMin(cash/MathAbs(loss),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX))+1e-12)/step)*step;
 return lots<minimum-1e-12 ? 0.0 : NormalizeDouble(lots,8);
}
double FridayClose()
{
 MqlRates d[];ArraySetAsSeries(d,true);int count=CopyRates(_Symbol,PERIOD_D1,1,10,d);
 for(int i=0;i<count;i++){MqlDateTime p;TimeToStruct(d[i].time,p);if(p.day_of_week==5)return d[i].close;}
 return 0;
}
void Enter(int module,int direction,double atr,int date,datetime signal_bar,double drop,double prior_rsi,double friday,
           double prior_close,double prior_high,double prior_low,double signal_open,double signal_close,double peak,
           double previous_atr,double pull,double previous_pull,double trend,double previous_trend,double slow)
{
 if(!CanEnter(module,date) || !BrokerSessionOpen())return;
 MqlTick q;if(!SymbolInfoTick(_Symbol,q) || q.ask<=0 || q.bid<=0)return;
 double quote=direction>0?q.ask:q.bid;
 double stop=quote-direction*InpStopATR*atr;
 stop=direction>0?MathMin(stop,q.bid-BrokerGap()):MathMax(stop,q.ask+BrokerGap());
 stop=Price(stop,direction>0);
 double equity=AccountInfoDouble(ACCOUNT_EQUITY),cash=equity*InpRiskPercent/100.0;
 ENUM_ORDER_TYPE type=direction>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 double lots=Lots(type,quote,stop,cash);
 if(lots<=0){minlot_skips[module-1]++;PrintFormat("UKT_SKIP_MINLOT date=%d module=%d budget=%.4f",date,module,cash);return;}
 double rr=module==1?InpDropTargetR:module==2?InpMondayTargetR:InpTrendTargetR;
 double target=Price(quote+direction*rr*MathAbs(quote-stop),direction<0);
 trade.SetExpertMagicNumber((ulong)(InpBaseMagic+module));
 string comment="UKT"+(string)date+"_M"+(string)module;
 bool ok=direction>0?trade.Buy(lots,_Symbol,0,stop,target,comment):trade.Sell(lots,_Symbol,0,stop,target,comment);
 if(!ok || trade.ResultRetcode()!=TRADE_RETCODE_DONE){
  entry_errors++;PrintFormat("UKT_ENTRY_FAILED date=%d module=%d reason=%s",date,module,trade.ResultRetcodeDescription());return;
 }
 ulong ticket=0;
 for(int i=PositionsTotal()-1;i>=0;i--){
  ulong p=PositionGetTicket(i);
  if(p>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpBaseMagic+module){ticket=p;break;}
 }
 if(ticket==0){entry_errors++;Print("UKT_ENTRY_FAILED no position after fill");return;}
 double requested=0,actual=0,open=PositionGetDouble(POSITION_PRICE_OPEN);
 if(!OrderCalcProfit(type,_Symbol,lots,quote,stop,requested) || !OrderCalcProfit(type,_Symbol,lots,open,stop,actual)){
  entry_errors++;Print("UKT_ENTRY_FAILED risk audit unavailable");return;
 }
 last_dates[module-1]=date;opened[module-1]++;
 PrintFormat("UKT_SIGNAL date=%d module=%d direction=%d bar=%s drop=%.8f prior_rsi=%.8f friday=%.8f prior_close=%.8f prior_high=%.8f prior_low=%.8f signal_open=%.8f signal_close=%.8f peak=%.8f previous_atr=%.8f atr=%.8f pull=%.8f previous_pull=%.8f trend=%.8f previous_trend=%.8f slow=%.8f",
  date,module,direction,TimeToString(signal_bar,TIME_DATE|TIME_MINUTES),drop,prior_rsi,friday,prior_close,prior_high,prior_low,signal_open,signal_close,peak,previous_atr,atr,pull,previous_pull,trend,previous_trend,slow);
 PrintFormat("UKT_ENTRY date=%d module=%d position=%I64u side=%d lots=%.8f actual_open=%.8f initial_sl=%.8f requested_tp=%.8f equity=%.4f budget=%.4f requested_stop_cash=%.4f actual_stop_cash=%.4f",
  date,module,(ulong)PositionGetInteger(POSITION_IDENTIFIER),direction,lots,open,stop,target,equity,cash,MathAbs(requested),MathAbs(actual));
}
void Manage()
{
 if(!BrokerSessionOpen())return;
 for(int i=PositionsTotal()-1;i>=0;i--){
  ulong ticket=PositionGetTicket(i);if(ticket==0 || !Ours())continue;
  if(TimeCurrent()<(datetime)PositionGetInteger(POSITION_TIME)+InpMaxHoldingHours*3600)continue;
  trade.SetExpertMagicNumber((ulong)PositionGetInteger(POSITION_MAGIC));
  if(!trade.PositionClose(ticket,(ulong)InpDeviationPoints) || trade.ResultRetcode()!=TRADE_RETCODE_DONE){
   close_errors++;PrintFormat("UKT_CLOSE_FAILED position=%I64u reason=%s",ticket,trade.ResultRetcodeDescription());
  }
 }
}
void Process()
{
 if(!EntryWindow() || !BrokerSessionOpen())return;
 if(TimeCurrent()<blocked_until){blocked_bars++;return;}
 int need=InpDropLookback+2;
 MqlRates r[];ArraySetAsSeries(r,true);if(CopyRates(_Symbol,PERIOD_H1,0,need,r)!=need)return;
 double atr=0,prior_atr=0,rsi=0,pull=0,previous_pull=0,trend=0,previous_trend=0,slow=0;
 if(!Value(h_atr,1,atr) || !Value(h_atr,2,prior_atr) || !Value(h_rsi,2,rsi) || !Value(h_pull,1,pull) ||
    !Value(h_pull,2,previous_pull) || !Value(h_trend,1,trend) || !Value(h_trend,2,previous_trend) ||
    !Value(h_slow,1,slow) || atr<=0 || prior_atr<=0)return;
 double peak=r[2].high;for(int i=2;i<need;i++)peak=MathMax(peak,r[i].high);
 double drop=peak-r[2].close;
 bool recovery=r[1].close>r[1].open && r[1].close>r[2].high;
 int date=DateKey(TimeCurrent());MqlDateTime now;TimeToStruct(London(TimeCurrent()),now);
 double friday=now.day_of_week==1?FridayClose():0;
 if(InpEnableDrop && drop>=InpDropATR*prior_atr && rsi<=InpOversoldRSI && recovery)
  Enter(1,1,atr,date,r[1].time,drop,rsi,friday,r[2].close,r[2].high,r[2].low,r[1].open,r[1].close,peak,prior_atr,pull,previous_pull,trend,previous_trend,slow);
 if(InpEnableMonday && now.day_of_week==1 && friday>0 && r[2].close<=friday-InpMondayDipATR*prior_atr && recovery)
  Enter(2,1,atr,date,r[1].time,drop,rsi,friday,r[2].close,r[2].high,r[2].low,r[1].open,r[1].close,peak,prior_atr,pull,previous_pull,trend,previous_trend,slow);
 int direction=0;
 if(trend>slow && trend>previous_trend && r[2].close<=previous_pull && r[1].close>pull && r[1].close>r[1].open)direction=1;
 if(trend<slow && trend<previous_trend && r[2].close>=previous_pull && r[1].close<pull && r[1].close<r[1].open)direction=-1;
 if(InpEnableTrend && direction!=0)
  Enter(3,direction,atr,date,r[1].time,drop,rsi,friday,r[2].close,r[2].high,r[2].low,r[1].open,r[1].close,peak,prior_atr,pull,previous_pull,trend,previous_trend,slow);
}
void OnTradeTransaction(const MqlTradeTransaction &trans,const MqlTradeRequest &request,const MqlTradeResult &result)
{
 if(trans.type!=TRADE_TRANSACTION_DEAL_ADD || trans.deal==0 || !HistoryDealSelect(trans.deal))return;
 long magic=HistoryDealGetInteger(trans.deal,DEAL_MAGIC);
 if(magic<InpBaseMagic+1 || magic>InpBaseMagic+3 || HistoryDealGetString(trans.deal,DEAL_SYMBOL)!=_Symbol)return;
 if(HistoryDealGetInteger(trans.deal,DEAL_ENTRY)!=DEAL_ENTRY_OUT)return;
 ulong id=(ulong)HistoryDealGetInteger(trans.deal,DEAL_POSITION_ID);int module=(int)(magic-InpBaseMagic);
 if(PositionAlive(id) || Seen(id))return;
 if(!HistorySelectByPosition(id)){Print("UKT_AUDIT_FAILED missing closed-position history");return;}
 double net=0;
 for(int i=0;i<HistoryDealsTotal();i++){
  ulong deal=HistoryDealGetTicket(i);if(deal==0)continue;
  net+=HistoryDealGetDouble(deal,DEAL_PROFIT)+HistoryDealGetDouble(deal,DEAL_COMMISSION)+HistoryDealGetDouble(deal,DEAL_SWAP)+HistoryDealGetDouble(deal,DEAL_FEE);
 }
 int n=ArraySize(processed);if(ArrayResize(processed,n+1)!=n+1){Print("UKT_AUDIT_FAILED record allocation");return;}processed[n]=id;
 losing_streak=net<0?losing_streak+1:0;
 bool pause=losing_streak>=InpLossesBeforePause;
 if(pause){blocked_until=TimeCurrent()+InpPauseHours*3600;losing_streak=0;pause_count++;}
 PrintFormat("UKT_RESULT position=%I64u module=%d net=%.4f losing_streak=%d pause=%d blocked_until=%s",
  id,module,net,losing_streak,pause,TimeToString(blocked_until,TIME_DATE|TIME_SECONDS));
}
int OnInit()
{
 if(!(bool)MQLInfoInteger(MQL_TESTER)){Print("UKT_RESEARCH_ONLY no live/demo execution");return INIT_FAILED;}
 if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING){Print("UKT_REQUIRES_HEDGING");return INIT_FAILED;}
 if(_Period!=PERIOD_H1 || InpATRPeriod<2 || InpDropLookback<2 || InpDropLookback>500 || InpDropATR<=0 ||
    InpRSIPeriod<2 || InpOversoldRSI<0 || InpOversoldRSI>100 || InpMondayDipATR<0 ||
    InpPullbackEMA<2 || InpTrendEMA<=InpPullbackEMA || InpSlowEMA<=InpTrendEMA || InpRiskPercent<=0 || InpRiskPercent>1 ||
    InpStopATR<=0 || InpDropTargetR<=0 || InpMondayTargetR<=0 || InpTrendTargetR<=0 ||
    InpMaxHoldingHours<1 || InpMaxPositions<1 || InpMaxPositions>3 || InpLossesBeforePause<1 || InpPauseHours<1 ||
    InpEntryStartHourLondon<0 || InpEntryEndHourLondon>24 || InpEntryStartHourLondon>=InpEntryEndHourLondon ||
    InpBaseMagic<=0 || InpDeviationPoints<0)return INIT_PARAMETERS_INCORRECT;
 h_atr=iATR(_Symbol,PERIOD_H1,InpATRPeriod);h_rsi=iRSI(_Symbol,PERIOD_H1,InpRSIPeriod,PRICE_CLOSE);
 h_pull=iMA(_Symbol,PERIOD_H1,InpPullbackEMA,0,MODE_EMA,PRICE_CLOSE);
 h_trend=iMA(_Symbol,PERIOD_H1,InpTrendEMA,0,MODE_EMA,PRICE_CLOSE);h_slow=iMA(_Symbol,PERIOD_H1,InpSlowEMA,0,MODE_EMA,PRICE_CLOSE);
 if(h_atr==INVALID_HANDLE || h_rsi==INVALID_HANDLE || h_pull==INVALID_HANDLE || h_trend==INVALID_HANDLE || h_slow==INVALID_HANDLE)return INIT_FAILED;
 trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(InpDeviationPoints);
 last_bar=iTime(_Symbol,PERIOD_H1,0);
 Print("UKT_INDEPENDENT_ASSUMPTIONS: three modules share account; 1% EACH trade; 3 simultaneous slots; numeric rules not vendor settings.");
 return INIT_SUCCEEDED;
}
void OnTick()
{
 Manage();datetime bar=iTime(_Symbol,PERIOD_H1,0);if(bar<=0 || bar==last_bar)return;
 last_bar=bar;Process();
}
void OnDeinit(const int reason)
{
 if(HistorySelect(0,TimeCurrent()+1)){
  for(int i=0;i<HistoryDealsTotal();i++){
   ulong deal=HistoryDealGetTicket(i);if(deal==0 || HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol)continue;
   long type=HistoryDealGetInteger(deal,DEAL_TYPE);if(type!=DEAL_TYPE_BUY && type!=DEAL_TYPE_SELL)continue;
   PrintFormat("UKT_DEAL_MAP deal=%I64u position=%I64u order=%I64u entry=%d",
    deal,(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID),(ulong)HistoryDealGetInteger(deal,DEAL_ORDER),(int)HistoryDealGetInteger(deal,DEAL_ENTRY));
  }
 }
 if(h_atr!=INVALID_HANDLE)IndicatorRelease(h_atr);if(h_rsi!=INVALID_HANDLE)IndicatorRelease(h_rsi);
 if(h_pull!=INVALID_HANDLE)IndicatorRelease(h_pull);if(h_trend!=INVALID_HANDLE)IndicatorRelease(h_trend);if(h_slow!=INVALID_HANDLE)IndicatorRelease(h_slow);
 PrintFormat("UKT_SUMMARY drop=%d monday=%d trend=%d pauses=%d blocked_bars=%d minlot_skips=%d entry_errors=%d close_errors=%d processed_exits=%d",
  opened[0],opened[1],opened[2],pause_count,blocked_bars,minlot_skips[0]+minlot_skips[1]+minlot_skips[2],entry_errors,close_errors,ArraySize(processed));
}

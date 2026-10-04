#property strict
#property version "1.00"
#property description "Tester-only raw candle lifecycle experiment. Refuses live initialization."
#include <Trade/Trade.mqh>
input ENUM_TIMEFRAMES InpParentTF=PERIOD_H1;
input bool InpControl=false;
input double InpRiskPercent=1.0;
input string InpTag="smoke";
input long InpMagic=100303710;
input datetime InpTradeFrom=D'2025.10.03';
CTrade trade;
datetime last_m1=0,attempted_parent=0,exit_due=0;
int audit=INVALID_HANDLE;
ulong Own()
{
 for(int i=PositionsTotal()-1;i>=0;i--)
 {
  ulong t=PositionGetTicket(i);
  if(t && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)return t;
 }
 return 0;
}
double Volume(const double entry,const double stop,double &requested,double &actual)
{
 double loss=0;
 if(!OrderCalcProfit(ORDER_TYPE_SELL,_Symbol,1,entry,stop,loss) || loss>=0)return 0;
 requested=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100;
 double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
 if(step<=0 || mn<=0 || mx<=0 || requested<=0)return 0;
 double raw=requested/MathAbs(loss);
 double lot=NormalizeDouble(MathMax(mn,MathMin(mx,MathCeil((MathMin(raw,mx)-1e-12)/step)*step)),8);
 actual=lot*MathAbs(loss);return lot;
}
int OnInit()
{
 if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;
 if(InpParentTF!=PERIOD_H1 && InpParentTF!=PERIOD_H4 && InpParentTF!=PERIOD_D1)return INIT_PARAMETERS_INCORRECT;
 if(InpRiskPercent<=0)return INIT_PARAMETERS_INCORRECT;
 trade.SetExpertMagicNumber((ulong)InpMagic);trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(80);
 audit=FileOpen("GoldLifecycle20261003-"+InpTag+".csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(audit==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(audit,"event","epoch","parent_epoch","parent_open","prior_open","prior_close","midpoint","end_epoch","signal_epoch","signal_close","first_high","known_high","observed_until","observed_count","decision_bid","decision_ask","stop","requested_risk","actual_risk","volume","retcode","fill_price");
 last_m1=iTime(_Symbol,PERIOD_M1,0);return INIT_SUCCEEDED;
}
void OnDeinit(const int reason){if(audit!=INVALID_HANDLE)FileClose(audit);}
void OnTick()
{
 ulong t=Own();
 if(t && exit_due>0 && TimeCurrent()>=exit_due)
 {
  bool ok=trade.PositionClose(t,80);
  FileWrite(audit,"exit",(long)TimeCurrent(),0,0,0,0,0,(long)exit_due,0,0,0,0,0,0,0,0,0,0,0,0,trade.ResultRetcode(),trade.ResultPrice());
  if(!ok && Own())Print("LIFECYCLE_CLOSE_FAILURE ",trade.ResultRetcode());
 }
 datetime minute=iTime(_Symbol,PERIOD_M1,0);
 if(minute<=0 || minute==last_m1)return;
 last_m1=minute;
 if(TimeCurrent()<InpTradeFrom || Own())return;
 datetime parent=iTime(_Symbol,InpParentTF,0);
 if(parent<=0 || parent==attempted_parent)return;
 int seconds=PeriodSeconds(InpParentTF);datetime midpoint=parent+seconds/2,end=parent+seconds;
 MqlRates prior[1],closed[1];
 if(CopyRates(_Symbol,InpParentTF,1,1,prior)!=1 || prior[0].close>=prior[0].open)return;
 if(CopyRates(_Symbol,PERIOD_M1,1,1,closed)!=1)return;
 if(closed[0].time<midpoint || closed[0].time+60>TimeCurrent() || TimeCurrent()>=end)return;
 double open=iOpen(_Symbol,InpParentTF,0);
 MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return;
 if(!InpControl && (closed[0].close>=open || tick.bid>=open))return;
 MqlRates observed[];
 int n=CopyRates(_Symbol,PERIOD_M1,parent,closed[0].time,observed);
 if(n<2)return;
 double first_high=-DBL_MAX,known_high=-DBL_MAX;int first_count=0;
 for(int i=0;i<n;i++)
 {
  if(observed[i].time+60>TimeCurrent())return;
  known_high=MathMax(known_high,observed[i].high);
  if(observed[i].time<midpoint){first_high=MathMax(first_high,observed[i].high);first_count++;}
 }
 if(first_count==0)return;
 double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);if(tick_size<=0)return;
 if(!InpControl && first_high<open+tick_size*.5)return;
 double stop=known_high+(tick.ask-tick.bid)+2*tick_size;
 double minimum=(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)+2)*_Point;
 stop=MathMax(stop,tick.ask+minimum);
 stop=MathCeil((stop-1e-10)/tick_size)*tick_size;stop=NormalizeDouble(stop,_Digits);
 double requested=0,actual=0,volume=Volume(tick.bid,stop,requested,actual);
 if(volume<=0)return;
 attempted_parent=parent;exit_due=end;
 bool ok=trade.Sell(volume,_Symbol,0,stop,0,"Candle lifecycle raw");
 FileWrite(audit,"entry",(long)TimeCurrent(),(long)parent,DoubleToString(open,_Digits),DoubleToString(prior[0].open,_Digits),DoubleToString(prior[0].close,_Digits),(long)midpoint,(long)end,(long)closed[0].time,DoubleToString(closed[0].close,_Digits),DoubleToString(first_high,_Digits),DoubleToString(known_high,_Digits),(long)closed[0].time,n,DoubleToString(tick.bid,_Digits),DoubleToString(tick.ask,_Digits),DoubleToString(stop,_Digits),requested,actual,volume,trade.ResultRetcode(),trade.ResultPrice());
 if(!ok)Print("LIFECYCLE_ENTRY_FAILURE ",trade.ResultRetcode());
}

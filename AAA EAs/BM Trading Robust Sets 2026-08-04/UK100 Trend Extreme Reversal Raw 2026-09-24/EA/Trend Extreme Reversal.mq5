#property strict
#property version "1.02"
#include <Trade/Trade.mqh>
// Research-only raw EA (2026-09-24). No active EA/includes/SETs are modified.
//
// Idea (user-supplied video transcript, UK 100): when the bigger trend is up and price drops to an extreme,
// buy the reversal; when the bigger trend is down and price rises to an extreme, sell. The transcript gives no
// exact rules, so every definition below is a disclosed research assumption selected by the user's options:
// - Trend (daily, last completed D1 bar): 0 = close vs SMA(200), 1 = close vs EMA(50).
// - Extreme (last completed signal-timeframe bar):
//   0 = RSI(2) < 10 (long) / > 90 (short)
//   1 = close <= highest high of the last 10 bars - 2*ATR(14) (long) / close >= lowest low + 2*ATR (short)
//   2 = three consecutive lower closes (long) / higher closes (short)
// - Exit: 0 = close when RSI(2) crosses back above 50 (long) / below 50 (short); protective stop 2*ATR(14)
//         1 = close when the bar closes above SMA(5) (long) / below (short); NO stop (sized as if 2*ATR)
//         2 = fixed stop and target at 1.5*ATR(14) (1:1)
// - Entry at market on the first tick after the signal bar closes. One position at a time.
// - v1.01: if an exit or entry is rejected because the market is closed (first quote of a bar can arrive before
//   the session opens), the same bar is retried on the next tick instead of waiting for the next bar.
// - v1.02: a new bar is only processed once the broker's trading session for the symbol is open
//   (SymbolInfoSessionTrade), so orders are not re-sent on every pre-open quote.
// - Risk: 1% of equity on the stop distance (2*ATR, or 1.5*ATR for exit 2); volume rounds UP to the broker
//   step with the minimum lot as floor, so actual risk can exceed 1%.
input int InpTrendMode=0;
input int InpExtremeMode=0;
input int InpExitMode=0;
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_H4;
input double InpRiskPercent=1;
input long InpExpectedLogin=0;
input string InpExpectedServer="";
input long InpMagic=89240901;
input string InpCase="raw";
CTrade trade;
int h_trend=INVALID_HANDLE,h_rsi=INVALID_HANDLE,h_atr=INVALID_HANDLE,h_sma5=INVALID_HANDLE;
datetime bar_seen=0;
int signals=0,entries=0,rejected=0,exits_rule=0,no_data=0,closed_retries=0;
bool retry_bar=false;
int audit_file=INVALID_HANDLE;

bool Buf(int h,int shift,double &v){double b[];if(h==INVALID_HANDLE||CopyBuffer(h,0,shift,1,b)!=1)return false;v=b[0];return MathIsValidNumber(v);}
double Price(double p){double t=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);return NormalizeDouble(MathRound(p/t)*t,_Digits);}
bool OwnPosition(ulong &id){
 for(int i=PositionsTotal()-1;i>=0;i--){ulong p=PositionGetTicket(i);
  if(p && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic){id=p;return true;}}
 return false;
}
void Audit(string kind,int side=0,double entry=0,double stop=0,double target=0,double lots=0,double risk=0){
 if(audit_file==INVALID_HANDLE)return;
 FileWrite(audit_file,kind,(long)TimeCurrent(),side,entry,stop,target,lots,risk);FileFlush(audit_file);
}
int TrendSide(){
 double ma,c=iClose(_Symbol,PERIOD_D1,1);
 if(c<=0 || !Buf(h_trend,1,ma))return 0;
 return c>ma?1:(c<ma?-1:0);
}
int ExtremeSide(){
 // +1 = extreme drop (long setup), -1 = extreme rise (short setup)
 if(InpExtremeMode==0){double r;if(!Buf(h_rsi,1,r))return 0;return r<10?1:(r>90?-1:0);}
 MqlRates b[];ArraySetAsSeries(b,true);
 if(CopyRates(_Symbol,InpSignalTimeframe,1,10,b)!=10)return 0;
 if(InpExtremeMode==1){
  double atr;if(!Buf(h_atr,1,atr))return 0;
  double hh=b[0].high,ll=b[0].low;for(int i=1;i<10;i++){hh=MathMax(hh,b[i].high);ll=MathMin(ll,b[i].low);}
  if(b[0].close<=hh-2*atr)return 1;
  if(b[0].close>=ll+2*atr)return -1;
  return 0;
 }
 if(b[0].close<b[1].close && b[1].close<b[2].close && b[2].close<b[3].close)return 1;
 if(b[0].close>b[1].close && b[1].close>b[2].close && b[2].close>b[3].close)return -1;
 return 0;
}
void ManageExit(){
 ulong id;if(!OwnPosition(id) || !PositionSelectByTicket(id))return;
 if(InpExitMode==2)return;   // broker-side stop/target only
 bool buy=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY;
 bool out=false;
 if(InpExitMode==0){double r1,r2;if(Buf(h_rsi,1,r1)&&Buf(h_rsi,2,r2))out=buy?(r1>50&&r2<=50):(r1<50&&r2>=50);}
 else {double s;double c=iClose(_Symbol,InpSignalTimeframe,1);if(Buf(h_sma5,1,s)&&c>0)out=buy?c>s:c<s;}
 if(out){
  if(trade.PositionClose(id) && trade.ResultRetcode()==TRADE_RETCODE_DONE){exits_rule++;Audit("rule_exit",buy?1:-1);}
  else if(trade.ResultRetcode()==TRADE_RETCODE_MARKET_CLOSED){retry_bar=true;closed_retries++;}
 }
}
bool SessionOpen(datetime now){
 MqlDateTime d;TimeToStruct(now,d);
 long sec=d.hour*3600+d.min*60+d.sec;datetime a,b;bool any=false;
 for(uint i=0;i<20;i++){
  if(!SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)d.day_of_week,i,a,b))break;
  any=true;long from=(long)a,to=(long)b;if(to==0 && from>0)to=86400;
  if(sec>=from && sec<to)return true;
 }
 return !any;   // no session data: do not block
}
void OnTick(){
 datetime current=iTime(_Symbol,InpSignalTimeframe,0);
 if(current==0 || current==bar_seen)return;
 if(!SessionOpen(TimeCurrent()))return;   // wait for the session; bar is processed on the first in-session tick
 retry_bar=false;
 ManageExit();
 if(retry_bar)return;   // bar_seen not advanced: retry on the next tick
 ulong id;if(OwnPosition(id)){bar_seen=current;return;}
 int trend=TrendSide(),ext=ExtremeSide();
 if(trend==0 || ext==0 || trend!=ext){bar_seen=current;return;}
 int side=trend;
 double atr;if(!Buf(h_atr,1,atr) || atr<=0){no_data++;bar_seen=current;return;}
 MqlTick tick;if(!SymbolInfoTick(_Symbol,tick)){rejected++;bar_seen=current;return;}
 double entry=side>0?tick.ask:tick.bid;
 double dist=(InpExitMode==2?1.5:2.0)*atr;
 double stop=Price(side>0?entry-dist:entry+dist);
 double target=InpExitMode==2?Price(side>0?entry+dist:entry-dist):0;
 double placed_stop=InpExitMode==1?0:stop;
 ENUM_ORDER_TYPE type=side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 double unit=0;if(!OrderCalcProfit(type,_Symbol,1,entry,stop,unit) || unit>=0){rejected++;bar_seen=current;return;}
 double equity=AccountInfoDouble(ACCOUNT_EQUITY),step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
 double lots=MathCeil(equity*InpRiskPercent/100/MathAbs(unit)/step-1e-10)*step;
 lots=NormalizeDouble(MathMin(SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),MathMax(SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),lots)),8);
 double margin=0;if(!OrderCalcMargin(type,_Symbol,lots,entry,margin) || margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)){rejected++;bar_seen=current;Audit("margin_rejected",side,entry,stop,target,lots);return;}
 string comment=StringFormat("TER t%d x%d e%d",InpTrendMode,InpExtremeMode,InpExitMode);
 bool sent=side>0?trade.Buy(lots,_Symbol,0,placed_stop,target,comment):trade.Sell(lots,_Symbol,0,placed_stop,target,comment);
 if(sent && (trade.ResultRetcode()==TRADE_RETCODE_DONE || trade.ResultRetcode()==TRADE_RETCODE_DONE_PARTIAL)){entries++;signals++;bar_seen=current;Audit("entry",side,entry,stop,target,lots,MathAbs(unit)*lots);}
 else if(trade.ResultRetcode()==TRADE_RETCODE_MARKET_CLOSED){closed_retries++;}   // retry this bar on the next tick
 else {signals++;rejected++;bar_seen=current;Audit("order_rejected",side,entry,stop,target,lots);Print("TER_REJECT|",trade.ResultRetcode(),"|",trade.ResultRetcodeDescription());}
}
int OnInit(){
 if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;
 if(InpExpectedLogin<=0 || AccountInfoInteger(ACCOUNT_LOGIN)!=InpExpectedLogin || AccountInfoString(ACCOUNT_SERVER)!=InpExpectedServer)return INIT_FAILED;
 if(InpTrendMode<0||InpTrendMode>1||InpExtremeMode<0||InpExtremeMode>2||InpExitMode<0||InpExitMode>2||InpRiskPercent<=0)return INIT_PARAMETERS_INCORRECT;
 h_trend=InpTrendMode==0?iMA(_Symbol,PERIOD_D1,200,0,MODE_SMA,PRICE_CLOSE):iMA(_Symbol,PERIOD_D1,50,0,MODE_EMA,PRICE_CLOSE);
 h_rsi=iRSI(_Symbol,InpSignalTimeframe,2,PRICE_CLOSE);
 h_atr=iATR(_Symbol,InpSignalTimeframe,14);
 h_sma5=iMA(_Symbol,InpSignalTimeframe,5,0,MODE_SMA,PRICE_CLOSE);
 if(h_trend==INVALID_HANDLE||h_rsi==INVALID_HANDLE||h_atr==INVALID_HANDLE||h_sma5==INVALID_HANDLE)return INIT_FAILED;
 trade.SetExpertMagicNumber(InpMagic);trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(50);
 audit_file=FileOpen(InpCase+"-audit.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');if(audit_file==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(audit_file,"kind","server_epoch","side","entry","stop","target","lots","planned_cash_risk");
 Print("TER_SPEC|",_Symbol,"|contract=",SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),"|tick=",SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE),"|vol_min=",SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),"|server=",AccountInfoString(ACCOUNT_SERVER));
 return INIT_SUCCEEDED;
}
void OnDeinit(const int reason){
 if(audit_file!=INVALID_HANDLE)FileClose(audit_file);
 PrintFormat("TER_SUMMARY|%s|signals=%d|entries=%d|rejected=%d|rule_exits=%d|no_data=%d|closed_retries=%d|balance=%.2f",InpCase,signals,entries,rejected,exits_rule,no_data,closed_retries,AccountInfoDouble(ACCOUNT_BALANCE));
}

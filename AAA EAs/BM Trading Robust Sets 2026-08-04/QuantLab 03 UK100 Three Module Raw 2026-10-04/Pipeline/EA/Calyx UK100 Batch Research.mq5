#property copyright "Calyx independent UK100 three-module research"
#property version "1.10"
#property strict
// Public concept only, not QuantLab's proprietary EA or preset.
// Tester-only: all numeric rules below are independent frozen assumptions.
#include <Trade/Trade.mqh>


bool InpEnableDrop=true;
bool InpEnableMonday=true;
bool InpEnableTrend=true;
int InpATRPeriod=14;
int InpDropLookback=24;
double InpDropATR=3.0;
int InpRSIPeriod=2;
double InpOversoldRSI=10.0;
double InpMondayDipATR=0.5;
int InpPullbackEMA=20;
int InpTrendEMA=50;
int InpSlowEMA=200;


double InpRiskPercent=1.0;
double InpStopATR=2.0;
double InpDropTargetR=1.0;
double InpMondayTargetR=1.0;
double InpTrendTargetR=2.0;
int InpMaxHoldingHours=48;
int InpMaxPositions=3;
int InpLossesBeforePause=3;
int InpPauseHours=24;


int InpEntryStartHourLondon=8;
int InpEntryEndHourLondon=16;
int InpServerUtcOffsetHours=0;
long InpBaseMagic=867300;
int InpDeviationPoints=50;


ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_H1;
int InpEntryMode=0; // 0 next open;1 next closed confirmation;2 retest;3 breakout
double InpEntryOffsetATR=0.25;
int InpArmExpiryHours=6;
int InpStopMode=0; // 0 ATR;1 signal;2 swing;3 price%;4 fixed price units
double InpStopPercent=0.5;
double InpStopPriceUnits=50;
int InpExitMode=0; // 0 fixedR;1 noTP+trail;2 time only;3 London session end;4 partial
int InpManagement=0; // none,BE,ATR,percent,MA,swing,chandelier,dynamic50/20
double InpTrailStartR=1.0;
double InpTrailATR=1.0;
double InpTrailPercent=0.25;
int InpSessionMode=0; // baseline,Asia,London,NY,overlap,NYopen,all
int InpDirection=0; // 0 both;1 long;-1 short
int InpExcludeDays=0; // 0 none;1 Monday;2 Friday;3 both
int InpFilter=0; // 0 none;1ADX;2DI;3both;4HTF;5vol;6spread
double InpADXMin=20;
double InpMaxSpreadATR=0.08;
int InpPerModuleDay=1;
bool InpControl=false;
int InpControlSeed=20261004;
string InpExportTag="none";
bool InpCaptureEquity=false;
input int InpConfigIndex=0;
input string InpConfigFile="none";
bool Assign(string header,string value){
if(header=="InpEnableDrop"){InpEnableDrop=(value=="true");return true;}
if(header=="InpEnableMonday"){InpEnableMonday=(value=="true");return true;}
if(header=="InpEnableTrend"){InpEnableTrend=(value=="true");return true;}
if(header=="InpATRPeriod"){InpATRPeriod=(int)StringToInteger(value);return true;}
if(header=="InpDropLookback"){InpDropLookback=(int)StringToInteger(value);return true;}
if(header=="InpDropATR"){InpDropATR=StringToDouble(value);return true;}
if(header=="InpRSIPeriod"){InpRSIPeriod=(int)StringToInteger(value);return true;}
if(header=="InpOversoldRSI"){InpOversoldRSI=StringToDouble(value);return true;}
if(header=="InpMondayDipATR"){InpMondayDipATR=StringToDouble(value);return true;}
if(header=="InpPullbackEMA"){InpPullbackEMA=(int)StringToInteger(value);return true;}
if(header=="InpTrendEMA"){InpTrendEMA=(int)StringToInteger(value);return true;}
if(header=="InpSlowEMA"){InpSlowEMA=(int)StringToInteger(value);return true;}
if(header=="InpRiskPercent"){InpRiskPercent=StringToDouble(value);return true;}
if(header=="InpStopATR"){InpStopATR=StringToDouble(value);return true;}
if(header=="InpDropTargetR"){InpDropTargetR=StringToDouble(value);return true;}
if(header=="InpMondayTargetR"){InpMondayTargetR=StringToDouble(value);return true;}
if(header=="InpTrendTargetR"){InpTrendTargetR=StringToDouble(value);return true;}
if(header=="InpMaxHoldingHours"){InpMaxHoldingHours=(int)StringToInteger(value);return true;}
if(header=="InpMaxPositions"){InpMaxPositions=(int)StringToInteger(value);return true;}
if(header=="InpLossesBeforePause"){InpLossesBeforePause=(int)StringToInteger(value);return true;}
if(header=="InpPauseHours"){InpPauseHours=(int)StringToInteger(value);return true;}
if(header=="InpEntryStartHourLondon"){InpEntryStartHourLondon=(int)StringToInteger(value);return true;}
if(header=="InpEntryEndHourLondon"){InpEntryEndHourLondon=(int)StringToInteger(value);return true;}
if(header=="InpServerUtcOffsetHours"){InpServerUtcOffsetHours=(int)StringToInteger(value);return true;}
if(header=="InpBaseMagic"){InpBaseMagic=(long)StringToInteger(value);return true;}
if(header=="InpDeviationPoints"){InpDeviationPoints=(int)StringToInteger(value);return true;}
if(header=="InpSignalTimeframe"){InpSignalTimeframe=(ENUM_TIMEFRAMES)StringToInteger(value);return true;}
if(header=="InpEntryMode"){InpEntryMode=(int)StringToInteger(value);return true;}
if(header=="InpEntryOffsetATR"){InpEntryOffsetATR=StringToDouble(value);return true;}
if(header=="InpArmExpiryHours"){InpArmExpiryHours=(int)StringToInteger(value);return true;}
if(header=="InpStopMode"){InpStopMode=(int)StringToInteger(value);return true;}
if(header=="InpStopPercent"){InpStopPercent=StringToDouble(value);return true;}
if(header=="InpStopPriceUnits"){InpStopPriceUnits=StringToDouble(value);return true;}
if(header=="InpExitMode"){InpExitMode=(int)StringToInteger(value);return true;}
if(header=="InpManagement"){InpManagement=(int)StringToInteger(value);return true;}
if(header=="InpTrailStartR"){InpTrailStartR=StringToDouble(value);return true;}
if(header=="InpTrailATR"){InpTrailATR=StringToDouble(value);return true;}
if(header=="InpTrailPercent"){InpTrailPercent=StringToDouble(value);return true;}
if(header=="InpSessionMode"){InpSessionMode=(int)StringToInteger(value);return true;}
if(header=="InpDirection"){InpDirection=(int)StringToInteger(value);return true;}
if(header=="InpExcludeDays"){InpExcludeDays=(int)StringToInteger(value);return true;}
if(header=="InpFilter"){InpFilter=(int)StringToInteger(value);return true;}
if(header=="InpADXMin"){InpADXMin=StringToDouble(value);return true;}
if(header=="InpMaxSpreadATR"){InpMaxSpreadATR=StringToDouble(value);return true;}
if(header=="InpPerModuleDay"){InpPerModuleDay=(int)StringToInteger(value);return true;}
if(header=="InpControl"){InpControl=(value=="true");return true;}
if(header=="InpControlSeed"){InpControlSeed=(int)StringToInteger(value);return true;}
if(header=="InpExportTag"){InpExportTag=value;return true;}
if(header=="InpCaptureEquity"){InpCaptureEquity=(value=="true");return true;}
return false;
}
bool LoadConfiguration(){
 int f=FileOpen("CalyxUKTPipeline20261004\\\\"+InpConfigFile,FILE_READ|FILE_SHARE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(f==INVALID_HANDLE)return false;
 string headers[49];for(int k=0;k<49;k++)headers[k]=FileReadString(f);
 for(int row=0;row<=InpConfigIndex;row++){
   if(FileIsEnding(f)){FileClose(f);return false;}
   for(int k=0;k<49;k++){string v=FileReadString(f);if(row==InpConfigIndex && !Assign(headers[k],v)){FileClose(f);return false;}}
 }
 FileClose(f);return true;
}
CTrade trade;
int h_adx=INVALID_HANDLE,h_htf=INVALID_HANDLE,equity_file=INVALID_HANDLE;
int counts_dates[3],day_counts[3];
ulong risk_ids[];double risk_distances[],extremes[];bool partial_done[];
struct Armed {bool active;int module;int direction;int date;datetime bar;datetime born;double v[17];double level;double high;double low;};
Armed arms[3];

int h_atr=INVALID_HANDLE,h_rsi=INVALID_HANDLE,h_pull=INVALID_HANDLE,h_trend=INVALID_HANDLE,h_slow=INVALID_HANDLE;
datetime last_bar=0,blocked_until=0;
int last_dates[3],opened[3],minlot_skips[3];
int losing_streak=0,pause_count=0,blocked_bars=0,entry_errors=0,close_errors=0;
ulong processed[];


int NewYorkMinute(datetime server){
 datetime utc=server-InpServerUtcOffsetHours*3600;MqlDateTime p;TimeToStruct(utc,p);
 MqlDateTime x;TimeToStruct(UtcDate(p.year,3,1,0),x);int march=1+(7-x.day_of_week)%7+7;
 TimeToStruct(UtcDate(p.year,11,1,0),x);int november=1+(7-x.day_of_week)%7;
 bool dst=utc>=UtcDate(p.year,3,march,7) && utc<UtcDate(p.year,11,november,6);
 TimeToStruct(utc-(dst?4:5)*3600,p);return p.hour*60+p.min;
}
bool FilterOK(int direction,double atr){
 if(InpDirection!=0 && direction!=InpDirection)return false;
 if(InpFilter==0)return true;
 if(InpFilter<=3){double adx=0,plus=0,minus=0,a[];
  if(!Value(h_adx,1,adx) || CopyBuffer(h_adx,1,1,1,a)!=1)return false;plus=a[0];
  if(CopyBuffer(h_adx,2,1,1,a)!=1)return false;minus=a[0];
  if((InpFilter==1 || InpFilter==3) && adx<InpADXMin)return false;
  if((InpFilter==2 || InpFilter==3) && (direction>0?plus<=minus:minus<=plus))return false;return true;
 }
 if(InpFilter==4){double ma=0;if(!Value(h_htf,1,ma))return false;double c=iClose(_Symbol,PERIOD_D1,1);return direction>0?c>ma:c<ma;}
 if(InpFilter==5){double values[];if(CopyBuffer(h_atr,0,2,100,values)!=100)return false;int below=0;for(int k=0;k<100;k++)if(values[k]<atr)below++;return below>=50 && below<=95;}
 MqlTick q;return SymbolInfoTick(_Symbol,q) && q.ask-q.bid<=InpMaxSpreadATR*atr;
}

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
 if(p.day_of_week<1 || p.day_of_week>5)return false;
 if((InpExcludeDays==1 || InpExcludeDays==3) && p.day_of_week==1)return false;
 if((InpExcludeDays==2 || InpExcludeDays==3) && p.day_of_week==5)return false;
 MqlDateTime utc;TimeToStruct(TimeCurrent()-InpServerUtcOffsetHours*3600,utc);
 int u=utc.hour*60+utc.min,l=p.hour*60+p.min;
 if(InpSessionMode==1)return u<480;
 if(InpSessionMode==2)return l>=480 && l<960;
 if(InpSessionMode>=3 && InpSessionMode<=5){
   int ny=NewYorkMinute(TimeCurrent());
   if(InpSessionMode==3)return ny>=570 && ny<960;
   if(InpSessionMode==4)return l>=780 && l<960 && ny>=570;
   return ny>=570 && ny<600;
 }
 if(InpSessionMode==6)return true;
 return p.hour>=InpEntryStartHourLondon && p.hour<InpEntryEndHourLondon;
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
 int m=module-1;
 int n=counts_dates[m]==date?day_counts[m]:0;
 return !ModuleOpen(module) && !arms[m].active && OwnCount()<InpMaxPositions && n<InpPerModuleDay && TimeCurrent()>=blocked_until;
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
void Execute(int module,int direction,double atr,int date,datetime signal_bar,double drop,double prior_rsi,double friday,
           double prior_close,double prior_high,double prior_low,double signal_open,double signal_close,double peak,
           double previous_atr,double pull,double previous_pull,double trend,double previous_trend,double slow)
{
 if(!CanEnter(module,date) || !BrokerSessionOpen())return;
 MqlTick q;if(!SymbolInfoTick(_Symbol,q) || q.ask<=0 || q.bid<=0)return;
 double quote=direction>0?q.ask:q.bid;
 double distance=InpStopATR*atr;
 if(InpStopMode==3)distance=quote*InpStopPercent/100.0;
 if(InpStopMode==4)distance=InpStopPriceUnits;
 double stop=quote-direction*distance;
 if(InpStopMode==1)stop=direction>0?MathMin(signal_open,MathMin(prior_low,iLow(_Symbol,InpSignalTimeframe,1)))-0.1*atr:MathMax(signal_open,MathMax(prior_high,iHigh(_Symbol,InpSignalTimeframe,1)))+0.1*atr;
 if(InpStopMode==2){
   stop=direction>0?iLow(_Symbol,InpSignalTimeframe,1):iHigh(_Symbol,InpSignalTimeframe,1);
   for(int k=2;k<=10;k++)stop=direction>0?MathMin(stop,iLow(_Symbol,InpSignalTimeframe,k)):MathMax(stop,iHigh(_Symbol,InpSignalTimeframe,k));
   stop-=direction*0.1*atr;
 }
 stop=direction>0?MathMin(stop,q.bid-BrokerGap()):MathMax(stop,q.ask+BrokerGap());
 stop=Price(stop,direction>0);
 double equity=AccountInfoDouble(ACCOUNT_EQUITY),cash=equity*InpRiskPercent/100.0;
 ENUM_ORDER_TYPE type=direction>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 double lots=Lots(type,quote,stop,cash);
 if(lots<=0){minlot_skips[module-1]++;PrintFormat("UKT_SKIP_MINLOT date=%d module=%d budget=%.4f",date,module,cash);return;}
 double rr=module==1?InpDropTargetR:module==2?InpMondayTargetR:InpTrendTargetR;
 double target=InpExitMode==1 || InpExitMode==2 ? 0 : Price(quote+direction*rr*MathAbs(quote-stop),direction<0);
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
 if(counts_dates[module-1]!=date){counts_dates[module-1]=date;day_counts[module-1]=0;}day_counts[module-1]++;
 int ix=ArraySize(risk_ids);ArrayResize(risk_ids,ix+1);ArrayResize(risk_distances,ix+1);ArrayResize(extremes,ix+1);ArrayResize(partial_done,ix+1);
 risk_ids[ix]=(ulong)PositionGetInteger(POSITION_IDENTIFIER);risk_distances[ix]=MathAbs(open-stop);extremes[ix]=open;partial_done[ix]=false;
 PrintFormat("UKT_SIGNAL date=%d module=%d direction=%d bar=%s drop=%.8f prior_rsi=%.8f friday=%.8f prior_close=%.8f prior_high=%.8f prior_low=%.8f signal_open=%.8f signal_close=%.8f peak=%.8f previous_atr=%.8f atr=%.8f pull=%.8f previous_pull=%.8f trend=%.8f previous_trend=%.8f slow=%.8f",
  date,module,direction,TimeToString(signal_bar,TIME_DATE|TIME_MINUTES),drop,prior_rsi,friday,prior_close,prior_high,prior_low,signal_open,signal_close,peak,previous_atr,atr,pull,previous_pull,trend,previous_trend,slow);
 PrintFormat("UKT_ENTRY date=%d module=%d position=%I64u side=%d lots=%.8f actual_open=%.8f initial_sl=%.8f requested_tp=%.8f equity=%.4f budget=%.4f requested_stop_cash=%.4f actual_stop_cash=%.4f",
  date,module,(ulong)PositionGetInteger(POSITION_IDENTIFIER),direction,lots,open,stop,target,equity,cash,MathAbs(requested),MathAbs(actual));
}
int RiskIndex(ulong id){for(int k=0;k<ArraySize(risk_ids);k++)if(risk_ids[k]==id)return k;return -1;}
void Manage()
{
 if(!BrokerSessionOpen())return;
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
 for(int i=PositionsTotal()-1;i>=0;i--){
  ulong ticket=PositionGetTicket(i);if(ticket==0 || !Ours())continue;
  ulong id=(ulong)PositionGetInteger(POSITION_IDENTIFIER);int k=RiskIndex(id);if(k<0)continue;
  int d=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1;
  double open=PositionGetDouble(POSITION_PRICE_OPEN),sl=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP),price=d>0?q.bid:q.ask,risk=risk_distances[k];
  if(risk<=0)continue;extremes[k]=d>0?MathMax(extremes[k],price):MathMin(extremes[k],price);
  double progress=d*(price-open)/risk;double rr=tp>0?MathAbs(tp-open)/risk:1;
  MqlDateTime l;TimeToStruct(London(TimeCurrent()),l);
  bool time_exit=TimeCurrent()>=(datetime)PositionGetInteger(POSITION_TIME)+InpMaxHoldingHours*3600;
  bool session_exit=InpExitMode==3 && l.hour>=16;
  trade.SetExpertMagicNumber((ulong)PositionGetInteger(POSITION_MAGIC));
  if(time_exit || session_exit){
   if(!trade.PositionClose(ticket,(ulong)InpDeviationPoints) || trade.ResultRetcode()!=TRADE_RETCODE_DONE){close_errors++;Print("UKT_CLOSE_FAILED timed exit");}continue;
  }
  if(InpExitMode==4 && !partial_done[k] && progress>=1){
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),vol=PositionGetDouble(POSITION_VOLUME);
   double half=MathFloor(vol*0.5/step)*step;
   if(half>=minimum && vol-half>=minimum){
    if(!trade.PositionClosePartial(ticket,half) || trade.ResultRetcode()!=TRADE_RETCODE_DONE){close_errors++;Print("UKT_CLOSE_FAILED partial");}
    else partial_done[k]=true;
   }else partial_done[k]=true;
  }
  int mode=InpManagement;if(InpExitMode==1 && mode==0)mode=2;
  double next=sl,atr=0;Value(h_atr,1,atr);
  if(mode==7){
   double trigger=tp>0?rr*0.5:0.5,lock=tp>0?rr*0.2:0.2;
   if(progress>=trigger)next=open+d*lock*risk;
  }else if(mode>0 && progress>=InpTrailStartR){
   if(mode==1)next=open;
   if(mode==2)next=price-d*InpTrailATR*atr;
   if(mode==3)next=price*(1-d*InpTrailPercent/100.0);
   if(mode==4){double ma=0;if(Value(h_pull,1,ma))next=ma-d*0.1*atr;}
   if(mode==5){next=d>0?iLow(_Symbol,InpSignalTimeframe,1):iHigh(_Symbol,InpSignalTimeframe,1);for(int z=2;z<=3;z++)next=d>0?MathMin(next,iLow(_Symbol,InpSignalTimeframe,z)):MathMax(next,iHigh(_Symbol,InpSignalTimeframe,z));next-=d*0.1*atr;}
   if(mode==6)next=extremes[k]-d*InpTrailATR*atr;
  }
  next=Price(d>0?MathMin(next,q.bid-BrokerGap()):MathMax(next,q.ask+BrokerGap()),d>0);
  if(next>0 && (d>0?next>sl+TickSize()/2:next<sl-TickSize()/2)){
   if(!trade.PositionModify(ticket,next,tp) || (trade.ResultRetcode()!=TRADE_RETCODE_DONE && trade.ResultRetcode()!=TRADE_RETCODE_NO_CHANGES)){close_errors++;Print("UKT_CLOSE_FAILED trail");}
  }
 }
}
void Enter(int module,int direction,double atr,int date,datetime signal_bar,double drop,double prior_rsi,double friday,
           double prior_close,double prior_high,double prior_low,double signal_open,double signal_close,double peak,
           double previous_atr,double pull,double previous_pull,double trend,double previous_trend,double slow)
{
 if(!CanEnter(module,date) || !FilterOK(direction,atr))return;
 if(InpEntryMode==0){Execute(module,direction,atr,date,signal_bar,drop,prior_rsi,friday,prior_close,prior_high,prior_low,signal_open,signal_close,peak,previous_atr,pull,previous_pull,trend,previous_trend,slow);return;}
 int k=module-1;arms[k].active=true;arms[k].module=module;arms[k].direction=direction;arms[k].date=date;arms[k].bar=signal_bar;arms[k].born=TimeCurrent();
 double data[17]={atr,drop,prior_rsi,friday,prior_close,prior_high,prior_low,signal_open,signal_close,peak,previous_atr,pull,previous_pull,trend,previous_trend,slow,0};
 for(int j=0;j<17;j++)arms[k].v[j]=data[j];
 arms[k].high=iHigh(_Symbol,InpSignalTimeframe,1);arms[k].low=iLow(_Symbol,InpSignalTimeframe,1);
 arms[k].level=InpEntryMode==2?signal_close-direction*InpEntryOffsetATR*atr:(direction>0?arms[k].high:arms[k].low)+direction*InpEntryOffsetATR*atr;
}
void ManageArms()
{
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
 for(int k=0;k<3;k++){
  if(!arms[k].active)continue;
  if(TimeCurrent()>=blocked_until && EntryWindow() && BrokerSessionOpen() && TimeCurrent()<arms[k].born+InpArmExpiryHours*3600 && DateKey(TimeCurrent())==arms[k].date){
   double quote=arms[k].direction>0?q.ask:q.bid;bool ready=false;
   if(InpEntryMode==1 && iTime(_Symbol,InpSignalTimeframe,0)>arms[k].born){
    double c=iClose(_Symbol,InpSignalTimeframe,1);ready=arms[k].direction>0?c>arms[k].high:c<arms[k].low;
    if(!ready){arms[k].active=false;continue;}
   }
   if(InpEntryMode==2)ready=arms[k].direction>0?quote<=arms[k].level:quote>=arms[k].level;
   if(InpEntryMode==3)ready=arms[k].direction>0?quote>=arms[k].level:quote<=arms[k].level;
   if(ready){Armed a=arms[k];arms[k].active=false;Execute(a.module,a.direction,a.v[0],a.date,a.bar,a.v[1],a.v[2],a.v[3],a.v[4],a.v[5],a.v[6],a.v[7],a.v[8],a.v[9],a.v[10],a.v[11],a.v[12],a.v[13],a.v[14],a.v[15]);}
  }else arms[k].active=false;
 }
}
void Process()
{
 if(!EntryWindow() || !BrokerSessionOpen())return;
 if(TimeCurrent()<blocked_until){blocked_bars++;return;}
 int need=InpDropLookback+2;
 MqlRates r[];ArraySetAsSeries(r,true);if(CopyRates(_Symbol,InpSignalTimeframe,0,need,r)!=need)return;
 double atr=0,prior_atr=0,rsi=0,pull=0,previous_pull=0,trend=0,previous_trend=0,slow=0;
 if(!Value(h_atr,1,atr) || !Value(h_atr,2,prior_atr) || !Value(h_rsi,2,rsi) || !Value(h_pull,1,pull) ||
    !Value(h_pull,2,previous_pull) || !Value(h_trend,1,trend) || !Value(h_trend,2,previous_trend) ||
    !Value(h_slow,1,slow) || atr<=0 || prior_atr<=0)return;
 double peak=r[2].high;for(int i=2;i<need;i++)peak=MathMax(peak,r[i].high);
 double drop=peak-r[2].close;
 bool recovery=r[1].close>r[1].open && r[1].close>r[2].high;
 int date=DateKey(TimeCurrent());MqlDateTime now;TimeToStruct(London(TimeCurrent()),now);
 double friday=now.day_of_week==1?FridayClose():0;
 if(InpControl){
  double probabilities[3]={0.02,0.04,0.06};
  bool enabled[3]={InpEnableDrop,InpEnableMonday,InpEnableTrend};
  for(int k=0;k<3;k++){
   if(!enabled[k] || (k==1 && now.day_of_week!=1))continue;
   if((double)MathRand()/32768.0<probabilities[k]){
    int d=k<2?1:(MathRand()<16384?1:-1);
    Enter(k+1,d,atr,date,r[1].time,drop,rsi,friday,r[2].close,r[2].high,r[2].low,r[1].open,r[1].close,peak,prior_atr,pull,previous_pull,trend,previous_trend,slow);
   }
  }return;
 }
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
 if(!LoadConfiguration()){Print("UKT_CONFIG_FAILED");return INIT_PARAMETERS_INCORRECT;}
 if(!(bool)MQLInfoInteger(MQL_TESTER)){Print("UKT_RESEARCH_ONLY no live/demo execution");return INIT_FAILED;}
 if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING){Print("UKT_REQUIRES_HEDGING");return INIT_FAILED;}
 if(InpATRPeriod<2 || InpDropLookback<2 || InpDropLookback>500 || InpDropATR<=0 ||
    InpRSIPeriod<2 || InpOversoldRSI<0 || InpOversoldRSI>100 || InpMondayDipATR<0 ||
    InpPullbackEMA<2 || InpTrendEMA<=InpPullbackEMA || InpSlowEMA<=InpTrendEMA || InpRiskPercent<=0 || InpRiskPercent>1.25 ||
    InpStopATR<=0 || InpDropTargetR<=0 || InpMondayTargetR<=0 || InpTrendTargetR<=0 ||
    InpMaxHoldingHours<1 || InpMaxPositions<1 || InpMaxPositions>3 || InpLossesBeforePause<1 || InpPauseHours<1 ||
    InpEntryStartHourLondon<0 || InpEntryEndHourLondon>24 || InpEntryStartHourLondon>=InpEntryEndHourLondon ||
    InpBaseMagic<=0 || InpDeviationPoints<0)return INIT_PARAMETERS_INCORRECT;
 h_atr=iATR(_Symbol,InpSignalTimeframe,InpATRPeriod);h_rsi=iRSI(_Symbol,InpSignalTimeframe,InpRSIPeriod,PRICE_CLOSE);
 h_pull=iMA(_Symbol,InpSignalTimeframe,InpPullbackEMA,0,MODE_EMA,PRICE_CLOSE);
 h_trend=iMA(_Symbol,InpSignalTimeframe,InpTrendEMA,0,MODE_EMA,PRICE_CLOSE);h_slow=iMA(_Symbol,InpSignalTimeframe,InpSlowEMA,0,MODE_EMA,PRICE_CLOSE);
 if(h_atr==INVALID_HANDLE || h_rsi==INVALID_HANDLE || h_pull==INVALID_HANDLE || h_trend==INVALID_HANDLE || h_slow==INVALID_HANDLE)return INIT_FAILED;
 h_adx=iADX(_Symbol,InpSignalTimeframe,14);h_htf=iMA(_Symbol,PERIOD_D1,200,0,MODE_EMA,PRICE_CLOSE);
 if(h_adx==INVALID_HANDLE || h_htf==INVALID_HANDLE)return INIT_FAILED;
 MathSrand(InpControlSeed);
 trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(InpDeviationPoints);
 if(InpCaptureEquity){FolderCreate("CalyxUKTPipeline20261004",FILE_COMMON);equity_file=FileOpen("CalyxUKTPipeline20261004\\\\"+InpExportTag+"-equity.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');if(equity_file==INVALID_HANDLE)return INIT_FAILED;FileWrite(equity_file,"time","balance","equity");}
 last_bar=iTime(_Symbol,InpSignalTimeframe,0);
 Print("UKT_INDEPENDENT_ASSUMPTIONS: three modules share account; 1% EACH trade; 3 simultaneous slots; numeric rules not vendor settings.");
 return INIT_SUCCEEDED;
}
void OnTick()
{
 Manage();ManageArms();
 if(equity_file!=INVALID_HANDLE)FileWrite(equity_file,(long)TimeCurrent(),AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY));
 datetime bar=iTime(_Symbol,InpSignalTimeframe,0);if(bar<=0 || bar==last_bar)return;
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
 if(equity_file!=INVALID_HANDLE){FileClose(equity_file);equity_file=INVALID_HANDLE;}
 if(h_adx!=INVALID_HANDLE)IndicatorRelease(h_adx);if(h_htf!=INVALID_HANDLE)IndicatorRelease(h_htf);
 if(h_atr!=INVALID_HANDLE)IndicatorRelease(h_atr);if(h_rsi!=INVALID_HANDLE)IndicatorRelease(h_rsi);
 if(h_pull!=INVALID_HANDLE)IndicatorRelease(h_pull);if(h_trend!=INVALID_HANDLE)IndicatorRelease(h_trend);if(h_slow!=INVALID_HANDLE)IndicatorRelease(h_slow);
 PrintFormat("UKT_SUMMARY drop=%d monday=%d trend=%d pauses=%d blocked_bars=%d minlot_skips=%d entry_errors=%d close_errors=%d processed_exits=%d",
  opened[0],opened[1],opened[2],pause_count,blocked_bars,minlot_skips[0]+minlot_skips[1]+minlot_skips[2],entry_errors,close_errors,ArraySize(processed));
}
double OnTester(){
 if(InpExportTag=="none")return TesterStatistics(STAT_PROFIT);
 FolderCreate("CalyxUKTPipeline20261004",FILE_COMMON);
 string stem="CalyxUKTPipeline20261004\\\\"+InpExportTag;
 int f=FileOpen(stem+"-stats.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(f==INVALID_HANDLE){Print("UKT_EXPORT_FAILED");return -1e12;}
 FileWrite(f,"profit","native_pf","equity_dd_pct","sharpe","recovery","native_trades","entry_errors","close_errors","pauses","minlot_skips");
 FileWrite(f,TesterStatistics(STAT_PROFIT),TesterStatistics(STAT_PROFIT_FACTOR),TesterStatistics(STAT_EQUITY_DDREL_PERCENT),TesterStatistics(STAT_SHARPE_RATIO),TesterStatistics(STAT_RECOVERY_FACTOR),TesterStatistics(STAT_TRADES),entry_errors,close_errors,pause_count,minlot_skips[0]+minlot_skips[1]+minlot_skips[2]);FileClose(f);
 f=FileOpen(stem+"-deals.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(f==INVALID_HANDLE){Print("UKT_EXPORT_FAILED");return -1e12;}
 FileWrite(f,"deal","position","order","time","type","entry","module","volume","price","profit","commission","swap","fee","comment");
 if(HistorySelect(0,TimeCurrent()+1))for(int i=0;i<HistoryDealsTotal();i++){
  ulong d=HistoryDealGetTicket(i);if(d==0 || HistoryDealGetString(d,DEAL_SYMBOL)!=_Symbol)continue;
  long type=HistoryDealGetInteger(d,DEAL_TYPE);if(type!=DEAL_TYPE_BUY && type!=DEAL_TYPE_SELL)continue;
  FileWrite(f,d,HistoryDealGetInteger(d,DEAL_POSITION_ID),HistoryDealGetInteger(d,DEAL_ORDER),HistoryDealGetInteger(d,DEAL_TIME),type,HistoryDealGetInteger(d,DEAL_ENTRY),HistoryDealGetInteger(d,DEAL_MAGIC)-InpBaseMagic,HistoryDealGetDouble(d,DEAL_VOLUME),HistoryDealGetDouble(d,DEAL_PRICE),HistoryDealGetDouble(d,DEAL_PROFIT),HistoryDealGetDouble(d,DEAL_COMMISSION),HistoryDealGetDouble(d,DEAL_SWAP),HistoryDealGetDouble(d,DEAL_FEE),HistoryDealGetString(d,DEAL_COMMENT));
 }FileClose(f);return TesterStatistics(STAT_PROFIT);
}

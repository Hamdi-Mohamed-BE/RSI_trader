#property copyright "Transparent research replica of the publicly described Apex Pulse concept"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

input group "Research gate"
input bool   InpEnableTrading=false;
input group "Selected transparent rule"
input double InpAsiaLondonStartHour=0.0;
input double InpAsiaLondonEndHour=7.0;
input double InpEntryNewYorkStartHour=8.0;
input double InpEntryNewYorkEndHour=12.0;
input double InpMinimumAsiaRangePips=15.0;
input double InpMaximumAsiaRangePips=40.0;
input double InpBreakoutBufferPips=0.0;
input double InpPipSize=0.0001;
input double InpStopAsiaRangeMultiple=1.0;
input double InpRewardRisk=2.0;
input bool   InpBreakEvenAtOneR=true;
input double InpRiskPercent=1.0;
input group "Execution"
input long   InpMagic=86100101;
input int    InpMaxDeviationPoints=30;
input group "Broker clock"
input bool   InpUseAutomaticLiveServerOffset=true;
input int    InpTesterServerUTCOffsetHours=0;
input int    InpManualLiveServerUTCOffsetHours=0;

CTrade trade;
int g_date_key=0;
bool g_range_ready=false;
double g_asia_high=0.0,g_asia_low=0.0;
double g_initial_risk=0.0;

int NthSunday(const int year,const int month,const int occurrence)
{
   MqlDateTime p={0}; p.year=year;p.mon=month;p.day=1;p.hour=12;
   datetime first=StructToTime(p); TimeToStruct(first,p);
   return 1+((7-p.day_of_week)%7)+(occurrence-1)*7;
}
int LastSunday(const int year,const int month)
{
   MqlDateTime p={0}; p.year=year;p.mon=month;p.day=31;p.hour=12;
   while(p.day>28){ datetime v=StructToTime(p);TimeToStruct(v,p);if(p.day_of_week==0)return p.day;p.day--; }
   return p.day;
}
int NewYorkOffset(const datetime utc)
{
   MqlDateTime p;TimeToStruct(utc,p);MqlDateTime a={0},b={0};
   a.year=p.year;a.mon=3;a.day=NthSunday(p.year,3,2);a.hour=7;
   b.year=p.year;b.mon=11;b.day=NthSunday(p.year,11,1);b.hour=6;
   return (utc>=StructToTime(a)&&utc<StructToTime(b)?-4:-5);
}
bool NyDateDST(const MqlDateTime &p)
{
   int a=NthSunday(p.year,3,2),b=NthSunday(p.year,11,1);
   if(p.mon>3&&p.mon<11)return true;if(p.mon<3||p.mon>11)return false;
   return p.mon==3?p.day>=a:p.day<b;
}
bool LondonDateDST(const MqlDateTime &p)
{
   int a=LastSunday(p.year,3),b=LastSunday(p.year,10);
   if(p.mon>3&&p.mon<10)return true;if(p.mon<3||p.mon>10)return false;
   return p.mon==3?p.day>=a:p.day<b;
}
int ServerOffsetSeconds()
{
   if((bool)MQLInfoInteger(MQL_TESTER))return InpTesterServerUTCOffsetHours*3600;
   if(!InpUseAutomaticLiveServerOffset)return InpManualLiveServerUTCOffsetHours*3600;
   datetime server=TimeTradeServer();if(server<=0)server=TimeCurrent();datetime utc=TimeGMT();
   if(utc<=0)return InpManualLiveServerUTCOffsetHours*3600;
   return (int)MathRound((double)(server-utc)/1800.0)*1800;
}
datetime ServerToNewYork(const datetime server){datetime utc=server-ServerOffsetSeconds();return utc+NewYorkOffset(utc)*3600;}
datetime NewYorkToServer(const MqlDateTime &source)
{
   MqlDateTime p=source;datetime utc=StructToTime(p)-(NyDateDST(p)?-4:-5)*3600;return utc+ServerOffsetSeconds();
}
datetime LondonToServer(const MqlDateTime &source)
{
   MqlDateTime p=source;datetime utc=StructToTime(p)-(LondonDateDST(p)?1:0)*3600;return utc+ServerOffsetSeconds();
}
void SetDecimalHour(MqlDateTime &p,const double hour){int m=(int)MathRound(hour*60.0);p.hour=m/60;p.min=m%60;p.sec=0;}
int MinuteOfDay(const double hour){return(int)MathRound(hour*60.0);}
int DateKey(const MqlDateTime &p){return p.year*10000+p.mon*100+p.day;}

double NormalizePrice(const double value)
{
   double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);if(tick<=0)tick=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   return NormalizeDouble(MathRound(value/tick)*tick,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}
double NormalizeLots(const double raw)
{
   double min=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),max=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(raw<min||min<=0||step<=0)return 0;return NormalizeDouble(MathFloor((MathMin(raw,max)+1e-12)/step)*step,8);
}
double LotsForRisk(const ENUM_ORDER_TYPE type,const double entry,const double stop)
{
   double p=0;if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,p)||MathAbs(p)<=0)return 0;
   return NormalizeLots(AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0/MathAbs(p));
}
bool SelectOurPosition(ulong &ticket)
{
   for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);if(t>0&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==InpMagic){ticket=t;return true;}}
   return false;
}
bool AttemptedToday(const MqlDateTime &ny)
{
   MqlDateTime start=ny;start.hour=0;start.min=0;start.sec=0;
   if(!HistorySelect(NewYorkToServer(start),TimeCurrent()))return false;
   for(int i=HistoryOrdersTotal()-1;i>=0;i--){ulong t=HistoryOrderGetTicket(i);if(t>0&&HistoryOrderGetString(t,ORDER_SYMBOL)==_Symbol&&HistoryOrderGetInteger(t,ORDER_MAGIC)==InpMagic)return true;}
   return false;
}
bool BuildAsiaRange(const MqlDateTime &ny)
{
   MqlDateTime a=ny,b=ny;SetDecimalHour(a,InpAsiaLondonStartHour);SetDecimalHour(b,InpAsiaLondonEndHour);
   MqlRates rates[];int n=CopyRates(_Symbol,PERIOD_M1,LondonToServer(a),LondonToServer(b)-1,rates);if(n<300)return false;
   g_asia_high=-DBL_MAX;g_asia_low=DBL_MAX;
   for(int i=0;i<n;i++){g_asia_high=MathMax(g_asia_high,rates[i].high);g_asia_low=MathMin(g_asia_low,rates[i].low);}
   double pips=(g_asia_high-g_asia_low)/InpPipSize;
   g_range_ready=pips>=InpMinimumAsiaRangePips&&pips<=InpMaximumAsiaRangePips;
   return g_range_ready;
}
void ManagePosition(const MqlDateTime &ny)
{
   ulong ticket=0;if(!SelectOurPosition(ticket))return;
   if(ny.hour*60+ny.min>=MinuteOfDay(InpEntryNewYorkEndHour)){trade.PositionClose(ticket,InpMaxDeviationPoints);return;}
   if(!InpBreakEvenAtOneR||!PositionSelectByTicket(ticket))return;
   double open=PositionGetDouble(POSITION_PRICE_OPEN),sl=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP);
   long type=PositionGetInteger(POSITION_TYPE);if(g_initial_risk<=0)g_initial_risk=MathAbs(open-sl);if(g_initial_risk<=0)return;
   MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
   bool reached=(type==POSITION_TYPE_BUY?q.bid-open>=g_initial_risk:open-q.ask>=g_initial_risk);
   bool needs=(type==POSITION_TYPE_BUY?sl<open:sl>open);
   if(reached&&needs)trade.PositionModify(ticket,NormalizePrice(open),tp);
}
void EvaluateEntry(const MqlDateTime &ny)
{
   if(!InpEnableTrading||AttemptedToday(ny))return;ulong ticket=0;if(SelectOurPosition(ticket))return;
   int minute=ny.hour*60+ny.min;if(minute<MinuteOfDay(InpEntryNewYorkStartHour)||minute>=MinuteOfDay(InpEntryNewYorkEndHour))return;
   int key=DateKey(ny);if(key!=g_date_key){g_date_key=key;g_range_ready=false;g_initial_risk=0;}
   if(!g_range_ready&&!BuildAsiaRange(ny))return;
   MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;double buffer=InpBreakoutBufferPips*InpPipSize;
   int direction=q.ask>=g_asia_high+buffer?1:q.bid<=g_asia_low-buffer?-1:0;if(direction==0)return;
   double entry=direction>0?q.ask:q.bid,distance=(g_asia_high-g_asia_low)*InpStopAsiaRangeMultiple;
   double stop=NormalizePrice(entry-direction*distance),target=NormalizePrice(entry+direction*InpRewardRisk*distance);
   double lots=LotsForRisk(direction>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,entry,stop);if(lots<=0)return;
   trade.SetExpertMagicNumber((ulong)InpMagic);trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(InpMaxDeviationPoints);
   bool ok=direction>0?trade.Buy(lots,_Symbol,0,stop,target,"Apex transparent LONG"):trade.Sell(lots,_Symbol,0,stop,target,"Apex transparent SHORT");
   if(ok)g_initial_risk=distance;else Print("Apex entry failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
}
int OnInit()
{
   if(InpPipSize<=0||InpRiskPercent<=0||InpRiskPercent>5||InpRewardRisk<=0||InpMagic<=0)return INIT_PARAMETERS_INCORRECT;
   if(!InpEnableTrading)Print("Apex research gate OFF: rejected untouched 2025-2026 validation.");return INIT_SUCCEEDED;
}
void OnTick()
{
   if(!InpEnableTrading)return;
   MqlDateTime ny;TimeToStruct(ServerToNewYork(TimeCurrent()),ny);if(ny.day_of_week<1||ny.day_of_week>5)return;
   ManagePosition(ny);EvaluateEntry(ny);
}

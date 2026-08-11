#property copyright "Transparent IVB/FRVP research implementation"
#property version   "1.01"
#property strict

#include <Trade/Trade.mqh>

input group "Research gate"
input bool   InpEnableTrading=false;
input group "Selected US30 setup"
input int    InpOpeningRangeMinutes=30;
input int    InpProfileBins=24;
input double InpValueAreaPercent=70.0;
input double InpMinimumRelativeTickVolume=1.10;
input int    InpVolumeAverageBars=20;
input int    InpAcceptanceCloses=1;
input int    InpRetestBars=6;
input double InpRetestToleranceORPercent=2.0;
input double InpStopBufferORPercent=5.0;
input double InpRewardRisk=3.0;
input double InpRiskPercent=1.0;
input group "New York session"
input int    InpOpenHourNewYork=9;
input int    InpOpenMinuteNewYork=30;
input int    InpHardExitHourNewYork=16;
input int    InpHardExitMinuteNewYork=0;
input group "Execution"
input long   InpMagic=86100201;
input int    InpMaxDeviationPoints=50;
input group "Broker clock"
input bool   InpUseAutomaticLiveServerOffset=true;
input int    InpTesterServerUTCOffsetHours=0;
input int    InpManualLiveServerUTCOffsetHours=0;

CTrade trade;
int g_date_key=0;
bool g_profile_ready=false,g_done=false;
double g_or_high=0.0,g_or_low=0.0,g_or_range=0.0,g_poc=0.0,g_vah=0.0,g_val=0.0;
int g_candidate_direction=0,g_candidate_closes=0,g_accepted_direction=0,g_retest_age=0;
datetime g_last_m1=0;

int NthSunday(const int year,const int month,const int occurrence)
{
   MqlDateTime p={0};p.year=year;p.mon=month;p.day=1;p.hour=12;
   datetime first=StructToTime(p);TimeToStruct(first,p);
   return 1+((7-p.day_of_week)%7)+(occurrence-1)*7;
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
   if(p.mon>3&&p.mon<11)return true;
   if(p.mon<3||p.mon>11)return false;
   return p.mon==3?p.day>=a:p.day<b;
}
int ServerOffsetSeconds()
{
   if((bool)MQLInfoInteger(MQL_TESTER))return InpTesterServerUTCOffsetHours*3600;
   if(!InpUseAutomaticLiveServerOffset)return InpManualLiveServerUTCOffsetHours*3600;
   datetime server=TimeTradeServer();if(server<=0)server=TimeCurrent();
   datetime utc=TimeGMT();if(utc<=0)return InpManualLiveServerUTCOffsetHours*3600;
   return (int)MathRound((double)(server-utc)/1800.0)*1800;
}
datetime ServerToNewYork(const datetime server)
{
   datetime utc=server-ServerOffsetSeconds();
   return utc+NewYorkOffset(utc)*3600;
}
datetime NewYorkToServer(const MqlDateTime &source)
{
   MqlDateTime p=source;
   datetime utc=StructToTime(p)-(NyDateDST(p)?-4:-5)*3600;
   return utc+ServerOffsetSeconds();
}
int DateKey(const MqlDateTime &p){return p.year*10000+p.mon*100+p.day;}
int MinuteOfDay(const MqlDateTime &p){return p.hour*60+p.min;}
int OpenMinute(){return InpOpenHourNewYork*60+InpOpenMinuteNewYork;}
int ExitMinute(){return InpHardExitHourNewYork*60+InpHardExitMinuteNewYork;}

double NormalizePrice(const double value)
{
   double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tick<=0)tick=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   return NormalizeDouble(MathRound(value/tick)*tick,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}
double NormalizeLots(const double raw)
{
   double min=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),max=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(raw<min||min<=0||step<=0)return 0.0;
   return NormalizeDouble(MathFloor((MathMin(raw,max)+1e-12)/step)*step,8);
}
double LotsForRisk(const ENUM_ORDER_TYPE type,const double entry,const double stop)
{
   double profit=0.0;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,profit)||MathAbs(profit)<=0)return 0.0;
   return NormalizeLots(AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0/MathAbs(profit));
}
bool SelectOurPosition(ulong &ticket)
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong t=PositionGetTicket(i);
      if(t>0&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==InpMagic)
      {ticket=t;return true;}
   }
   return false;
}
bool AttemptedToday(const MqlDateTime &ny)
{
   MqlDateTime start=ny;start.hour=0;start.min=0;start.sec=0;
   if(!HistorySelect(NewYorkToServer(start),TimeCurrent()))return false;
   for(int i=HistoryOrdersTotal()-1;i>=0;i--)
   {
      ulong t=HistoryOrderGetTicket(i);
      if(t>0&&HistoryOrderGetString(t,ORDER_SYMBOL)==_Symbol&&HistoryOrderGetInteger(t,ORDER_MAGIC)==InpMagic)return true;
   }
   return false;
}
void ResetDay(const MqlDateTime &ny)
{
   g_date_key=DateKey(ny);g_profile_ready=false;g_done=AttemptedToday(ny);
   g_or_high=0.0;g_or_low=0.0;g_or_range=0.0;g_poc=0.0;g_vah=0.0;g_val=0.0;
   g_candidate_direction=0;g_candidate_closes=0;g_accepted_direction=0;g_retest_age=0;
}
bool BuildProfile(const MqlDateTime &ny)
{
   MqlDateTime a=ny,b=ny;
   a.hour=InpOpenHourNewYork;a.min=InpOpenMinuteNewYork;a.sec=0;
   b=a;datetime end_local=StructToTime(b)+InpOpeningRangeMinutes*60;TimeToStruct(end_local,b);
   datetime from=NewYorkToServer(a),to=NewYorkToServer(b)-1;
   MqlRates rates[];int count=CopyRates(_Symbol,PERIOD_M1,from,to,rates);
   if(count<InpOpeningRangeMinutes-3)return false;
   g_or_high=-DBL_MAX;g_or_low=DBL_MAX;
   for(int i=0;i<count;i++){g_or_high=MathMax(g_or_high,rates[i].high);g_or_low=MathMin(g_or_low,rates[i].low);}
   g_or_range=g_or_high-g_or_low;if(g_or_range<=0)return false;
   double width=g_or_range/InpProfileBins,profile[];ArrayResize(profile,InpProfileBins);ArrayInitialize(profile,0.0);
   for(int i=0;i<count;i++)
   {
      int first=(int)MathFloor((rates[i].low-g_or_low)/width),last=(int)MathFloor((rates[i].high-g_or_low)/width);
      first=MathMax(0,MathMin(InpProfileBins-1,first));last=MathMax(0,MathMin(InpProfileBins-1,last));
      int touched=last-first+1;double add=(double)MathMax((long)1,rates[i].tick_volume)/touched;
      for(int j=first;j<=last;j++)profile[j]+=add;
   }
   int poc_index=0;double total=0.0;
   for(int i=0;i<InpProfileBins;i++){total+=profile[i];if(profile[i]>profile[poc_index])poc_index=i;}
   int left=poc_index-1,right=poc_index+1,val_index=poc_index,vah_index=poc_index;
   double accumulated=profile[poc_index],required=total*InpValueAreaPercent/100.0;
   while(accumulated<required&&(left>=0||right<InpProfileBins))
   {
      double lv=left>=0?profile[left]:-1.0,rv=right<InpProfileBins?profile[right]:-1.0;
      if(rv>lv){accumulated+=rv;vah_index=right;right++;}
      else {accumulated+=lv;val_index=left;left--;}
   }
   g_poc=g_or_low+(poc_index+0.5)*width;g_val=g_or_low+val_index*width;g_vah=g_or_low+(vah_index+1)*width;
   g_profile_ready=true;
   PrintFormat("IVB profile ready: OR %.2f-%.2f, VAL %.2f, POC %.2f, VAH %.2f",g_or_low,g_or_high,g_val,g_poc,g_vah);
   return true;
}
double RelativeVolume()
{
   long current=iVolume(_Symbol,PERIOD_M1,1);if(current<=0)return 0.0;
   double total=0.0;int valid=0;
   for(int i=2;i<2+InpVolumeAverageBars;i++){long v=iVolume(_Symbol,PERIOD_M1,i);if(v>0){total+=(double)v;valid++;}}
   return valid>=MathMax(10,InpVolumeAverageBars/2)?(double)current/(total/valid):0.0;
}
void OpenTrade(const int direction,const double signal_low,const double signal_high)
{
   MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
   double entry=direction>0?q.ask:q.bid;
   double spread=q.ask-q.bid,buffer=g_or_range*InpStopBufferORPercent/100.0;
   double stop=direction>0?signal_low-buffer:signal_high+spread+buffer;
   double distance=direction*(entry-stop);
   if(distance<=MathMax(spread*1.5,g_or_range*0.05)||distance>g_or_range*2.5){g_done=true;return;}
   stop=NormalizePrice(stop);double target=NormalizePrice(entry+direction*InpRewardRisk*distance);
   double lots=LotsForRisk(direction>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,entry,stop);
   if(lots<=0){Print("IVB rejected: broker minimum volume exceeds 1% risk.");g_done=true;return;}
   trade.SetExpertMagicNumber((ulong)InpMagic);trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(InpMaxDeviationPoints);
   bool ok=direction>0?trade.Buy(lots,_Symbol,0,stop,target,"IVB FRVP LONG"):trade.Sell(lots,_Symbol,0,stop,target,"IVB FRVP SHORT");
   if(!ok)Print("IVB entry failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
   g_done=true;
}
void ProcessClosedMinute(const MqlDateTime &ny)
{
   if(g_done||!g_profile_ready)return;
   int minute=MinuteOfDay(ny);
   if(minute<OpenMinute()+InpOpeningRangeMinutes||minute>=ExitMinute())return;
   double open=iOpen(_Symbol,PERIOD_M1,1),high=iHigh(_Symbol,PERIOD_M1,1),low=iLow(_Symbol,PERIOD_M1,1),close=iClose(_Symbol,PERIOD_M1,1);
   if(open<=0||close<=0)return;
   MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;double spread=q.ask-q.bid;
   if(g_accepted_direction==0)
   {
      int candidate=close>g_or_high?1:(close+spread<g_or_low?-1:0);
      if(candidate==0||RelativeVolume()<InpMinimumRelativeTickVolume){g_candidate_direction=0;g_candidate_closes=0;return;}
      if(candidate==g_candidate_direction)g_candidate_closes++;else {g_candidate_direction=candidate;g_candidate_closes=1;}
      if(g_candidate_closes>=InpAcceptanceCloses){g_accepted_direction=candidate;g_retest_age=0;}
      return;
   }
   g_retest_age++;
   if(g_retest_age>InpRetestBars){g_done=true;return;}
   if((g_accepted_direction>0&&close<g_or_low)||(g_accepted_direction<0&&close+spread>g_or_high)){g_done=true;return;}
   double tolerance=g_or_range*InpRetestToleranceORPercent/100.0;
   bool valid=g_accepted_direction>0?(low<=g_vah+tolerance&&close>g_vah&&close>open):(high+spread>=g_vah-tolerance&&close+spread<g_vah&&close<open);
   if(valid)OpenTrade(g_accepted_direction,low,high);
}
void ManagePosition(const MqlDateTime &ny)
{
   ulong ticket=0;if(!SelectOurPosition(ticket))return;
   if(MinuteOfDay(ny)>=ExitMinute())trade.PositionClose(ticket,InpMaxDeviationPoints);
}
int OnInit()
{
   if(InpOpeningRangeMinutes<5||InpProfileBins<8||InpValueAreaPercent<=0||InpValueAreaPercent>=100||InpAcceptanceCloses<1||InpRetestBars<1||InpRiskPercent<=0||InpRiskPercent>5||InpRewardRisk<=0||InpMagic<=0)return INIT_PARAMETERS_INCORRECT;
   if(!InpEnableTrading)Print("IVB research gate OFF: native full-period portfolio threshold failed.");
   return INIT_SUCCEEDED;
}
void OnTick()
{
   if(!InpEnableTrading)return;
   MqlDateTime ny;TimeToStruct(ServerToNewYork(TimeCurrent()),ny);
   if(ny.day_of_week<1||ny.day_of_week>5)return;
   if(DateKey(ny)!=g_date_key)ResetDay(ny);
   ManagePosition(ny);
   int minute=MinuteOfDay(ny);
   if(!g_profile_ready&&minute>=OpenMinute()+InpOpeningRangeMinutes&&minute<ExitMinute())BuildProfile(ny);
   datetime current=iTime(_Symbol,PERIOD_M1,0);
   if(current>0&&current!=g_last_m1){g_last_m1=current;ProcessClosedMinute(ny);}
}

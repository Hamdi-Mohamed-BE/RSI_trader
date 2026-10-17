#property strict
#property version "1.00"
#property description "TESTER ONLY: labelled reconstruction of NY drop, supply retest, rejection-close short."
#include <Trade/Trade.mqh>

input double InpRiskPercent=0.5;
input int InpATRPeriod=14;
input double InpImpulseBodyATR=1.5;
input int InpMaxImpulseBars=3;
input int InpBullishSearchBars=6;
input double InpImpulseCloseBottomFraction=0.25;
input double InpUpperWickBodyRatio=1.0;
input double InpMinUpperWickFraction=0.25;
input double InpStopBufferATR=0.10;
input int InpOpenMinuteNY=570;
input int InpImpulseUntilMinuteNY=630;
input int InpEntryUntilMinuteNY=955;
input int InpCloseMinuteNY=960;
input int InpServerUTCOffsetHours=0;
input long InpMagic=26100930;
input int InpDeviationPoints=1000;
input string InpSignalAuditTag="";

CTrade trade;
int atr_handle=INVALID_HANDLE,audit=INVALID_HANDLE;
datetime last_bar=0,close_server=0,origin_time=0,impulse_end=0;
int date_key=0;
bool saw_open=false,created=false,active=false,traded=false,may_hold=false;
double session_low=DBL_MAX,zone_low=0,zone_high=0,origin_high=0,zone_atr=0;
long sessions=0,zones=0,invalidations=0,wick_signals=0,placed=0,rejected=0,bad_geometry=0,undersize=0,time_closes=0;

datetime UTCDate(int year,int month,int day,int hour)
{
   MqlDateTime p;ZeroMemory(p);p.year=year;p.mon=month;p.day=day;p.hour=hour;return StructToTime(p);
}
int NthSunday(int year,int month,int nth)
{
   MqlDateTime p;TimeToStruct(UTCDate(year,month,1,0),p);
   return 1+(7-p.day_of_week)%7+(nth-1)*7;
}
int NYOffset(datetime utc)
{
   MqlDateTime p;TimeToStruct(utc,p);
   datetime begin=UTCDate(p.year,3,NthSunday(p.year,3,2),7);
   datetime end=UTCDate(p.year,11,NthSunday(p.year,11,1),6);
   return utc>=begin && utc<end?-4:-5;
}
void NYParts(datetime server,MqlDateTime &p)
{
   datetime utc=server-InpServerUTCOffsetHours*3600;
   TimeToStruct(utc+NYOffset(utc)*3600,p);
}
int NYMinute(datetime server){MqlDateTime p;NYParts(server,p);return p.hour*60+p.min;}
int NYDate(datetime server){MqlDateTime p;NYParts(server,p);return p.year*10000+p.mon*100+p.day;}
double Price(double value)
{
   double step=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   return NormalizeDouble(MathRound(value/step)*step,_Digits);
}
bool OurPosition(ulong &ticket)
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong t=PositionGetTicket(i);
      if(t>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic){ticket=t;return true;}
   }
   ticket=0;return false;
}
double Lots(double entry,double stop)
{
   double profit=0;
   if(!OrderCalcProfit(ORDER_TYPE_SELL,_Symbol,1,entry,stop,profit) || profit>=0)return 0;
   double budget=AccountInfoDouble(ACCOUNT_BALANCE)*InpRiskPercent/100;
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double volume=MathFloor((MathMin(budget/MathAbs(profit),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX))+1e-10)/step)*step;
   if(volume<minimum-1e-10)return 0;
   double margin=0;
   if(!OrderCalcMargin(ORDER_TYPE_SELL,_Symbol,volume,entry,margin) || margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE))return 0;
   return NormalizeDouble(volume,8);
}
void ResetDay(int key,datetime server)
{
   date_key=key;saw_open=false;created=false;active=false;traded=false;session_low=DBL_MAX;
   MqlDateTime ny;NYParts(server,ny);ny.hour=InpCloseMinuteNY/60;ny.min=InpCloseMinuteNY%60;ny.sec=0;
   datetime utc=server-InpServerUTCOffsetHours*3600;
   close_server=StructToTime(ny)-NYOffset(utc)*3600+InpServerUTCOffsetHours*3600;
}
bool FindSupply(MqlRates &bars[])
{
   // Earliest qualifying 1-3-bar bearish leg wins. Never retrospectively pick
   // the best zone from the whole session, and never use an unclosed candle.
   int count=ArraySize(bars);
   for(int length=1;length<=InpMaxImpulseBars;length++)
   {
      if(length+InpBullishSearchBars>=count)break;
      double high=-DBL_MAX,low=DBL_MAX;bool bearish=true;
      for(int k=1;k<=length;k++)
      {
         int minute=NYMinute(bars[k].time);
         if(bars[k].close>=bars[k].open || NYDate(bars[k].time)!=date_key ||
            minute<InpOpenMinuteNY || minute>=InpImpulseUntilMinuteNY ||
            (k>1 && bars[k-1].time-bars[k].time!=300)){bearish=false;break;}
         high=MathMax(high,bars[k].high);low=MathMin(low,bars[k].low);
      }
      if(!bearish || high<=low)continue;
      double values[];
      if(CopyBuffer(atr_handle,0,length+1,1,values)!=1 || values[0]<=0)continue;
      double atr=values[0];
      if(bars[length].open-bars[1].close<InpImpulseBodyATR*atr)continue;
      if((bars[1].close-low)/(high-low)>InpImpulseCloseBottomFraction)continue;
      for(int k=length+1;k<=length+InpBullishSearchBars;k++)
      {
         if(bars[k].close<=bars[k].open)continue;
         if(NYDate(bars[k].time)!=date_key || NYMinute(bars[k].time)<InpOpenMinuteNY-30)break;
         // Last up candle before this leg; a drop must close beneath its body.
         if(bars[1].close>=bars[k].open)return false;
         zone_low=bars[k].open;zone_high=bars[k].close;origin_high=bars[k].high;
         zone_atr=atr;origin_time=bars[k].time;impulse_end=bars[1].time+300;
         created=true;active=true;zones++;return true;
      }
   }
   return false;
}

int OnInit()
{
   if(!MQLInfoInteger(MQL_TESTER) || InpSignalAuditTag=="")return INIT_FAILED;
   if(InpRiskPercent<=0 || InpATRPeriod<2 || InpMaxImpulseBars<1 || InpBullishSearchBars<1 || InpStopBufferATR<=0)return INIT_PARAMETERS_INCORRECT;
   atr_handle=iATR(_Symbol,PERIOD_M5,InpATRPeriod);if(atr_handle==INVALID_HANDLE)return INIT_FAILED;
   trade.SetExpertMagicNumber((ulong)InpMagic);trade.SetDeviationInPoints(InpDeviationPoints);trade.SetTypeFillingBySymbol(_Symbol);
   FolderCreate("CalyxNYSupply20261009",FILE_COMMON);
   audit=FileOpen("CalyxNYSupply20261009\\"+InpSignalAuditTag+".csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   if(audit==INVALID_HANDLE)return INIT_FAILED;
   FileWrite(audit,"date_ny","origin_epoch","impulse_end_epoch","rejection_start_epoch","signal_close_epoch","requested_entry","stop","target","zone_low","zone_high","origin_high","rejection_high","atr","requested_risk_usd","lots","reward_risk");
   return INIT_SUCCEEDED;
}
void OnTick()
{
   // First tick at/after 16:00 ET flattens the position; this is a declared
   // reconstruction assumption, not an exit specified in the reel.
   if(may_hold && close_server>0 && TimeCurrent()>=close_server)
   {
      ulong ticket;
      if(!OurPosition(ticket))may_hold=false;
      else if(trade.PositionClose(ticket) && trade.ResultRetcode()==TRADE_RETCODE_DONE){may_hold=false;time_closes++;}
   }
   datetime current=iTime(_Symbol,PERIOD_M5,0);
   if(current==0 || current==last_bar)return;last_bar=current;
   MqlDateTime ny;NYParts(current,ny);
   if(ny.day_of_week<1 || ny.day_of_week>5)return;
   int key=ny.year*10000+ny.mon*100+ny.day;
   if(key!=date_key)ResetDay(key,current);
   int minute=ny.hour*60+ny.min;
   if(minute<InpOpenMinuteNY || minute>InpEntryUntilMinuteNY || traded)return;
   MqlRates bars[];ArraySetAsSeries(bars,true);
   int copied=CopyRates(_Symbol,PERIOD_M5,0,InpMaxImpulseBars+InpBullishSearchBars+3,bars);
   if(copied<InpMaxImpulseBars+InpBullishSearchBars+3)return;
   int bar_minute=NYMinute(bars[1].time);
   if(NYDate(bars[1].time)!=date_key || bar_minute<InpOpenMinuteNY)return;
   if(!saw_open)
   {
      if(bar_minute!=InpOpenMinuteNY)return;
      saw_open=true;sessions++;
   }
   session_low=MathMin(session_low,bars[1].low);
   if(!created){FindSupply(bars);return;}
   if(!active || bars[1].time<impulse_end)return;
   if(bars[1].close>origin_high){active=false;invalidations++;return;}
   double body=bars[1].open-bars[1].close;
   double wick=bars[1].high-MathMax(bars[1].open,bars[1].close);
   double range=bars[1].high-bars[1].low;
   bool rejection=body>0 && bars[2].close<zone_low && bars[1].high>=zone_low && bars[1].close<zone_low &&
      wick>=InpUpperWickBodyRatio*body && range>0 && wick/range>=InpMinUpperWickFraction;
   if(!rejection)return;wick_signals++;
   MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return;
   // Both the zone and rejecting wick are known now. Stop protects both.
   double stop=Price(MathMax(origin_high,bars[1].high)+InpStopBufferATR*zone_atr);
   double target=Price(session_low),entry=tick.bid;
   double guard=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
   if(stop<=tick.ask+guard || target>=tick.ask-guard || target>=entry || stop<=entry){bad_geometry++;return;}
   ulong ticket;if(OurPosition(ticket))return;
   double volume=Lots(entry,stop);if(volume<=0){undersize++;return;}
   double budget=AccountInfoDouble(ACCOUNT_BALANCE)*InpRiskPercent/100;
   if(trade.Sell(volume,_Symbol,0,stop,target,"NYSupply "+IntegerToString(date_key)) &&
      (trade.ResultRetcode()==TRADE_RETCODE_DONE || trade.ResultRetcode()==TRADE_RETCODE_DONE_PARTIAL))
   {
      traded=true;active=false;may_hold=true;placed++;
      FileWrite(audit,key,(long)origin_time,(long)impulse_end,(long)bars[1].time,(long)current,
         DoubleToString(entry,8),DoubleToString(stop,8),DoubleToString(target,8),DoubleToString(zone_low,8),DoubleToString(zone_high,8),
         DoubleToString(origin_high,8),DoubleToString(bars[1].high,8),DoubleToString(zone_atr,8),DoubleToString(budget,2),DoubleToString(volume,8),DoubleToString((entry-target)/(stop-entry),8));
   }
   else {rejected++;Print("NYSUPPLY_ORDER_REJECTED ",trade.ResultRetcodeDescription());}
}
void OnDeinit(const int reason)
{
   if(atr_handle!=INVALID_HANDLE)IndicatorRelease(atr_handle);
   if(audit!=INVALID_HANDLE){FileClose(audit);audit=INVALID_HANDLE;}
   Print("NYSUPPLY_STATS sessions=",sessions," zones=",zones," invalidations=",invalidations," wick_signals=",wick_signals,
      " placed=",placed," rejected=",rejected," invalid_geometry=",bad_geometry," undersize_or_margin=",undersize," time_closes=",time_closes);
}

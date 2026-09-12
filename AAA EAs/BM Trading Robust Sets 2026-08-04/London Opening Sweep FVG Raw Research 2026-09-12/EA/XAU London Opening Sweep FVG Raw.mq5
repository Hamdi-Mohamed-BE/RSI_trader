#property strict
#property version "1.00"
#property description "Research only: London opening H1 range, H1 wick sweep, lower timeframe FVG retest"
#include <Trade/Trade.mqh>

input double InpRiskPercent=1.0;
input ENUM_TIMEFRAMES InpEntryTimeframe=PERIOD_M5;
input int InpLondonOpenHour=8;
input int InpLondonEndHour=17;
input int InpTesterServerUTCOffsetHours=0;
input int InpDeviationPoints=30;
input long InpMagic=84124001;

CTrade trade;
int day_key=0, bias=0;
bool range_ready=false, finished=false, attempted=false;
double range_high=0, range_low=0, sweep_stop=0;
datetime range_start=0, sweep_confirmed=0, last_h1=0, last_m5=0;
int audit=INVALID_HANDLE;
long range_count=0,sweep_count=0,gap_count=0,order_count=0,fill_count=0,error_count=0,invalid_count=0;
datetime retry_close_after=0;

datetime LastSunday(const int year,const int month)
{
   MqlDateTime p={0}; p.year=year;p.mon=month;p.day=31;p.hour=1;
   datetime d=StructToTime(p);TimeToStruct(d,p);
   return d-p.day_of_week*86400;
}
int LondonOffset(const datetime utc)
{
   MqlDateTime p;TimeToStruct(utc,p);
   return utc>=LastSunday(p.year,3) && utc<LastSunday(p.year,10) ? 3600 : 0;
}
datetime LondonTime(const datetime server)
{
   datetime utc=server-InpTesterServerUTCOffsetHours*3600;
   return utc+LondonOffset(utc);
}
int DayKey(const datetime server)
{
   MqlDateTime p;TimeToStruct(LondonTime(server),p);
   return p.year*10000+p.mon*100+p.day;
}
void Audit(const string event,const string detail,const double entry=0,const double stop=0,const double target=0,const double lots=0)
{
   if(audit==INVALID_HANDLE)return;
   FileWrite(audit,TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),TimeToString(LondonTime(TimeCurrent()),TIME_DATE|TIME_SECONDS),event,detail,range_high,range_low,TimeToString(sweep_confirmed,TIME_DATE|TIME_SECONDS),bias,entry,stop,target,lots);
   FileFlush(audit);
}
bool OurPosition()
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      if(PositionGetTicket(i)>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)return true;
   }
   return false;
}
bool OurOrder()
{
   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      if(OrderGetTicket(i)>0 && OrderGetString(ORDER_SYMBOL)==_Symbol && OrderGetInteger(ORDER_MAGIC)==InpMagic)return true;
   }
   return false;
}
void DeleteOrders(const string reason)
{
   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      ulong ticket=OrderGetTicket(i);
      if(ticket==0 || OrderGetString(ORDER_SYMBOL)!=_Symbol || OrderGetInteger(ORDER_MAGIC)!=InpMagic)continue;
      if(trade.OrderDelete(ticket))Audit("cancel",reason);
      else { error_count++;Audit("error",reason+" "+trade.ResultRetcodeDescription()); }
   }
}
void Flatten()
{
   if(TimeCurrent()<retry_close_after)return;
   DeleteOrders("London end or stale prior day");
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || PositionGetString(POSITION_SYMBOL)!=_Symbol || PositionGetInteger(POSITION_MAGIC)!=InpMagic)continue;
      if(trade.PositionClose(ticket))Audit("time_exit","London end or stale prior day");
      else {error_count++;Audit("error","time exit "+trade.ResultRetcodeDescription());}
   }
   retry_close_after=TimeCurrent()+60;
}
void ResetDay(const datetime now)
{
   day_key=DayKey(now);bias=0;range_ready=false;finished=false;attempted=false;
   range_high=0;range_low=0;sweep_stop=0;sweep_confirmed=0;last_h1=0;last_m5=0;
   MqlDateTime p;TimeToStruct(LondonTime(now),p);p.hour=InpLondonOpenHour;p.min=0;p.sec=0;
   datetime utc=now-InpTesterServerUTCOffsetHours*3600;
   range_start=StructToTime(p)-LondonOffset(utc)+InpTesterServerUTCOffsetHours*3600;
}
double PriceStep()
{
   return MathMax(SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE),SymbolInfoDouble(_Symbol,SYMBOL_POINT));
}
double RoundPrice(const double value,const bool up)
{
   double step=PriceStep();
   return NormalizeDouble((up?MathCeil(value/step):MathFloor(value/step))*step,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}
double RiskLots(const bool buy,const double entry,const double sl)
{
   double pnl=0;
   if(!OrderCalcProfit(buy?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,1.0,entry,sl,pnl) || pnl==0)return 0;
   double raw=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0/MathAbs(pnl);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),lo=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),hi=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   if(step<=0 || lo<=0)return 0;
   return NormalizeDouble(MathMax(lo,MathMin(hi,MathCeil(raw/step-1e-10)*step)),8);
}
void ReadRange(const datetime now)
{
   if(now<range_start+3600)return;
   MqlRates r[];
   if(CopyRates(_Symbol,PERIOD_H1,range_start,1,r)!=1 || r[0].time!=range_start)return;
   if(r[0].high<=r[0].low)return;
   range_high=r[0].high;range_low=r[0].low;range_ready=true;range_count++;
   Audit("range","closed London opening H1");
}
void ReadSweep(const datetime now)
{
   MqlRates h[];
   if(CopyRates(_Symbol,PERIOD_H1,1,1,h)!=1)return;
   if(h[0].time==last_h1 || h[0].time<range_start+3600 || h[0].time+3600>now)return;
   last_h1=h[0].time;
   // The complete body must lie inside; a bar sweeping both ends is ambiguous.
   bool body_inside=h[0].open>=range_low && h[0].open<=range_high && h[0].close>=range_low && h[0].close<=range_high;
   bool down=h[0].low<range_low,up=h[0].high>range_high;
   if(!body_inside || down==up)return;
   bias=down?1:-1;sweep_stop=down?h[0].low:h[0].high;sweep_confirmed=h[0].time+3600;sweep_count++;
   Audit("sweep",down?"H1 downside wick reclaim":"H1 upside wick reclaim",0,sweep_stop,bias>0?range_high:range_low);
}
void ReadGap(const datetime now,const MqlTick &tick)
{
   MqlRates b[];
   // CopyRates gives oldest first: all three bars are fully closed after confirmation.
   int seconds=PeriodSeconds(InpEntryTimeframe);
   if(CopyRates(_Symbol,InpEntryTimeframe,1,3,b)!=3)return;
   if(b[2].time==last_m5)return;
   if(b[2].time+seconds>now || b[0].time<sweep_confirmed)return;
   last_m5=b[2].time;
   if(b[1].time-b[0].time!=seconds || b[2].time-b[1].time!=seconds)return;
   bool buy=bias>0;
   bool gap=buy?(b[2].low>b[0].high && b[1].close>b[1].open):(b[2].high<b[0].low && b[1].close<b[1].open);
   if(!gap)return;
   attempted=true;gap_count++;
   double entry=RoundPrice(buy?b[2].low:b[2].high,!buy);
   // User-selected stop: one tradable tick beyond the far FVG edge.
   double stop=RoundPrice(buy?b[0].high-PriceStep():b[0].low+PriceStep(),!buy);
   double target=RoundPrice(buy?range_high:range_low,!buy);
   double min_distance=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
   Audit("fvg","first confirmed "+EnumToString(InpEntryTimeframe)+" gap; nearest edge retest",entry,stop,target);
   if((buy && (entry>=tick.ask || stop>=entry || target<=entry || tick.bid>=target)) ||
      (!buy && (entry<=tick.bid || stop<=entry || target>=entry || tick.ask<=target)) ||
      MathAbs(entry-stop)<min_distance || MathAbs(target-entry)<min_distance ||
      (buy?tick.ask-entry:entry-tick.bid)<min_distance)
   {
      finished=true;invalid_count++;Audit("invalid","gap already crossed, target reached, or broker stop-distance requirement",entry,stop,target);return;
   }
   double lots=RiskLots(buy,entry,stop);
   if(lots<=0){finished=true;error_count++;Audit("error","risk or contract calculation failed",entry,stop,target);return;}
   bool sent=buy?trade.BuyLimit(lots,entry,_Symbol,stop,target,ORDER_TIME_GTC,0,"LondonSweepFVG"):
                 trade.SellLimit(lots,entry,_Symbol,stop,target,ORDER_TIME_GTC,0,"LondonSweepFVG");
   if(sent){order_count++;Audit("limit","first FVG edge",entry,stop,target,lots);}
   else {finished=true;error_count++;Audit("error",trade.ResultRetcodeDescription(),entry,stop,target,lots);}
}
void OnTick()
{
   datetime now=TimeCurrent();MqlDateTime local;TimeToStruct(LondonTime(now),local);
   if(day_key!=DayKey(now))
   {
      if(OurPosition() || OurOrder()){Flatten();return;}
      ResetDay(now);
   }
   if(local.hour>=InpLondonEndHour){Flatten();finished=true;return;}
   if(local.day_of_week<1 || local.day_of_week>5 || local.hour<InpLondonOpenHour || finished)return;
   if(OurPosition())return;
   if(!range_ready){ReadRange(now);if(!range_ready)return;}
   if(bias==0){ReadSweep(now);if(bias==0)return;}
   MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return;
   bool invalid=bias>0?(tick.bid<=sweep_stop || tick.bid>=range_high):(tick.bid>=sweep_stop || tick.bid<=range_low);
   if(invalid){DeleteOrders("sweep extreme broken or opposite range target reached before entry");finished=true;invalid_count++;Audit("invalid","setup invalidated before fill");return;}
   if(!attempted)ReadGap(now,tick);
}
void OnTradeTransaction(const MqlTradeTransaction &trans,const MqlTradeRequest &request,const MqlTradeResult &result)
{
   if(trans.type!=TRADE_TRANSACTION_DEAL_ADD || trans.deal==0 || !HistoryDealSelect(trans.deal))return;
   if(HistoryDealGetString(trans.deal,DEAL_SYMBOL)!=_Symbol || HistoryDealGetInteger(trans.deal,DEAL_MAGIC)!=InpMagic)return;
   long dir=HistoryDealGetInteger(trans.deal,DEAL_ENTRY);
   if(dir==DEAL_ENTRY_IN){fill_count++;finished=true;Audit("fill",(string)trans.deal,trans.price,trans.price_sl,trans.price_tp,trans.volume);}
   if(dir==DEAL_ENTRY_OUT)Audit("exit",(string)HistoryDealGetInteger(trans.deal,DEAL_REASON),trans.price,0,0,trans.volume);
}
int OnInit()
{
   // This research artifact is deliberately tester-only.
   if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;
   if(InpRiskPercent<=0 || InpLondonOpenHour<0 || InpLondonEndHour>23 || InpLondonEndHour<=InpLondonOpenHour+1)return INIT_PARAMETERS_INCORRECT;
   if(InpEntryTimeframe!=PERIOD_M1 && InpEntryTimeframe!=PERIOD_M5 && InpEntryTimeframe!=PERIOD_M15)return INIT_PARAMETERS_INCORRECT;
   trade.SetExpertMagicNumber((ulong)InpMagic);trade.SetDeviationInPoints(InpDeviationPoints);trade.SetTypeFillingBySymbol(_Symbol);
   audit=FileOpen("LondonSweepFVG-"+(string)InpMagic+".csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(audit!=INVALID_HANDLE)FileWrite(audit,"server_time","london_time","event","detail","range_high","range_low","sweep_confirmed","bias","entry","stop","target","lots");
   Print("LONDON RAW contract ",_Symbol," custom=",SymbolInfoInteger(_Symbol,SYMBOL_CUSTOM)," min=",SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN)," step=",SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP));
   for(int d=1;d<=5;d++)for(uint i=0;i<10;i++){datetime a,z;if(!SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)d,i,a,z))break;Print("LONDON RAW session day=",d," ",TimeToString(a,TIME_MINUTES),"-",TimeToString(z,TIME_MINUTES));}
   return INIT_SUCCEEDED;
}
void OnDeinit(const int reason)
{
   Audit("summary",StringFormat("ranges=%I64d sweeps=%I64d gaps=%I64d orders=%I64d fills=%I64d invalid=%I64d errors=%I64d",range_count,sweep_count,gap_count,order_count,fill_count,invalid_count,error_count));
   if(audit!=INVALID_HANDLE)FileClose(audit);
}

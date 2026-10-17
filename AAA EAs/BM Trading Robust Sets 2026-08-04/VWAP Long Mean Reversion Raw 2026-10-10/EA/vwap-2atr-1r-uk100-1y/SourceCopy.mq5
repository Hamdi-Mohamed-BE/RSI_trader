#property strict
#property version "1.00"
#property description "TESTER ONLY. Reconstructed two-ATR VWAP discount, long-only, fixed 1R."
#include <Trade/Trade.mqh>

input double InpRiskPercent=1.0;
input int InpATRPeriod=14;
input double InpDiscountATR=2.0;
input double InpStopATR=1.0;
input double InpRewardRisk=1.0;
input int InpMinSessionBars=15;
input int InpEntryUntilMinuteUTC=1430;
input int InpCloseMinuteUTC=1435;
input int InpServerUTCOffsetHours=0;
input long InpMagic=26101021;
input int InpDeviationPoints=1000;
input string InpSignalAuditTag="";

CTrade trade;
int atr_handle=INVALID_HANDLE,audit=INVALID_HANDLE;
datetime last_bar=0;
int day_key=0,position_day=0;
bool armed=true,may_hold=false;
long bars_seen=0,discount_signals=0,placed=0,rejected=0,invalid_geometry=0,undersize=0,time_closes=0,held_skips=0;

int DayKey(datetime server)
{
   MqlDateTime p;TimeToStruct(server-InpServerUTCOffsetHours*3600,p);
   return p.year*10000+p.mon*100+p.day;
}
int MinuteUTC(datetime server)
{
   MqlDateTime p;TimeToStruct(server-InpServerUTCOffsetHours*3600,p);
   return p.hour*60+p.min;
}
datetime DayStartServer(datetime server)
{
   MqlDateTime p;TimeToStruct(server-InpServerUTCOffsetHours*3600,p);
   p.hour=0;p.min=0;p.sec=0;
   return StructToTime(p)+InpServerUTCOffsetHours*3600;
}
double Price(double value)
{
   double step=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(step<=0)return 0;
   return NormalizeDouble(MathRound(value/step)*step,_Digits);
}
bool OurPosition(ulong &ticket)
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong t=PositionGetTicket(i);
      if(t>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)
      {ticket=t;return true;}
   }
   ticket=0;return false;
}
double Lots(double entry,double stop)
{
   double loss=0;
   if(!OrderCalcProfit(ORDER_TYPE_BUY,_Symbol,1,entry,stop,loss) || loss>=0)return 0;
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   if(step<=0 || minimum<=0)return 0;
   double budget=AccountInfoDouble(ACCOUNT_BALANCE)*InpRiskPercent/100;
   double volume=MathFloor((MathMin(budget/MathAbs(loss),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX))+1e-10)/step)*step;
   if(volume<minimum-1e-10)return 0;
   double margin=0;
   if(!OrderCalcMargin(ORDER_TYPE_BUY,_Symbol,volume,entry,margin) || margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE))return 0;
   return NormalizeDouble(volume,8);
}
bool ClosedSessionVWAP(datetime start,datetime last,double &vwap,int &positive_bars)
{
   MqlRates session[];
   int got=CopyRates(_Symbol,PERIOD_M5,start,last,session);
   double pv=0,vol=0;positive_bars=0;
   for(int i=0;i<got;i++)
   {
      // Only fully closed M5 bars. Zero tick-volume bars are not fabricated.
      if(session[i].time<start || session[i].time>last || session[i].tick_volume<=0)continue;
      double weight=(double)session[i].tick_volume;
      pv+=(session[i].high+session[i].low+session[i].close)/3.0*weight;
      vol+=weight;positive_bars++;
   }
   if(vol<=0 || positive_bars<InpMinSessionBars)return false;
   vwap=pv/vol;return MathIsValidNumber(vwap) && vwap>0;
}
int OnInit()
{
   if(!MQLInfoInteger(MQL_TESTER) || InpSignalAuditTag=="")return INIT_FAILED;
   if(InpRiskPercent<=0 || InpATRPeriod<2 || InpDiscountATR<=0 || InpStopATR<=0 ||
      InpRewardRisk!=1.0 || InpMinSessionBars<2 || InpEntryUntilMinuteUTC>=InpCloseMinuteUTC)
      return INIT_PARAMETERS_INCORRECT;
   atr_handle=iATR(_Symbol,PERIOD_M5,InpATRPeriod);
   if(atr_handle==INVALID_HANDLE)return INIT_FAILED;
   trade.SetExpertMagicNumber((ulong)InpMagic);trade.SetDeviationInPoints(InpDeviationPoints);trade.SetTypeFillingBySymbol(_Symbol);
   FolderCreate("CalyxVWAPRaw20261010",FILE_COMMON);
   audit=FileOpen("CalyxVWAPRaw20261010\\"+InpSignalAuditTag+".csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   if(audit==INVALID_HANDLE)return INIT_FAILED;
   FileWrite(audit,"day_utc","session_start_epoch","signal_start_epoch","signal_close_epoch","signal_close_price",
      "vwap","atr","discount_atr","positive_session_bars","requested_entry","stop","target",
      "requested_risk_usd","lots","fill_price","initial_risk_usd","reward_risk");
   return INIT_SUCCEEDED;
}
void OnTick()
{
   datetime now=TimeCurrent();
   if(may_hold && (MinuteUTC(now)>=InpCloseMinuteUTC || DayKey(now)!=position_day))
   {
      ulong ticket;
      if(!OurPosition(ticket))may_hold=false;
      else if(trade.PositionClose(ticket) && trade.ResultRetcode()==TRADE_RETCODE_DONE)
      {may_hold=false;time_closes++;}
   }
   datetime current=iTime(_Symbol,PERIOD_M5,0);
   if(current<=0 || current==last_bar)return;
   // Do not mark a bar as processed until history and closed-bar ATR are ready.
   MqlRates bars[];ArraySetAsSeries(bars,true);
   double values[];
   if(CopyRates(_Symbol,PERIOD_M5,0,2,bars)!=2 || CopyBuffer(atr_handle,0,1,1,values)!=1 || values[0]<=0)return;
   last_bar=current;bars_seen++;
   int key=DayKey(current);
   if(key!=day_key){day_key=key;armed=true;}
   // No stale Friday/suspension candle entry on the first tick after a gap.
   if(bars[1].time+300!=current || DayKey(bars[1].time)!=key)return;
   double vwap=0;int count=0;
   datetime session_start=DayStartServer(current);
   if(!ClosedSessionVWAP(session_start,bars[1].time,vwap,count))return;
   double atr=values[0],discount=(vwap-bars[1].close)/atr;
   if(discount<InpDiscountATR){armed=true;return;}
   if(!armed)return;
   // One attempt per excursion; re-arm only on a completed close back inside
   // the two-ATR boundary (or a new UTC session). No pyramiding or averaging.
   armed=false;discount_signals++;
   if(MinuteUTC(current)>InpEntryUntilMinuteUTC)return;
   ulong ticket;if(OurPosition(ticket)){held_skips++;return;}
   MqlTick tick;if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0 || tick.bid<=0)return;
   double entry=tick.ask,stop=Price(entry-InpStopATR*atr);
   double target=Price(entry+(entry-stop)*InpRewardRisk);
   double guard=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
   if(stop<=0 || stop>=tick.bid-guard || target<=entry+guard){invalid_geometry++;return;}
   double volume=Lots(entry,stop);
   if(volume<=0){undersize++;return;}
   double budget=AccountInfoDouble(ACCOUNT_BALANCE)*InpRiskPercent/100;
   if(trade.Buy(volume,_Symbol,0,stop,target,"VWAP2ATR 1R") &&
      (trade.ResultRetcode()==TRADE_RETCODE_DONE || trade.ResultRetcode()==TRADE_RETCODE_DONE_PARTIAL))
   {
      may_hold=true;position_day=key;placed++;
      double fill=trade.ResultPrice(),loss=0;
      if(!OrderCalcProfit(ORDER_TYPE_BUY,_Symbol,volume,fill,stop,loss))Print("VWAPRAW_RISK_CALC_FAILED");
      FileWrite(audit,key,(long)session_start,(long)bars[1].time,(long)current,DoubleToString(bars[1].close,8),
         DoubleToString(vwap,8),DoubleToString(atr,8),DoubleToString(discount,8),count,
         DoubleToString(entry,8),DoubleToString(stop,8),DoubleToString(target,8),DoubleToString(budget,2),
         DoubleToString(volume,8),DoubleToString(fill,8),DoubleToString(MathAbs(loss),8),
         DoubleToString((target-entry)/(entry-stop),8));
   }
   else {rejected++;Print("VWAPRAW_ORDER_REJECTED ",trade.ResultRetcodeDescription());}
}
void OnDeinit(const int reason)
{
   if(atr_handle!=INVALID_HANDLE)IndicatorRelease(atr_handle);
   if(audit!=INVALID_HANDLE){FileClose(audit);audit=INVALID_HANDLE;}
   Print("VWAPRAW_STATS bars=",bars_seen," discount_signals=",discount_signals," placed=",placed,
      " rejected=",rejected," invalid_geometry=",invalid_geometry," undersize_or_margin=",undersize,
      " time_closes=",time_closes," held_skips=",held_skips);
}

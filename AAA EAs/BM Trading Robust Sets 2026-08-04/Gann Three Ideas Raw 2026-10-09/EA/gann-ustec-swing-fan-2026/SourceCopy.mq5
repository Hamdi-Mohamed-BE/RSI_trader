#property strict
#property version "1.00"
#property description "TESTER ONLY. Frozen Gann-inspired boxes, swing-scaled fan and time-cycle gates."
#include <Trade/Trade.mqh>

// 0=eighth rejection, 1=range break/retest, 2=fan break/retest,
// 3=EMA-cross baseline, 4=cycle-gated EMA cross, 5=random-window EMA cross,
// 6=quartile-rejection control. None is an exact original Gann system.
input int InpIdea=0;
input ENUM_TIMEFRAMES InpSignalTF=PERIOD_M15;
input ENUM_TIMEFRAMES InpReferenceTF=PERIOD_D1;
input double InpRiskPercent=0.5;
input int InpATRPeriod=14;
input int InpPivotNeighbours=2;
input int InpFanMaxH4Bars=32;
input int InpRetestBars=8;
input double InpTargetR=2;
input double InpStopBufferATR=0.25;
input double InpRetestBufferATR=0.10;
input int InpCloseMinuteUTC=1255; // 20:55 UTC, a declared common day-flat rule
input int InpEntryUntilMinuteUTC=1230;
input int InpMaxHoldMinutes=480;
input int InpServerUTCOffsetHours=0;
input uint InpRandomSeed=26100950;
input long InpMagic=26100950;
input int InpDeviationPoints=1000;
input string InpSignalAuditTag="";

CTrade trade;
int atr_handle=INVALID_HANDLE,fast_handle=INVALID_HANDLE,slow_handle=INVALID_HANDLE,audit=INVALID_HANDLE;
datetime last_bar=0,last_h4=0,reference_time=0,close_at=0,opened_at=0;
datetime last_low_time=0,last_high_time=0,low_anchor=0,high_anchor=0,low_confirm=0,high_confirm=0,cycle_confirm=0,cycle_pivot=0;
double last_low=0,last_high=0,low_price=0,high_price=0,low_slope=0,high_slope=0,range_low=0,range_high=0;
int day_key=0,arm_side=0,arm_age=0,random_centres[3];
datetime arm_anchor=0;
bool traded=false,history_seeded=false,may_hold=false;
long bars_seen=0,raw_signals=0,gate_blocks=0,placed=0,rejected=0,invalid_geometry=0,undersize=0,time_closes=0;

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
double Lots(int side,double entry,double stop)
{
   ENUM_ORDER_TYPE type=side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   double loss=0;
   if(!OrderCalcProfit(type,_Symbol,1,entry,stop,loss) || loss>=0)return 0;
   double budget=AccountInfoDouble(ACCOUNT_BALANCE)*InpRiskPercent/100;
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double volume=MathFloor((MathMin(budget/MathAbs(loss),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX))+1e-10)/step)*step;
   if(volume<minimum-1e-10)return 0;
   double margin=0;
   if(!OrderCalcMargin(type,_Symbol,volume,entry,margin) || margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE))return 0;
   return NormalizeDouble(volume,8);
}
void SetRandomCentres(datetime confirm)
{
   uint state=(uint)((long)confirm/3600)^InpRandomSeed;
   for(int i=0;i<3;i++)
   {
      bool accepted=false;
      for(int attempt=0;attempt<10000 && !accepted;attempt++)
      {
         state=1664525*state+1013904223;
         int candidate=2+(int)(state%31);accepted=true;
         for(int j=0;j<i;j++)if(MathAbs(candidate-random_centres[j])<=2)accepted=false;
         if(accepted)random_centres[i]=candidate;
      }
   }
}
void AddPivot(bool is_low,MqlRates &bars[],int k,datetime confirm)
{
   datetime time=bars[k].time;double price=is_low?bars[k].low:bars[k].high;
   datetime previous=is_low?last_low_time:last_high_time;
   double previous_price=is_low?last_low:last_high;
   int length=previous>0?iBarShift(_Symbol,PERIOD_H4,previous,false)-iBarShift(_Symbol,PERIOD_H4,time,false):0;
   // A rising fan uses two already-confirmed higher lows; falling fan two lower highs.
   if(length>=4 && ((is_low && price>previous_price) || (!is_low && price<previous_price)))
   {
      double slope=MathAbs(price-previous_price)/length;
      if(is_low){low_anchor=time;low_confirm=confirm;low_price=price;low_slope=slope;}
      else{high_anchor=time;high_confirm=confirm;high_price=price;high_slope=slope;}
   }
   if(is_low){last_low_time=time;last_low=price;}
   else{last_high_time=time;last_high=price;}
   cycle_pivot=time;cycle_confirm=confirm;SetRandomCentres(confirm);
}
void CheckPivot(MqlRates &bars[],int k)
{
   bool low=true,high=true;
   for(int j=1;j<=InpPivotNeighbours;j++)
   {
      if(bars[k].low>=bars[k-j].low || bars[k].low>=bars[k+j].low)low=false;
      if(bars[k].high<=bars[k-j].high || bars[k].high<=bars[k+j].high)high=false;
   }
   datetime confirmation=bars[k-InpPivotNeighbours-1].time;
   if(low)AddPivot(true,bars,k,confirmation);
   if(high)AddPivot(false,bars,k,confirmation); // outside-bar tie: high is last, explicitly deterministic
}
void UpdatePivots()
{
   datetime current=iTime(_Symbol,PERIOD_H4,0);
   if(current==0 || current==last_h4)return;
   MqlRates bars[];ArraySetAsSeries(bars,true);
   int got=CopyRates(_Symbol,PERIOD_H4,0,130,bars);
   if(got<120)return;
   last_h4=current;
   if(!history_seeded)
   {
      for(int k=got-InpPivotNeighbours-1;k>=InpPivotNeighbours+1;k--)CheckPivot(bars,k);
      history_seeded=true;
   }
   else CheckPivot(bars,InpPivotNeighbours+1);
}
double FanAge(datetime anchor,datetime now)
{
   int shift=iBarShift(_Symbol,PERIOD_H4,anchor,false);
   datetime h4=iTime(_Symbol,PERIOD_H4,0);
   if(shift<0 || h4<=0)return -1;
   // Completed tradable H4 bars plus elapsed time in the current bar; no weekend-clock jump.
   return shift+(double)(now-h4)/14400.0;
}
double FanLine(int side,datetime now)
{
   if(side>0)return low_price+low_slope*FanAge(low_anchor,now);
   return high_price-high_slope*FanAge(high_anchor,now);
}
bool CyclePass(int idea,int age)
{
   if(idea==3)return true;
   if(age<1 || age>33)return false;
   if(idea==4)return MathAbs(age-8)<=1 || MathAbs(age-16)<=1 || MathAbs(age-32)<=1;
   for(int i=0;i<3;i++)if(MathAbs(age-random_centres[i])<=1)return true;
   return false;
}
void ResetDay(datetime current)
{
   datetime utc=current-InpServerUTCOffsetHours*3600;
   MqlDateTime p;TimeToStruct(utc,p);
   int key=p.year*10000+p.mon*100+p.day;
   if(key==day_key)return;
   day_key=key;traded=false;arm_side=0;arm_age=0;
   p.hour=InpCloseMinuteUTC/60;p.min=InpCloseMinuteUTC%60;p.sec=0;
   close_at=StructToTime(p)+InpServerUTCOffsetHours*3600;
}
bool Place(int side,MqlRates &bars[],double atr,double raw_stop,double raw_target,
           datetime known,datetime pivot,double feature,double age)
{
   MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return false;
   double entry=side>0?tick.ask:tick.bid;
   double stop=Price(raw_stop);
   double risk=side>0?entry-stop:stop-entry;
   double target=Price(raw_target>0?raw_target:entry+side*InpTargetR*risk);
   double guard=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
   bool good=side>0?(stop<tick.bid-guard && target>tick.bid+guard && target>entry):(stop>tick.ask+guard && target<tick.ask-guard && target<entry);
   if(risk<=0 || !good || known>bars[0].time || (pivot>0 && pivot>=known)){invalid_geometry++;return false;}
   double volume=Lots(side,entry,stop);if(volume<=0){undersize++;return false;}
   double budget=AccountInfoDouble(ACCOUNT_BALANCE)*InpRiskPercent/100;
   bool sent=side>0?trade.Buy(volume,_Symbol,0,stop,target,"Gann raw "+IntegerToString(InpIdea)):
      trade.Sell(volume,_Symbol,0,stop,target,"Gann raw "+IntegerToString(InpIdea));
   if(sent && (trade.ResultRetcode()==TRADE_RETCODE_DONE || trade.ResultRetcode()==TRADE_RETCODE_DONE_PARTIAL))
   {
      traded=true;may_hold=true;opened_at=TimeCurrent();placed++;arm_side=0;
      FileWrite(audit,InpIdea,side,(long)bars[1].time,(long)bars[0].time,(long)known,(long)pivot,
         DoubleToString(entry,8),DoubleToString(stop,8),DoubleToString(target,8),DoubleToString(budget,2),DoubleToString(volume,8),
         DoubleToString(atr,8),DoubleToString(feature,8),DoubleToString(age,8),random_centres[0],random_centres[1],random_centres[2]);
      return true;
   }
   rejected++;Print("GANN_ORDER_REJECTED ",trade.ResultRetcodeDescription());return false;
}
void BoxSignal(MqlRates &bars[],double atr)
{
   MqlRates reference[];ArraySetAsSeries(reference,true);
   if(CopyRates(_Symbol,InpReferenceTF,0,2,reference)!=2 || reference[1].high<=reference[1].low)return;
   if(reference[1].time!=reference_time)
   {
      reference_time=reference[1].time;range_high=reference[1].high;range_low=reference[1].low;
      arm_side=0;arm_age=0;
   }
   double middle=(range_high+range_low)/2;
   if(InpIdea==0 || InpIdea==6)
   {
      double fraction=InpIdea==0?0.125:0.25;
      double lower=range_low+fraction*(range_high-range_low),upper=range_high-fraction*(range_high-range_low);
      if(bars[1].close>bars[1].open && bars[1].low<=lower && bars[1].close>lower && bars[1].close<middle)
      {
         raw_signals++;Place(1,bars,atr,MathMin(range_low,bars[1].low)-0.1*atr,middle,reference[0].time,reference_time,lower,0);
      }
      else if(bars[1].close<bars[1].open && bars[1].high>=upper && bars[1].close<upper && bars[1].close>middle)
      {
         raw_signals++;Place(-1,bars,atr,MathMax(range_high,bars[1].high)+0.1*atr,middle,reference[0].time,reference_time,upper,0);
      }
      return;
   }
   if(arm_side!=0)
   {
      arm_age++;
      double level=arm_side>0?range_high:range_low;
      bool retest=arm_side>0?(bars[1].low<=level+InpRetestBufferATR*atr && bars[1].close>level && bars[1].close>bars[1].open):
         (bars[1].high>=level-InpRetestBufferATR*atr && bars[1].close<level && bars[1].close<bars[1].open);
      if(arm_age<=InpRetestBars && retest)
      {
         raw_signals++;double stop=arm_side>0?MathMin(level,bars[1].low)-InpStopBufferATR*atr:MathMax(level,bars[1].high)+InpStopBufferATR*atr;
         Place(arm_side,bars,atr,stop,0,reference[0].time,reference_time,level,arm_age);return;
      }
      if(arm_age>InpRetestBars || (arm_side>0?bars[1].close<range_high-atr:bars[1].close>range_low+atr))arm_side=0;
      else return;
   }
   if(bars[2].close<=range_high && bars[1].close>range_high){arm_side=1;arm_age=0;}
   else if(bars[2].close>=range_low && bars[1].close<range_low){arm_side=-1;arm_age=0;}
}
void FanSignal(MqlRates &bars[],double atr)
{
   if(arm_side!=0)
   {
      datetime anchor=arm_side>0?low_anchor:high_anchor;
      double age=anchor>0?FanAge(anchor,bars[0].time):-1;
      arm_age++;
      if(anchor!=arm_anchor || age<0 || age>InpFanMaxH4Bars || arm_age>InpRetestBars)arm_side=0;
      else
      {
         double level=FanLine(arm_side,bars[0].time);
         bool retest=arm_side>0?(bars[1].low<=level+InpRetestBufferATR*atr && bars[1].close>level && bars[1].close>bars[1].open):
            (bars[1].high>=level-InpRetestBufferATR*atr && bars[1].close<level && bars[1].close<bars[1].open);
         if(retest)
         {
            raw_signals++;double stop=arm_side>0?MathMin(level,bars[1].low)-InpStopBufferATR*atr:MathMax(level,bars[1].high)+InpStopBufferATR*atr;
            Place(arm_side,bars,atr,stop,0,arm_side>0?low_confirm:high_confirm,anchor,arm_side>0?low_slope:high_slope,age);
         }
         return;
      }
   }
   for(int side=1;side>=-1;side-=2)
   {
      datetime anchor=side>0?low_anchor:high_anchor,confirm=side>0?low_confirm:high_confirm;
      if(anchor<=0 || confirm>bars[1].time)continue;
      double age=FanAge(anchor,bars[0].time);
      if(age<0 || age>InpFanMaxH4Bars)continue;
      double now=FanLine(side,bars[0].time),before=FanLine(side,bars[1].time);
      if(side>0?(bars[2].close<=before && bars[1].close>now):(bars[2].close>=before && bars[1].close<now))
      {arm_side=side;arm_anchor=anchor;arm_age=0;return;}
   }
}
void CrossSignal(MqlRates &bars[],double atr)
{
   double fast[],slow[];ArraySetAsSeries(fast,true);ArraySetAsSeries(slow,true);
   if(CopyBuffer(fast_handle,0,1,2,fast)!=2 || CopyBuffer(slow_handle,0,1,2,slow)!=2)return;
   int side=fast[1]<=slow[1] && fast[0]>slow[0]?1:(fast[1]>=slow[1] && fast[0]<slow[0]?-1:0);
   if(side==0)return;raw_signals++;
   int age=cycle_confirm>0?iBarShift(_Symbol,PERIOD_H1,cycle_confirm,false):-1;
   if(!CyclePass(InpIdea,age)){gate_blocks++;return;}
   MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return;
   double entry=side>0?tick.ask:tick.bid;
   // The baseline does not require an available pivot; its known-at time is signal close.
   datetime known=InpIdea==3?bars[0].time:cycle_confirm,pivot=InpIdea==3?0:cycle_pivot;
   Place(side,bars,atr,entry-side*1.5*atr,0,known,pivot,(double)age,age);
}
int OnInit()
{
   if(!MQLInfoInteger(MQL_TESTER) || InpSignalAuditTag=="")return INIT_FAILED;
   if(InpIdea<0 || InpIdea>6 || InpRiskPercent<=0 || InpPivotNeighbours!=2 || InpTargetR<=0)return INIT_PARAMETERS_INCORRECT;
   if(InpIdea>=3 && InpIdea<=5 && InpSignalTF!=PERIOD_H1)return INIT_PARAMETERS_INCORRECT;
   atr_handle=iATR(_Symbol,InpSignalTF,InpATRPeriod);
   if(InpIdea>=3 && InpIdea<=5)
   {
      fast_handle=iMA(_Symbol,PERIOD_H1,12,0,MODE_EMA,PRICE_CLOSE);
      slow_handle=iMA(_Symbol,PERIOD_H1,26,0,MODE_EMA,PRICE_CLOSE);
      if(fast_handle==INVALID_HANDLE || slow_handle==INVALID_HANDLE)return INIT_FAILED;
   }
   if(atr_handle==INVALID_HANDLE)return INIT_FAILED;
   trade.SetExpertMagicNumber((ulong)InpMagic);trade.SetDeviationInPoints(InpDeviationPoints);trade.SetTypeFillingBySymbol(_Symbol);
   FolderCreate("CalyxGann20261009",FILE_COMMON);
   audit=FileOpen("CalyxGann20261009\\"+InpSignalAuditTag+".csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   if(audit==INVALID_HANDLE)return INIT_FAILED;
   FileWrite(audit,"idea","side","signal_start_epoch","signal_close_epoch","feature_known_epoch","anchor_epoch","requested_entry","stop","target","requested_risk_usd","lots","atr","feature","age","random1","random2","random3");
   return INIT_SUCCEEDED;
}
void OnTick()
{
   if(may_hold && ((close_at>0 && TimeCurrent()>=close_at) || TimeCurrent()-opened_at>=InpMaxHoldMinutes*60))
   {
      ulong ticket;
      if(!OurPosition(ticket))may_hold=false;
      else if(trade.PositionClose(ticket) && trade.ResultRetcode()==TRADE_RETCODE_DONE){may_hold=false;time_closes++;}
   }
   datetime current=iTime(_Symbol,InpSignalTF,0);
   if(current==0 || current==last_bar)return;last_bar=current;ResetDay(current);UpdatePivots();bars_seen++;
   MqlDateTime utc;TimeToStruct(current-InpServerUTCOffsetHours*3600,utc);
   if(utc.hour*60+utc.min>InpEntryUntilMinuteUTC || traded)return;
   ulong ticket;if(OurPosition(ticket))return;
   MqlRates bars[];ArraySetAsSeries(bars,true);double values[];
   if(CopyRates(_Symbol,InpSignalTF,0,3,bars)!=3 || CopyBuffer(atr_handle,0,1,1,values)!=1 || values[0]<=0)return;
   if(current-bars[1].time!=PeriodSeconds(InpSignalTF))return; // never treat a stale pre-gap bar as a fresh signal
   if(InpIdea==0 || InpIdea==1 || InpIdea==6)BoxSignal(bars,values[0]);
   else if(InpIdea==2)FanSignal(bars,values[0]);
   else CrossSignal(bars,values[0]);
}
void OnDeinit(const int reason)
{
   if(atr_handle!=INVALID_HANDLE)IndicatorRelease(atr_handle);
   if(fast_handle!=INVALID_HANDLE)IndicatorRelease(fast_handle);
   if(slow_handle!=INVALID_HANDLE)IndicatorRelease(slow_handle);
   if(audit!=INVALID_HANDLE){FileClose(audit);audit=INVALID_HANDLE;}
   Print("GANN_STATS idea=",InpIdea," bars=",bars_seen," raw_signals=",raw_signals," gate_blocks=",gate_blocks," placed=",placed,
      " rejected=",rejected," invalid_geometry=",invalid_geometry," undersize_or_margin=",undersize," time_closes=",time_closes);
}

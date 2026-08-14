#property copyright "AAA auction-market research implementation"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

enum AuctionEntryModel
{
   MODEL_FAILED_AUCTION=0,
   MODEL_BREAKOUT_RETEST=1
};

enum AuctionRegimeMode
{
   REGIME_MIGRATING_VALUE=0,
   REGIME_BALANCED_VALUE=1
};

input group "Trading"
input bool                 InpEnableTrading=true;
input double               InpRiskPercent=1.0;
input long                 InpMagic=814180100;
input bool                 InpLongOnly=false;

input group "Auction-market model"
input AuctionEntryModel    InpModel=MODEL_FAILED_AUCTION;
input ENUM_TIMEFRAMES      InpSignalTimeframe=PERIOD_H4;
input int                  InpProfileLookbackDays=80;
input int                  InpProfileBins=64;
input double               InpValueAreaPercent=70.0;
input AuctionRegimeMode    InpRegimeMode=REGIME_BALANCED_VALUE;
input int                  InpShiftLagDays=5;
input double               InpShiftThresholdATR=0.50;
input double               InpEntryToleranceATR=0.0;
input int                  InpRetestExpiryBars=6;
input int                  InpATRPeriod=14;

input group "Stops and trade management"
input double               InpStopBufferATR=0.0;
input double               InpRewardRisk=0.0;
input double               InpMinimumRewardRisk=1.0;
input int                  InpMaximumHoldHours=336;
input bool                 InpBreakEvenAtOneR=false;

input group "Execution and display"
input double               InpMaximumSpreadPrice=0.0;
input int                  InpMaxDeviationPoints=100;
input bool                 InpDrawProfile=true;

struct ProfileLevels
{
   double poc;
   double vah;
   double val;
   datetime asof;
   bool valid;
};

CTrade g_trade;
datetime g_last_signal_bar=0;
datetime g_cached_profile_asof=0;
ProfileLevels g_profile;
ProfileLevels g_previous_profile;

int g_pending_direction=0;
double g_pending_level=0.0;
double g_pending_vah=0.0;
double g_pending_val=0.0;
int g_pending_bars_left=0;

string PendingKey(const string field)
{
   return "AAA_AMVA_"+IntegerToString(InpMagic)+"_"+field;
}

void SavePending()
{
   GlobalVariableSet(PendingKey("direction"),(double)g_pending_direction);
   GlobalVariableSet(PendingKey("level"),g_pending_level);
   GlobalVariableSet(PendingKey("vah"),g_pending_vah);
   GlobalVariableSet(PendingKey("val"),g_pending_val);
   GlobalVariableSet(PendingKey("bars"),(double)g_pending_bars_left);
}

void LoadPending()
{
   if(!GlobalVariableCheck(PendingKey("direction"))) return;
   g_pending_direction=(int)GlobalVariableGet(PendingKey("direction"));
   g_pending_level=GlobalVariableGet(PendingKey("level"));
   g_pending_vah=GlobalVariableGet(PendingKey("vah"));
   g_pending_val=GlobalVariableGet(PendingKey("val"));
   g_pending_bars_left=(int)GlobalVariableGet(PendingKey("bars"));
   if(g_pending_bars_left<=0 || (g_pending_direction!=1 && g_pending_direction!=-1))
   {
      g_pending_direction=0;
      g_pending_bars_left=0;
   }
}

void ClearPending()
{
   g_pending_direction=0;
   g_pending_level=0.0;
   g_pending_vah=0.0;
   g_pending_val=0.0;
   g_pending_bars_left=0;
   SavePending();
}

double NormalizePrice(const double value)
{
   double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tick_size<=0.0) tick_size=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   return NormalizeDouble(MathRound(value/tick_size)*tick_size,digits);
}

double NormalizeVolume(const double raw)
{
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(minimum<=0.0 || maximum<=0.0 || step<=0.0 || raw<minimum) return 0.0;
   return NormalizeDouble(MathFloor((MathMin(raw,maximum)+1e-12)/step)*step,8);
}

double LotsForRisk(const ENUM_ORDER_TYPE type,const double entry,const double stop)
{
   double one_lot_result=0.0;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,one_lot_result) || MathAbs(one_lot_result)<=0.0)
      return 0.0;
   double risk_cash=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   return NormalizeVolume(risk_cash/MathAbs(one_lot_result));
}

bool SelectOurPosition(ulong &ticket)
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong candidate=PositionGetTicket(i);
      if(candidate>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)
      {
         ticket=candidate;
         return true;
      }
   }
   return false;
}

bool CalculateProfile(const int asof_d1_shift,ProfileLevels &result)
{
   result.valid=false;
   datetime finish=iTime(_Symbol,PERIOD_D1,asof_d1_shift);
   datetime start=iTime(_Symbol,PERIOD_D1,asof_d1_shift+InpProfileLookbackDays);
   if(start<=0 || finish<=start)
   {
      Print("Auction profile unavailable: insufficient D1 history for ",InpProfileLookbackDays," days.");
      return false;
   }

   MqlRates minutes[];
   ArraySetAsSeries(minutes,false);
   int copied=CopyRates(_Symbol,PERIOD_M1,start,finish-1,minutes);
   if(copied<InpProfileLookbackDays*60)
   {
      Print("Auction profile unavailable: only ",copied," M1 bars copied for ",
            TimeToString(start)," to ",TimeToString(finish),".");
      return false;
   }

   double profile_low=minutes[0].low;
   double profile_high=minutes[0].high;
   for(int i=1;i<copied;i++)
   {
      if(minutes[i].low<profile_low) profile_low=minutes[i].low;
      if(minutes[i].high>profile_high) profile_high=minutes[i].high;
   }
   if(profile_high<=profile_low) return false;

   double row_width=(profile_high-profile_low)/InpProfileBins;
   double histogram[];
   ArrayResize(histogram,InpProfileBins);
   ArrayInitialize(histogram,0.0);
   for(int i=0;i<copied;i++)
   {
      int low_bin=(int)MathFloor((minutes[i].low-profile_low)/row_width);
      int high_bin=(int)MathFloor((minutes[i].high-profile_low)/row_width);
      low_bin=(int)MathMax(0,MathMin(InpProfileBins-1,low_bin));
      high_bin=(int)MathMax(0,MathMin(InpProfileBins-1,high_bin));
      if(high_bin<low_bin)
      {
         int temporary=low_bin;
         low_bin=high_bin;
         high_bin=temporary;
      }
      double allocation=(double)MathMax((long)1,minutes[i].tick_volume)/(high_bin-low_bin+1);
      for(int row=low_bin;row<=high_bin;row++) histogram[row]+=allocation;
   }

   int poc_index=0;
   double total=histogram[0];
   for(int row=1;row<InpProfileBins;row++)
   {
      total+=histogram[row];
      if(histogram[row]>histogram[poc_index]) poc_index=row;
   }
   double target_volume=total*InpValueAreaPercent/100.0;
   int low_index=poc_index;
   int high_index=poc_index;
   double included=histogram[poc_index];
   while(included<target_volume && (low_index>0 || high_index<InpProfileBins-1))
   {
      double below=(low_index>0 ? histogram[low_index-1] : -1.0);
      double above=(high_index<InpProfileBins-1 ? histogram[high_index+1] : -1.0);
      if(above>=below && high_index<InpProfileBins-1)
      {
         high_index++;
         included+=histogram[high_index];
      }
      else if(low_index>0)
      {
         low_index--;
         included+=histogram[low_index];
      }
      else break;
   }

   result.poc=profile_low+(poc_index+0.5)*row_width;
   result.val=profile_low+low_index*row_width;
   result.vah=profile_low+(high_index+1.0)*row_width;
   result.asof=finish;
   result.valid=true;
   return true;
}

void DrawLevel(const string suffix,const double price,const color line_color,const ENUM_LINE_STYLE style)
{
   string name="AAA_AMVA_"+IntegerToString(InpMagic)+"_"+suffix;
   if(ObjectFind(0,name)<0) ObjectCreate(0,name,OBJ_HLINE,0,0,price);
   ObjectSetDouble(0,name,OBJPROP_PRICE,price);
   ObjectSetInteger(0,name,OBJPROP_COLOR,line_color);
   ObjectSetInteger(0,name,OBJPROP_STYLE,style);
   ObjectSetInteger(0,name,OBJPROP_WIDTH,1);
   ObjectSetString(0,name,OBJPROP_TEXT,"Auction "+suffix);
}

void DrawProfile()
{
   if(!InpDrawProfile || !g_profile.valid) return;
   DrawLevel("POC",g_profile.poc,clrGold,STYLE_SOLID);
   DrawLevel("VAH",g_profile.vah,clrLimeGreen,STYLE_DASH);
   DrawLevel("VAL",g_profile.val,clrTomato,STYLE_DASH);
   ChartRedraw();
}

bool UpdateProfileForClosedBar(const datetime closed_bar_time)
{
   int asof_shift=iBarShift(_Symbol,PERIOD_D1,closed_bar_time,false);
   if(asof_shift<0) return false;
   datetime asof=iTime(_Symbol,PERIOD_D1,asof_shift);
   if(g_cached_profile_asof==asof && g_profile.valid && g_previous_profile.valid) return true;

   ProfileLevels current,previous;
   if(!CalculateProfile(asof_shift,current)) return false;
   if(!CalculateProfile(asof_shift+InpShiftLagDays,previous)) return false;
   g_profile=current;
   g_previous_profile=previous;
   g_cached_profile_asof=asof;
   DrawProfile();
   Print("Auction profile ",_Symbol," as of ",TimeToString(asof,TIME_DATE),
         ": VAL=",DoubleToString(g_profile.val,_Digits),
         " POC=",DoubleToString(g_profile.poc,_Digits),
         " VAH=",DoubleToString(g_profile.vah,_Digits));
   return true;
}

double ClosedATR()
{
   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   int needed=InpATRPeriod+1;
   if(CopyRates(_Symbol,InpSignalTimeframe,1,needed,bars)!=needed) return 0.0;
   double total=0.0;
   for(int i=0;i<InpATRPeriod;i++)
   {
      double range=bars[i].high-bars[i].low;
      double high_gap=MathAbs(bars[i].high-bars[i+1].close);
      double low_gap=MathAbs(bars[i].low-bars[i+1].close);
      total+=MathMax(range,MathMax(high_gap,low_gap));
   }
   return total/InpATRPeriod;
}

bool RegimeAllows(const int direction,const double atr)
{
   double shift=g_profile.poc-g_previous_profile.poc;
   if(InpRegimeMode==REGIME_MIGRATING_VALUE)
      return direction*shift>0.0 && direction*shift>=InpShiftThresholdATR*atr;
   return MathAbs(shift)<=InpShiftThresholdATR*atr;
}

bool BrokerDistancesValid(const int direction,const double entry,const double stop,const double target)
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double broker_min=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point;
   double practical_min=MathMax(broker_min,2.0*(tick.ask-tick.bid));
   if(direction>0)
      return stop<entry-practical_min && target>entry+practical_min;
   return stop>entry+practical_min && target<entry-practical_min;
}

bool OpenTrade(const int direction,const double stop_reference,const double exact_target,const double atr)
{
   if(!InpEnableTrading) return false;
   if(InpLongOnly && direction<0) return false;
   ulong existing=0;
   if(SelectOurPosition(existing)) return false;

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double spread=tick.ask-tick.bid;
   if(InpMaximumSpreadPrice>0.0 && spread>InpMaximumSpreadPrice)
   {
      Print("Auction entry skipped: spread ",DoubleToString(spread,_Digits)," exceeds limit.");
      return false;
   }

   double entry=(direction>0 ? tick.ask : tick.bid);
   double stop=NormalizePrice(stop_reference-direction*InpStopBufferATR*atr);
   double distance=(direction>0 ? entry-stop : stop-entry);
   if(distance<=0.0) return false;
   double target=exact_target;
   if(InpModel==MODEL_BREAKOUT_RETEST)
      target=entry+direction*InpRewardRisk*distance;
   else
   {
      double available_rr=direction*(target-entry)/distance;
      if(available_rr<InpMinimumRewardRisk)
      {
         Print("Auction failed-auction entry skipped: available RR ",DoubleToString(available_rr,2),
               " is below ",DoubleToString(InpMinimumRewardRisk,2),".");
         return false;
      }
   }
   target=NormalizePrice(target);
   if(!BrokerDistancesValid(direction,entry,stop,target))
   {
      Print("Auction entry skipped: live spread or broker stop level makes SL/TP invalid.");
      return false;
   }

   ENUM_ORDER_TYPE order_type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=LotsForRisk(order_type,entry,stop);
   if(lots<=0.0)
   {
      Print("Auction entry skipped: 1% risk volume is below broker minimum or contract data is unavailable.");
      return false;
   }

   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetDeviationInPoints(InpMaxDeviationPoints);
   string comment=(InpModel==MODEL_FAILED_AUCTION ? "Auction failed auction" : "Auction breakout retest");
   bool sent=(direction>0
      ? g_trade.Buy(lots,_Symbol,0.0,stop,target,comment+" BUY")
      : g_trade.Sell(lots,_Symbol,0.0,stop,target,comment+" SELL"));
   if(!sent)
   {
      Print("Auction entry failed: ",g_trade.ResultRetcode()," ",g_trade.ResultRetcodeDescription());
      return false;
   }
   Print("Auction trade opened: ",(direction>0 ? "BUY " : "SELL "),_Symbol,
         " lots=",DoubleToString(lots,8)," SL=",DoubleToString(stop,_Digits),
         " TP=",DoubleToString(target,_Digits)," risk=",DoubleToString(InpRiskPercent,2),"%.");
   return true;
}

void ManagePosition()
{
   ulong ticket=0;
   if(!SelectOurPosition(ticket) || !PositionSelectByTicket(ticket)) return;
   datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
   int elapsed_market_minutes=Bars(_Symbol,PERIOD_M1,opened,TimeCurrent());
   if(InpMaximumHoldHours>0 && elapsed_market_minutes>=InpMaximumHoldHours*60)
   {
      if(!g_trade.PositionClose(ticket,(ulong)InpMaxDeviationPoints))
         Print("Auction time exit failed: ",g_trade.ResultRetcode()," ",g_trade.ResultRetcodeDescription());
      return;
   }
   if(!InpBreakEvenAtOneR) return;

   double open=PositionGetDouble(POSITION_PRICE_OPEN);
   double stop=PositionGetDouble(POSITION_SL);
   double target=PositionGetDouble(POSITION_TP);
   long type=PositionGetInteger(POSITION_TYPE);
   bool stop_not_at_be=(type==POSITION_TYPE_BUY ? stop<open : stop>open);
   if(!stop_not_at_be) return;
   double initial_risk=MathAbs(open-stop);
   if(initial_risk<=0.0) return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   bool reached=(type==POSITION_TYPE_BUY ? tick.bid-open>=initial_risk : open-tick.ask>=initial_risk);
   if(reached && !g_trade.PositionModify(ticket,NormalizePrice(open),target))
      Print("Auction break-even move failed: ",g_trade.ResultRetcode()," ",g_trade.ResultRetcodeDescription());
}

void EvaluateFailedAuction(const MqlRates &closed,const double atr)
{
   double tolerance=InpEntryToleranceATR*atr;
   if(RegimeAllows(1,atr) && closed.low<g_profile.val && closed.close>=g_profile.val+tolerance)
   {
      if(OpenTrade(1,closed.low,g_profile.vah,atr)) return;
   }
   if(!InpLongOnly && RegimeAllows(-1,atr) && closed.high>g_profile.vah && closed.close<=g_profile.vah-tolerance)
      OpenTrade(-1,closed.high,g_profile.val,atr);
}

bool ProcessPendingRetest(const MqlRates &closed,const double atr)
{
   if(g_pending_direction==0 || g_pending_bars_left<=0) return false;
   double tolerance=InpEntryToleranceATR*atr;
   bool invalid=(g_pending_direction>0 ? closed.close<g_pending_val : closed.close>g_pending_vah);
   if(invalid)
   {
      ClearPending();
      return false;
   }
   bool accepted=(g_pending_direction>0
      ? closed.low<=g_pending_level+tolerance && closed.close>g_pending_level
      : closed.high>=g_pending_level-tolerance && closed.close<g_pending_level);
   if(accepted)
   {
      int direction=g_pending_direction;
      double stop_reference=(direction>0 ? closed.low : closed.high);
      ClearPending();
      return OpenTrade(direction,stop_reference,0.0,atr);
   }
   g_pending_bars_left--;
   if(g_pending_bars_left<=0) ClearPending();
   else SavePending();
   return false;
}

void DetectBreakout(const MqlRates &closed,const MqlRates &previous,const double atr)
{
   double tolerance=InpEntryToleranceATR*atr;
   if(RegimeAllows(1,atr) && closed.close>g_profile.vah+tolerance && previous.close<=g_profile.vah+tolerance)
   {
      g_pending_direction=1;
      g_pending_level=g_profile.vah;
   }
   else if(!InpLongOnly && RegimeAllows(-1,atr) && closed.close<g_profile.val-tolerance && previous.close>=g_profile.val-tolerance)
   {
      g_pending_direction=-1;
      g_pending_level=g_profile.val;
   }
   else return;
   g_pending_vah=g_profile.vah;
   g_pending_val=g_profile.val;
   g_pending_bars_left=InpRetestExpiryBars;
   SavePending();
   Print("Auction breakout armed: ",(g_pending_direction>0 ? "LONG " : "SHORT "),_Symbol,
         " retest level=",DoubleToString(g_pending_level,_Digits),
         " expiry bars=",g_pending_bars_left,".");
}

void EvaluateEntry()
{
   ulong ticket=0;
   if(SelectOurPosition(ticket)) return;
   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   if(CopyRates(_Symbol,InpSignalTimeframe,1,2,bars)!=2) return;
   double atr=ClosedATR();
   if(atr<=0.0) return;
   if(!UpdateProfileForClosedBar(bars[0].time)) return;

   if(InpModel==MODEL_FAILED_AUCTION)
      EvaluateFailedAuction(bars[0],atr);
   else
   {
      if(ProcessPendingRetest(bars[0],atr)) return;
      if(g_pending_direction==0) DetectBreakout(bars[0],bars[1],atr);
   }
}

bool NewSignalBar()
{
   datetime current=iTime(_Symbol,InpSignalTimeframe,0);
   if(current<=0 || current==g_last_signal_bar) return false;
   g_last_signal_bar=current;
   return true;
}

int OnInit()
{
   if(InpRiskPercent<=0.0 || InpRiskPercent>5.0 || InpMagic<=0 ||
      (InpSignalTimeframe!=PERIOD_H4 && InpSignalTimeframe!=PERIOD_D1) ||
      InpProfileLookbackDays<5 || InpProfileBins<16 || InpProfileBins>256 ||
      InpValueAreaPercent<50.0 || InpValueAreaPercent>95.0 || InpShiftLagDays<1 ||
      InpShiftThresholdATR<0.0 || InpEntryToleranceATR<0.0 || InpATRPeriod<2 ||
      InpStopBufferATR<0.0 || InpMaximumHoldHours<1 ||
      (InpModel==MODEL_BREAKOUT_RETEST && InpRetestExpiryBars<1) ||
      (InpModel==MODEL_BREAKOUT_RETEST && InpRewardRisk<=0.0) ||
      (InpModel==MODEL_FAILED_AUCTION && InpMinimumRewardRisk<=0.0))
      return INIT_PARAMETERS_INCORRECT;

   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetDeviationInPoints(InpMaxDeviationPoints);
   g_last_signal_bar=iTime(_Symbol,InpSignalTimeframe,0);
   LoadPending();
   if(!InpEnableTrading)
      Print("Auction Market EA loaded with trading disabled.");
   else
      Print("Auction Market EA active on ",_Symbol," at 1% preset risk. Research deployment was user-approved despite the 15% CAGR gate not passing.");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   SavePending();
}

void OnTick()
{
   ManagePosition();
   if(!InpEnableTrading) return;
   if(NewSignalBar()) EvaluateEntry();
}

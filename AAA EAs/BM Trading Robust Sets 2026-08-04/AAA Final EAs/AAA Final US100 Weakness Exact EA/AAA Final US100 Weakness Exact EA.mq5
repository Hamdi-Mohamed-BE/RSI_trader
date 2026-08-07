#property copyright "Exact MT5 implementation of the supplied US100 weakness setup"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

enum ENUM_REBOUND_CONFIRMATION
{
   REBOUND_CLOSE_ABOVE_REFERENCE_OPEN=0,
   REBOUND_CLOSE_ABOVE_REFERENCE_HIGH=1
};

input group "New York setup"
input bool   InpEnableTrading=false; // Research gate: load the tested set to enable manually
input int    InpReferenceHour=9;
input int    InpReferenceMinute=30;
input int    InpLastEntryHour=16;
input int    InpLastEntryMinute=0;
input ENUM_REBOUND_CONFIRMATION InpReboundConfirmation=REBOUND_CLOSE_ABOVE_REFERENCE_OPEN;
input bool   InpRequireBullishReboundCandle=true;
input int    InpEntryOffsetTicks=0;

input group "Bracket shown in the example"
input double InpReferenceTickSize=0.1; // TradingView example: 600 ticks = 60.0 index points
input int    InpStopLossTicks=600;
input int    InpTakeProfitTicks=1000;

input group "Two-leg management"
input double InpTotalRiskPercent=1.0;
input double InpRunnerPartialClosePercent=20.0;
input int    InpTrailingBufferTicks=0;
input bool   InpTrailOnlyAfterFixedTarget=true;

input group "Execution"
input long   InpMagicFixedLeg=84081620;
input long   InpMagicRunnerLeg=84081621;
input int    InpMaxSpreadPoints=0;
input int    InpMaxDeviationPoints=30;

input group "Broker clock"
input bool   InpUseAutomaticLiveServerOffset=true;
input int    InpTesterServerUTCOffsetHours=0; // Exness USTEC history uses UTC bars
input int    InpManualLiveServerUTCOffsetHours=0;

CTrade trade;
datetime g_last_m15_bar=0;
bool g_runner_trailing_active=false;
bool g_runner_partial_processed=false;

int DaysInMonth(const int year,const int month)
{
   if(month==2) return (((year%4==0 && year%100!=0) || year%400==0) ? 29 : 28);
   if(month==4 || month==6 || month==9 || month==11) return 30;
   return 31;
}

int NthSunday(const int year,const int month,const int occurrence)
{
   MqlDateTime p={0};
   p.year=year; p.mon=month; p.day=1; p.hour=12;
   datetime first=StructToTime(p);
   TimeToStruct(first,p);
   return 1+((7-p.day_of_week)%7)+(occurrence-1)*7;
}

int NewYorkUTCOffsetHours(const datetime utc_time)
{
   MqlDateTime p; TimeToStruct(utc_time,p);
   MqlDateTime start={0},finish={0};
   start.year=p.year; start.mon=3; start.day=NthSunday(p.year,3,2); start.hour=7;
   finish.year=p.year; finish.mon=11; finish.day=NthSunday(p.year,11,1); finish.hour=6;
   return (utc_time>=StructToTime(start) && utc_time<StructToTime(finish) ? -4 : -5);
}

int ServerUTCOffsetSeconds()
{
   if((bool)MQLInfoInteger(MQL_TESTER)) return InpTesterServerUTCOffsetHours*3600;
   if(!InpUseAutomaticLiveServerOffset) return InpManualLiveServerUTCOffsetHours*3600;
   datetime server=TimeTradeServer();
   if(server<=0) server=TimeCurrent();
   datetime utc=TimeGMT();
   if(utc<=0) return InpManualLiveServerUTCOffsetHours*3600;
   return (int)MathRound((double)(server-utc)/1800.0)*1800;
}

datetime ServerToNewYork(const datetime server_time)
{
   datetime utc=server_time-ServerUTCOffsetSeconds();
   return utc+NewYorkUTCOffsetHours(utc)*3600;
}

bool NewYorkDateUsesDST(const MqlDateTime &ny)
{
   int march=NthSunday(ny.year,3,2),november=NthSunday(ny.year,11,1);
   if(ny.mon>3 && ny.mon<11) return true;
   if(ny.mon<3 || ny.mon>11) return false;
   if(ny.mon==3) return ny.day>=march;
   return ny.day<november;
}

datetime NewYorkToServer(const MqlDateTime &source)
{
   MqlDateTime ny=source;
   int ny_offset=(NewYorkDateUsesDST(ny) ? -4 : -5);
   datetime utc=StructToTime(ny)-ny_offset*3600;
   return utc+ServerUTCOffsetSeconds();
}

int DateKey(const MqlDateTime &p)
{
   return p.year*10000+p.mon*100+p.day;
}

double PriceToTick(const double value,const int rounding=0)
{
   double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tick<=0.0) tick=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(tick<=0.0) return value;
   double units=value/tick;
   if(rounding<0) units=MathFloor(units+1e-9);
   else if(rounding>0) units=MathCeil(units-1e-9);
   else units=MathRound(units);
   return NormalizeDouble(units*tick,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

double NormalizeVolume(const double raw)
{
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(minimum<=0.0 || maximum<=0.0 || step<=0.0 || raw<minimum) return 0.0;
   double lots=MathFloor((MathMin(raw,maximum)+1e-12)/step)*step;
   return NormalizeDouble(lots,8);
}

double LotsForLegRisk(const double entry,const double stop)
{
   double one_lot=0.0;
   if(!OrderCalcProfit(ORDER_TYPE_SELL,_Symbol,1.0,entry,stop,one_lot)) return 0.0;
   double loss=MathAbs(one_lot);
   if(loss<=0.0) return 0.0;
   double risk_cash=AccountInfoDouble(ACCOUNT_EQUITY)*InpTotalRiskPercent/200.0;
   return NormalizeVolume(risk_cash/loss);
}

bool SpreadOK()
{
   if(InpMaxSpreadPoints<=0) return true;
   MqlTick tick;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   return SymbolInfoTick(_Symbol,tick) && point>0.0 && (tick.ask-tick.bid)/point<=InpMaxSpreadPoints;
}

bool SelectPositionByMagic(const long magic,ulong &ticket,datetime &opened)
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong candidate=PositionGetTicket(i);
      if(candidate==0) continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==magic)
      {
         ticket=candidate;
         opened=(datetime)PositionGetInteger(POSITION_TIME);
         return true;
      }
   }
   return false;
}

bool HasOrderByMagic(const long magic)
{
   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      ulong ticket=OrderGetTicket(i);
      if(ticket==0) continue;
      if(OrderGetString(ORDER_SYMBOL)==_Symbol && OrderGetInteger(ORDER_MAGIC)==magic) return true;
   }
   return false;
}

bool HasAnyExposure()
{
   ulong ticket=0; datetime opened=0;
   return SelectPositionByMagic(InpMagicFixedLeg,ticket,opened) ||
          SelectPositionByMagic(InpMagicRunnerLeg,ticket,opened) ||
          HasOrderByMagic(InpMagicFixedLeg) || HasOrderByMagic(InpMagicRunnerLeg);
}

bool SetupAlreadyAttemptedToday(const MqlDateTime &now_ny)
{
   MqlDateTime start=now_ny;
   start.hour=0; start.min=0; start.sec=0;
   datetime from=NewYorkToServer(start);
   if(!HistorySelect(from,TimeCurrent())) return false;
   for(int i=HistoryOrdersTotal()-1;i>=0;i--)
   {
      ulong ticket=HistoryOrderGetTicket(i);
      if(ticket==0 || HistoryOrderGetString(ticket,ORDER_SYMBOL)!=_Symbol) continue;
      long magic=HistoryOrderGetInteger(ticket,ORDER_MAGIC);
      if(magic==InpMagicFixedLeg || magic==InpMagicRunnerLeg) return true;
   }
   return false;
}

void DeleteOrderTicket(const ulong ticket)
{
   if(ticket==0) return;
   trade.OrderDelete(ticket);
}

bool FixedTargetHitAfter(const datetime runner_open_time)
{
   if(!HistorySelect(runner_open_time-60,TimeCurrent())) return false;
   for(int i=HistoryDealsTotal()-1;i>=0;i--)
   {
      ulong deal=HistoryDealGetTicket(i);
      if(deal==0 || HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol) continue;
      if(HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagicFixedLeg) continue;
      long entry=HistoryDealGetInteger(deal,DEAL_ENTRY);
      if(entry!=DEAL_ENTRY_OUT && entry!=DEAL_ENTRY_INOUT) continue;
      return HistoryDealGetInteger(deal,DEAL_REASON)==DEAL_REASON_TP;
   }
   return false;
}

bool RunnerAlreadyPartiallyClosed(const ulong runner_ticket)
{
   if(!PositionSelectByTicket(runner_ticket)) return false;
   long identifier=PositionGetInteger(POSITION_IDENTIFIER);
   if(identifier<=0 || !HistorySelectByPosition((ulong)identifier)) return false;
   for(int i=0;i<HistoryDealsTotal();i++)
   {
      ulong deal=HistoryDealGetTicket(i);
      if(deal==0 || HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagicRunnerLeg) continue;
      long entry=HistoryDealGetInteger(deal,DEAL_ENTRY);
      if(entry==DEAL_ENTRY_OUT || entry==DEAL_ENTRY_INOUT) return true;
   }
   return false;
}

void ActivateAndScaleRunner(const ulong runner_ticket)
{
   g_runner_trailing_active=true;
   if(g_runner_partial_processed || RunnerAlreadyPartiallyClosed(runner_ticket))
   {
      g_runner_partial_processed=true;
      return;
   }
   if(!PositionSelectByTicket(runner_ticket)) return;
   double current=PositionGetDouble(POSITION_VOLUME);
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double partial=NormalizeVolume(current*InpRunnerPartialClosePercent/100.0);
   if(partial<minimum || current-partial<minimum)
   {
      Print("Runner 20% scale-out skipped because it is below the broker minimum; trailing remains active.");
      g_runner_partial_processed=true;
      return;
   }
   trade.SetExpertMagicNumber((ulong)InpMagicRunnerLeg);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(InpMaxDeviationPoints);
   if(trade.PositionClosePartial(runner_ticket,partial,InpMaxDeviationPoints))
      g_runner_partial_processed=true;
   else
      Print("Runner partial close failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
}

void TrailRunnerOnClosedCandle(const ulong runner_ticket)
{
   if(!PositionSelectByTicket(runner_ticket)) return;
   MqlRates closed[];
   ArraySetAsSeries(closed,true);
   if(CopyRates(_Symbol,PERIOD_M15,1,1,closed)!=1) return;
   double buffer=InpTrailingBufferTicks*InpReferenceTickSize;
   double candidate=PriceToTick(closed[0].high+buffer,1);
   double current_sl=PositionGetDouble(POSITION_SL);
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double minimum_distance=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point;
   if(candidate<=tick.ask+minimum_distance) return;
   if(current_sl>0.0 && candidate>=current_sl-SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE)) return;
   trade.SetExpertMagicNumber((ulong)InpMagicRunnerLeg);
   trade.SetTypeFillingBySymbol(_Symbol);
   if(!trade.PositionModify(runner_ticket,candidate,0.0))
      Print("Runner trailing stop failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
}

void ManageRunner(const bool new_m15_bar)
{
   ulong runner=0,fixed=0; datetime runner_opened=0,fixed_opened=0;
   bool has_runner=SelectPositionByMagic(InpMagicRunnerLeg,runner,runner_opened);
   bool has_fixed=SelectPositionByMagic(InpMagicFixedLeg,fixed,fixed_opened);
   if(!has_runner)
   {
      g_runner_trailing_active=false;
      g_runner_partial_processed=false;
      return;
   }
   if(!InpTrailOnlyAfterFixedTarget)
      g_runner_trailing_active=true;
   else if(!has_fixed && FixedTargetHitAfter(runner_opened))
      ActivateAndScaleRunner(runner);
   if(g_runner_trailing_active && new_m15_bar) TrailRunnerOnClosedCandle(runner);
}

bool GetReferenceCandle(const MqlDateTime &now_ny,MqlRates &reference)
{
   MqlDateTime p=now_ny;
   p.hour=InpReferenceHour; p.min=InpReferenceMinute; p.sec=0;
   datetime start=NewYorkToServer(p);
   MqlRates rates[];
   int count=CopyRates(_Symbol,PERIOD_M15,start,start+14*60+59,rates);
   if(count!=1) return false;
   reference=rates[0];
   return true;
}

bool PlaceTwoSellStops(const MqlRates &reference,const MqlDateTime &now_ny)
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || !SpreadOK()) return false;
   double entry=PriceToTick(reference.low-InpEntryOffsetTicks*InpReferenceTickSize,-1);
   double stop=PriceToTick(entry+InpStopLossTicks*InpReferenceTickSize,1);
   double target=PriceToTick(entry-InpTakeProfitTicks*InpReferenceTickSize,-1);
   if(entry<=0.0 || stop<=entry || target>=entry || tick.bid<=entry) return false;
   double minimum_distance=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(tick.bid-entry<minimum_distance) return false;
   double lots=LotsForLegRisk(entry,stop);
   if(lots<=0.0)
   {
      Print("Two-leg size is below the broker minimum or contract data is unavailable.");
      return false;
   }
   MqlDateTime expiry_ny=now_ny;
   expiry_ny.hour=InpLastEntryHour; expiry_ny.min=InpLastEntryMinute; expiry_ny.sec=0;
   datetime expiry=NewYorkToServer(expiry_ny);
   if(expiry<=TimeCurrent()) return false;

   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(InpMaxDeviationPoints);
   trade.SetExpertMagicNumber((ulong)InpMagicFixedLeg);
   bool fixed_ok=trade.SellStop(lots,entry,_Symbol,stop,target,ORDER_TIME_SPECIFIED,expiry,"US100 weakness fixed");
   ulong fixed_ticket=(fixed_ok ? trade.ResultOrder() : 0);
   if(!fixed_ok)
   {
      Print("Fixed sell stop failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
      return false;
   }
   trade.SetExpertMagicNumber((ulong)InpMagicRunnerLeg);
   bool runner_ok=trade.SellStop(lots,entry,_Symbol,stop,0.0,ORDER_TIME_SPECIFIED,expiry,"US100 weakness runner");
   if(!runner_ok)
   {
      Print("Runner sell stop failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
      DeleteOrderTicket(fixed_ticket);
      return false;
   }
   return true;
}

void EvaluateSetupOnNewBar()
{
   if(!InpEnableTrading || HasAnyExposure()) return;
   datetime now_server=TimeCurrent();
   MqlDateTime now_ny; TimeToStruct(ServerToNewYork(now_server),now_ny);
   if(now_ny.day_of_week<1 || now_ny.day_of_week>5) return;
   int now_minute=now_ny.hour*60+now_ny.min;
   int first_confirmation=(InpReferenceHour*60+InpReferenceMinute)+30;
   int last_entry=InpLastEntryHour*60+InpLastEntryMinute;
   if(now_minute<first_confirmation || now_minute>=last_entry) return;
   if(SetupAlreadyAttemptedToday(now_ny)) return;

   MqlRates reference;
   if(!GetReferenceCandle(now_ny,reference) || reference.close>=reference.open) return;
   MqlRates rebound[];
   ArraySetAsSeries(rebound,true);
   if(CopyRates(_Symbol,PERIOD_M15,1,1,rebound)!=1) return;
   MqlDateTime rebound_ny; TimeToStruct(ServerToNewYork(rebound[0].time),rebound_ny);
   int rebound_minute=rebound_ny.hour*60+rebound_ny.min;
   if(rebound_minute<InpReferenceHour*60+InpReferenceMinute+15) return;
   if(InpRequireBullishReboundCandle && rebound[0].close<=rebound[0].open) return;
   double confirmation=(InpReboundConfirmation==REBOUND_CLOSE_ABOVE_REFERENCE_HIGH ? reference.high : reference.open);
   if(rebound[0].close<=confirmation) return;
   PlaceTwoSellStops(reference,now_ny);
}

int OnInit()
{
   if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)
   {
      Print("This exact two-leg EA requires a hedging account.");
      return INIT_FAILED;
   }
   if(InpTotalRiskPercent<=0.0 || InpTotalRiskPercent>5.0 || InpReferenceTickSize<=0.0 ||
      InpStopLossTicks<=0 || InpTakeProfitTicks<=0 || InpRunnerPartialClosePercent<0.0 ||
      InpRunnerPartialClosePercent>=100.0 || InpMagicFixedLeg==InpMagicRunnerLeg)
      return INIT_PARAMETERS_INCORRECT;
   g_last_m15_bar=iTime(_Symbol,PERIOD_M15,0);
   return INIT_SUCCEEDED;
}

void OnTick()
{
   datetime current=iTime(_Symbol,PERIOD_M15,0);
   bool new_bar=(current>0 && current!=g_last_m15_bar);
   if(new_bar) g_last_m15_bar=current;
   ManageRunner(new_bar);
   if(new_bar) EvaluateSetupOnNewBar();
}

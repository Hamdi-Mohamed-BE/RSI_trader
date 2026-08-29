#property copyright "AAA Final News Pulse - NFP/CPI/FOMC straddle"
#property version   "2.11"
#property strict

#include "AAA_Final_Common.mqh"
#include "SafeRegimeFilter.mqh"

input group "Trading"
input bool   InpEnableTrading=true;
input bool   InpEnableBuySide=true;
input bool   InpEnableSellSide=true;
input double InpRiskPercent=1.0;              // risk per triggered trade on each enabled side
input long   InpMagic=860301;
input int    InpMaxDeviationPoints=100;

input group "Events"
input bool   InpUseEconomicCalendar=true;
input bool   InpWatchNFP=true;
input bool   InpWatchCPI=true;
input bool   InpWatchFOMC=true;
input int    InpPlacementLeadSeconds=60;       // place the straddle this many seconds before release
input int    InpMaxQuoteAgeSeconds=5;           // require a fresh broker-stamped quote before placement
input int    InpCalendarLookaheadDays=8;        // cache upcoming target events ahead of the release
input int    InpCalendarRefreshSeconds=300;     // refresh cached server-time event schedule

input group "Order geometry - symbol price units"
input double InpEntryOffsetPrice=12.0;         // buy above Ask / sell below Bid
input double InpStopLossPrice=10.0;            // one R
input double InpTrailStartR=3.0;               // start trailing after +3R
input double InpTrailDistancePrice=10.0;        // trail one R behind current price
input int    InpForceCloseSecondsAfterEvent=120;

input group "Tester"
input int    InpTesterServerClockMode=0;        // 0 = Exness tester timestamps are UTC; live uses calendar server time

datetime g_active_event_time=0;
long     g_last_event_id=0;
string   g_active_state_key="";
string   g_last_state_key="";
datetime g_last_calendar_warning=0;
datetime g_last_quote_warning=0;
long     g_attempt_event_id=0;
datetime g_last_placement_attempt=0;
double   g_event_buy_entry=0.0;
double   g_event_sell_entry=0.0;
double   g_event_max_ask=-DBL_MAX;
double   g_event_min_bid=DBL_MAX;
datetime g_last_broker_quote_time=0;
long     g_last_broker_tick_msc=0;
ulong    g_last_quote_arrival_ms=0;
datetime g_cached_event_time=0;
long     g_cached_event_id=0;
string   g_cached_event_kind="";
ulong    g_last_calendar_refresh_ms=0;

void NP_RecordBrokerQuote()
{
   if((bool)MQLInfoInteger(MQL_TESTER)) return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.time<=0) return;
   if(tick.time_msc==g_last_broker_tick_msc && tick.time==g_last_broker_quote_time) return;
   g_last_broker_tick_msc=tick.time_msc;
   g_last_broker_quote_time=tick.time;
   g_last_quote_arrival_ms=GetTickCount64();
}

datetime NP_ServerNow()
{
   if((bool)MQLInfoInteger(MQL_TESTER)) return TimeCurrent();
   if(g_last_broker_quote_time>0 && g_last_quote_arrival_ms>0)
      return g_last_broker_quote_time+(datetime)((GetTickCount64()-g_last_quote_arrival_ms)/1000);
   // TimeCurrent is the last known broker-server quote time and does not use
   // the VPS local timezone. It is only a startup fallback until the first tick.
   return TimeCurrent();
}

bool NP_GetFreshBrokerPlacementTime(datetime &server_now)
{
   if((bool)MQLInfoInteger(MQL_TESTER))
   {
      server_now=TimeCurrent();
      return server_now>0;
   }

   MqlTick tick;
   if(!(bool)TerminalInfoInteger(TERMINAL_CONNECTED) || !SymbolInfoTick(_Symbol,tick) ||
      tick.time<=0 || g_last_quote_arrival_ms==0)
   {
      datetime warn_now=NP_ServerNow();
      if(warn_now-g_last_quote_warning>=60)
      {
         Print("News Pulse: placement blocked because a fresh broker-stamped quote or connection is unavailable.");
         g_last_quote_warning=warn_now;
      }
      return false;
   }

   ulong age_ms=GetTickCount64()-g_last_quote_arrival_ms;
   if(age_ms>(ulong)InpMaxQuoteAgeSeconds*1000)
   {
      datetime warn_now=NP_ServerNow();
      if(warn_now-g_last_quote_warning>=60)
      {
         Print("News Pulse: placement blocked; broker quote age is ",DoubleToString((double)age_ms/1000.0,1),
               "s (maximum ",InpMaxQuoteAgeSeconds,"s). Waiting for a fresh ",_Symbol," tick.");
         g_last_quote_warning=warn_now;
      }
      return false;
   }

   // The broker stamps tick.time in the same server-time basis used by MT5's
   // economic calendar. VPS local time, timezone and daylight saving are ignored.
   server_now=tick.time;
   return true;
}

string NP_StateKey(const string suffix)
{
   return "AAA_NP_"+IntegerToString((long)AccountInfoInteger(ACCOUNT_LOGIN))+"_"+
          IntegerToString(InpMagic)+"_"+_Symbol+"_"+suffix;
}

void NP_SaveState()
{
   if(g_active_event_time>0) GlobalVariableSet(g_active_state_key,(double)g_active_event_time);
   else if(GlobalVariableCheck(g_active_state_key)) GlobalVariableDel(g_active_state_key);
   if(g_last_event_id>0) GlobalVariableSet(g_last_state_key,(double)g_last_event_id);
}

bool NP_IsOurPositionSelected()
{
   return PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic;
}

bool NP_IsOurOrderSelected()
{
   return OrderGetString(ORDER_SYMBOL)==_Symbol && OrderGetInteger(ORDER_MAGIC)==InpMagic;
}

datetime NP_EventTimeFromComment(const string comment)
{
   if(StringFind(comment,"NP|")!=0) return 0;
   int separator=StringFind(comment,"|",3);
   if(separator<0) return 0;
   return (datetime)StringToInteger(StringSubstr(comment,3,separator-3));
}

void NP_RecoverActiveEvent()
{
   if(g_active_event_time>0) return;
   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      if(OrderGetTicket(i)==0 || !NP_IsOurOrderSelected()) continue;
      datetime recovered=NP_EventTimeFromComment(OrderGetString(ORDER_COMMENT));
      if(recovered>0) { g_active_event_time=recovered; NP_SaveState(); return; }
   }
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      if(PositionGetTicket(i)==0 || !NP_IsOurPositionSelected()) continue;
      datetime recovered=NP_EventTimeFromComment(PositionGetString(POSITION_COMMENT));
      if(recovered>0) { g_active_event_time=recovered; NP_SaveState(); return; }
   }
}

void NP_DeletePendingOrders()
{
   AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);
   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      ulong ticket=OrderGetTicket(i);
      if(ticket==0 || !NP_IsOurOrderSelected()) continue;
      if(!AAA_Trade.OrderDelete(ticket))
         Print("News Pulse: could not delete pending order ",ticket,": ",AAA_Trade.ResultRetcodeDescription());
   }
}

void NP_ClosePositions()
{
   AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);
   AAA_Trade.SetDeviationInPoints(InpMaxDeviationPoints);
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !NP_IsOurPositionSelected()) continue;
      if(!AAA_Trade.PositionClose(ticket,(ulong)InpMaxDeviationPoints))
         Print("News Pulse: could not close position ",ticket,": ",AAA_Trade.ResultRetcodeDescription());
   }
}

void NP_TrailPositions()
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double broker_gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                             (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
   double trail_gap=MathMax(InpTrailDistancePrice,broker_gap);
   AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);

   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !NP_IsOurPositionSelected()) continue;
      long type=PositionGetInteger(POSITION_TYPE);
      double open=PositionGetDouble(POSITION_PRICE_OPEN);
      double current_sl=PositionGetDouble(POSITION_SL);
      double current_tp=PositionGetDouble(POSITION_TP);
      bool buy=(type==POSITION_TYPE_BUY);
      double exit_price=(buy ? tick.bid : tick.ask);
      double favorable=(buy ? exit_price-open : open-exit_price);
      if(favorable+point<InpTrailStartR*InpStopLossPrice) continue;

      double candidate=AAA_Price(_Symbol,(buy ? exit_price-trail_gap : exit_price+trail_gap));
      bool improves=(buy ? (candidate>current_sl+point && candidate<tick.bid-broker_gap+point)
                         : ((current_sl<=0.0 || candidate<current_sl-point) && candidate>tick.ask+broker_gap-point));
      if(improves && !AAA_Trade.PositionModify(ticket,candidate,current_tp))
         Print("News Pulse: trailing-stop update failed for ",ticket,": ",AAA_Trade.ResultRetcodeDescription());
   }
}

bool NP_DateInList(const int key,const int &dates[])
{
   for(int i=0;i<ArraySize(dates);i++) if(dates[i]==key) return true;
   return false;
}

void NP_ConsiderTesterEvent(const bool enabled,const bool date_match,const int hour,const int minute,
                            const string kind,const datetime now,const MqlDateTime &ny,
                            datetime &best_time,string &best_kind)
{
   if(!enabled || !date_match) return;
   MqlDateTime release=ny;
   release.hour=hour; release.min=minute; release.sec=0;
   datetime candidate=AAA_NewYorkToServer(StructToTime(release));
   if(candidate<=now || candidate>now+InpPlacementLeadSeconds) return;
   if(best_time==0 || candidate<best_time) { best_time=candidate; best_kind=kind; }
}

bool NP_FindTesterEvent(datetime &event_time,long &event_id,string &kind)
{
   // MT5's economic calendar is unavailable in the Strategy Tester. These are
   // official release/decision dates covering the portfolio's current test year.
   int nfp_dates[]={20250905,20251120,20251216,20260109,20260211,20260306,
                    20260403,20260508,20260605,20260702,20260807};
   int cpi_dates[]={20250812,20250911,20251024,20251218,20260113,20260213,
                    20260311,20260410,20260512,20260610,20260714,20260812};
   int fomc_dates[]={20250917,20251029,20251210,20260128,20260318,20260429,
                     20260617,20260729};

   datetime now=TimeCurrent();
   MqlDateTime ny;
   TimeToStruct(AAA_ToNewYork(now),ny);
   int key=ny.year*10000+ny.mon*100+ny.day;
   datetime best=0;
   string best_kind="";
   NP_ConsiderTesterEvent(InpWatchNFP,NP_DateInList(key,nfp_dates),8,30,"NFP",now,ny,best,best_kind);
   NP_ConsiderTesterEvent(InpWatchCPI,NP_DateInList(key,cpi_dates),8,30,"CPI",now,ny,best,best_kind);
   NP_ConsiderTesterEvent(InpWatchFOMC,NP_DateInList(key,fomc_dates),14,0,"FOMC",now,ny,best,best_kind);
   if(best<=0) return false;
   event_time=best;
   event_id=(long)best;
   kind=best_kind;
   return true;
}

string NP_EventKind(const string original_name)
{
   string name=original_name;
   StringToLower(name);
   if(InpWatchNFP &&
      (StringFind(name,"nonfarm payroll")>=0 || StringFind(name,"non-farm payroll")>=0) &&
      StringFind(name,"private")<0) return "NFP";
   if(InpWatchCPI &&
      (StringFind(name,"consumer price index")>=0 || StringFind(name,"cpi")>=0)) return "CPI";
   if(InpWatchFOMC &&
      (StringFind(name,"fomc statement")>=0 || StringFind(name,"federal funds rate")>=0 ||
       StringFind(name,"fed interest rate decision")>=0 || StringFind(name,"federal reserve interest rate decision")>=0)) return "FOMC";
   return "";
}

bool NP_RefreshLiveCalendarCache(const datetime now)
{
   if(!InpUseEconomicCalendar) return false;
   ulong monotonic_now=GetTickCount64();
   bool cache_is_future=(g_cached_event_time>now);
   bool refresh_due=(g_last_calendar_refresh_ms==0 ||
                     monotonic_now-g_last_calendar_refresh_ms>=(ulong)InpCalendarRefreshSeconds*1000 ||
                     !cache_is_future);
   if(!refresh_due) return cache_is_future;

   MqlCalendarValue values[];
   ResetLastError();
   int total=CalendarValueHistory(values,now,now+InpCalendarLookaheadDays*86400,NULL,"USD");
   g_last_calendar_refresh_ms=monotonic_now;
   if(total<=0)
   {
      if(now-g_last_calendar_warning>=60)
      {
         Print("News Pulse: USD calendar refresh returned ",total," entries (error ",GetLastError(),
               "). Keeping any previously cached future event.");
         g_last_calendar_warning=now;
      }
      return cache_is_future;
   }

   datetime best=0;
   long best_id=0;
   string best_kind="";
   for(int i=0;i<total;i++)
   {
      // Calendar values and now are both broker trade-server timestamps.
      if(values[i].time<=now) continue;
      MqlCalendarEvent event;
      if(!CalendarEventById(values[i].event_id,event)) continue;
      string candidate_kind=NP_EventKind(event.name);
      if(candidate_kind=="") continue;
      if(best==0 || values[i].time<best)
      {
         best=values[i].time;
         // event_id identifies the calendar definition and is reused every
         // month (for example, every NFP). The server release timestamp is
         // the unique occurrence key, so future monthly releases are not skipped.
         best_id=(long)values[i].time;
         best_kind=candidate_kind;
      }
   }
   if(best<=0)
   {
      g_cached_event_time=0;
      g_cached_event_id=0;
      g_cached_event_kind="";
      return false;
   }

   bool changed=(best!=g_cached_event_time || best_kind!=g_cached_event_kind);
   g_cached_event_time=best;
   g_cached_event_id=best_id;
   g_cached_event_kind=best_kind;
   if(changed)
      Print("News Pulse: cached next ",best_kind," for broker-server time ",
            TimeToString(best,TIME_DATE|TIME_SECONDS),"; VPS local timezone is not used.");
   return true;
}

bool NP_FindLiveEvent(datetime &event_time,long &event_id,string &kind)
{
   if(!InpUseEconomicCalendar) return false;
   datetime now=0;
   if(!NP_GetFreshBrokerPlacementTime(now)) return false;
   if(!NP_RefreshLiveCalendarCache(now)) return false;
   // Equal-to-now is deliberately rejected: orders must exist before release.
   if(g_cached_event_time<=now || g_cached_event_time>now+InpPlacementLeadSeconds) return false;
   event_time=g_cached_event_time;
   event_id=g_cached_event_id;
   kind=g_cached_event_kind;
   return true;
}

bool NP_FindUpcomingEvent(datetime &event_time,long &event_id,string &kind)
{
   if((bool)MQLInfoInteger(MQL_TESTER)) return NP_FindTesterEvent(event_time,event_id,kind);
   return NP_FindLiveEvent(event_time,event_id,kind);
}

bool NP_SendStraddle(const datetime event_time,const long event_id,const string kind)
{
   datetime placement_time=0;
   if(!NP_GetFreshBrokerPlacementTime(placement_time)) return false;
   int seconds_before=(int)(event_time-placement_time);
   if(seconds_before<=0 || seconds_before>InpPlacementLeadSeconds)
   {
      Print("News Pulse: placement blocked because event timing is outside the T-",
            InpPlacementLeadSeconds,"s window. Server now=",TimeToString(placement_time,TIME_DATE|TIME_SECONDS),
            ", event=",TimeToString(event_time,TIME_DATE|TIME_SECONDS),".");
      return false;
   }

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0) return false;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double broker_gap=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point;
   if(InpEntryOffsetPrice+point<broker_gap)
   {
      Print("News Pulse: $",DoubleToString(InpEntryOffsetPrice,2)," entry offset is below this broker's minimum distance of ",
            DoubleToString(broker_gap,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS)),".");
      return false;
   }

   double buy_entry=AAA_Price(_Symbol,tick.ask+InpEntryOffsetPrice);
   double sell_entry=AAA_Price(_Symbol,tick.bid-InpEntryOffsetPrice);
   double buy_sl=AAA_Price(_Symbol,buy_entry-InpStopLossPrice);
   double sell_sl=AAA_Price(_Symbol,sell_entry+InpStopLossPrice);
   double side_risk=InpRiskPercent;
   double buy_lots=0.0;
   double sell_lots=0.0;
   bool allow_buy=InpEnableBuySide && HAMA_SafeRegimeAllowsDirection(1);
   bool allow_sell=InpEnableSellSide && HAMA_SafeRegimeAllowsDirection(-1);
   if(allow_buy)
      buy_lots=AAA_LotsForRisk(_Symbol,ORDER_TYPE_BUY,buy_entry,buy_sl,side_risk);
   if(allow_sell)
      sell_lots=AAA_LotsForRisk(_Symbol,ORDER_TYPE_SELL,sell_entry,sell_sl,side_risk);
   if(!allow_buy && !allow_sell)
   {
      Print("News Pulse: both order directions were vetoed by this EA's completed-D1 Safe Mode gate.");
      return false;
   }
   if((allow_buy && buy_lots<=0.0) || (allow_sell && sell_lots<=0.0))
   {
      Print("News Pulse: broker contract data or minimum lot prevents risk-based sizing.");
      return false;
   }

   datetime expiry=event_time+InpForceCloseSecondsAfterEvent;
   string prefix="NP|"+IntegerToString((long)event_time)+"|"+kind+"|";
   AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);
   AAA_Trade.SetTypeFillingBySymbol(_Symbol);
   AAA_Trade.SetDeviationInPoints(InpMaxDeviationPoints);
   bool buy_ok=false;
   bool sell_ok=false;
   if(allow_buy)
   {
      buy_ok=AAA_Trade.BuyStop(buy_lots,buy_entry,_Symbol,buy_sl,0.0,ORDER_TIME_SPECIFIED,expiry,prefix+"B");
      if(!buy_ok)
         Print("News Pulse: buy-stop placement failed: ",AAA_Trade.ResultRetcodeDescription());
   }
   if(allow_sell)
   {
      sell_ok=AAA_Trade.SellStop(sell_lots,sell_entry,_Symbol,sell_sl,0.0,ORDER_TIME_SPECIFIED,expiry,prefix+"S");
      if(!sell_ok)
         Print("News Pulse: sell-stop placement failed: ",AAA_Trade.ResultRetcodeDescription());
   }
   if(!buy_ok && !sell_ok) return false;

   g_active_event_time=event_time;
   g_last_event_id=event_id;
   g_event_buy_entry=allow_buy ? buy_entry : 0.0;
   g_event_sell_entry=allow_sell ? sell_entry : 0.0;
   g_event_max_ask=tick.ask;
   g_event_min_bid=tick.bid;
   NP_SaveState();
   string side_mode=allow_buy && allow_sell ? "two-sided" :
                    (allow_buy ? "long-only" : "short-only");
   double enabled_sides=(allow_buy ? 1.0 : 0.0)+(allow_sell ? 1.0 : 0.0);
   Print("News Pulse: ",kind," ",side_mode," orders placed. Buy ",
         (allow_buy ? DoubleToString(buy_entry,_Digits) : "disabled"),
         ", sell ",(allow_sell ? DoubleToString(sell_entry,_Digits) : "disabled"),
         ", SL distance $",DoubleToString(InpStopLossPrice,2),
         ", risk per triggered trade ",DoubleToString(InpRiskPercent,2),
         "%; up to ",DoubleToString(InpRiskPercent*enabled_sides,2),"% planned event risk. Server placement=",
         TimeToString(placement_time,TIME_DATE|TIME_SECONDS),", event=",
         TimeToString(event_time,TIME_DATE|TIME_SECONDS),", lead=",seconds_before,"s.");
   return true;
}

void NP_ManageLifecycle()
{
   NP_RecoverActiveEvent();
   if(g_active_event_time>0)
   {
      MqlTick range_tick;
      if(SymbolInfoTick(_Symbol,range_tick))
      {
         g_event_max_ask=MathMax(g_event_max_ask,range_tick.ask);
         g_event_min_bid=MathMin(g_event_min_bid,range_tick.bid);
      }
   }
   bool has_position=AAA_HasPosition(_Symbol,InpMagic);
   if(has_position)
   {
      // Deliberately not OCO: the opposite pending order remains eligible to fill.
      NP_TrailPositions();
   }

   if(g_active_event_time>0 && NP_ServerNow()>=g_active_event_time+InpForceCloseSecondsAfterEvent)
   {
      NP_DeletePendingOrders();
      NP_ClosePositions();
      if(!AAA_HasExposure(_Symbol,InpMagic))
      {
         string reach="";
         if(g_event_buy_entry>0.0 && g_event_max_ask>-DBL_MAX)
            reach+=" Highest Ask="+DoubleToString(g_event_max_ask,_Digits)+
                   " (buy gap="+DoubleToString(g_event_buy_entry-g_event_max_ask,_Digits)+").";
         if(g_event_sell_entry>0.0 && g_event_min_bid<DBL_MAX)
            reach+=" Lowest Bid="+DoubleToString(g_event_min_bid,_Digits)+
                   " (sell gap="+DoubleToString(g_event_min_bid-g_event_sell_entry,_Digits)+").";
         Print("News Pulse: event window finished; all exposure is closed.",reach);
         g_active_event_time=0;
         g_event_buy_entry=0.0;
         g_event_sell_entry=0.0;
         g_event_max_ask=-DBL_MAX;
         g_event_min_bid=DBL_MAX;
         NP_SaveState();
      }
   }
}

void NP_Run()
{
   NP_ManageLifecycle();
   if(!InpEnableTrading || AAA_HasExposure(_Symbol,InpMagic)) return;
   datetime event_time=0;
   long event_id=0;
   string kind="";
   if(!NP_FindUpcomingEvent(event_time,event_id,kind)) return;
   if(event_id==g_last_event_id || event_time==g_active_event_time) return;
   datetime now=NP_ServerNow();
   if(event_id==g_attempt_event_id && now-g_last_placement_attempt<5) return;
   g_attempt_event_id=event_id;
   g_last_placement_attempt=now;
   NP_SendStraddle(event_time,event_id,kind);
}

int OnInit()
{
   if((!InpEnableBuySide && !InpEnableSellSide) ||
      InpRiskPercent<=0.0 || InpEntryOffsetPrice<=0.0 || InpStopLossPrice<=0.0 ||
      InpTrailStartR<=0.0 || InpTrailDistancePrice<=0.0 || InpPlacementLeadSeconds<=0 ||
      InpForceCloseSecondsAfterEvent<=0 || InpMaxQuoteAgeSeconds<=0 ||
      InpCalendarLookaheadDays<=0 || InpCalendarRefreshSeconds<=0)
   {
      Print("News Pulse: invalid risk, distance, or timing input.");
      return INIT_PARAMETERS_INCORRECT;
   }
   AAA_TesterServerOffsetMode=InpTesterServerClockMode;
   AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);
   AAA_Trade.SetTypeFillingBySymbol(_Symbol);
   AAA_Trade.SetDeviationInPoints(InpMaxDeviationPoints);
   g_active_state_key=NP_StateKey("ACTIVE");
   g_last_state_key=NP_StateKey("LAST");
   if(GlobalVariableCheck(g_active_state_key)) g_active_event_time=(datetime)GlobalVariableGet(g_active_state_key);
   if(GlobalVariableCheck(g_last_state_key)) g_last_event_id=(long)GlobalVariableGet(g_last_state_key);
   NP_RecoverActiveEvent();
   EventSetTimer(1);
   string side_mode=InpEnableBuySide && InpEnableSellSide ? "two-sided" :
                    (InpEnableBuySide ? "long-only" : "short-only");
   Print("AAA Final News Pulse v2.11 loaded on ",_Symbol,
         ". Watches NFP/CPI/FOMC; places at T-",InpPlacementLeadSeconds,
         "s; mode=",side_mode,"; ",DoubleToString(InpRiskPercent,2),
         "% risk per triggered enabled side; hard exit at T+",
         InpForceCloseSecondsAfterEvent,
         "s. Live timing is broker-quote/calendar anchored; VPS local timezone is ignored.");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   NP_SaveState();
}

void OnTick()
{
   NP_RecordBrokerQuote();
   NP_Run();
}

void OnTimer()
{
   NP_Run();
}

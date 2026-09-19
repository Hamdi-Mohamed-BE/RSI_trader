#property copyright "AAA Final News Pulse - NFP/CPI/FOMC straddle"
#property version   "2.17"
#property strict

#include "C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/AAA Final EAs/AAA Final News Pulse EA/AAA_Final_Common.mqh"
#include "C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/AAA Final EAs/AAA Final News Pulse EA/SafeRegimeFilter.mqh"
#include "C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/AAA Final EAs/AAA Final News Pulse EA/DynamicTrailingSessionFilter.mqh"
#include "C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/News Pulse Multi Asset Event Parameters 2026-09-19/Calendar.mqh"
#include "C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/_Shared/CalyxAdaptivePortfolio.mqh"

input group "Trading"
input bool   InpEnableTrading=true;
input bool   InpEnableBuySide=true;
input bool   InpEnableSellSide=true;
input double InpRiskPercent=0.75;             // locked compatibility value; EA rejects any other value
input bool   InpAdaptivePortfolioControls=false;
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

input bool   InpUseAssetEventSpecific=true;       // XAG/BTC/EURUSD full-year fitted; approved 2026-09-19

input group "Order geometry - symbol price units"
input double InpEntryOffsetPrice=12.0;         // buy above Ask / sell below Bid
input double InpStopLossPrice=10.0;            // one R
input double InpTrailStartR=3.0;               // start trailing after +3R
input double InpTrailDistancePrice=10.0;        // trail one R behind current price
input int    InpForceCloseSecondsAfterEvent=120;

input group "Tester"
input int    InpTesterServerClockMode=0;        // 0 = Exness tester timestamps are UTC; live uses calendar server time
input int    InpTesterFromDateUTC=0;            // required in Strategy Tester: YYYYMMDD; generated-calendar coverage gate
input int    InpTesterToDateUTC=0;              // required in Strategy Tester: YYYYMMDD; generated-calendar coverage gate


string g_active_event_kind="";
// Generated from the frozen selected.json full-year candidates. Hindsight optimized.
string NP_Asset()
{
   string symbol=_Symbol; StringToUpper(symbol);
   if(StringFind(symbol,"XAG")==0 || StringFind(symbol,"SILVER")==0) return "XAG";
   if(StringFind(symbol,"BTC")==0 || StringFind(symbol,"BITCOIN")==0) return "BTC";
   if(StringFind(symbol,"EURUSD")==0) return "EURUSD";
   return "";
}
int g_np_lead=30,g_np_hold=60,g_np_anchor=0;
double g_np_offset=1,g_np_stop=1,g_np_trail_start=1.5,g_np_trail_distance=1,g_np_tp=0;
void NP_ApplyEventParameters(const string kind)
{
   g_np_lead=InpPlacementLeadSeconds; g_np_hold=InpForceCloseSecondsAfterEvent;
   g_np_offset=InpEntryOffsetPrice; g_np_stop=InpStopLossPrice;
   g_np_trail_start=InpTrailStartR; g_np_trail_distance=InpTrailDistancePrice;
   g_np_tp=0; g_np_anchor=0;
   string asset=NP_Asset();
   if(asset=="XAG" && kind=="NFP") {g_np_lead=15;g_np_anchor=0;g_np_offset=0.1200000000;g_np_stop=0.0200000000;g_np_tp=0.0;g_np_trail_start=0.0;g_np_trail_distance=0.0600000000;g_np_hold=60;}
   if(asset=="XAG" && kind=="CPI") {g_np_lead=10;g_np_anchor=2;g_np_offset=0.0200000000;g_np_stop=0.0200000000;g_np_tp=0.0;g_np_trail_start=0.0;g_np_trail_distance=0.0600000000;g_np_hold=60;}
   if(asset=="XAG" && kind=="FOMC") {g_np_lead=120;g_np_anchor=2;g_np_offset=0.1200000000;g_np_stop=0.0200000000;g_np_tp=0.0;g_np_trail_start=0.5;g_np_trail_distance=0.4000000000;g_np_hold=60;}
   if(asset=="BTC" && kind=="NFP") {g_np_lead=90;g_np_anchor=0;g_np_offset=75.0000000000;g_np_stop=12.5000000000;g_np_tp=0.0;g_np_trail_start=1.5;g_np_trail_distance=50.0000000000;g_np_hold=600;}
   if(asset=="BTC" && kind=="CPI") {g_np_lead=5;g_np_anchor=1;g_np_offset=6.2500000000;g_np_stop=12.5000000000;g_np_tp=0.0;g_np_trail_start=0.5;g_np_trail_distance=187.5000000000;g_np_hold=180;}
   if(asset=="BTC" && kind=="FOMC") {g_np_lead=45;g_np_anchor=0;g_np_offset=12.5000000000;g_np_stop=12.5000000000;g_np_tp=0.0;g_np_trail_start=1.5;g_np_trail_distance=100.0000000000;g_np_hold=600;}
   if(asset=="EURUSD" && kind=="NFP") {g_np_lead=90;g_np_anchor=2;g_np_offset=0.0002000000;g_np_stop=0.0001000000;g_np_tp=0.0;g_np_trail_start=0.0;g_np_trail_distance=0.0020000000;g_np_hold=300;}
   if(asset=="EURUSD" && kind=="CPI") {g_np_lead=60;g_np_anchor=0;g_np_offset=0.0001000000;g_np_stop=0.0002000000;g_np_tp=0.0;g_np_trail_start=3.0;g_np_trail_distance=0.0004000000;g_np_hold=60;}
   if(asset=="EURUSD" && kind=="FOMC") {g_np_lead=10;g_np_anchor=2;g_np_offset=0.0001000000;g_np_stop=0.0001000000;g_np_tp=0.0;g_np_trail_start=0.0;g_np_trail_distance=0.0003000000;g_np_hold=60;}
}
int NP_LeadSeconds(const string kind)
{
   // Called only when no owned exposure is being managed. Event-kind parameters
   // are restored from persistent state/comments before every lifecycle action.
   NP_ApplyEventParameters(kind);
   return g_np_lead;
}
string NP_KindFromComment(const string comment)
{
   string parts[];if(StringSplit(comment,'|',parts)<4 || parts[0]!="NP")return "";
   return parts[2];
}

datetime g_active_event_time=0;
const double NP_TOTAL_EVENT_RISK_PERCENT=1.50;
const double NP_RISK_PER_STOP_PERCENT=0.75;
long     g_last_event_id=0;
string   g_active_state_key="";
string   g_last_state_key="";
datetime g_last_calendar_warning=0;
datetime g_last_quote_warning=0;
const int NP_REPEAT_WARNING_SECONDS=900;
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
bool     g_tester_calendar_boundary_violation=false;
int      g_tester_expected_event_count=0;
int      g_tester_attempted_event_count=0;
int      g_tester_successful_event_count=0;
long     g_tester_last_attempted_event_id=0;
long     g_tester_last_successful_event_id=0;

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
      datetime warn_now=TimeLocal();
      if(g_last_quote_warning==0 || warn_now-g_last_quote_warning>=NP_REPEAT_WARNING_SECONDS)
      {
         Print("News Pulse: placement blocked because a fresh broker-stamped quote or connection is unavailable.");
         g_last_quote_warning=warn_now;
      }
      return false;
   }

   ulong age_ms=GetTickCount64()-g_last_quote_arrival_ms;
   if(age_ms>(ulong)InpMaxQuoteAgeSeconds*1000)
   {
      datetime warn_now=TimeLocal();
      if(g_last_quote_warning==0 || warn_now-g_last_quote_warning>=NP_REPEAT_WARNING_SECONDS)
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
   int kind_code=g_active_event_kind=="NFP"?1:g_active_event_kind=="CPI"?2:g_active_event_kind=="FOMC"?3:0;
   if(g_active_event_time>0) GlobalVariableSet(NP_StateKey("KIND"),kind_code);
   else if(GlobalVariableCheck(NP_StateKey("KIND"))) GlobalVariableDel(NP_StateKey("KIND"));
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
   if(g_active_event_time>0 && g_active_event_kind!="") return;
   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      if(OrderGetTicket(i)==0 || !NP_IsOurOrderSelected()) continue;
      datetime recovered=NP_EventTimeFromComment(OrderGetString(ORDER_COMMENT));
      if(recovered>0) { g_active_event_time=recovered; g_active_event_kind=NP_KindFromComment(OrderGetString(ORDER_COMMENT)); NP_SaveState(); return; }
   }
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      if(PositionGetTicket(i)==0 || !NP_IsOurPositionSelected()) continue;
      datetime recovered=NP_EventTimeFromComment(PositionGetString(POSITION_COMMENT));
      if(recovered>0) { g_active_event_time=recovered; g_active_event_kind=NP_KindFromComment(PositionGetString(POSITION_COMMENT)); NP_SaveState(); return; }
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
   if(g_np_trail_start<=0) return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double broker_gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                             (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
   double trail_gap=MathMax(g_np_trail_distance,broker_gap);
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
      if(favorable+point<g_np_trail_start*g_np_stop) continue;

      double candidate=AAA_Price(_Symbol,(buy ? exit_price-trail_gap : exit_price+trail_gap));
      bool improves=(buy ? (candidate>current_sl+point && candidate<tick.bid-broker_gap+point)
                         : ((current_sl<=0.0 || candidate<current_sl-point) && candidate>tick.ask+broker_gap-point));
      if(improves && !AAA_Trade.PositionModify(ticket,candidate,current_tp))
         Print("News Pulse: trailing-stop update failed for ",ticket,": ",AAA_Trade.ResultRetcodeDescription());
   }
}

int NP_UTCDateKeyFromUTC(const datetime utc_time)
{
   MqlDateTime part;
   TimeToStruct(utc_time,part);
   return part.year*10000+part.mon*100+part.day;
}

bool NP_TesterKindEnabled(const string kind)
{
   if(kind=="NFP") return InpWatchNFP;
   if(kind=="CPI") return InpWatchCPI;
   if(kind=="FOMC") return InpWatchFOMC;
   return false;
}

int NP_TesterExpectedEventCount()
{
   int expected=0;
   int total=NP_GeneratedCalendarEventCount();
   for(int i=0;i<total;i++)
   {
      int key=NP_UTCDateKeyFromUTC((datetime)NP_GENERATED_EVENT_UTC_EPOCHS[i]);
      if(key<InpTesterFromDateUTC || key>InpTesterToDateUTC) continue;
      if(NP_TesterKindEnabled(NP_GENERATED_EVENT_KINDS[i])) expected++;
   }
   return expected;
}

bool NP_ValidateTesterCalendar()
{
   if(!(bool)MQLInfoInteger(MQL_TESTER)) return true;
   if(InpTesterFromDateUTC<=0 || InpTesterToDateUTC<=0)
   {
      Print("News Pulse tester blocked: InpTesterFromDateUTC and InpTesterToDateUTC are required. ",
            "Generate the FXMacroData calendar through the Calyx pipeline and pass the exact test window.");
      return false;
   }
   if(InpTesterFromDateUTC>InpTesterToDateUTC ||
      InpTesterFromDateUTC<NP_TESTER_CALENDAR_COVERAGE_START_DATE ||
      InpTesterToDateUTC>NP_TESTER_CALENDAR_COVERAGE_END_DATE)
   {
      Print("News Pulse tester blocked: requested UTC window ",InpTesterFromDateUTC,"..",InpTesterToDateUTC,
            " is outside verified generated-calendar coverage ",NP_TESTER_CALENDAR_COVERAGE_START_DATE,"..",
            NP_TESTER_CALENDAR_COVERAGE_END_DATE,".");
      return false;
   }
   if(NP_GeneratedCalendarEventCount()!=ArraySize(NP_GENERATED_EVENT_KINDS) ||
      NP_GeneratedCalendarEventCount()!=NP_TESTER_CALENDAR_EXPECTED_EVENTS)
   {
      Print("News Pulse tester blocked: generated calendar arrays or manifest count are inconsistent.");
      return false;
   }
   g_tester_expected_event_count=NP_TesterExpectedEventCount();
   if(g_tester_expected_event_count<=0)
   {
      Print("News Pulse tester blocked: no enabled NFP/CPI/FOMC events exist in the requested verified window.");
      return false;
   }
   Print("News Pulse tester calendar accepted: provider=",NP_GeneratedCalendarProvider(),
         ", coverage=",NP_TESTER_CALENDAR_COVERAGE_START_DATE,"..",NP_TESTER_CALENDAR_COVERAGE_END_DATE,
         ", requested=",InpTesterFromDateUTC,"..",InpTesterToDateUTC,
         ", enabled events=",g_tester_expected_event_count,
         ", SHA-256=",NP_GeneratedCalendarHash(),".");
   return true;
}

bool NP_FindTesterEvent(datetime &event_time,long &event_id,string &kind)
{
   // MT5 does not expose its economic calendar in Strategy Tester. Exact UTC
   // release epochs are generated from FXMacroData with a coverage manifest.
   // Manual date/time assumptions and silent partial schedules are forbidden.
   datetime now=TimeCurrent();
   int now_key=NP_UTCDateKeyFromUTC(AAA_ToUTC(now));
   if(now_key<NP_TESTER_CALENDAR_COVERAGE_START_DATE || now_key>NP_TESTER_CALENDAR_COVERAGE_END_DATE)
   {
      if(!g_tester_calendar_boundary_violation)
      {
         g_tester_calendar_boundary_violation=true;
         Print("News Pulse tester stopped: runtime date ",now_key,
               " escaped generated-calendar coverage ",NP_TESTER_CALENDAR_COVERAGE_START_DATE,"..",
               NP_TESTER_CALENDAR_COVERAGE_END_DATE,". This partial report must not be used.");
         ExpertRemove();
      }
      return false;
   }

   datetime best=0;
   string best_kind="";
   int total=NP_GeneratedCalendarEventCount();
   for(int i=0;i<total;i++)
   {
      string candidate_kind=NP_GENERATED_EVENT_KINDS[i];
      if(!NP_TesterKindEnabled(candidate_kind)) continue;
      datetime candidate=AAA_ToServer((datetime)NP_GENERATED_EVENT_UTC_EPOCHS[i]);
      if(candidate<=now || candidate>now+NP_LeadSeconds(candidate_kind)) continue;
      if(best==0 || candidate<best)
      {
         best=candidate;
         best_kind=candidate_kind;
      }
   }
   if(best<=0) return false;
   event_time=best;
   event_id=(long)best;
   kind=best_kind;
   return true;
}

bool NP_IsPrimaryCPIName(const string normalized_name)
{
   // The live MT5 calendar also contains secondary series such as Cleveland
   // Fed Median CPI and CPI expectations. News Pulse is intentionally limited
   // to the main headline/core CPI family released by the BLS.
   return (StringFind(normalized_name,"cpi")==0 ||
           StringFind(normalized_name,"core cpi")==0 ||
           StringFind(normalized_name,"consumer price index")==0 ||
           StringFind(normalized_name,"core consumer price index")==0);
}

string NP_EventKind(const string original_name)
{
   string name=original_name;
   StringToLower(name);
   StringTrimLeft(name);
   StringTrimRight(name);
   if(InpWatchNFP &&
      (StringFind(name,"nonfarm payroll")>=0 || StringFind(name,"non-farm payroll")>=0) &&
      StringFind(name,"private")<0) return "NFP";
   if(InpWatchCPI && NP_IsPrimaryCPIName(name)) return "CPI";
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
   string best_name="";
   for(int i=0;i<total;i++)
   {
      // Calendar values and now are both broker trade-server timestamps.
      if(values[i].time<=now) continue;
      MqlCalendarEvent event;
      if(!CalendarEventById(values[i].event_id,event)) continue;
      // News Pulse is a top-tier release strategy. Medium/low-importance
      // derivative indicators must never create another straddle.
      if(event.importance!=CALENDAR_IMPORTANCE_HIGH) continue;
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
         best_name=event.name;
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
            TimeToString(best,TIME_DATE|TIME_SECONDS)," from calendar event '",best_name,
            "'; VPS local timezone is not used.");
   return true;
}

bool NP_FindLiveEvent(datetime &event_time,long &event_id,string &kind)
{
   if(!InpUseEconomicCalendar) return false;
   datetime now=0;
   if(!NP_GetFreshBrokerPlacementTime(now)) return false;
   if(!NP_RefreshLiveCalendarCache(now)) return false;
   // Equal-to-now is deliberately rejected: orders must exist before release.
   if(g_cached_event_time<=now || g_cached_event_time>now+NP_LeadSeconds(g_cached_event_kind)) return false;
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
   NP_ApplyEventParameters(kind);
   if(!DTS_EntrySessionAllowed()) return false;
   datetime placement_time=0;
   if(!NP_GetFreshBrokerPlacementTime(placement_time)) return false;
   int seconds_before=(int)(event_time-placement_time);
   if(seconds_before<=0 || seconds_before>g_np_lead)
   {
      Print("News Pulse: placement blocked because event timing is outside the T-",
            g_np_lead,"s window. Server now=",TimeToString(placement_time,TIME_DATE|TIME_SECONDS),
            ", event=",TimeToString(event_time,TIME_DATE|TIME_SECONDS),".");
      return false;
   }

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0) return false;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double broker_gap=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point;
   if(g_np_offset+point<broker_gap)
   {
      Print("News Pulse: $",DoubleToString(g_np_offset,2)," entry offset is below this broker's minimum distance of ",
            DoubleToString(broker_gap,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS)),".");
      return false;
   }

   double high=tick.ask,low=tick.bid;
   if(g_np_anchor>0)
   {
      int shift=(g_np_anchor==1 ? 0:1);
      double h=iHigh(_Symbol,PERIOD_M1,shift),l=iLow(_Symbol,PERIOD_M1,shift);
      if(h<=0 || l<=0 || h<l) {Print("News Pulse: M1 anchor unavailable; waiting for history.");return false;}
      high=h+(tick.ask-tick.bid);low=l;
   }
   double buy_entry=AAA_Price(_Symbol,high+g_np_offset);
   double sell_entry=AAA_Price(_Symbol,low-g_np_offset);
   double buy_sl=AAA_Price(_Symbol,buy_entry-g_np_stop);
   double sell_sl=AAA_Price(_Symbol,sell_entry+g_np_stop);
   // This is intentionally a source-level portfolio invariant. Each side is
   // capped at 0.75%, so a two-sided event cannot plan more than 1.50% total.
   const double adaptive=CalyxAdaptiveRiskMultiplier(InpAdaptivePortfolioControls,InpMagic);
   if(adaptive<=0.0)
   {
      Print("News Pulse: placement blocked by the Recommended Adaptive daily-entry stop.");
      return false;
   }
   double side_risk=NP_RISK_PER_STOP_PERCENT*adaptive;
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
      Print("News Pulse: broker contract data prevents risk-based sizing.");
      return false;
   }

   datetime expiry=event_time+g_np_hold;
   string prefix="NP|"+IntegerToString((long)event_time)+"|"+kind+"|";
   AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);
   AAA_Trade.SetTypeFillingBySymbol(_Symbol);
   AAA_Trade.SetDeviationInPoints(InpMaxDeviationPoints);
   bool buy_ok=false;
   bool sell_ok=false;
   if(allow_buy)
   {
      buy_ok=AAA_Trade.BuyStop(buy_lots,buy_entry,_Symbol,buy_sl,(g_np_tp>0 ? AAA_Price(_Symbol,buy_entry+g_np_tp*g_np_stop):0.0),ORDER_TIME_SPECIFIED,expiry,prefix+"B");
      if(!buy_ok)
         Print("News Pulse: buy-stop placement failed: ",AAA_Trade.ResultRetcodeDescription());
   }
   if(allow_sell)
   {
      sell_ok=AAA_Trade.SellStop(sell_lots,sell_entry,_Symbol,sell_sl,(g_np_tp>0 ? AAA_Price(_Symbol,sell_entry-g_np_tp*g_np_stop):0.0),ORDER_TIME_SPECIFIED,expiry,prefix+"S");
      if(!sell_ok)
         Print("News Pulse: sell-stop placement failed: ",AAA_Trade.ResultRetcodeDescription());
   }
   if(!buy_ok && !sell_ok) return false;

   if((bool)MQLInfoInteger(MQL_TESTER) && event_id!=g_tester_last_successful_event_id)
   {
      g_tester_successful_event_count++;
      g_tester_last_successful_event_id=event_id;
   }

   g_active_event_time=event_time;
   g_active_event_kind=kind;
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
         ", SL distance $",DoubleToString(g_np_stop,2),
         ", hard risk per enabled stop ",DoubleToString(NP_RISK_PER_STOP_PERCENT,2),
         "%; up to ",DoubleToString(NP_RISK_PER_STOP_PERCENT*enabled_sides,2),"% planned event risk. Server placement=",
         TimeToString(placement_time,TIME_DATE|TIME_SECONDS),", event=",
         TimeToString(event_time,TIME_DATE|TIME_SECONDS),", lead=",seconds_before,"s.");
   return true;
}

void NP_ManageLifecycle()
{
   NP_RecoverActiveEvent();
   NP_ApplyEventParameters(g_active_event_kind);
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

   if(g_active_event_time>0 && NP_ServerNow()>=g_active_event_time+g_np_hold)
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
         g_active_event_kind="";
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
   if((bool)MQLInfoInteger(MQL_TESTER) && event_id!=g_tester_last_attempted_event_id)
   {
      g_tester_attempted_event_count++;
      g_tester_last_attempted_event_id=event_id;
   }
   NP_SendStraddle(event_time,event_id,kind);
}

int OnInit()
{
   if(!InpUseAssetEventSpecific || NP_Asset()=="") {Print("News Pulse v2.17 requires the approved XAG, BTC or EURUSD event profile.");return INIT_PARAMETERS_INCORRECT;}
   if(!DTS_InputsValid()) return INIT_PARAMETERS_INCORRECT;
   if((!InpEnableBuySide && !InpEnableSellSide) ||
      MathAbs(InpRiskPercent-NP_RISK_PER_STOP_PERCENT)>0.000001 ||
      InpEntryOffsetPrice<=0.0 || InpStopLossPrice<=0.0 ||
      InpTrailStartR<=0.0 || InpTrailDistancePrice<=0.0 || InpPlacementLeadSeconds<=0 ||
      InpForceCloseSecondsAfterEvent<=0 || InpMaxQuoteAgeSeconds<=0 ||
      InpCalendarLookaheadDays<=0 || InpCalendarRefreshSeconds<=0)
   {
      Print("News Pulse: invalid distance/timing input, or InpRiskPercent was changed. This build hard-locks 0.75% per stop / 1.50% total event exposure.");
      return INIT_PARAMETERS_INCORRECT;
   }
   AAA_TesterServerOffsetMode=InpTesterServerClockMode;
   if(!NP_ValidateTesterCalendar()) return INIT_PARAMETERS_INCORRECT;
   AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);
   AAA_Trade.SetTypeFillingBySymbol(_Symbol);
   AAA_Trade.SetDeviationInPoints(InpMaxDeviationPoints);
   g_active_state_key=NP_StateKey("ACTIVE");
   g_last_state_key=NP_StateKey("LAST");
   if(GlobalVariableCheck(g_active_state_key)) g_active_event_time=(datetime)GlobalVariableGet(g_active_state_key);
   if(GlobalVariableCheck(g_last_state_key)) g_last_event_id=(long)GlobalVariableGet(g_last_state_key);
   int kind_code=(int)GlobalVariableGet(NP_StateKey("KIND"));
   g_active_event_kind=kind_code==1?"NFP":kind_code==2?"CPI":kind_code==3?"FOMC":"";
   NP_RecoverActiveEvent();
   NP_ApplyEventParameters(g_active_event_kind);
   EventSetTimer(1);
   string side_mode=InpEnableBuySide && InpEnableSellSide ? "two-sided" :
                    (InpEnableBuySide ? "long-only" : "short-only");
   Print("AAA Final News Pulse v2.17 FULL-YEAR FITTED loaded on ",_Symbol,
         ". Fallback geometry (asset/event-specific overrides): T-",InpPlacementLeadSeconds,
         "s; mode=",side_mode,"; hard risk ",DoubleToString(NP_RISK_PER_STOP_PERCENT,2),
         "% per stop / ",DoubleToString(NP_TOTAL_EVENT_RISK_PERCENT,2),"% maximum planned event exposure; hard exit at T+",
         InpForceCloseSecondsAfterEvent,
         "s. Live timing is broker-quote/calendar anchored; VPS local timezone is ignored.");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   NP_SaveState();
   if((bool)MQLInfoInteger(MQL_TESTER))
      Print("News Pulse tester calendar audit: expected=",g_tester_expected_event_count,
            ", attempted=",g_tester_attempted_event_count,
            ", successfully placed=",g_tester_successful_event_count,
            ", boundary violation=",(g_tester_calendar_boundary_violation ? "YES" : "NO"),".");
}

double OnTester()
{
   if(g_tester_calendar_boundary_violation) return -1.0;
   // The runner asserts this equals the manifest's enabled event count. A
   // smaller value makes the report fail rather than silently omit releases.
   return (double)g_tester_successful_event_count;
}

void OnTick()
{
   DTS_ManageDynamicTrailing(InpMagic);
   NP_RecordBrokerQuote();
   NP_Run();
}

void OnTimer()
{
   NP_Run();
}

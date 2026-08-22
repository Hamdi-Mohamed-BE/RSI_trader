#property copyright "Research implementation - post-release CPI/NFP continuation"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

input group "Trading and risk"
input bool   InpEnableTrading=true;
input double InpRiskPercent=0.50;
input long   InpMagic=861608;
input int    InpMaxDeviationPoints=30;
input bool   InpEnableLong=true;
input bool   InpEnableShort=true;

input group "Events"
input bool   InpWatchNFP=true;
input bool   InpWatchCPI=true;
input int    InpCalendarRefreshSeconds=30;
input int    InpTesterServerUTCOffsetHours=0;

input group "Post-release confirmation"
input int    InpPreRangeMinutes=30;
input int    InpSignalDelayMinutes=5;
input double InpMinBodyFraction=0.60;
input int    InpATRPeriod=14;
input double InpMinImpulseATR=0.50;
input double InpMaxImpulseATR=2.00;
input int    InpMaxSpreadPoints=30;
input double InpMaxSpreadVsPreEvent=2.00;

input group "Entry and exit"
input double InpRetraceFraction=0.50;
input int    InpEntryExpiryMinutes=15;
input double InpStopBufferATR=0.10;
input double InpMinStopATR=1.00;
input double InpMaxStopATR=3.00;
input double InpRewardRisk=1.80;
input double InpBreakEvenAtR=1.00;
input int    InpForceExitMinutes=45;

CTrade g_trade;
datetime g_last_processed_event=0;
datetime g_active_event=0;
ulong g_last_calendar_refresh_ms=0;
datetime g_cached_live_event=0;
string g_cached_live_kind="";

int LastSunday(const int year,const int month)
{
   MqlDateTime d={0};
   d.year=year; d.mon=month; d.day=31;
   while(d.day>27)
   {
      datetime t=StructToTime(d);
      MqlDateTime p; TimeToStruct(t,p);
      if(p.day_of_week==0) return d.day;
      d.day--;
   }
   return 31;
}

int NthSunday(const int year,const int month,const int ordinal)
{
   MqlDateTime d={0};
   d.year=year; d.mon=month; d.day=1;
   datetime t=StructToTime(d);
   MqlDateTime p; TimeToStruct(t,p);
   int first=1+((7-p.day_of_week)%7);
   return first+7*(ordinal-1);
}

int NewYorkUTCOffsetHours(const MqlDateTime &ny)
{
   if(ny.mon<3 || ny.mon>11) return -5;
   if(ny.mon>3 && ny.mon<11) return -4;
   if(ny.mon==3) return (ny.day>=NthSunday(ny.year,3,2) ? -4 : -5);
   return (ny.day<NthSunday(ny.year,11,1) ? -4 : -5);
}

datetime TesterNewYorkToServer(const MqlDateTime &ny)
{
   int ny_offset=NewYorkUTCOffsetHours(ny);
   MqlDateTime local=ny;
   datetime pseudo_local=StructToTime(local);
   datetime utc=pseudo_local-ny_offset*3600;
   return utc+InpTesterServerUTCOffsetHours*3600;
}

datetime TesterServerToNewYork(const datetime server_time)
{
   datetime utc=server_time-InpTesterServerUTCOffsetHours*3600;
   MqlDateTime guess; TimeToStruct(utc-5*3600,guess);
   int offset=NewYorkUTCOffsetHours(guess);
   return utc+offset*3600;
}

bool DateInList(const int key,const int &items[])
{
   for(int i=0;i<ArraySize(items);i++) if(items[i]==key) return true;
   return false;
}

bool FindTesterEvent(datetime &event_time,string &kind)
{
   // Official BLS release dates. All listed releases occurred at 08:30 New York time.
   int nfp_dates[]={
      20210108,20210205,20210305,20210402,20210507,20210604,20210702,20210806,20210903,20211008,20211105,20211203,
      20220107,20220204,20220304,20220401,20220506,20220603,20220708,20220805,20220902,20221007,20221104,20221202,
      20230106,20230203,20230310,20230407,20230505,20230602,20230707,20230804,20230901,20231006,20231103,20231208,
      20240105,20240202,20240308,20240405,20240503,20240607,20240705,20240802,20240906,20241004,20241101,20241206,
      20250110,20250207,20250307,20250404,20250502,20250606,20250703,20250801,20250905,20251120,20251216,
      20260109,20260211,20260306,20260403,20260508,20260605,20260702,20260807
   };
   int cpi_dates[]={
      20210113,20210210,20210310,20210413,20210512,20210610,20210713,20210811,20210914,20211013,20211110,20211210,
      20220112,20220210,20220310,20220412,20220511,20220610,20220713,20220810,20220913,20221013,20221110,20221213,
      20230112,20230214,20230314,20230412,20230510,20230613,20230712,20230810,20230913,20231012,20231114,20231212,
      20240111,20240213,20240312,20240410,20240515,20240612,20240711,20240814,20240911,20241010,20241113,20241211,
      20250115,20250212,20250312,20250410,20250513,20250611,20250715,20250812,20250911,20251024,20251218,
      20260113,20260213,20260311,20260410,20260512,20260610,20260714,20260812
   };

   datetime now=TimeCurrent();
   MqlDateTime ny; TimeToStruct(TesterServerToNewYork(now),ny);
   int key=ny.year*10000+ny.mon*100+ny.day;
   bool nfp=InpWatchNFP && DateInList(key,nfp_dates);
   bool cpi=InpWatchCPI && DateInList(key,cpi_dates);
   if(!nfp && !cpi) return false;
   ny.hour=8; ny.min=30; ny.sec=0;
   event_time=TesterNewYorkToServer(ny);
   kind=(nfp ? "NFP" : "CPI");
   return true;
}

string CalendarKind(const string original)
{
   string name=original; StringToLower(name);
   if(InpWatchNFP &&
      (StringFind(name,"nonfarm payroll")>=0 || StringFind(name,"non-farm payroll")>=0 ||
       StringFind(name,"nonfarm employment")>=0) && StringFind(name,"private")<0) return "NFP";
   if(InpWatchCPI &&
      (StringFind(name,"consumer price index")>=0 || StringFind(name,"cpi")>=0)) return "CPI";
   return "";
}

bool FindLiveEvent(datetime &event_time,string &kind)
{
   datetime now=TimeTradeServer(); if(now<=0) now=TimeCurrent();
   ulong monotonic=GetTickCount64();
   if(g_last_calendar_refresh_ms==0 ||
      monotonic-g_last_calendar_refresh_ms>=(ulong)InpCalendarRefreshSeconds*1000)
   {
      MqlCalendarValue values[];
      int count=CalendarValueHistory(values,now-3600,now,NULL,"USD");
      g_last_calendar_refresh_ms=monotonic;
      datetime best=0; string best_kind="";
      for(int i=0;i<count;i++)
      {
         if(values[i].time>now) continue;
         MqlCalendarEvent item;
         if(!CalendarEventById(values[i].event_id,item)) continue;
         string candidate=CalendarKind(item.name);
         if(candidate!="" && values[i].time>best)
         {
            best=values[i].time; best_kind=candidate;
         }
      }
      g_cached_live_event=best;
      g_cached_live_kind=best_kind;
   }
   if(g_cached_live_event<=0 || now-g_cached_live_event>3600) return false;
   event_time=g_cached_live_event; kind=g_cached_live_kind;
   return true;
}

bool FindCurrentEvent(datetime &event_time,string &kind)
{
   if((bool)MQLInfoInteger(MQL_TESTER)) return FindTesterEvent(event_time,kind);
   return FindLiveEvent(event_time,kind);
}

double NormalizePrice(const double price)
{
   return NormalizeDouble(price,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

double LotsForRisk(const ENUM_ORDER_TYPE type,const double entry,const double stop)
{
   double risk_cash=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   double one_lot=0.0;
   if(risk_cash<=0.0 || !OrderCalcProfit(type,_Symbol,1.0,entry,stop,one_lot)) return 0.0;
   one_lot=MathAbs(one_lot);
   if(one_lot<=0.0) return 0.0;
   double min_lot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double max_lot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(step<=0.0) return 0.0;
   double lots=MathFloor((risk_cash/one_lot)/step+1e-9)*step;
   if(lots<min_lot) return 0.0;
   return MathMin(lots,max_lot);
}

bool IsOurOrder()
{
   return OrderGetString(ORDER_SYMBOL)==_Symbol && OrderGetInteger(ORDER_MAGIC)==InpMagic;
}

bool IsOurPosition()
{
   return PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic;
}

bool HasOurExposure()
{
   for(int i=PositionsTotal()-1;i>=0;i--)
      if(PositionGetTicket(i)>0 && IsOurPosition()) return true;
   for(int i=OrdersTotal()-1;i>=0;i--)
      if(OrderGetTicket(i)>0 && IsOurOrder()) return true;
   return false;
}

double MedianSpreadPoints(const MqlRates &rates[])
{
   double values[];
   for(int i=0;i<ArraySize(rates);i++)
   {
      if(rates[i].spread<=0) continue;
      int n=ArraySize(values); ArrayResize(values,n+1); values[n]=(double)rates[i].spread;
   }
   int count=ArraySize(values);
   if(count==0) return 0.0;
   ArraySort(values);
   if(count%2==1) return values[count/2];
   return (values[count/2-1]+values[count/2])/2.0;
}

bool AggregateRates(const datetime from,const datetime to,double &open,double &high,double &low,double &close,double &median_spread)
{
   MqlRates rates[];
   int count=CopyRates(_Symbol,PERIOD_M1,from,to,rates);
   if(count<=0) return false;
   open=rates[0].open; close=rates[count-1].close;
   high=-DBL_MAX; low=DBL_MAX;
   for(int i=0;i<count;i++) { high=MathMax(high,rates[i].high); low=MathMin(low,rates[i].low); }
   median_spread=MedianSpreadPoints(rates);
   return high>low && open>0.0 && close>0.0;
}

double ATRBeforeEvent(const datetime event_time)
{
   MqlRates rates[];
   int needed=InpATRPeriod+1;
   int count=CopyRates(_Symbol,PERIOD_M5,event_time-(needed+3)*300,event_time-1,rates);
   if(count<needed) return 0.0;
   double sum=0.0;
   int first=count-InpATRPeriod;
   for(int i=first;i<count;i++)
   {
      double previous=(i>0 ? rates[i-1].close : rates[i].open);
      double tr=MathMax(rates[i].high-rates[i].low,
                        MathMax(MathAbs(rates[i].high-previous),MathAbs(rates[i].low-previous)));
      sum+=tr;
   }
   return sum/InpATRPeriod;
}

bool RejectSignal(const datetime event_time,const string kind,const string reason)
{
   Print("PNC skipped ",kind," ",TimeToString(event_time,TIME_DATE|TIME_MINUTES),": ",reason);
   return false;
}

bool PlacePullback(const datetime event_time,const string kind)
{
   double pre_o,pre_h,pre_l,pre_c,pre_spread;
   double imp_o,imp_h,imp_l,imp_c,ignored;
   if(!AggregateRates(event_time-InpPreRangeMinutes*60,event_time-1,pre_o,pre_h,pre_l,pre_c,pre_spread))
      return RejectSignal(event_time,kind,"pre-event bars unavailable");
   if(!AggregateRates(event_time,event_time+InpSignalDelayMinutes*60-1,imp_o,imp_h,imp_l,imp_c,ignored))
      return RejectSignal(event_time,kind,"impulse bars unavailable");

   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   MqlTick tick; if(point<=0.0 || !SymbolInfoTick(_Symbol,tick)) return RejectSignal(event_time,kind,"quote unavailable");
   double current_spread=(tick.ask-tick.bid)/point;
   if(current_spread>InpMaxSpreadPoints) return RejectSignal(event_time,kind,"absolute spread gate");
   if(pre_spread>0.0 && current_spread>pre_spread*InpMaxSpreadVsPreEvent) return RejectSignal(event_time,kind,"relative spread gate");

   double range=imp_h-imp_l;
   double body=MathAbs(imp_c-imp_o);
   double atr=ATRBeforeEvent(event_time);
   if(range<=0.0 || atr<=0.0) return RejectSignal(event_time,kind,"range or ATR unavailable");
   if(body/range<InpMinBodyFraction) return RejectSignal(event_time,kind,"weak impulse body");
   double impulse_atr=range/atr;
   if(impulse_atr<InpMinImpulseATR) return RejectSignal(event_time,kind,"impulse below ATR floor");
   if(impulse_atr>InpMaxImpulseATR) return RejectSignal(event_time,kind,"impulse above ATR ceiling");

   int direction=0;
   if(InpEnableLong && imp_c>pre_h) direction=1;
   if(InpEnableShort && imp_c<pre_l) direction=-1;
   if(direction==0) return RejectSignal(event_time,kind,"no close beyond pre-event range");

   double entry=(direction>0 ? imp_h-InpRetraceFraction*range : imp_l+InpRetraceFraction*range);
   double structural=(direction>0 ? imp_l-InpStopBufferATR*atr : imp_h+InpStopBufferATR*atr);
   double minimum=(direction>0 ? entry-InpMinStopATR*atr : entry+InpMinStopATR*atr);
   double stop=(direction>0 ? MathMin(structural,minimum) : MathMax(structural,minimum));
   double stop_atr=MathAbs(entry-stop)/atr;
   if(stop_atr>InpMaxStopATR) return RejectSignal(event_time,kind,"required stop too wide");

   double broker_gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                             (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
   if(direction>0)
   {
      if(entry>=tick.ask-broker_gap || stop>=entry-broker_gap) return RejectSignal(event_time,kind,"long retracement already crossed or broker gap");
   }
   else
   {
      if(entry<=tick.bid+broker_gap || stop<=entry+broker_gap) return RejectSignal(event_time,kind,"short retracement already crossed or broker gap");
   }

   entry=NormalizePrice(entry); stop=NormalizePrice(stop);
   double tp=NormalizePrice(entry+direction*MathAbs(entry-stop)*InpRewardRisk);
   ENUM_ORDER_TYPE market_type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=LotsForRisk(market_type,entry,stop);
   if(lots<=0.0) return RejectSignal(event_time,kind,"risk lot below broker minimum");
   datetime expiry=event_time+InpEntryExpiryMinutes*60;
   if(expiry<=TimeCurrent()) return RejectSignal(event_time,kind,"entry window expired");
   string comment="PNC|"+IntegerToString((long)event_time)+"|"+kind;
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetDeviationInPoints(InpMaxDeviationPoints);
   bool ok=(direction>0 ? g_trade.BuyLimit(lots,entry,_Symbol,stop,tp,ORDER_TIME_SPECIFIED,expiry,comment)
                        : g_trade.SellLimit(lots,entry,_Symbol,stop,tp,ORDER_TIME_SPECIFIED,expiry,comment));
   if(ok)
   {
      g_active_event=event_time;
      Print("PNC accepted ",kind," ",(direction>0 ? "LONG" : "SHORT")," entry=",entry,
            " SL=",stop," TP=",tp," lots=",lots," impulseATR=",DoubleToString(impulse_atr,2));
   }
   else Print("PNC order rejected: ",g_trade.ResultRetcodeDescription());
   return ok;
}

datetime EventFromComment(const string comment)
{
   if(StringFind(comment,"PNC|")!=0) return 0;
   int separator=StringFind(comment,"|",4);
   if(separator<0) return 0;
   return (datetime)StringToInteger(StringSubstr(comment,4,separator-4));
}

void ManagePositions()
{
   MqlTick tick; if(!SymbolInfoTick(_Symbol,tick)) return;
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetDeviationInPoints(InpMaxDeviationPoints);
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !IsOurPosition()) continue;
      long type=PositionGetInteger(POSITION_TYPE);
      bool buy=(type==POSITION_TYPE_BUY);
      double open=PositionGetDouble(POSITION_PRICE_OPEN);
      double sl=PositionGetDouble(POSITION_SL);
      double tp=PositionGetDouble(POSITION_TP);
      double initial_risk=MathAbs(open-sl);
      double current=(buy ? tick.bid : tick.ask);
      double favorable=(buy ? current-open : open-current);
      if(InpBreakEvenAtR>0.0 && initial_risk>0.0 && favorable>=InpBreakEvenAtR*initial_risk)
      {
         double break_even=NormalizePrice(open);
         bool improves=(buy ? sl<break_even : (sl<=0.0 || sl>break_even));
         if(improves) g_trade.PositionModify(ticket,break_even,tp);
      }
      datetime event_time=EventFromComment(PositionGetString(POSITION_COMMENT));
      if(event_time<=0) event_time=g_active_event;
      if(event_time>0 && TimeCurrent()>=event_time+InpForceExitMinutes*60)
         g_trade.PositionClose(ticket,(ulong)InpMaxDeviationPoints);
   }
}

int OnInit()
{
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   if(_Symbol!="EURUSD") Print("PNC research was designed and validated for EURUSD; attached symbol is ",_Symbol,".");
   return INIT_SUCCEEDED;
}

void OnTick()
{
   ManagePositions();
   if(!InpEnableTrading) return;
   datetime event_time=0; string kind="";
   if(!FindCurrentEvent(event_time,kind)) return;
   datetime now=TimeCurrent();
   if(now<event_time+InpSignalDelayMinutes*60 || now>event_time+InpEntryExpiryMinutes*60) return;
   if(event_time==g_last_processed_event) return;
   g_last_processed_event=event_time;
   if(HasOurExposure()) return;
   PlacePullback(event_time,kind);
}

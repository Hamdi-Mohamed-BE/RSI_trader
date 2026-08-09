#property copyright "Mechanical implementation of the supplied Drift VWAP Pullback transcript"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

input group "Drift VWAP rules"
input bool                  InpEnableTrading=true;
input ENUM_TIMEFRAMES       InpSignalTimeframe=PERIOD_M5;
input ENUM_TIMEFRAMES       InpVWAPTimeframe=PERIOD_M15;
input int                   InpDriftLookbackBars=4;
input double                InpMinimumHourlyDriftPercent=0.10;
input bool                  InpRequireFirstPullbackOnly=false;

input group "Stops and targets in NASDAQ index points"
input double                InpIndexPointSize=1.0;
input double                InpStopPoints=80.0;
input double                InpLongTargetPoints=40.0;
input double                InpShortTargetPoints=50.0;

input group "Daily guardrails"
input int                   InpMaximumTradesPerDay=4;
input int                   InpMaximumLossesPerDay=2;
input double                InpRiskPercent=1.0;
input double                InpMaximumSpreadIndexPoints=10.0;
input int                   InpMaxDeviationPoints=50;
input long                  InpMagic=86080850;

input group "New York session"
input int                   InpAnchorHourNY=9;
input int                   InpAnchorMinuteNY=30;
input int                   InpStartTradingHourNY=10;
input int                   InpStartTradingMinuteNY=30;
input int                   InpStopNewTradesHourNY=15;
input int                   InpStopNewTradesMinuteNY=30;
input int                   InpFlatHourNY=15;
input int                   InpFlatMinuteNY=55;
input bool                  InpWeekdaysOnly=true;

input group "Broker clock"
input bool                  InpUseAutomaticLiveServerOffset=true;
input int                   InpTesterServerUTCOffsetHours=0;
input int                   InpManualLiveServerUTCOffsetHours=0;

CTrade trade;
datetime g_last_signal_bar=0;
int g_session_date_key=0;
int g_trades_today=0;
int g_losses_today=0;
int g_previous_drift=0;
bool g_episode_consumed=false;

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

bool NewYorkDateUsesDST(const MqlDateTime &ny)
{
   int march=NthSunday(ny.year,3,2),november=NthSunday(ny.year,11,1);
   if(ny.mon>3 && ny.mon<11) return true;
   if(ny.mon<3 || ny.mon>11) return false;
   if(ny.mon==3) return ny.day>=march;
   return ny.day<november;
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

datetime NewYorkToServer(const MqlDateTime &ny_source)
{
   MqlDateTime ny=ny_source;
   datetime local=StructToTime(ny);
   int offset=(NewYorkDateUsesDST(ny) ? -4 : -5);
   datetime utc=local-offset*3600;
   return utc+ServerUTCOffsetSeconds();
}

int DateKey(const MqlDateTime &p)
{
   return p.year*10000+p.mon*100+p.day;
}

datetime SessionAnchor(const MqlDateTime &ny_date)
{
   MqlDateTime anchor=ny_date;
   anchor.hour=InpAnchorHourNY; anchor.min=InpAnchorMinuteNY; anchor.sec=0;
   return NewYorkToServer(anchor);
}

double NormalizePrice(const double price)
{
   double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tick<=0.0) tick=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(tick<=0.0) return price;
   return NormalizeDouble(MathRound(price/tick)*tick,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
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

double LotsForRisk(const ENUM_ORDER_TYPE order_type,const double entry,const double stop)
{
   double result=0.0;
   if(!OrderCalcProfit(order_type,_Symbol,1.0,entry,stop,result)) return 0.0;
   double one_lot_loss=MathAbs(result);
   if(one_lot_loss<=0.0) return 0.0;
   double risk_cash=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   return NormalizeVolume(risk_cash/one_lot_loss);
}

bool SelectOurPosition(ulong &ticket)
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong candidate=PositionGetTicket(i);
      if(candidate==0) continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)
      {
         ticket=candidate;
         return true;
      }
   }
   return false;
}

void RefreshDailyStats(const MqlDateTime &ny_date)
{
   MqlDateTime start=ny_date;
   start.hour=0; start.min=0; start.sec=0;
   MqlDateTime finish=start;
   finish.hour=23; finish.min=59; finish.sec=59;
   if(!HistorySelect(NewYorkToServer(start),NewYorkToServer(finish))) return;
   int entries=0,losses=0;
   for(int i=0;i<HistoryDealsTotal();i++)
   {
      ulong deal=HistoryDealGetTicket(i);
      if(deal==0) continue;
      if(HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol || HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic) continue;
      long entry=HistoryDealGetInteger(deal,DEAL_ENTRY);
      if(entry==DEAL_ENTRY_IN) entries++;
      if(entry==DEAL_ENTRY_OUT || entry==DEAL_ENTRY_OUT_BY)
      {
         double pnl=HistoryDealGetDouble(deal,DEAL_PROFIT)+HistoryDealGetDouble(deal,DEAL_SWAP)+HistoryDealGetDouble(deal,DEAL_COMMISSION);
         if(pnl<0.0) losses++;
      }
   }
   g_trades_today=entries;
   g_losses_today=losses;
}

bool SessionVWAPState(const MqlDateTime &ny_date,double &vwap,double &prior_vwap,
                      double &latest_close,double &hourly_change_percent)
{
   datetime anchor=SessionAnchor(ny_date);
   datetime last_start=iTime(_Symbol,InpVWAPTimeframe,1);
   if(last_start<=0 || last_start<anchor) return false;
   datetime through=last_start+PeriodSeconds(InpVWAPTimeframe)-1;
   MqlRates rates[];
   int count=CopyRates(_Symbol,InpVWAPTimeframe,anchor,through,rates);
   if(count<InpDriftLookbackBars+1) return false;
   double weighted=0.0,volume=0.0;
   double prior_weighted=0.0,prior_volume=0.0;
   for(int i=0;i<count;i++)
   {
      double vol=(double)rates[i].tick_volume;
      if(vol<=0.0) continue;
      double typical=(rates[i].high+rates[i].low+rates[i].close)/3.0;
      weighted+=typical*vol;
      volume+=vol;
      if(i<count-1)
      {
         prior_weighted+=typical*vol;
         prior_volume+=vol;
      }
   }
   if(volume<=0.0 || prior_volume<=0.0) return false;
   vwap=weighted/volume;
   prior_vwap=prior_weighted/prior_volume;
   latest_close=rates[count-1].close;
   double old_close=rates[count-1-InpDriftLookbackBars].close;
   if(old_close<=0.0) return false;
   hourly_change_percent=(latest_close/old_close-1.0)*100.0;
   return true;
}

int DriftDirection(const MqlDateTime &ny_date)
{
   double vwap=0.0,prior=0.0,close=0.0,change=0.0;
   if(!SessionVWAPState(ny_date,vwap,prior,close,change)) return 0;
   if(close>vwap && vwap>prior && change>=InpMinimumHourlyDriftPercent) return 1;
   if(close<vwap && vwap<prior && change<=-InpMinimumHourlyDriftPercent) return -1;
   return 0;
}

bool SpreadOK()
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || InpIndexPointSize<=0.0) return false;
   return (tick.ask-tick.bid)/InpIndexPointSize<=InpMaximumSpreadIndexPoints;
}

bool EnterTrade(const int direction)
{
   if(!InpEnableTrading || !SpreadOK() || g_trades_today>=InpMaximumTradesPerDay || g_losses_today>=InpMaximumLossesPerDay) return false;
   ulong existing=0;
   if(SelectOurPosition(existing)) return false;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double stop_distance=InpStopPoints*InpIndexPointSize;
   double target_distance=(direction>0 ? InpLongTargetPoints : InpShortTargetPoints)*InpIndexPointSize;
   double stop=NormalizePrice(direction>0 ? entry-stop_distance : entry+stop_distance);
   double target=NormalizePrice(direction>0 ? entry+target_distance : entry-target_distance);
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double minimum=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point;
   if(stop_distance<minimum || target_distance<minimum) return false;
   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=LotsForRisk(type,entry,stop);
   if(lots<=0.0) return false;
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(InpMaxDeviationPoints);
   bool sent=(direction>0 ? trade.Buy(lots,_Symbol,0.0,stop,target,"Drift VWAP long")
                          : trade.Sell(lots,_Symbol,0.0,stop,target,"Drift VWAP short"));
   if(!sent)
   {
      Print("Drift VWAP entry failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
      return false;
   }
   g_trades_today++;
   return true;
}

void ManageFlatTime(const MqlDateTime &ny_now)
{
   int minutes=ny_now.hour*60+ny_now.min;
   int flat=InpFlatHourNY*60+InpFlatMinuteNY;
   if(minutes<flat) return;
   ulong ticket=0;
   if(!SelectOurPosition(ticket)) return;
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(InpMaxDeviationPoints);
   if(!trade.PositionClose(ticket))
      Print("Drift VWAP flat-time close failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
}

void EvaluateClosedSignalBar(const MqlDateTime &ny_now)
{
   int minutes=ny_now.hour*60+ny_now.min;
   int start=InpStartTradingHourNY*60+InpStartTradingMinuteNY;
   int stop=InpStopNewTradesHourNY*60+InpStopNewTradesMinuteNY;
   if(minutes<start || minutes>=stop) return;
   if(InpWeekdaysOnly && (ny_now.day_of_week==0 || ny_now.day_of_week==6)) return;
   RefreshDailyStats(ny_now);
   if(g_trades_today>=InpMaximumTradesPerDay || g_losses_today>=InpMaximumLossesPerDay) return;
   ulong existing=0;
   if(SelectOurPosition(existing)) return;
   int drift=DriftDirection(ny_now);
   if(drift!=g_previous_drift)
   {
      g_episode_consumed=false;
      g_previous_drift=drift;
   }
   if(drift==0 || (InpRequireFirstPullbackOnly && g_episode_consumed)) return;
   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   if(CopyRates(_Symbol,InpSignalTimeframe,1,1,bars)!=1) return;
   bool trigger=(drift>0 ? bars[0].close<bars[0].open : bars[0].close>bars[0].open);
   if(!trigger) return;
   if(EnterTrade(drift)) g_episode_consumed=true;
}

void ProcessStrategy()
{
   datetime now_server=TimeCurrent();
   if(now_server<=0) return;
   MqlDateTime ny_now; TimeToStruct(ServerToNewYork(now_server),ny_now);
   int key=DateKey(ny_now);
   if(key!=g_session_date_key)
   {
      g_session_date_key=key;
      g_previous_drift=0;
      g_episode_consumed=false;
      RefreshDailyStats(ny_now);
   }
   ManageFlatTime(ny_now);
   datetime current_bar=iTime(_Symbol,InpSignalTimeframe,0);
   if(current_bar<=0 || current_bar==g_last_signal_bar) return;
   g_last_signal_bar=current_bar;
   EvaluateClosedSignalBar(ny_now);
}

int OnInit()
{
   if(InpRiskPercent<=0.0 || InpRiskPercent>2.0 || InpDriftLookbackBars<1 ||
      InpMinimumHourlyDriftPercent<=0.0 || InpIndexPointSize<=0.0 || InpStopPoints<=0.0 ||
      InpLongTargetPoints<=0.0 || InpShortTargetPoints<=0.0 ||
      InpMaximumTradesPerDay<1 || InpMaximumLossesPerDay<1 ||
      InpAnchorHourNY<0 || InpAnchorHourNY>23 || InpAnchorMinuteNY<0 || InpAnchorMinuteNY>59 ||
      InpStartTradingHourNY<0 || InpStartTradingHourNY>23 || InpStartTradingMinuteNY<0 || InpStartTradingMinuteNY>59 ||
      InpStopNewTradesHourNY<0 || InpStopNewTradesHourNY>23 || InpStopNewTradesMinuteNY<0 || InpStopNewTradesMinuteNY>59 ||
      InpFlatHourNY<0 || InpFlatHourNY>23 || InpFlatMinuteNY<0 || InpFlatMinuteNY>59)
      return INIT_PARAMETERS_INCORRECT;
   g_last_signal_bar=iTime(_Symbol,InpSignalTimeframe,0);
   EventSetTimer(10);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
}

void OnTick()
{
   ProcessStrategy();
}

void OnTimer()
{
   ProcessStrategy();
}

double OnTester()
{
   double trades=TesterStatistics(STAT_TRADES);
   double profit=TesterStatistics(STAT_PROFIT);
   double pf=TesterStatistics(STAT_PROFIT_FACTOR);
   double dd=TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
   if(trades<80.0 || profit<=0.0 || pf<1.05 || dd<=0.0) return -1000.0+trades;
   return (profit/dd)*MathMin(2.0,MathSqrt(trades/200.0))*MathMin(pf,3.0);
}

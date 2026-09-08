#property strict
#property version   "1.00"
#property description "Calyx XAU demo-stage Markov switch: H4 slow trend in directional regimes and M5 session VWAP snapback in sideways regimes."

#include <Trade/Trade.mqh>

input group "Frozen causal regime switch"
input int      InpRegimeReturnWindow=40;
input double   InpRegimeThreshold=0.02;
input int      InpRegimeHistory=126;
input double   InpRegimeSignalGate=0.00;
input double   InpSidewaysProbability=0.50;

input group "Frozen trend leg"
input ENUM_TIMEFRAMES InpTrendTimeframe=PERIOD_H4;
input double   InpTrendStopATR=1.50;
input double   InpTrendRewardRisk=6.00;

input group "Frozen mean-reversion leg"
input ENUM_TIMEFRAMES InpVWAPTimeframe=PERIOD_M5;
input double   InpVWAPSigma=2.00;
input double   InpMaximumVWAPADX=20.00;
input double   InpVWAPStopATR=1.50;
input double   InpVWAPRewardRisk=3.00;
input int      InpMaximumVWAPTradesPerSession=1;

input group "Execution and safety"
input double   InpRiskPercent=1.00;
input double   InpMaximumSpreadRiskPercent=25.00;
input int      InpMaximumDeviationPoints=100;
input long     InpMagic=969070101;
input bool     InpTesterOnly=false;
input bool     InpDemoOnly=true;
input int      InpTesterServerUTCOffsetHours=0;
input bool     InpUseAutomaticLiveServerOffset=true;
input int      InpManualLiveServerUTCOffsetHours=0;
input bool     InpShowStatus=true;

CTrade trade;
int g_trend_atr=INVALID_HANDLE;
int g_trend_ema=INVALID_HANDLE;
int g_vwap_atr=INVALID_HANDLE;
int g_vwap_adx=INVALID_HANDLE;
datetime g_last_h4=0;
datetime g_last_m5=0;
datetime g_last_trend_entry=0;
datetime g_cached_d1=0;
int g_cached_state=1;
double g_cached_sideways=0.0;
double g_cached_signal=0.0;

int ScaleTrendBars(const int trading_days)
{
   if(InpTrendTimeframe==PERIOD_H4)return MathMax(1,trading_days*6);
   return MathMax(1,trading_days);
}

bool ReadBufferValue(const int handle,const int buffer,const int shift,double &value)
{
   double values[1];
   if(handle==INVALID_HANDLE || CopyBuffer(handle,buffer,shift,1,values)!=1)return false;
   value=values[0];return MathIsValidNumber(value);
}

int SignOf(const double value)
{
   if(value>0.0)return 1;
   if(value<0.0)return -1;
   return 0;
}

int StateAtShift(const int shift)
{
   const double recent=iClose(_Symbol,PERIOD_D1,shift);
   const double past=iClose(_Symbol,PERIOD_D1,shift+InpRegimeReturnWindow);
   if(recent<=0.0 || past<=0.0)return -1;
   const double change=recent/past-1.0;
   if(change>InpRegimeThreshold)return 2;
   if(change<-InpRegimeThreshold)return 0;
   return 1;
}

bool CurrentRegime(int &state,double &sideways_probability,double &signal)
{
   const datetime completed=iTime(_Symbol,PERIOD_D1,1);
   if(completed<=0)return false;
   if(completed==g_cached_d1)
   {
      state=g_cached_state;sideways_probability=g_cached_sideways;signal=g_cached_signal;return true;
   }
   if(Bars(_Symbol,PERIOD_D1)<InpRegimeHistory+InpRegimeReturnWindow+4)return false;
   double counts[3][3];
   for(int from=0;from<3;from++)for(int to=0;to<3;to++)counts[from][to]=1.0;
   // Exclude the transition into the newest/current completed label. This is
   // the same conservative no-lookahead rule used by the research overlay.
   for(int older=InpRegimeHistory+2;older>=3;older--)
   {
      const int from_state=StateAtShift(older);
      const int to_state=StateAtShift(older-1);
      if(from_state<0 || to_state<0)return false;
      counts[from_state][to_state]+=1.0;
   }
   state=StateAtShift(1);if(state<0)return false;
   const double total=counts[state][0]+counts[state][1]+counts[state][2];
   if(total<=0.0)return false;
   const double bear=counts[state][0]/total;
   sideways_probability=counts[state][1]/total;
   const double bull=counts[state][2]/total;
   signal=bull-bear;
   g_cached_d1=completed;g_cached_state=state;g_cached_sideways=sideways_probability;g_cached_signal=signal;
   return true;
}

bool DirectionalRegimeAllows(const int direction)
{
   int state=1;double sideways=0.0,signal=0.0;
   if(!CurrentRegime(state,sideways,signal))return false;
   return state!=1 && direction*signal>InpRegimeSignalGate;
}

bool SidewaysRegimeAllows()
{
   int state=1;double sideways=0.0,signal=0.0;
   if(!CurrentRegime(state,sideways,signal))return false;
   return state==1 && sideways>=InpSidewaysProbability;
}

double NormalizePrice(const double raw)
{
   double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tick<=0.0)tick=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   return NormalizeDouble(MathRound(raw/tick)*tick,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

double NormalizeVolume(const double raw)
{
   const double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   const double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   const double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(raw<minimum || minimum<=0.0 || step<=0.0)return 0.0;
   return NormalizeDouble(MathFloor((MathMin(raw,maximum)+1e-12)/step)*step,8);
}

double LotsForRisk(const ENUM_ORDER_TYPE type,const double entry,const double stop)
{
   double pnl=0.0;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,pnl) || pnl==0.0)return 0.0;
   return NormalizeVolume(AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0/MathAbs(pnl));
}

bool SelectOurPosition(ulong &ticket,string &comment)
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      const ulong candidate=PositionGetTicket(i);
      if(candidate==0 || !PositionSelectByTicket(candidate))continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol || PositionGetInteger(POSITION_MAGIC)!=InpMagic)continue;
      ticket=candidate;comment=PositionGetString(POSITION_COMMENT);return true;
   }
   return false;
}

bool SpreadOK(const double risk)
{
   MqlTick tick;if(!SymbolInfoTick(_Symbol,tick) || risk<=0.0)return false;
   return 100.0*(tick.ask-tick.bid)/risk<=InpMaximumSpreadRiskPercent;
}

bool Submit(const int side,const double stop_distance,const double reward_risk,const string comment)
{
   if(stop_distance<=0.0)return false;
   MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return false;
   const double entry=side>0?tick.ask:tick.bid;
   const double stop=NormalizePrice(entry-side*stop_distance);
   const double target=NormalizePrice(entry+side*reward_risk*stop_distance);
   const double risk=MathAbs(entry-stop);
   if(risk<=0.0 || !SpreadOK(risk))return false;
   const double minimum=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(risk<minimum || MathAbs(target-entry)<minimum)return false;
   const ENUM_ORDER_TYPE type=side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   const double lots=LotsForRisk(type,entry,stop);if(lots<=0.0)return false;
   trade.SetExpertMagicNumber((ulong)InpMagic);trade.SetDeviationInPoints(InpMaximumDeviationPoints);trade.SetTypeFillingBySymbol(_Symbol);
   const bool sent=side>0?trade.Buy(lots,_Symbol,0.0,stop,target,comment):trade.Sell(lots,_Symbol,0.0,stop,target,comment);
   if(!sent)Print("Calyx regime-switch entry failed: ",trade.ResultRetcodeDescription());
   return sent;
}

bool TrendSignal(int &direction)
{
   const double current=iClose(_Symbol,InpTrendTimeframe,1);
   if(current<=0.0)return false;
   const int horizons[3]={21,63,126};double vote=0.0;
   for(int i=0;i<3;i++)
   {
      const double past=iClose(_Symbol,InpTrendTimeframe,1+ScaleTrendBars(horizons[i]));
      if(past<=0.0)return false;
      vote+=(double)SignOf(current/past-1.0);
   }
   direction=SignOf(vote/3.0);if(direction==0)return true;
   double ema=0.0;if(!ReadBufferValue(g_trend_ema,0,1,ema))return false;
   if((direction>0 && current<=ema) || (direction<0 && current>=ema))direction=0;
   return true;
}

void EvaluateTrend()
{
   ulong ticket=0;string comment="";if(SelectOurPosition(ticket,comment))return;
   if(g_last_trend_entry>0 && TimeCurrent()-g_last_trend_entry<86400)return;
   int direction=0;if(!TrendSignal(direction) || direction==0 || !DirectionalRegimeAllows(direction))return;
   double atr=0.0;if(!ReadBufferValue(g_trend_atr,0,1,atr) || atr<=0.0)return;
   if(Submit(direction,InpTrendStopATR*atr,InpTrendRewardRisk,"Calyx Regime Trend"))g_last_trend_entry=TimeCurrent();
}

int NthSunday(const int year,const int month,const int occurrence)
{
   MqlDateTime x={0};x.year=year;x.mon=month;x.day=1;x.hour=12;
   datetime first=StructToTime(x);TimeToStruct(first,x);
   return 1+((7-x.day_of_week)%7)+(occurrence-1)*7;
}

int NewYorkUTCOffset(const datetime utc)
{
   MqlDateTime x;TimeToStruct(utc,x);MqlDateTime start={0},finish={0};
   start.year=x.year;start.mon=3;start.day=NthSunday(x.year,3,2);start.hour=7;
   finish.year=x.year;finish.mon=11;finish.day=NthSunday(x.year,11,1);finish.hour=6;
   return utc>=StructToTime(start) && utc<StructToTime(finish)?-4:-5;
}

int ServerUTCOffsetSeconds()
{
   if((bool)MQLInfoInteger(MQL_TESTER))return InpTesterServerUTCOffsetHours*3600;
   if(!InpUseAutomaticLiveServerOffset)return InpManualLiveServerUTCOffsetHours*3600;
   datetime server=TimeTradeServer();if(server<=0)server=TimeCurrent();const datetime utc=TimeGMT();
   if(utc<=0)return InpManualLiveServerUTCOffsetHours*3600;
   return (int)MathRound((double)(server-utc)/1800.0)*1800;
}

datetime ServerToUTC(const datetime value){return value-ServerUTCOffsetSeconds();}
datetime NewYorkLocal(const datetime server){const datetime utc=ServerToUTC(server);return utc+NewYorkUTCOffset(utc)*3600;}

datetime NewYorkToServer(MqlDateTime &local)
{
   const datetime local_value=StructToTime(local);
   const datetime guess=local_value+5*3600;
   const datetime utc=local_value-NewYorkUTCOffset(guess)*3600;
   return utc+ServerUTCOffsetSeconds();
}

bool VWAPSessionBounds(const datetime server,datetime &from,datetime &to)
{
   MqlDateTime local;TimeToStruct(NewYorkLocal(server),local);
   local.hour=9;local.min=30;local.sec=0;from=NewYorkToServer(local);
   local.hour=12;local.min=0;local.sec=0;to=NewYorkToServer(local);
   return to>from;
}

int NewYorkDateKey(const datetime server)
{
   MqlDateTime local;TimeToStruct(NewYorkLocal(server),local);return local.year*10000+local.mon*100+local.day;
}

bool InVWAPEntryWindow(const datetime server)
{
   MqlDateTime local;TimeToStruct(NewYorkLocal(server),local);const int minute=local.hour*60+local.min;
   return minute>=600 && minute<705;
}

int VWAPTradesInSession(const datetime from,const datetime to)
{
   if(!HistorySelect(from,to))return 0;int count=0;
   for(int i=HistoryDealsTotal()-1;i>=0;i--)
   {
      const ulong deal=HistoryDealGetTicket(i);if(deal==0)continue;
      if(HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol || HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic || HistoryDealGetInteger(deal,DEAL_ENTRY)!=DEAL_ENTRY_IN)continue;
      if(StringFind(HistoryDealGetString(deal,DEAL_COMMENT),"Regime VWAP")>=0)count++;
   }
   return count;
}

bool SessionVWAP(const datetime signal_open,double &vwap,double &deviation)
{
   datetime from,to;if(!VWAPSessionBounds(signal_open,from,to))return false;
   MqlRates rates[];const int count=CopyRates(_Symbol,InpVWAPTimeframe,from,signal_open-1,rates);
   if(count<6)return false;
   double volume=0.0,pv=0.0,p2v=0.0;
   for(int i=0;i<count;i++)
   {
      const double weight=(double)MathMax(1,rates[i].tick_volume);
      const double price=(rates[i].high+rates[i].low+rates[i].close)/3.0;
      volume+=weight;pv+=price*weight;p2v+=price*price*weight;
   }
   if(volume<=0.0)return false;
   vwap=pv/volume;deviation=MathSqrt(MathMax(0.0,p2v/volume-vwap*vwap));return deviation>0.0;
}

void EvaluateVWAP()
{
   if(!SidewaysRegimeAllows())return;
   MqlRates bars[];ArraySetAsSeries(bars,true);if(CopyRates(_Symbol,InpVWAPTimeframe,1,1,bars)!=1)return;
   const MqlRates bar=bars[0];if(!InVWAPEntryWindow(bar.time))return;
   datetime from,to;if(!VWAPSessionBounds(bar.time,from,to) || bar.time<from || bar.time>=to)return;
   if(VWAPTradesInSession(from,to)>=InpMaximumVWAPTradesPerSession)return;
   ulong ticket=0;string comment="";if(SelectOurPosition(ticket,comment))return;
   double adx=0.0;if(!ReadBufferValue(g_vwap_adx,0,1,adx) || adx>InpMaximumVWAPADX)return;
   double vwap=0.0,deviation=0.0;if(!SessionVWAP(bar.time,vwap,deviation))return;
   MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return;const double spread=tick.ask-tick.bid;
   const double upper=vwap+InpVWAPSigma*deviation,lower=vwap-InpVWAPSigma*deviation;
   const bool long_signal=bar.low+spread<=lower && bar.close+spread>lower;
   const bool short_signal=bar.high>=upper && bar.close<upper;
   if(long_signal==short_signal)return;
   double atr=0.0;if(!ReadBufferValue(g_vwap_atr,0,1,atr) || atr<=0.0)return;
   Submit(long_signal?1:-1,InpVWAPStopATR*atr,InpVWAPRewardRisk,"Calyx Regime VWAP");
}

void CloseExpiredVWAP()
{
   ulong ticket=0;string comment="";if(!SelectOurPosition(ticket,comment) || StringFind(comment,"Regime VWAP")<0)return;
   datetime from,to;if(!VWAPSessionBounds(TimeCurrent(),from,to))return;
   if(TimeCurrent()>=to || TimeCurrent()<from)
   {
      trade.SetExpertMagicNumber((ulong)InpMagic);trade.SetDeviationInPoints(InpMaximumDeviationPoints);trade.SetTypeFillingBySymbol(_Symbol);
      trade.PositionClose(ticket);
   }
}

void DrawStatus()
{
   if(!InpShowStatus)return;
   int state=1;double sideways=0.0,signal=0.0;
   if(!CurrentRegime(state,sideways,signal)){Comment("Calyx XAU Regime Switch\nWaiting for D1 regime history");return;}
   const string name=state==0?"BEAR":state==2?"BULL":"SIDEWAYS";
   Comment(StringFormat("Calyx XAU Regime Switch — DEMO STAGE\nRegime: %s | P(sideways): %.1f%% | signal: %+.3f\nRisk: %.2f%% hard locked",name,100.0*sideways,signal,InpRiskPercent));
}

void Process()
{
   CloseExpiredVWAP();
   const datetime h4=iTime(_Symbol,InpTrendTimeframe,0);
   if(h4>0 && h4!=g_last_h4){g_last_h4=h4;EvaluateTrend();}
   const datetime m5=iTime(_Symbol,InpVWAPTimeframe,0);
   if(m5>0 && m5!=g_last_m5){g_last_m5=m5;EvaluateVWAP();}
   DrawStatus();
}

int OnInit()
{
   if(InpTesterOnly && !(bool)MQLInfoInteger(MQL_TESTER))return INIT_FAILED;
   if(!(bool)MQLInfoInteger(MQL_TESTER) && InpDemoOnly && (ENUM_ACCOUNT_TRADE_MODE)AccountInfoInteger(ACCOUNT_TRADE_MODE)==ACCOUNT_TRADE_MODE_REAL)
   {
      Print("Calyx XAU Regime Switch is demo-stage and will not start on a real-money account while InpDemoOnly=true.");
      return INIT_FAILED;
   }
   if(InpRiskPercent<=0.0 || MathAbs(InpRiskPercent-1.0)>1e-9 || InpRegimeReturnWindow<2 || InpRegimeHistory<60 || InpRegimeThreshold<=0.0 || InpSidewaysProbability<0.0 || InpSidewaysProbability>1.0)return INIT_PARAMETERS_INCORRECT;
   g_trend_atr=iATR(_Symbol,InpTrendTimeframe,14);
   g_trend_ema=iMA(_Symbol,InpTrendTimeframe,ScaleTrendBars(100),0,MODE_EMA,PRICE_CLOSE);
   g_vwap_atr=iATR(_Symbol,InpVWAPTimeframe,14);
   g_vwap_adx=iADX(_Symbol,InpVWAPTimeframe,14);
   if(g_trend_atr==INVALID_HANDLE || g_trend_ema==INVALID_HANDLE || g_vwap_atr==INVALID_HANDLE || g_vwap_adx==INVALID_HANDLE)return INIT_FAILED;
   trade.SetExpertMagicNumber((ulong)InpMagic);trade.SetDeviationInPoints(InpMaximumDeviationPoints);trade.SetTypeFillingBySymbol(_Symbol);
   g_last_h4=iTime(_Symbol,InpTrendTimeframe,0);g_last_m5=iTime(_Symbol,InpVWAPTimeframe,0);
   EventSetTimer(10);DrawStatus();return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();Comment("");
   if(g_trend_atr!=INVALID_HANDLE)IndicatorRelease(g_trend_atr);
   if(g_trend_ema!=INVALID_HANDLE)IndicatorRelease(g_trend_ema);
   if(g_vwap_atr!=INVALID_HANDLE)IndicatorRelease(g_vwap_atr);
   if(g_vwap_adx!=INVALID_HANDLE)IndicatorRelease(g_vwap_adx);
}

void OnTick(){Process();}
void OnTimer(){Process();}

double OnTester()
{
   const double trades=TesterStatistics(STAT_TRADES),profit=TesterStatistics(STAT_PROFIT),pf=TesterStatistics(STAT_PROFIT_FACTOR),dd=TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
   if(trades<20 || profit<=0.0 || pf<1.0 || dd<=0.0)return -1000.0+trades;
   return profit/dd*MathMin(pf,3.0)*MathMin(2.0,MathSqrt(trades/100.0));
}

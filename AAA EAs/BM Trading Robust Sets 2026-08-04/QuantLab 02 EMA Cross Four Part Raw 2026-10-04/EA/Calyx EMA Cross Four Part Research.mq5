#property copyright "Calyx independent EMA-cross four-part research"
#property version "1.00"
#property strict
// Inspired by the publicly described NQBlade concept, not its proprietary rules.
// Numerical settings and confirmation/time limits are our frozen assumptions.
// Tester-only. Not installed into or enabled on any active trading account.
#include <Trade/Trade.mqh>

input group "Independent signal assumptions"
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_M3;
input int InpFastEMA=9;
input int InpSlowEMA=21;
input int InpADXPeriod=14;
input double InpMinimumADX=20.0;
input bool InpRequireDI=true;
input int InpATRPeriod=14;
input double InpStopATR=2.0;

input group "Four equal planned-risk portions, not four independent risk budgets"
input double InpBasketRiskPercent=1.0;
input double InpTarget1R=1.0;
input double InpTarget2R=2.0;
input double InpTarget3R=3.0;
input double InpRunnerArmR=1.0;
input int InpMaximumHoldingMinutes=1440;

input group "Independent session and risk-boundary assumptions"
input int InpEntryStartHourNY=9;
input int InpEntryStartMinuteNY=30;
input int InpEntryEndHourNY=15;
input int InpEntryEndMinuteNY=30;
input bool InpFridayFlatten=true;
input int InpFridayCloseHourNY=15;
input int InpFridayCloseMinuteNY=55;
input int InpServerUtcOffsetHours=0;
input long InpBaseMagic=864100;
input int InpDeviationPoints=50;

CTrade g_trade;
int g_fast=INVALID_HANDLE,g_slow=INVALID_HANDLE,g_adx=INVALID_HANDLE,g_atr=INVALID_HANDLE;
datetime g_last_bar=0,g_last_entry_attempt=0,g_last_runner_update=0;
bool g_aborting=false;
int g_baskets=0,g_skips=0,g_entry_errors=0,g_modify_errors=0,g_close_errors=0;

datetime UtcDate(const int year,const int month,const int day,const int hour)
  {
   MqlDateTime p;ZeroMemory(p);p.year=year;p.mon=month;p.day=day;p.hour=hour;
   return StructToTime(p);
  }
int NthSunday(const int year,const int month,const int nth)
  {
   MqlDateTime p;TimeToStruct(UtcDate(year,month,1,0),p);
   return 1+(7-p.day_of_week)%7+(nth-1)*7;
  }
datetime NewYork(const datetime server)
  {
   datetime utc=server-InpServerUtcOffsetHours*3600;MqlDateTime p;TimeToStruct(utc,p);
   datetime start=UtcDate(p.year,3,NthSunday(p.year,3,2),7);
   datetime end=UtcDate(p.year,11,NthSunday(p.year,11,1),6);
   return utc+(utc>=start && utc<end ? -4 : -5)*3600;
  }
int DateKey(const datetime server)
  {
   MqlDateTime p;TimeToStruct(NewYork(server),p);return p.year*10000+p.mon*100+p.day;
  }
bool SignalSession(const datetime bar_open)
  {
   MqlDateTime p;TimeToStruct(NewYork(bar_open),p);int minute=p.hour*60+p.min;
   return p.day_of_week>=1 && p.day_of_week<=5 &&
          minute>=InpEntryStartHourNY*60+InpEntryStartMinuteNY &&
          minute<InpEntryEndHourNY*60+InpEntryEndMinuteNY;
  }
bool FridayClose(const datetime now)
  {
   if(!InpFridayFlatten) return false;
   MqlDateTime p;TimeToStruct(NewYork(now),p);
   return p.day_of_week==5 && p.hour*60+p.min>=InpFridayCloseHourNY*60+InpFridayCloseMinuteNY;
  }
bool BrokerSessionOpen()
  {
   MqlDateTime p;TimeToStruct(TimeCurrent(),p);int seconds=p.hour*3600+p.min*60+p.sec;
   for(uint i=0;i<20;i++)
     {
      datetime from=0,to=0;
      if(!SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)p.day_of_week,i,from,to)) break;
      int a=(int)((long)from%86400),b=(int)((long)to%86400);
      if(a==b || (a<b && seconds>=a && seconds<b) || (a>b && (seconds>=a || seconds<b))) return true;
     }
   return false;
  }
bool Ours()
  {
   long magic=PositionGetInteger(POSITION_MAGIC);
   return PositionGetString(POSITION_SYMBOL)==_Symbol && magic>=InpBaseMagic+1 && magic<=InpBaseMagic+4;
  }
bool FindLeg(const int leg,ulong &ticket)
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ticket=PositionGetTicket(i);
      if(ticket>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpBaseMagic+leg) return true;
     }
   ticket=0;return false;
  }
bool HasBasket()
  {
   for(int i=PositionsTotal()-1;i>=0;i--) if(PositionGetTicket(i)>0 && Ours()) return true;
   return false;
  }
bool EnteredOnDate(const int key)
  {
   if(!HistorySelect(TimeCurrent()-4*86400,TimeCurrent()+1)) return true;
   for(int i=HistoryDealsTotal()-1;i>=0;i--)
     {
      ulong deal=HistoryDealGetTicket(i);if(deal==0) continue;
      long magic=HistoryDealGetInteger(deal,DEAL_MAGIC);
      if(magic<InpBaseMagic+1 || magic>InpBaseMagic+4 || HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol) continue;
      if(HistoryDealGetInteger(deal,DEAL_ENTRY)!=DEAL_ENTRY_IN) continue;
      if(DateKey((datetime)HistoryDealGetInteger(deal,DEAL_TIME))==key) return true;
     }
   return false;
  }
double TickSize()
  {
   double size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   return size>0.0 ? size : SymbolInfoDouble(_Symbol,SYMBOL_POINT);
  }
double Price(const double raw,const bool round_down)
  {
   double size=TickSize();
   double steps=raw/size;
   return NormalizeDouble((round_down ? MathFloor(steps+1e-9) : MathCeil(steps-1e-9))*size,
                          (int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
  }
double BrokerGap()
  {
   return MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                  (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*SymbolInfoDouble(_Symbol,SYMBOL_POINT)+TickSize();
  }
bool Value(const int handle,const int buffer,const int shift,double &value)
  {
   double a[];if(CopyBuffer(handle,buffer,shift,1,a)!=1 || !MathIsValidNumber(a[0])) return false;
   value=a[0];return true;
  }
double Lots(const ENUM_ORDER_TYPE type,const double entry,const double stop,const double cash)
  {
   double loss=0.0;if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,loss) || MathAbs(loss)<=0.0) return 0.0;
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   if(step<=0.0 || minimum<=0.0) return 0.0;
   double lots=MathFloor((MathMin(cash/MathAbs(loss),maximum)+1e-12)/step)*step;
   if(lots<minimum-1e-12) return 0.0;
   return NormalizeDouble(lots,8);
  }
string Key(const string suffix)
  {
   return "QNBR."+(string)InpBaseMagic+"."+(string)PositionGetInteger(POSITION_IDENTIFIER)+"."+suffix;
  }
void CloseAll()
  {
   if(!BrokerSessionOpen()) return;
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);if(ticket==0 || !Ours()) continue;
      g_trade.SetExpertMagicNumber((ulong)PositionGetInteger(POSITION_MAGIC));
      if(!g_trade.PositionClose(ticket,(ulong)InpDeviationPoints))
        {g_close_errors++;Print("QNB_CLOSE_FAILED ",g_trade.ResultRetcodeDescription());}
     }
  }

void OpenBasket(const int direction,const double atr,const int date_key)
  {
   if(!BrokerSessionOpen() || HasBasket()) return;
   MqlTick tick;if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0) return;
   double quote=(direction>0 ? tick.ask : tick.bid);
   double stop=quote-direction*InpStopATR*atr;
   stop=(direction>0 ? MathMin(stop,tick.bid-BrokerGap()) : MathMax(stop,tick.ask+BrokerGap()));
   stop=Price(stop,direction>0);
   double budget=AccountInfoDouble(ACCOUNT_EQUITY)*InpBasketRiskPercent/100.0;
   double part=budget/4.0;
   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   if(part<=0.0 || Lots(type,quote,stop,part)<=0.0)
     {g_skips++;PrintFormat("QNB_SKIP_MIN_LOT date=%d quarter_budget=%.2f",date_key,part);return;}
   g_last_entry_attempt=TimeCurrent();
   for(int leg=1;leg<=4;leg++)
     {
      if(!SymbolInfoTick(_Symbol,tick)) {g_entry_errors++;g_aborting=true;CloseAll();return;}
      quote=(direction>0 ? tick.ask : tick.bid);
      double lots=Lots(type,quote,stop,part);
      double rr=(leg==1 ? InpTarget1R : leg==2 ? InpTarget2R : InpTarget3R);
      double target=(leg<4 ? Price(quote+direction*rr*MathAbs(quote-stop),direction<0) : 0.0);
      g_trade.SetExpertMagicNumber((ulong)(InpBaseMagic+leg));
      string comment="QNB"+(string)date_key+"_L"+(string)leg;
      bool sent=false;
      if(lots>0.0)
         sent=(direction>0 ? g_trade.Buy(lots,_Symbol,0.0,stop,target,comment) :
                            g_trade.Sell(lots,_Symbol,0.0,stop,target,comment));
      ulong ticket=0;
      if(!sent || g_trade.ResultRetcode()!=TRADE_RETCODE_DONE || !FindLeg(leg,ticket))
        {
         g_entry_errors++;g_aborting=true;
         PrintFormat("QNB_ENTRY_FAILED date=%d leg=%d lots=%.8f reason=%s",date_key,leg,lots,g_trade.ResultRetcodeDescription());
         CloseAll();return;
        }
      double risk=MathAbs(PositionGetDouble(POSITION_PRICE_OPEN)-PositionGetDouble(POSITION_SL));
      GlobalVariableSet(Key("R"),risk);
      GlobalVariableSet(Key("ARM"),0.0);
      double requested_cash=0.0,actual_cash=0.0;
      if(!OrderCalcProfit(type,_Symbol,lots,quote,stop,requested_cash) ||
         !OrderCalcProfit(type,_Symbol,lots,PositionGetDouble(POSITION_PRICE_OPEN),stop,actual_cash))
        {
         g_entry_errors++;g_aborting=true;
         PrintFormat("QNB_ENTRY_FAILED date=%d leg=%d risk audit unavailable",date_key,leg);
         CloseAll();return;
        }
      PrintFormat("QNB_ENTRY date=%d leg=%d direction=%d lots=%.8f actual_open=%.8f initial_sl=%.8f requested_tp=%.8f quarter_cash=%.4f requested_stop_cash=%.4f actual_stop_cash=%.4f",
                  date_key,leg,direction,lots,PositionGetDouble(POSITION_PRICE_OPEN),stop,target,part,MathAbs(requested_cash),MathAbs(actual_cash));
     }
   g_baskets++;
  }
void ManageBasket()
  {
   if(!HasBasket()) {g_aborting=false;return;}
   bool expired=false;
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      if(PositionGetTicket(i)==0 || !Ours()) continue;
      if(TimeCurrent()>=(datetime)PositionGetInteger(POSITION_TIME)+InpMaximumHoldingMinutes*60) expired=true;
     }
   if(g_aborting || expired || FridayClose(TimeCurrent())) {CloseAll();return;}
   ulong runner=0;if(!FindLeg(4,runner) || !BrokerSessionOpen()) return;
   MqlTick tick;if(!SymbolInfoTick(_Symbol,tick)) return;
   bool buy=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY;
   double open=PositionGetDouble(POSITION_PRICE_OPEN),old_stop=PositionGetDouble(POSITION_SL);
   string risk_key=Key("R"),arm_key=Key("ARM");
   double risk=(GlobalVariableCheck(risk_key) ? GlobalVariableGet(risk_key) : MathAbs(open-old_stop));
   if(risk<=0.0) return;
   double favourable=(buy ? tick.bid-open : open-tick.ask);
   if(favourable>=InpRunnerArmR*risk) GlobalVariableSet(arm_key,1.0);
   if(!GlobalVariableCheck(arm_key) || GlobalVariableGet(arm_key)<0.5) return;
   datetime bar=iTime(_Symbol,InpSignalTimeframe,0);
   if(bar<=0 || bar==g_last_runner_update) return;
   double ema=0.0;if(!Value(g_slow,0,1,ema) || ema<=0.0) return;
   g_last_runner_update=bar;
   double candidate=(buy ? MathMin(ema,tick.bid-BrokerGap()) : MathMax(ema,tick.ask+BrokerGap()));
   candidate=Price(candidate,buy);
   bool improves=(buy ? candidate>old_stop+TickSize()*0.5 : candidate<old_stop-TickSize()*0.5);
   if(!improves) return;
   g_trade.SetExpertMagicNumber((ulong)(InpBaseMagic+4));
   if(!g_trade.PositionModify(runner,candidate,0.0))
     {g_modify_errors++;Print("QNB_MODIFY_FAILED ",g_trade.ResultRetcodeDescription());}
  }
void ProcessSignal()
  {
   if(HasBasket() || g_aborting || !BrokerSessionOpen() || FridayClose(TimeCurrent())) return;
   MqlRates rates[];ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,InpSignalTimeframe,0,3,rates)!=3 || !SignalSession(rates[1].time)) return;
   int date_key=DateKey(rates[1].time);
   if(EnteredOnDate(date_key) || (g_last_entry_attempt>0 && DateKey(g_last_entry_attempt)==date_key)) return;
   double fast=0,slow=0,pfast=0,pslow=0,adx=0,plus_di=0,minus_di=0,atr=0;
   if(!Value(g_fast,0,1,fast) || !Value(g_slow,0,1,slow) ||
      !Value(g_fast,0,2,pfast) || !Value(g_slow,0,2,pslow) ||
      !Value(g_adx,0,1,adx) || !Value(g_adx,1,1,plus_di) ||
      !Value(g_adx,2,1,minus_di) || !Value(g_atr,0,1,atr) || atr<=0.0) return;
   int direction=(pfast<=pslow && fast>slow ? 1 : pfast>=pslow && fast<slow ? -1 : 0);
   if(direction==0 || adx<InpMinimumADX) return;
   if(InpRequireDI && (direction>0 ? plus_di<=minus_di : minus_di<=plus_di)) return;
   PrintFormat("QNB_SIGNAL date=%d closed_bar=%s direction=%d fast=%.8f slow=%.8f previous_fast=%.8f previous_slow=%.8f adx=%.8f plus_di=%.8f minus_di=%.8f atr=%.8f",
               date_key,TimeToString(rates[1].time,TIME_DATE|TIME_MINUTES),direction,fast,slow,pfast,pslow,adx,plus_di,minus_di,atr);
   OpenBasket(direction,atr,date_key);
  }
int OnInit()
  {
   if(!(bool)MQLInfoInteger(MQL_TESTER))
     {Print("QNB_RESEARCH_ONLY: tester-only; no live or demo-account execution.");return INIT_FAILED;}
   if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)
     {Print("QNB_REQUIRES_HEDGING");return INIT_FAILED;}
   if(InpSignalTimeframe!=PERIOD_M3 || InpFastEMA<2 || InpSlowEMA<=InpFastEMA ||
      InpADXPeriod<2 || InpATRPeriod<2 || InpMinimumADX<0.0 || InpStopATR<=0.0 ||
      InpBasketRiskPercent<=0.0 || InpBasketRiskPercent>1.0 || InpTarget1R<=0.0 ||
      InpTarget2R<=InpTarget1R || InpTarget3R<=InpTarget2R || InpRunnerArmR<0.0 ||
      InpMaximumHoldingMinutes<=0 || InpBaseMagic<=0 || InpDeviationPoints<0 ||
      InpEntryStartHourNY<0 || InpEntryStartHourNY>23 || InpEntryStartMinuteNY<0 || InpEntryStartMinuteNY>59 ||
      InpEntryEndHourNY<0 || InpEntryEndHourNY>23 || InpEntryEndMinuteNY<0 || InpEntryEndMinuteNY>59 ||
      InpEntryEndHourNY*60+InpEntryEndMinuteNY<=InpEntryStartHourNY*60+InpEntryStartMinuteNY ||
      InpFridayCloseHourNY<0 || InpFridayCloseHourNY>23 || InpFridayCloseMinuteNY<0 || InpFridayCloseMinuteNY>59)
      return INIT_PARAMETERS_INCORRECT;
   g_fast=iMA(_Symbol,InpSignalTimeframe,InpFastEMA,0,MODE_EMA,PRICE_CLOSE);
   g_slow=iMA(_Symbol,InpSignalTimeframe,InpSlowEMA,0,MODE_EMA,PRICE_CLOSE);
   g_adx=iADX(_Symbol,InpSignalTimeframe,InpADXPeriod);g_atr=iATR(_Symbol,InpSignalTimeframe,InpATRPeriod);
   if(g_fast==INVALID_HANDLE || g_slow==INVALID_HANDLE || g_adx==INVALID_HANDLE || g_atr==INVALID_HANDLE) return INIT_FAILED;
   g_trade.SetTypeFillingBySymbol(_Symbol);g_trade.SetDeviationInPoints(InpDeviationPoints);
   g_last_bar=iTime(_Symbol,InpSignalTimeframe,0);
   Print("QNB_ASSUMED_PARAMETERS: independent EMA9/21 four-portion concept; 1% TOTAL basket risk, not vendor settings.");
   return INIT_SUCCEEDED;
  }
void OnTick()
  {
   ManageBasket();
   datetime bar=iTime(_Symbol,InpSignalTimeframe,0);
   if(bar<=0 || bar==g_last_bar) return;
   g_last_bar=bar;ProcessSignal();
  }
void OnDeinit(const int reason)
  {
   if(g_fast!=INVALID_HANDLE) IndicatorRelease(g_fast);
   if(g_slow!=INVALID_HANDLE) IndicatorRelease(g_slow);
   if(g_adx!=INVALID_HANDLE) IndicatorRelease(g_adx);
   if(g_atr!=INVALID_HANDLE) IndicatorRelease(g_atr);
   PrintFormat("QNB_SUMMARY baskets=%d minlot_skips=%d entry_errors=%d modify_errors=%d close_errors=%d",
               g_baskets,g_skips,g_entry_errors,g_modify_errors,g_close_errors);
  }

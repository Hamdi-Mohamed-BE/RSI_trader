#property strict
#property version "1.00"
#property description "Research only (2026-10-19). FTSE 100 H1: Rule 1 Monday RSI<40 buy (2.5ATR stop), Rule 2 close far below SMA40 + RSI<35 buy (2ATR stop),"
#property description "both 2R target and 24h time exit. Random-entry control mode. Rules: RULES.md."
#include <Trade/Trade.mqh>

input double InpRiskPercent=0.75;        // % of equity per trade; lots rounded UP to the step (minimum lot if needed)
input bool   InpRule1=true;
input bool   InpRule2=true;
input int    InpR1DayMode=0;             // 0 = Monday only (London day); 1 = control: Tuesday-Friday, one per day
input double InpR1Rsi=40.0;
input double InpR1StopAtr=2.5;
input double InpR2Rsi=35.0;
input double InpR2DistAtr=1.5;           // close <= SMA - dist*ATR
input double InpR2StopAtr=2.0;
input int    InpR2MaPeriod=40;
input double InpRewardRisk=2.0;
input int    InpMaxHoldHours=24;
input int    InpRsiPeriod=14;
input int    InpAtrPeriod=14;
input int    InpSessionMode=0;           // 0 = all broker hours; 1 = London cash session 08:00-16:30 UK time (entry time)
input bool   InpRandomMode=false;        // control: random long entries with Rule-2 exits, rules disabled
input double InpRandomProb=0.02;         // per closed H1 bar while flat
input int    InpRandomSeed=1;
input int    InpServerUtcOffsetHours=0;  // Exness server = UTC
input int    InpMaximumDeviationPoints=1000;
input long   InpMagic=1910260;

CTrade trade;
int hRsi=INVALID_HANDLE,hAtr=INVALID_HANDLE,hMa=INVALID_HANDLE;
datetime lastBar=0,lastR1Day=0,lastClose=0;
long bars=0,r1Signals=0,r1Entries=0,r2Signals=0,r2Entries=0,r2FlatBars=0,rngEntries=0,skippedStops=0,skippedMargin=0,placeFails=0,closeFails=0;

datetime LastSunday(int year,int month){            // March and October both have 31 days
   MqlDateTime t={};t.year=year;t.mon=month;t.day=31;
   datetime x=StructToTime(t);MqlDateTime d;TimeToStruct(x,d);
   return x-(datetime)(d.day_of_week*86400);
}
datetime London(datetime utc){
   MqlDateTime d;TimeToStruct(utc,d);
   datetime on=LastSunday(d.year,3)+3600,off=LastSunday(d.year,10)+3600;
   return utc+((utc>=on&&utc<off)?3600:0);
}
datetime Utc(datetime server){return server-(datetime)((long)InpServerUtcOffsetHours*3600);}
double Price(double p){double t=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);return NormalizeDouble(MathRound(p/t)*t,_Digits);}
double Buf(int h,int shift){double v[];if(CopyBuffer(h,0,shift,1,v)!=1)return EMPTY_VALUE;return v[0];}

bool HasPosition(long magic){
   for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);
      if(t&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==magic)return true;}
   return false;
}

bool Buy(long magic,double stopAtr,double atr,string cm){
   MqlTick q;if(!SymbolInfoTick(_Symbol,q)||q.ask<=0||q.bid<=0)return false;
   double dist=stopAtr*atr,entry=q.ask,sl=Price(entry-dist),tp=Price(entry+InpRewardRisk*dist);
   double gap=MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*_Point;
   if(q.bid-sl<=gap||tp-q.bid<=gap){skippedStops++;return false;}
   double unit=0,margin=0;
   if(!OrderCalcProfit(ORDER_TYPE_BUY,_Symbol,1.0,entry,sl,unit)||unit>=0){skippedStops++;return false;}
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double goal=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   double volume=NormalizeDouble(MathMax(mn,MathCeil((goal/-unit-1e-10)/step)*step),8);
   if(volume>mx||!OrderCalcMargin(ORDER_TYPE_BUY,_Symbol,volume,entry,margin)||margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)){skippedMargin++;return false;}
   trade.SetExpertMagicNumber(magic);
   if(!trade.Buy(volume,_Symbol,0,sl,tp,cm)||trade.ResultRetcode()!=TRADE_RETCODE_DONE){placeFails++;PrintFormat("FTSE_PLACE_FAIL %s code=%u",cm,trade.ResultRetcode());return false;}
   PrintFormat("FTSE_ENTRY %s entry=%.2f sl=%.2f tp=%.2f atr=%.2f lots=%.2f risk=%.2f",cm,entry,sl,tp,atr,volume,goal);
   return true;
}

bool InTradeSession(){                               // broker trade-session table; quotes can arrive while trading is closed
   datetime now=TimeCurrent(),from=0,to=0;MqlDateTime d;TimeToStruct(now,d);long sec=(long)(now%86400);
   for(uint i=0;SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)d.day_of_week,i,from,to);i++)
      if(sec>=(long)from&&sec<(long)to)return true;
   return false;
}

void TimeExits(){
   datetime now=TimeCurrent();if(now-lastClose<30||!InTradeSession())return;
   for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);
      if(!t||PositionGetString(POSITION_SYMBOL)!=_Symbol)continue;
      long m=PositionGetInteger(POSITION_MAGIC);if(m<InpMagic+1||m>InpMagic+3)continue;
      if(now-(datetime)PositionGetInteger(POSITION_TIME)<(long)InpMaxHoldHours*3600)continue;
      lastClose=now;
      if(!trade.PositionClose(t)||trade.ResultRetcode()!=TRADE_RETCODE_DONE){
         if(trade.ResultRetcode()!=TRADE_RETCODE_POSITION_CLOSED&&trade.ResultRetcode()!=TRADE_RETCODE_MARKET_CLOSED){closeFails++;PrintFormat("FTSE_CLOSE_FAIL code=%u",trade.ResultRetcode());}}
   }
}

int OnInit(){
   if(InpRiskPercent<=0||InpRiskPercent>5||InpRewardRisk<=0||InpMaxHoldHours<=0||InpRandomProb<0||InpRandomProb>1)return INIT_PARAMETERS_INCORRECT;
   if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING){Print("Hedging account required (rules may hold positions together).");return INIT_FAILED;}
   hRsi=iRSI(_Symbol,PERIOD_H1,InpRsiPeriod,PRICE_CLOSE);hAtr=iATR(_Symbol,PERIOD_H1,InpAtrPeriod);hMa=iMA(_Symbol,PERIOD_H1,InpR2MaPeriod,0,MODE_SMA,PRICE_CLOSE);
   if(hRsi==INVALID_HANDLE||hAtr==INVALID_HANDLE||hMa==INVALID_HANDLE)return INIT_FAILED;
   trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   MathSrand(InpRandomSeed);
   PrintFormat("FTSE_SPEC symbol=%s digits=%d contract=%.2f profit_ccy=%s vol_min=%.2f step=%.2f stops_level=%d rule1=%d rule2=%d day_mode=%d session=%d random=%d p=%.5f seed=%d",
               _Symbol,_Digits,SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),SymbolInfoString(_Symbol,SYMBOL_CURRENCY_PROFIT),
               SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
               InpRule1,InpRule2,InpR1DayMode,InpSessionMode,InpRandomMode,InpRandomProb,InpRandomSeed);
   return INIT_SUCCEEDED;
}

void OnTick(){
   TimeExits();
   datetime bar=iTime(_Symbol,PERIOD_H1,0);
   if(bar==0||bar==lastBar)return;
   lastBar=bar;bars++;
   datetime prev=iTime(_Symbol,PERIOD_H1,1);
   double rsi=Buf(hRsi,1),atr=Buf(hAtr,1),ma=Buf(hMa,1),close=iClose(_Symbol,PERIOD_H1,1);
   if(prev==0||rsi==EMPTY_VALUE||atr==EMPTY_VALUE||ma==EMPTY_VALUE||atr<=0||close<=0)return;
   if(InpSessionMode==1){
      MqlDateTime n;TimeToStruct(London(Utc(TimeCurrent())),n);int mins=n.hour*60+n.min;
      if(mins<8*60||mins>=16*60+30)return;
   }
   if(InpRandomMode){
      if(HasPosition(InpMagic+3))return;
      if(MathRand()/32768.0<InpRandomProb&&Buy(InpMagic+3,InpR2StopAtr,atr,"FTSE RNG"))rngEntries++;
      return;
   }
   datetime lon=London(Utc(prev));MqlDateTime d;TimeToStruct(lon,d);datetime day=lon-lon%86400;
   if(InpRule1){
      bool dayOk=InpR1DayMode==0?d.day_of_week==1:(d.day_of_week>=2&&d.day_of_week<=5);
      if(dayOk&&rsi<InpR1Rsi&&day!=lastR1Day&&!HasPosition(InpMagic+1)){
         r1Signals++;
         if(Buy(InpMagic+1,InpR1StopAtr,atr,InpR1DayMode==0?"FTSE R1":"FTSE R1 TF")){r1Entries++;lastR1Day=day;}
      }
   }
   if(InpRule2&&!HasPosition(InpMagic+2)){
      r2FlatBars++;
      if(close<=ma-InpR2DistAtr*atr&&rsi<InpR2Rsi){
         r2Signals++;
         if(Buy(InpMagic+2,InpR2StopAtr,atr,"FTSE R2"))r2Entries++;
      }
   }
}

void OnDeinit(const int reason){
   PrintFormat("FTSE_SUMMARY bars=%I64d r1_signals=%I64d r1_entries=%I64d r2_signals=%I64d r2_entries=%I64d r2_flat_bars=%I64d rng_entries=%I64d skipped_stops=%I64d skipped_margin=%I64d place_fails=%I64d close_fails=%I64d",
               bars,r1Signals,r1Entries,r2Signals,r2Entries,r2FlatBars,rngEntries,skippedStops,skippedMargin,placeFails,closeFails);
}

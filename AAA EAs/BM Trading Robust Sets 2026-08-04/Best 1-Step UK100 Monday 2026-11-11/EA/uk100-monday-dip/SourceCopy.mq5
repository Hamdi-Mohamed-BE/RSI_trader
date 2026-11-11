#property strict
#property version "1.00"
#property description "Research only (2026-10-27). FTSE 100 H1 three-setup bot from a pasted clip: S1 panic drop (close < lower BB40/2 + RSI<35, long),"
#property description "S2 Monday dip (Monday, close < SMA20, RSI<40, long), S3 trend pullback (SMA100 slope, 1.5ATR from SMA40, RSI 40/60, long+short)."
#property description "2R target, 24h time exit. Random-entry controls. Rules: RULES.md."
#include <Trade/Trade.mqh>

input double InpRiskPercent=0.75;        // % of equity per trade; lots rounded UP to the step (minimum lot if needed)
input bool   InpSetup1=true;
input bool   InpSetup2=true;
input bool   InpSetup3=true;
input int    InpS1BandPeriod=40;
input double InpS1BandDev=2.0;
input double InpS1Rsi=35.0;
input double InpS1StopAtr=2.0;
input int    InpS2DayMode=0;             // 0 = Monday only (London day); 1 = control: Tuesday-Friday, one per day
input int    InpS2MaPeriod=20;
input double InpS2Rsi=40.0;
input double InpS2StopAtr=2.5;
input int    InpS3TrendPeriod=100;
input int    InpS3SlopeBars=5;
input int    InpS3MaPeriod=40;
input double InpS3DistAtr=1.5;
input double InpS3LongRsi=40.0;
input double InpS3ShortRsi=60.0;
input double InpS3StopAtr=2.0;
input bool   InpS3Shorts=true;
input double InpRewardRisk=2.0;
input int    InpMaxHoldHours=24;
input int    InpRsiPeriod=14;
input int    InpAtrPeriod=14;
input int    InpRandomMode=0;            // control: 0 off; 1 random long (S1 exits); 2 random direction (S3 exits). Setups disabled.
input double InpRandomProb=0.02;         // per closed H1 bar while flat
input int    InpRandomSeed=1;
input int    InpServerUtcOffsetHours=0;  // Exness server = UTC
input int    InpMaximumDeviationPoints=1000;
input long   InpMagic=2710260;

CTrade trade;
int hRsi=INVALID_HANDLE,hAtr=INVALID_HANDLE,hBand=INVALID_HANDLE,hMa20=INVALID_HANDLE,hMa40=INVALID_HANDLE,hMa100=INVALID_HANDLE;
datetime lastBar=0,lastS2Day=0,lastClose=0;
long bars=0,s1Entries=0,s1FlatBars=0,s2Entries=0,s3Long=0,s3Short=0,s3FlatBars=0,rngEntries=0,skippedStops=0,skippedMargin=0,placeFails=0,closeFails=0;

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
double Buf(int h,int buffer,int shift){double v[];if(CopyBuffer(h,buffer,shift,1,v)!=1)return EMPTY_VALUE;return v[0];}

bool HasPosition(long magic){
   for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);
      if(t&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==magic)return true;}
   return false;
}

bool Open(long magic,bool buy,double stopAtr,double atr,string cm){
   MqlTick q;if(!SymbolInfoTick(_Symbol,q)||q.ask<=0||q.bid<=0)return false;
   double dist=stopAtr*atr,entry=buy?q.ask:q.bid;
   double sl=Price(buy?entry-dist:entry+dist),tp=Price(buy?entry+InpRewardRisk*dist:entry-InpRewardRisk*dist);
   double gap=MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*_Point;
   double ref=buy?q.bid:q.ask;
   if(MathAbs(ref-sl)<=gap||MathAbs(tp-ref)<=gap){skippedStops++;return false;}
   double unit=0,margin=0;ENUM_ORDER_TYPE type=buy?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,sl,unit)||unit>=0){skippedStops++;return false;}
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double goal=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   double volume=NormalizeDouble(MathMax(mn,MathCeil((goal/-unit-1e-10)/step)*step),8);
   if(volume>mx||!OrderCalcMargin(type,_Symbol,volume,entry,margin)||margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)){skippedMargin++;return false;}
   trade.SetExpertMagicNumber(magic);
   bool ok=buy?trade.Buy(volume,_Symbol,0,sl,tp,cm):trade.Sell(volume,_Symbol,0,sl,tp,cm);
   if(!ok||trade.ResultRetcode()!=TRADE_RETCODE_DONE){placeFails++;PrintFormat("FTSE3_PLACE_FAIL %s code=%u",cm,trade.ResultRetcode());return false;}
   PrintFormat("FTSE3_ENTRY %s %s entry=%.2f sl=%.2f tp=%.2f atr=%.2f lots=%.2f risk=%.2f",cm,buy?"buy":"sell",entry,sl,tp,atr,volume,goal);
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
      long m=PositionGetInteger(POSITION_MAGIC);if(m<InpMagic+1||m>InpMagic+4)continue;
      if(now-(datetime)PositionGetInteger(POSITION_TIME)<(long)InpMaxHoldHours*3600)continue;
      lastClose=now;
      if(!trade.PositionClose(t)||trade.ResultRetcode()!=TRADE_RETCODE_DONE){
         if(trade.ResultRetcode()!=TRADE_RETCODE_POSITION_CLOSED&&trade.ResultRetcode()!=TRADE_RETCODE_MARKET_CLOSED){closeFails++;PrintFormat("FTSE3_CLOSE_FAIL code=%u",trade.ResultRetcode());}}
   }
}

int OnInit(){
   if(InpRiskPercent<=0||InpRiskPercent>5||InpRewardRisk<=0||InpMaxHoldHours<=0||InpRandomProb<0||InpRandomProb>1||InpRandomMode<0||InpRandomMode>2||InpS3SlopeBars<1)return INIT_PARAMETERS_INCORRECT;
   if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING){Print("Hedging account required (setups may hold positions together).");return INIT_FAILED;}
   hRsi=iRSI(_Symbol,PERIOD_H1,InpRsiPeriod,PRICE_CLOSE);hAtr=iATR(_Symbol,PERIOD_H1,InpAtrPeriod);
   hBand=iBands(_Symbol,PERIOD_H1,InpS1BandPeriod,0,InpS1BandDev,PRICE_CLOSE);
   hMa20=iMA(_Symbol,PERIOD_H1,InpS2MaPeriod,0,MODE_SMA,PRICE_CLOSE);hMa40=iMA(_Symbol,PERIOD_H1,InpS3MaPeriod,0,MODE_SMA,PRICE_CLOSE);
   hMa100=iMA(_Symbol,PERIOD_H1,InpS3TrendPeriod,0,MODE_SMA,PRICE_CLOSE);
   if(hRsi==INVALID_HANDLE||hAtr==INVALID_HANDLE||hBand==INVALID_HANDLE||hMa20==INVALID_HANDLE||hMa40==INVALID_HANDLE||hMa100==INVALID_HANDLE)return INIT_FAILED;
   trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   MathSrand(InpRandomSeed);
   PrintFormat("FTSE3_SPEC symbol=%s digits=%d contract=%.2f profit_ccy=%s vol_min=%.2f step=%.2f stops_level=%d s1=%d s2=%d s3=%d s3_shorts=%d day_mode=%d random=%d p=%.5f seed=%d",
               _Symbol,_Digits,SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),SymbolInfoString(_Symbol,SYMBOL_CURRENCY_PROFIT),
               SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
               InpSetup1,InpSetup2,InpSetup3,InpS3Shorts,InpS2DayMode,InpRandomMode,InpRandomProb,InpRandomSeed);
   return INIT_SUCCEEDED;
}

void OnTick(){
   TimeExits();
   datetime bar=iTime(_Symbol,PERIOD_H1,0);
   if(bar==0||bar==lastBar)return;
   lastBar=bar;bars++;
   datetime prev=iTime(_Symbol,PERIOD_H1,1);
   double rsi=Buf(hRsi,0,1),atr=Buf(hAtr,0,1),lower=Buf(hBand,2,1),ma20=Buf(hMa20,0,1),ma40=Buf(hMa40,0,1);
   double t0=Buf(hMa100,0,1),tN=Buf(hMa100,0,1+InpS3SlopeBars),close=iClose(_Symbol,PERIOD_H1,1);
   if(prev==0||rsi==EMPTY_VALUE||atr==EMPTY_VALUE||lower==EMPTY_VALUE||ma20==EMPTY_VALUE||ma40==EMPTY_VALUE||t0==EMPTY_VALUE||tN==EMPTY_VALUE||atr<=0||close<=0)return;
   if(InpRandomMode>0){
      if(HasPosition(InpMagic+4))return;
      bool buy=InpRandomMode==1?true:(MathRand()%2==0);
      double p=MathRand()/32768.0;
      if(p<InpRandomProb&&Open(InpMagic+4,buy,InpRandomMode==1?InpS1StopAtr:InpS3StopAtr,atr,InpRandomMode==1?"FTSE3 RNG":"FTSE3 RNGD"))rngEntries++;
      return;
   }
   if(InpSetup1&&!HasPosition(InpMagic+1)){
      s1FlatBars++;
      if(close<lower&&rsi<InpS1Rsi&&Open(InpMagic+1,true,InpS1StopAtr,atr,"FTSE3 S1"))s1Entries++;
   }
   if(InpSetup2){
      datetime lon=London(Utc(prev));MqlDateTime d;TimeToStruct(lon,d);datetime day=lon-lon%86400;
      bool dayOk=InpS2DayMode==0?d.day_of_week==1:(d.day_of_week>=2&&d.day_of_week<=5);
      if(dayOk&&day!=lastS2Day&&close<ma20&&rsi<InpS2Rsi&&!HasPosition(InpMagic+2)&&
         Open(InpMagic+2,true,InpS2StopAtr,atr,InpS2DayMode==0?"FTSE3 S2":"FTSE3 S2 TF")){s2Entries++;lastS2Day=day;}
   }
   if(InpSetup3&&!HasPosition(InpMagic+3)){
      s3FlatBars++;
      if(t0>tN&&close<=ma40-InpS3DistAtr*atr&&rsi<InpS3LongRsi){if(Open(InpMagic+3,true,InpS3StopAtr,atr,"FTSE3 S3L"))s3Long++;}
      else if(InpS3Shorts&&t0<tN&&close>=ma40+InpS3DistAtr*atr&&rsi>InpS3ShortRsi){if(Open(InpMagic+3,false,InpS3StopAtr,atr,"FTSE3 S3S"))s3Short++;}
   }
}

void OnDeinit(const int reason){
   PrintFormat("FTSE3_SUMMARY bars=%I64d s1_entries=%I64d s1_flat_bars=%I64d s2_entries=%I64d s3_long=%I64d s3_short=%I64d s3_flat_bars=%I64d rng_entries=%I64d skipped_stops=%I64d skipped_margin=%I64d place_fails=%I64d close_fails=%I64d",
               bars,s1Entries,s1FlatBars,s2Entries,s3Long,s3Short,s3FlatBars,rngEntries,skippedStops,skippedMargin,placeFails,closeFails);
}

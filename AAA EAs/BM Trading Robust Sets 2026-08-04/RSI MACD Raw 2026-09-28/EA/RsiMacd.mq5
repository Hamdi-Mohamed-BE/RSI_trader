#property strict
#property version "1.00"
#property description "Tester-only frozen RSI14 + native MACD12/26/9 M15 raw comparison."
input int InpVariant=0;
input double InpRiskPercent=1.0;
input double InpRR=1.0;
input long InpMagic=9282630;
input bool InpAdaptivePortfolioControls=false;
input datetime InpTradeFrom=D'2025.09.27';
input string InpTag="smoke";
#include "..\..\RSI Mean Reversion 15m Raw 2026-09-25\EA\AAA_Final_Common.mqh"
int rsiHandle,atrHandle,macdHandle,emaHandle,hmacdHandle,audit=INVALID_HANDLE;
datetime lastBar=0,lastCloseAttempt=0,day=0;
long barNumber=0,longArm=-100,shortArm=-100;
int dayEntries=0,entries=0,signals=0,missing=0,stale=0,invalid=0,marginSkip=0,entryFails=0,closeFails=0;
double tickSize;

bool Value(int handle,int buffer,int shift,double &value){double x[];if(CopyBuffer(handle,buffer,shift,1,x)!=1)return false;value=x[0];return MathIsValidNumber(value) && value!=EMPTY_VALUE;}
double Price(double p){return NormalizeDouble(MathRound(p/tickSize)*tickSize,_Digits);}
bool Own(ulong &ticket){for(int i=PositionsTotal()-1;i>=0;i--){ticket=PositionGetTicket(i);if(ticket && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)return true;}ticket=0;return false;}
void Manage(datetime now){ulong ticket;if(!Own(ticket))return;int held=iBarShift(_Symbol,PERIOD_M15,(datetime)PositionGetInteger(POSITION_TIME),false);if(held<16 || now-lastCloseAttempt<60)return;lastCloseAttempt=now;if(!AAA_Trade.PositionClose(ticket) || AAA_Trade.ResultRetcode()!=TRADE_RETCODE_DONE){closeFails++;PrintFormat("RM_CLOSE_FAIL at=%I64d code=%u",(long)now,AAA_Trade.ResultRetcode());}else PrintFormat("RM_TIME_EXIT at=%I64d ticket=%I64u held=%d",(long)now,ticket,held);}
int Enter(int side,datetime signalBar,datetime now,double atr){
 ulong ticket;if(Own(ticket))return 1;if(dayEntries>=2)return 2;
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return 3;
 double entry=side>0?q.ask:q.bid,sl=Price(entry-side*2.0*atr),distance=side*(entry-sl),tp=Price(entry+side*distance*InpRR);
 double gap=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point,ref=side>0?q.bid:q.ask;
 if(distance<=0 || side*(ref-sl)<gap || side*(tp-ref)<gap){invalid++;return 4;}
 ENUM_ORDER_TYPE type=side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 double volume=AAA_LotsForRisk(_Symbol,type,entry,sl,InpRiskPercent),margin=0,one=0,planned=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100;
 if(volume<=0 || !OrderCalcProfit(type,_Symbol,1,entry,sl,one) || one>=0){invalid++;return 4;}
 if(!OrderCalcMargin(type,_Symbol,volume,entry,margin) || margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)){marginSkip++;return 5;}
 bool ok=side>0?AAA_Trade.Buy(volume,_Symbol,0,sl,tp,"RM long"):AAA_Trade.Sell(volume,_Symbol,0,sl,tp,"RM short");
 if(!ok || AAA_Trade.ResultRetcode()!=TRADE_RETCODE_DONE){entryFails++;PrintFormat("RM_ENTRY_FAIL at=%I64d code=%u %s",(long)now,AAA_Trade.ResultRetcode(),AAA_Trade.ResultRetcodeDescription());return 6;}
 entries++;dayEntries++;if(side>0)longArm=-100;else shortArm=-100;
 PrintFormat("RM_ORDER at=%I64d bar=%I64d side=%d entry=%.10f fill=%.10f sl=%.10f tp=%.10f atr=%.10f lots=%.8f risk=%.8f planned=%.8f order=%I64u",(long)now,(long)signalBar,side,entry,AAA_Trade.ResultPrice(),sl,tp,atr,volume,-one*volume,planned,AAA_Trade.ResultOrder());return 7;
}
int OnInit(){
 if(!MQLInfoInteger(MQL_TESTER)){Print("Research only: tester required");return INIT_FAILED;}
 if(InpVariant<0 || InpVariant>3 || InpRiskPercent<=0 || InpRR<=0 || InpAdaptivePortfolioControls || InpUseDynamicTrailingSL || InpResearchSession!=DTS_SESSION_ALL)return INIT_PARAMETERS_INCORRECT;
 rsiHandle=iRSI(_Symbol,PERIOD_M15,14,PRICE_CLOSE);atrHandle=iATR(_Symbol,PERIOD_M15,14);
 macdHandle=iMACD(_Symbol,PERIOD_M15,12,26,9,PRICE_CLOSE);emaHandle=iMA(_Symbol,PERIOD_H1,200,0,MODE_EMA,PRICE_CLOSE);hmacdHandle=iMACD(_Symbol,PERIOD_H1,12,26,9,PRICE_CLOSE);
 if(rsiHandle==INVALID_HANDLE || atrHandle==INVALID_HANDLE || macdHandle==INVALID_HANDLE || emaHandle==INVALID_HANDLE || hmacdHandle==INVALID_HANDLE)return INIT_FAILED;
 tickSize=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);if(tickSize<=0)return INIT_FAILED;
 AAA_Trade.SetExpertMagicNumber(InpMagic);AAA_Trade.SetTypeFillingBySymbol(_Symbol);AAA_Trade.SetDeviationInPoints(1000);
 audit=FileOpen("CalyxRsiMacd20260928\\"+InpTag+"-audit.bin",FILE_COMMON|FILE_WRITE|FILE_BIN);if(audit==INVALID_HANDLE)return INIT_FAILED;
 PrintFormat("RM_SPEC symbol=%s description=%s broker=%s currency=%s contract=%.8f min=%.8f max=%.8f step=%.8f tick=%.10f stops=%d swapLong=%.8f swapShort=%.8f",_Symbol,SymbolInfoString(_Symbol,SYMBOL_DESCRIPTION),AccountInfoString(ACCOUNT_COMPANY),AccountInfoString(ACCOUNT_CURRENCY),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),tickSize,(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoDouble(_Symbol,SYMBOL_SWAP_LONG),SymbolInfoDouble(_Symbol,SYMBOL_SWAP_SHORT));
 return INIT_SUCCEEDED;
}
void OnTick(){
 datetime now=TimeCurrent(),d=now-now%86400;Manage(now);if(day!=d){day=d;dayEntries=0;}
 datetime current=iTime(_Symbol,PERIOD_M15,0);if(current<=0 || current==lastBar)return;lastBar=current;barNumber++;
 if(now<InpTradeFrom)return;
 MqlRates b[],hb[];double r1,r2,m1,m2,m3,s1,s2,s3,atr,ema,hm;
 if(CopyRates(_Symbol,PERIOD_M15,1,1,b)!=1 || CopyRates(_Symbol,PERIOD_H1,1,1,hb)!=1 ||
 !Value(rsiHandle,0,1,r1) || !Value(rsiHandle,0,2,r2) || !Value(macdHandle,0,1,m1) || !Value(macdHandle,0,2,m2) || !Value(macdHandle,0,3,m3) ||
 !Value(macdHandle,1,1,s1) || !Value(macdHandle,1,2,s2) || !Value(macdHandle,1,3,s3) || !Value(atrHandle,0,1,atr) || !Value(emaHandle,0,1,ema) || !Value(hmacdHandle,0,1,hm) || atr<=0){missing++;return;}
 if(r1<=30)longArm=barNumber;if(r1>=70)shortArm=barNumber;
 long longAge=barNumber-longArm,shortAge=barNumber-shortArm;
 double h1=m1-s1,h2=m2-s2,h3=m3-s3;bool up=h1>0 && h2<=0,down=h1<0 && h2>=0;
 int side=0,result=0;
 if(InpVariant==0 || InpVariant==3){
  if(hb[0].close>ema && hm>0 && h1>h2 && h2>h3 && (InpVariant==3 || (r2<=40 && r1>40)))side=1;
  if(hb[0].close<ema && hm<0 && h1<h2 && h2<h3 && (InpVariant==3 || (r2>=60 && r1<60)))side=-1;
 }else if(InpVariant==1){
  if(longAge>=1 && longAge<=8 && r1>30 && up)side=1;
  if(shortAge>=1 && shortAge<=8 && r1<70 && down)side=-1;
 }else{if(up)side=1;if(down)side=-1;}
 if(b[0].time+900>now || now-(b[0].time+900)>=60 || hb[0].time+3600>b[0].time+900){stale++;result=8;}
 else if(side!=0){signals++;result=Enter(side,b[0].time,now,atr);}
 // 3 int64 times, 10 doubles, 4 int32 fields. Indicator values are known at decision time.
 FileWriteLong(audit,(long)now);FileWriteLong(audit,(long)b[0].time);FileWriteLong(audit,(long)hb[0].time);
 FileWriteDouble(audit,r1);FileWriteDouble(audit,r2);FileWriteDouble(audit,h1);FileWriteDouble(audit,h2);FileWriteDouble(audit,h3);
 FileWriteDouble(audit,atr);FileWriteDouble(audit,hb[0].close);FileWriteDouble(audit,ema);FileWriteDouble(audit,hm);FileWriteDouble(audit,b[0].close);
 FileWriteInteger(audit,side);FileWriteInteger(audit,result);FileWriteInteger(audit,(int)longAge);FileWriteInteger(audit,(int)shortAge);
}
double OnTester(){
 if(audit!=INVALID_HANDLE)FileFlush(audit);
 if(!HistorySelect(0,TimeCurrent())){Print("RM_EXPORT_FAIL history");return -999;}
 int f=FileOpen("CalyxRsiMacd20260928\\"+InpTag+"-deals.csv",FILE_COMMON|FILE_WRITE|FILE_CSV|FILE_ANSI,',');if(f==INVALID_HANDLE){Print("RM_EXPORT_FAIL deals");return -999;}
 FileWrite(f,"deal","position","order","time","time_msc","entry","type","volume","price","profit","commission","swap","fee","reason","magic","comment");
 for(int i=0;i<HistoryDealsTotal();i++){ulong id=HistoryDealGetTicket(i);if(!id)continue;
 FileWrite(f,id,HistoryDealGetInteger(id,DEAL_POSITION_ID),HistoryDealGetInteger(id,DEAL_ORDER),HistoryDealGetInteger(id,DEAL_TIME),HistoryDealGetInteger(id,DEAL_TIME_MSC),HistoryDealGetInteger(id,DEAL_ENTRY),HistoryDealGetInteger(id,DEAL_TYPE),DoubleToString(HistoryDealGetDouble(id,DEAL_VOLUME),8),DoubleToString(HistoryDealGetDouble(id,DEAL_PRICE),10),DoubleToString(HistoryDealGetDouble(id,DEAL_PROFIT),8),DoubleToString(HistoryDealGetDouble(id,DEAL_COMMISSION),8),DoubleToString(HistoryDealGetDouble(id,DEAL_SWAP),8),DoubleToString(HistoryDealGetDouble(id,DEAL_FEE),8),HistoryDealGetInteger(id,DEAL_REASON),HistoryDealGetInteger(id,DEAL_MAGIC),HistoryDealGetString(id,DEAL_COMMENT));}
 FileClose(f);return TesterStatistics(STAT_PROFIT);
}
void OnDeinit(const int reason){
 if(audit!=INVALID_HANDLE)FileClose(audit);
 IndicatorRelease(rsiHandle);IndicatorRelease(atrHandle);IndicatorRelease(macdHandle);IndicatorRelease(emaHandle);IndicatorRelease(hmacdHandle);
 PrintFormat("RM_SUMMARY tag=%s signals=%d stale=%d missing=%d invalid=%d marginSkip=%d orders=%d entryFails=%d closeFails=%d",InpTag,signals,stale,missing,invalid,marginSkip,entries,entryFails,closeFails);
}

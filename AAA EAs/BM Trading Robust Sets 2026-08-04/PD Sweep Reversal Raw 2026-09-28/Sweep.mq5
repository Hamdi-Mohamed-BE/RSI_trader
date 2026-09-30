#property strict
#property version "1.00"
#property description "Tester-only previous-day sweep/rejection; M5/M15 frozen raw rules."
#include <Trade/Trade.mqh>
input ENUM_TIMEFRAMES InpTimeframe=PERIOD_M5;
input bool InpControl=false;
input double InpRiskPercent=1.0;
input double InpRR=2.0;
input uint InpSeed=9282026;
input datetime InpTradeFrom=D'2025.09.27';
input bool InpExportBars=false;
input string InpTag="smoke";
input long InpMagic=9282610;
CTrade trade;
double tickSize=0;
datetime day=0,lastBar=0,lastCloseAttempt=0;
bool usedHigh=false,usedLow=false;
int signals=0,ambiguous=0,stale=0,missing=0,busy=0,invalid=0,marginSkip=0,entries=0,entryFails=0,closeFails=0;
datetime Midnight(datetime t){return t-t%86400;}
double RoundTick(double p){return NormalizeDouble(MathRound(p/tickSize)*tickSize,_Digits);}
bool Own(ulong &ticket){for(int i=PositionsTotal()-1;i>=0;i--){ticket=PositionGetTicket(i);if(ticket && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)return true;}ticket=0;return false;}
int RandomSide(datetime bar,int level){uint x=(uint)((long)bar/60)^InpSeed^(uint)(level*2654435761);x=((x>>16)^x)*0x45d9f3b;x=((x>>16)^x)*0x45d9f3b;x=(x>>16)^x;return (x&1)==0?1:-1;}
void Enter(int level,const MqlRates &b,const MqlRates &pd,datetime now)
{
 signals++;int side=InpControl?RandomSide(b.time,level):(level==0?-1:1);
 PrintFormat("PS_SIGNAL at=%I64d bar=%I64d pd=%I64d level=%d side=%d high=%.8f low=%.8f close=%.8f pdh=%.8f pdl=%.8f",(long)now,(long)b.time,(long)pd.time,level,side,b.high,b.low,b.close,pd.high,pd.low);
 ulong ticket;if(Own(ticket)){busy++;return;}
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
 if(q.bid<=pd.low || q.bid>=pd.high){invalid++;return;}
 double entry=side>0?q.ask:q.bid;
 double stop=RoundTick(side>0?b.low-tickSize:b.high+tickSize);
 double distance=side*(entry-stop),target=RoundTick(entry+side*distance*InpRR);
 double gap=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point,ref=side>0?q.bid:q.ask;
 if(distance<=0 || side*(target-entry)<=0 || side*(ref-stop)<gap || side*(target-ref)<gap){invalid++;return;}
 ENUM_ORDER_TYPE type=side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;double one=0;
 if(!OrderCalcProfit(type,_Symbol,1,entry,stop,one) || one>=0){invalid++;return;}
 double cash=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100;
 double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),vmin=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),vmax=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
 if(cash<=0 || step<=0){marginSkip++;return;}
 double raw=cash/-one,volume=MathMax(vmin,MathMin(vmax,MathCeil((raw-1e-12)/step)*step)),margin=0;
 if(!OrderCalcMargin(type,_Symbol,volume,entry,margin) || margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)){marginSkip++;return;}
 bool ok=side>0?trade.Buy(volume,_Symbol,0,stop,target,level==0?"PS PDH":"PS PDL"):trade.Sell(volume,_Symbol,0,stop,target,level==0?"PS PDH":"PS PDL");
 if(ok && trade.ResultRetcode()==TRADE_RETCODE_DONE){entries++;PrintFormat("PS_ORDER at=%I64d bar=%I64d pd=%I64d level=%d side=%d entry=%.8f fill=%.8f sl=%.8f tp=%.8f lots=%.8f risk=%.8f planned=%.8f order=%I64u",(long)now,(long)b.time,(long)pd.time,level,side,entry,trade.ResultPrice(),stop,target,volume,-volume*one,cash,trade.ResultOrder());}
 else{entryFails++;PrintFormat("PS_ENTRY_FAIL at=%I64d code=%u %s",(long)now,trade.ResultRetcode(),trade.ResultRetcodeDescription());}
}
int OnInit()
{
 if(!MQLInfoInteger(MQL_TESTER)){Print("Research only: tester required");return INIT_FAILED;}
 if((InpTimeframe!=PERIOD_M5 && InpTimeframe!=PERIOD_M15) || InpRiskPercent<=0 || InpRR<=0)return INIT_PARAMETERS_INCORRECT;
 tickSize=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);if(tickSize<=0)return INIT_FAILED;
 trade.SetExpertMagicNumber(InpMagic);trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(1000);
 PrintFormat("PS_SPEC symbol=%s description=%s broker=%s currency=%s leverage=%d contract=%.8f min=%.8f max=%.8f step=%.8f tick=%.8f stops=%d swapLong=%.8f swapShort=%.8f",_Symbol,SymbolInfoString(_Symbol,SYMBOL_DESCRIPTION),AccountInfoString(ACCOUNT_COMPANY),AccountInfoString(ACCOUNT_CURRENCY),(int)AccountInfoInteger(ACCOUNT_LEVERAGE),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),tickSize,(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoDouble(_Symbol,SYMBOL_SWAP_LONG),SymbolInfoDouble(_Symbol,SYMBOL_SWAP_SHORT));
 return INIT_SUCCEEDED;
}
void OnTick()
{
 datetime now=TimeCurrent(),d=Midnight(now);ulong ticket;
 if(Own(ticket) && (now>=d+85800 || Midnight((datetime)PositionGetInteger(POSITION_TIME))<d) && now-lastCloseAttempt>=60){
  lastCloseAttempt=now;
  if(!trade.PositionClose(ticket) || trade.ResultRetcode()!=TRADE_RETCODE_DONE){closeFails++;PrintFormat("PS_CLOSE_FAIL at=%I64d code=%u",(long)now,trade.ResultRetcode());}
 }
 if(day!=d){day=d;usedHigh=false;usedLow=false;}
 datetime current=iTime(_Symbol,InpTimeframe,0);if(current==lastBar || current==0)return;lastBar=current;
 if(now<InpTradeFrom || now>=d+85800)return;
 MqlRates b[],pd[];int seconds=PeriodSeconds(InpTimeframe);
 if(CopyRates(_Symbol,InpTimeframe,1,1,b)!=1 || CopyRates(_Symbol,PERIOD_D1,1,1,pd)!=1){missing++;return;}
 if(b[0].time<d || b[0].time+seconds>now || now-(b[0].time+seconds)>=60){stale++;return;}
 if(pd[0].time+86400>d || pd[0].high<=pd[0].low){missing++;return;}
 bool hi=b[0].high>pd[0].high,lo=b[0].low<pd[0].low,inside=b[0].close<pd[0].high && b[0].close>pd[0].low;
 if(!inside)return;
 if(hi && lo){ambiguous++;return;}
 if(hi && !usedHigh){usedHigh=true;Enter(0,b[0],pd[0],now);}
 if(lo && !usedLow){usedLow=true;Enter(1,b[0],pd[0],now);}
}
bool ExportBars(ENUM_TIMEFRAMES tf,string suffix)
{
 MqlRates bars[];int n=CopyRates(_Symbol,tf,InpTradeFrom-45*86400,TimeCurrent(),bars);
 if(n<=0)return false;
 int f=FileOpen("CalyxPDSweep20260928\\"+InpTag+"-"+suffix+".bin",FILE_COMMON|FILE_WRITE|FILE_BIN);
 if(f==INVALID_HANDLE)return false;
 for(int i=0;i<n;i++){FileWriteLong(f,(long)bars[i].time);FileWriteDouble(f,bars[i].open);FileWriteDouble(f,bars[i].high);FileWriteDouble(f,bars[i].low);FileWriteDouble(f,bars[i].close);FileWriteLong(f,bars[i].tick_volume);}
 FileClose(f);PrintFormat("PS_BARS tf=%s rows=%d first=%I64d last=%I64d",suffix,n,(long)bars[0].time,(long)bars[n-1].time);return true;
}
double OnTester()
{
 if(!HistorySelect(0,TimeCurrent())){Print("PS_EXPORT_FAIL history");return -999;}
 int f=FileOpen("CalyxPDSweep20260928\\"+InpTag+"-deals.csv",FILE_COMMON|FILE_WRITE|FILE_CSV|FILE_ANSI,',');
 if(f==INVALID_HANDLE){Print("PS_EXPORT_FAIL deals");return -999;}
 FileWrite(f,"deal","position","order","time","time_msc","entry","type","volume","price","profit","commission","swap","fee","reason","magic","comment");
 for(int i=0;i<HistoryDealsTotal();i++){
  ulong id=HistoryDealGetTicket(i);if(!id)continue;
  FileWrite(f,id,HistoryDealGetInteger(id,DEAL_POSITION_ID),HistoryDealGetInteger(id,DEAL_ORDER),HistoryDealGetInteger(id,DEAL_TIME),HistoryDealGetInteger(id,DEAL_TIME_MSC),HistoryDealGetInteger(id,DEAL_ENTRY),HistoryDealGetInteger(id,DEAL_TYPE),DoubleToString(HistoryDealGetDouble(id,DEAL_VOLUME),8),DoubleToString(HistoryDealGetDouble(id,DEAL_PRICE),8),DoubleToString(HistoryDealGetDouble(id,DEAL_PROFIT),8),DoubleToString(HistoryDealGetDouble(id,DEAL_COMMISSION),8),DoubleToString(HistoryDealGetDouble(id,DEAL_SWAP),8),DoubleToString(HistoryDealGetDouble(id,DEAL_FEE),8),HistoryDealGetInteger(id,DEAL_REASON),HistoryDealGetInteger(id,DEAL_MAGIC),HistoryDealGetString(id,DEAL_COMMENT));
 }
 FileClose(f);
 if(InpExportBars && (!ExportBars(InpTimeframe,"SIGNAL") || !ExportBars(PERIOD_D1,"D1"))){Print("PS_EXPORT_FAIL bars");return -999;}
 return TesterStatistics(STAT_PROFIT);
}
void OnDeinit(const int reason)
{
 PrintFormat("PS_SUMMARY tag=%s signals=%d ambiguous=%d stale=%d missing=%d busy=%d invalid=%d marginSkip=%d orders=%d entryFails=%d closeFails=%d",InpTag,signals,ambiguous,stale,missing,busy,invalid,marginSkip,entries,entryFails,closeFails);
}

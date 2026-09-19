#property strict
#property version "1.00"
#property description "Tester-only frozen D14 structure / H1 broken wick zone / M5 rejection and stairs / 2R"
#include <Trade/Trade.mqh>
input double InpRiskPercent=1.0;
input long InpMagic=84133001;
input int InpDeviationPoints=30;
CTrade trade;
int audit=INVALID_HANDLE;
datetime lastM5=0,lastH1=0,lastD1=0,firstTick=0;
int bias=0,zoneDir=0;
MqlRates hHigh,hLow,mHigh,mLow;
datetime zoneOrigin=0,zoneCreated=0,seenBuyOrigin=0,seenSellOrigin=0;
datetime touchTime=0,heldAt=0;
double zoneLow=0,zoneHigh=0,holdExtreme=0;
bool attempted=false;
long zones=0,holds=0,signals=0,errors=0,fills=0;

double Step(){return MathMax(_Point,SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE));}
double RoundPrice(double p,bool up){double s=Step();return NormalizeDouble((up?MathCeil(p/s-1e-9):MathFloor(p/s+1e-9))*s,_Digits);}
string Stamp(datetime t){return t>0?TimeToString(t,TIME_DATE|TIME_SECONDS):"";}
void Audit(string event,string detail,double entry=0,double sl=0,double tp=0,double lots=0,double risk=0)
{
 if(audit==INVALID_HANDLE)return;
 FileWrite(audit,Stamp(TimeCurrent()),event,detail,bias,zoneDir,Stamp(zoneOrigin),Stamp(zoneCreated),zoneLow,zoneHigh,
           Stamp(touchTime),Stamp(heldAt),holdExtreme,Stamp(mHigh.time),mHigh.high,Stamp(mLow.time),mLow.low,
           entry,sl,tp,lots,risk,AccountInfoDouble(ACCOUNT_EQUITY));
 FileFlush(audit);
}
int DailyDirection(MqlRates &b[])
{
 double ah=b[0].high,al=b[0].low,bh=b[7].high,bl=b[7].low;
 for(int i=1;i<7;i++){ah=MathMax(ah,b[i].high);al=MathMin(al,b[i].low);}
 for(int i=8;i<14;i++){bh=MathMax(bh,b[i].high);bl=MathMin(bl,b[i].low);}
 return bh>ah && bl>al?1:(bh<ah && bl<al?-1:0);
}
bool PivotHigh(MqlRates &b[]){return b[2].high>b[0].high && b[2].high>b[1].high && b[2].high>b[3].high && b[2].high>b[4].high;}
bool PivotLow(MqlRates &b[]){return b[2].low<b[0].low && b[2].low<b[1].low && b[2].low<b[3].low && b[2].low<b[4].low;}
bool Reject(MqlRates &b,int dir,double lo,double hi)
{
 return dir>0?(b.low>=lo && b.low<=hi && MathMin(b.open,b.close)>hi):
              (b.high<=hi && b.high>=lo && MathMax(b.open,b.close)<lo);
}
bool SelfTest()
{
 MqlRates d[14],p[5];ZeroMemory(d);ZeroMemory(p);
 for(int i=0;i<14;i++){d[i].high=i<7?10:12;d[i].low=i<7?5:7;}
 if(DailyDirection(d)!=1)return false;
 for(int i=7;i<14;i++){d[i].high=8;d[i].low=3;}
 if(DailyDirection(d)!=-1)return false;
 for(int i=7;i<14;i++){d[i].high=12;d[i].low=3;}
 if(DailyDirection(d)!=0)return false;
 for(int i=0;i<5;i++){p[i].high=10;p[i].low=5;}
 p[2].high=11;if(!PivotHigh(p))return false;
 p[4].high=11;if(PivotHigh(p))return false;
 p[2].low=4;if(!PivotLow(p))return false;
 p[0].low=4;if(PivotLow(p))return false;
 MqlRates w;ZeroMemory(w);w.open=12;w.close=13;w.low=10.5;w.high=14;
 if(!Reject(w,1,10,11))return false;
 w.close=10.5;if(Reject(w,1,10,11))return false;
 w.open=8;w.close=9;w.high=10.5;if(!Reject(w,-1,10,11))return false;
 return true;
}
void ResetSetup(){touchTime=0;heldAt=0;holdExtreme=0;ZeroMemory(mHigh);ZeroMemory(mLow);attempted=false;}
void ClearZone(string reason){if(zoneDir!=0)Audit("invalidate",reason);zoneDir=0;zoneOrigin=0;zoneCreated=0;zoneLow=0;zoneHigh=0;ResetSetup();}
void ReadDaily()
{
 datetime t=iTime(_Symbol,PERIOD_D1,0);if(t==0 || t==lastD1)return;
 MqlRates d[];if(CopyRates(_Symbol,PERIOD_D1,1,14,d)!=14)return;
 int next=DailyDirection(d);if(next!=bias)ClearZone("daily bias changed");bias=next;lastD1=t;Audit("bias","last fourteen completed daily candles");
}
void SetZone(int dir,MqlRates &origin,datetime created)
{
 zoneDir=dir;zoneOrigin=origin.time;zoneCreated=created;
 zoneLow=dir>0?MathMax(origin.open,origin.close):origin.low;
 zoneHigh=dir>0?origin.high:MathMin(origin.open,origin.close);
 if(zoneHigh-zoneLow<Step()){if(dir>0)zoneLow=zoneHigh-Step();else zoneHigh=zoneLow+Step();}
 ResetSetup();zones++;Audit("zone",dir>0?"H1 high-low-break":"H1 low-high-break");
}
void ReadHour()
{
 datetime t=iTime(_Symbol,PERIOD_H1,0);if(t==0 || t==lastH1)return;
 MqlRates h[];if(CopyRates(_Symbol,PERIOD_H1,1,5,h)!=5)return;
 if(h[4].time+3600>TimeCurrent())return;
 lastH1=t;
 if(PivotHigh(h))hHigh=h[2];if(PivotLow(h))hLow=h[2];
 if(h[4].time+3600<firstTick)return;
 if(bias>0 && hHigh.time>0 && hLow.time>hHigh.time && h[4].close>hHigh.high && h[3].close<=hHigh.high && hHigh.time!=seenBuyOrigin)
 {seenBuyOrigin=hHigh.time;SetZone(1,hHigh,h[4].time+3600);}
 if(bias<0 && hLow.time>0 && hHigh.time>hLow.time && h[4].close<hLow.low && h[3].close>=hLow.low && hLow.time!=seenSellOrigin)
 {seenSellOrigin=hLow.time;SetZone(-1,hLow,h[4].time+3600);}
}
bool OurPosition(){for(int i=PositionsTotal()-1;i>=0;i--){if(PositionGetTicket(i)>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)return true;}return false;}
void SendEntry(bool buy)
{
 attempted=true;signals++;MqlTick tick;if(!SymbolInfoTick(_Symbol,tick)){errors++;Audit("error","no tick");return;}
 double entry=buy?tick.ask:tick.bid,sl=RoundPrice(buy?mLow.low-Step():mHigh.high+Step(),!buy);
 double distance=buy?entry-sl:sl-entry;
 double tp=RoundPrice(buy?entry+2*distance:entry-2*distance,buy);
 double minDist=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
 if(distance<=0 || (buy?tick.bid-sl:sl-tick.ask)<minDist || (buy?tp-tick.bid:tick.ask-tp)<minDist)
 {Audit("rejected","invalid side or broker stop distance",entry,sl,tp);return;}
 double pnl=0;if(!OrderCalcProfit(buy?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,1,entry,sl,pnl) || pnl==0){errors++;Audit("error","cannot calculate risk",entry,sl,tp);return;}
 double target=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
 double lotStep=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),lo=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),hi=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
 if(lotStep<=0 || lo<=0){errors++;Audit("error","invalid volume specification");return;}
 double lots=NormalizeDouble(MathMax(lo,MathMin(hi,MathCeil(target/MathAbs(pnl)/lotStep-1e-10)*lotStep)),8);
 double risk=MathAbs(pnl)*lots;
 Audit("signal",buy?"confirmed M5 high-low-high break":"confirmed M5 low-high-low break",entry,sl,tp,lots,risk);
 bool sent=buy?trade.Buy(lots,_Symbol,0,sl,tp,"D14H1M5_RAW_2R"):trade.Sell(lots,_Symbol,0,sl,tp,"D14H1M5_RAW_2R");
 uint rc=trade.ResultRetcode();
 if(!sent || (rc!=TRADE_RETCODE_DONE && rc!=TRADE_RETCODE_DONE_PARTIAL)){errors++;Audit("error",trade.ResultRetcodeDescription(),entry,sl,tp,lots,risk);}
 else Audit("accepted",(string)trade.ResultDeal(),trade.ResultPrice(),sl,tp,lots,risk);
}
void ReadFive()
{
 if(zoneDir==0 || zoneDir!=bias)return;
 MqlRates b[];if(CopyRates(_Symbol,PERIOD_M5,1,5,b)!=5)return;
 MqlRates c=b[4];if(c.time<zoneCreated || c.time+300>TimeCurrent())return;
 bool buy=zoneDir>0;
 if((buy && c.close<zoneLow) || (!buy && c.close>zoneHigh)){ClearZone("M5 close through far edge");return;}
 if(attempted || OurPosition())return;
 if(touchTime==0)
 {
  if(c.low>zoneHigh || c.high<zoneLow)return;
  touchTime=c.time;Audit("touch","first completed M5 touch");
 }
 if(heldAt==0)
 {
  if(b[2].time<touchTime || b[3].time-b[2].time!=300 || b[4].time-b[3].time!=300)return;
  int wicks=0;for(int i=2;i<5;i++)if(Reject(b[i],zoneDir,zoneLow,zoneHigh))wicks++;
  if(wicks<2)return;
  heldAt=c.time+300;holdExtreme=buy?MathMin(b[2].low,MathMin(b[3].low,b[4].low)):MathMax(b[2].high,MathMax(b[3].high,b[4].high));
  holds++;Audit("held","at least two rejection wicks in three closed M5 bars");return;
 }
 // No retrospective swings from before the holding confirmation are accepted.
 if(b[2].time>=heldAt)
 {
  if(PivotHigh(b))mHigh=b[2];if(PivotLow(b))mLow=b[2];
 }
 if(buy && mHigh.time>=heldAt && mLow.time>mHigh.time && mLow.low>holdExtreme && c.close>mHigh.high && b[3].close<=mHigh.high)SendEntry(true);
 if(!buy && mLow.time>=heldAt && mHigh.time>mLow.time && mHigh.high<holdExtreme && c.close<mLow.low && b[3].close>=mLow.low)SendEntry(false);
}
void OnTick()
{
 if(firstTick==0)firstTick=TimeCurrent();
 datetime t=iTime(_Symbol,PERIOD_M5,0);if(t==0 || t==lastM5)return;lastM5=t;
 ReadDaily();ReadHour();ReadFive();
}
void OnTradeTransaction(const MqlTradeTransaction &trans,const MqlTradeRequest &request,const MqlTradeResult &result)
{
 if(trans.type!=TRADE_TRANSACTION_DEAL_ADD || trans.deal==0 || !HistoryDealSelect(trans.deal))return;
 if(HistoryDealGetString(trans.deal,DEAL_SYMBOL)!=_Symbol || HistoryDealGetInteger(trans.deal,DEAL_MAGIC)!=InpMagic)return;
 long type=HistoryDealGetInteger(trans.deal,DEAL_ENTRY);
 if(type==DEAL_ENTRY_IN){fills++;Audit("fill",(string)trans.deal,trans.price,trans.price_sl,trans.price_tp,trans.volume);}
 if(type==DEAL_ENTRY_OUT)Audit("exit",(string)HistoryDealGetInteger(trans.deal,DEAL_REASON),trans.price,0,0,trans.volume);
}
void ExportBars(ENUM_TIMEFRAMES tf)
{
 MqlRates b[];int n=CopyRates(_Symbol,tf,firstTick-45*86400,TimeCurrent(),b);if(n<=0)return;
 int f=FileOpen("D14BreakRetest-"+(string)InpMagic+"-"+EnumToString(tf)+".csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');if(f==INVALID_HANDLE)return;
 FileWrite(f,"time","open","high","low","close","spread","tick_volume");
 for(int i=0;i<n;i++)FileWrite(f,Stamp(b[i].time),b[i].open,b[i].high,b[i].low,b[i].close,b[i].spread,b[i].tick_volume);
 FileClose(f);
}
int OnInit()
{
 if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;
 if(InpRiskPercent<=0 || !SelfTest()){Print("RAW SELF TEST FAILED");return INIT_PARAMETERS_INCORRECT;}
 trade.SetExpertMagicNumber((ulong)InpMagic);trade.SetDeviationInPoints(InpDeviationPoints);trade.SetTypeFillingBySymbol(_Symbol);
 audit=FileOpen("D14BreakRetest-"+(string)InpMagic+".csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');if(audit==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(audit,"server_time","event","detail","bias","zone_dir","zone_origin","zone_created","zone_low","zone_high","touch_time","held_at","hold_extreme","m5_high_time","m5_high","m5_low_time","m5_low","entry","stop","target","lots","risk_cash","equity");
 Audit("init","tester-only; self-tests passed; frozen rules v1");
 Print("RAW CONTRACT ",_Symbol," point=",_Point," tick=",Step()," contract=",SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE)," min=",SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN)," step=",SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP)," swapLong=",SymbolInfoDouble(_Symbol,SYMBOL_SWAP_LONG)," swapShort=",SymbolInfoDouble(_Symbol,SYMBOL_SWAP_SHORT));
 return INIT_SUCCEEDED;
}
void OnDeinit(const int reason)
{
 Audit("summary",StringFormat("zones=%I64d holds=%I64d signals=%I64d fills=%I64d errors=%I64d",zones,holds,signals,fills,errors));
 if(audit!=INVALID_HANDLE)FileClose(audit);ExportBars(PERIOD_D1);ExportBars(PERIOD_H1);ExportBars(PERIOD_M5);
}

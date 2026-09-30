#property strict
#property version "1.00"
#property description "Research-only causal first-touch continuation and breakout-retest; synthetic controls."
#include <Trade/Trade.mqh>
input int InpEntry=0;
input bool InpControl=false;
input double InpRiskPercent=1.0;
input datetime InpTradeFrom=D'2025.09.27';
input string InpTag="smoke";
input long InpMagic=9278120;
struct Level {double p; int state; datetime formed,touched,broken,expiry;};
Level levels[8];
double donorDist[8][36],donorVol[8][36];datetime donorTime[8][36];int donorN[8];
CTrade trade;int atrHandle=INVALID_HANDLE;double atr=0,tickSize=0,previousBid=0;
datetime day=0,week=0,lastMinute=0,lastM5=0,lastExitAttempt=0;bool asia=false,london=false;
long quotes=0,volumeQuotes=0,tradeFlags=0;int forms=0,missing=0,noDonor=0,touches=0,entries=0,busy=0,skips=0,entryFails=0,closeFails=0,retestExpired=0;
string Names[8]={"PDH","PDL","ASH","ASL","LDH","LDL","PWH","PWL"};
int Side(int i){return (i%2==0)?1:-1;}
datetime Midnight(datetime t){return t-t%86400;}
datetime Monday(datetime t){MqlDateTime d;TimeToStruct(t,d);return Midnight(t)-((d.day_of_week+6)%7)*86400;}
double Rounded(double p){return NormalizeDouble(MathRound(p/tickSize)*tickSize,_Digits);}
bool Own(ulong &ticket){for(int j=PositionsTotal()-1;j>=0;j--){ticket=PositionGetTicket(j);if(ticket && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)return true;}ticket=0;return false;}
void Form(int i,double real,datetime now,datetime expiry,double bid)
{
 levels[i].state=3;levels[i].formed=now;levels[i].expiry=expiry;levels[i].p=real;
 double distance=Side(i)*(real-bid)/atr,vol=atr/bid;int donor=-1,eligible=0,n=donorN[i];
 if(distance>0){
  for(int j=n-1;j>=MathMax(0,n-36);j--){int k=j%36;if(donorVol[i][k]>0 && vol/donorVol[i][k]>=.5 && vol/donorVol[i][k]<=2){eligible++;if(eligible==5){donor=k;break;}}}
  if(!InpControl || donor>=0){levels[i].p=InpControl?Rounded(bid+Side(i)*donorDist[i][donor]*atr):real;levels[i].state=0;forms++;}
  else noDonor++;
  if(now>=InpTradeFrom)PrintFormat("LC_LEVEL i=%d at=%I64d expires=%I64d real=%.8f level=%.8f bid=%.8f atr=%.8f donor=%I64d donorDist=%.8f state=%d",i,(long)now,(long)expiry,real,levels[i].p,bid,atr,donor>=0?(long)donorTime[i][donor]:0,donor>=0?donorDist[i][donor]:0,levels[i].state);
  int k=n%36;donorDist[i][k]=distance;donorVol[i][k]=vol;donorTime[i][k]=now;donorN[i]++;
 }
}
bool Range(datetime a,datetime b,double &hi,double &lo,bool session)
{
 MqlRates r[];int n=CopyRates(_Symbol,session?PERIOD_M1:PERIOD_D1,a,b-1,r);
 if(n<1 || (session && n<(b-a)/60*.8)){missing++;return false;}
 hi=-DBL_MAX;lo=DBL_MAX;
 for(int j=0;j<n;j++){if(r[j].time<a || r[j].time+(session?60:86400)>b){missing++;return false;}hi=MathMax(hi,r[j].high);lo=MathMin(lo,r[j].low);}
 return hi>lo;
}
void UpdateLevels(datetime now,double bid)
{
 datetime d=Midnight(now),w=Monday(now);double hi=0,lo=0;
 if(d!=day){day=d;asia=london=false;for(int i=0;i<6;i++)levels[i].state=3;
  MqlRates r[];if(CopyRates(_Symbol,PERIOD_D1,1,1,r)==1 && r[0].time+86400<=now){Form(0,r[0].high,now,d+86400,bid);Form(1,r[0].low,now,d+86400,bid);}else missing++;
 }
 if(w!=week){week=w;levels[6].state=levels[7].state=3;if(Range(w-7*86400,w,hi,lo,false)){Form(6,hi,now,w+7*86400,bid);Form(7,lo,now,w+7*86400,bid);}}
 if(!asia && now>=d+6*3600){asia=true;if(Range(d,d+6*3600,hi,lo,true)){Form(2,hi,now,d+86400,bid);Form(3,lo,now,d+86400,bid);}}
 if(!london && now>=d+10*3600){london=true;if(Range(d+7*3600,d+10*3600,hi,lo,true)){Form(4,hi,now,d+86400,bid);Form(5,lo,now,d+86400,bid);}}
}
void Enter(int i,datetime now)
{
 levels[i].state=3;if(now<InpTradeFrom)return;
 ulong ticket;if(Own(ticket)){busy++;return;}
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;int side=Side(i);double entry=side>0?q.ask:q.bid;
 double stop=NormalizeDouble((side>0?MathFloor((entry-atr)/tickSize):MathCeil((entry+atr)/tickSize))*tickSize,_Digits),target=Rounded(entry+side*atr);
 double gap=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point,ref=side>0?q.bid:q.ask;
 if(side*(entry-stop)<=0 || side*(target-entry)<=0 || side*(ref-stop)<gap || side*(target-ref)<gap){skips++;return;}
 double one=0;ENUM_ORDER_TYPE type=side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 if(!OrderCalcProfit(type,_Symbol,1,entry,stop,one) || MathAbs(one)<=0){skips++;return;}
 double vmin=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),vmax=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
 double cash=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100,raw=cash/MathAbs(one),volume=MathMax(vmin,MathMin(vmax,MathCeil((raw-1e-12)/step)*step)),margin=0;
 if(volume<=0 || !OrderCalcMargin(type,_Symbol,volume,entry,margin) || margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)){skips++;return;}
 bool ok=side>0?trade.Buy(volume,_Symbol,0,stop,target,"LC "+Names[i]):trade.Sell(volume,_Symbol,0,stop,target,"LC "+Names[i]);
 if(ok && trade.ResultRetcode()==TRADE_RETCODE_DONE){entries++;PrintFormat("LC_ORDER at=%I64d i=%d type=%d entry=%.8f fill=%.8f sl=%.8f tp=%.8f atr=%.8f level=%.8f lots=%.8f risk=%.8f planned=%.8f order=%I64u",(long)now,i,side,entry,trade.ResultPrice(),stop,target,atr,levels[i].p,volume,volume*MathAbs(one),cash,trade.ResultOrder());}
 else{entryFails++;PrintFormat("LC_ENTRY_FAIL %u %s",trade.ResultRetcode(),trade.ResultRetcodeDescription());}
}
int OnInit()
{
 if(!MQLInfoInteger(MQL_TESTER)){Print("Research only: tester required");return INIT_FAILED;}
 if(InpEntry<0 || InpEntry>1 || InpRiskPercent<=0)return INIT_PARAMETERS_INCORRECT;
 tickSize=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);if(tickSize<=0)return INIT_FAILED;
 atrHandle=iATR(_Symbol,PERIOD_M5,14);if(atrHandle==INVALID_HANDLE)return INIT_FAILED;
 for(int i=0;i<8;i++){levels[i].state=3;donorN[i]=0;}
 trade.SetExpertMagicNumber(InpMagic);trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(1000);
 PrintFormat("LC_SPEC symbol=%s description=%s broker=%s currency=%s leverage=%d contract=%.8f min=%.8f max=%.8f step=%.8f tick=%.8f stops=%d swapLong=%.8f swapShort=%.8f",_Symbol,SymbolInfoString(_Symbol,SYMBOL_DESCRIPTION),AccountInfoString(ACCOUNT_COMPANY),AccountInfoString(ACCOUNT_CURRENCY),(int)AccountInfoInteger(ACCOUNT_LEVERAGE),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),tickSize,(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoDouble(_Symbol,SYMBOL_SWAP_LONG),SymbolInfoDouble(_Symbol,SYMBOL_SWAP_SHORT));
 return INIT_SUCCEEDED;
}
void OnDeinit(const int reason)
{
 IndicatorRelease(atrHandle);
 PrintFormat("LC_SUMMARY tag=%s forms=%d missing=%d noDonor=%d touches=%d orders=%d busy=%d skips=%d entryFails=%d closeFails=%d retestExpired=%d quotes=%I64d volumeQuotes=%I64d tradeFlags=%I64d",InpTag,forms,missing,noDonor,touches,entries,busy,skips,entryFails,closeFails,retestExpired,quotes,volumeQuotes,tradeFlags);
}
void OnTick()
{
 datetime now=TimeCurrent();MqlTick q;if(!SymbolInfoTick(_Symbol,q) || q.bid<=0 || q.ask<=0)return;
 quotes++;if(q.volume_real>0 || q.volume>0)volumeQuotes++;if((q.flags&TICK_FLAG_BUY)!=0 || (q.flags&TICK_FLAG_SELL)!=0)tradeFlags++;
 ulong ticket;if(Own(ticket) && now-PositionGetInteger(POSITION_TIME)>=3600 && now-lastExitAttempt>=60){lastExitAttempt=now;if(!trade.PositionClose(ticket) || trade.ResultRetcode()!=TRADE_RETCODE_DONE){closeFails++;PrintFormat("LC_CLOSE_FAIL %u",trade.ResultRetcode());}}
 datetime m=now-now%60;bool newM5=false;MqlRates bar[];
 if(m!=lastMinute){lastMinute=m;datetime t=iTime(_Symbol,PERIOD_M5,0);if(t!=lastM5){double a[];if(CopyBuffer(atrHandle,0,1,1,a)!=1 || a[0]<=0)return;atr=a[0];lastM5=t;newM5=CopyRates(_Symbol,PERIOD_M5,1,1,bar)==1 && bar[0].time+300<=now;}
  if(atr>0)UpdateLevels(now,q.bid);
 }
 if(atr<=0){previousBid=q.bid;return;}
 // Confirm retest only from completed, distinct bars, before processing this tick's new touches.
 if(InpEntry==1 && newM5){for(int i=0;i<8;i++){
  if(levels[i].state!=1 && levels[i].state!=2)continue;
  if(now>=levels[i].expiry || now-levels[i].touched>1800){levels[i].state=3;retestExpired++;continue;}
  int side=Side(i);bool outside=side*(bar[0].close-levels[i].p)>0;
  if(levels[i].state==1 && bar[0].time+300>levels[i].touched && outside){levels[i].state=2;levels[i].broken=bar[0].time;}
  else if(levels[i].state==2 && bar[0].time>levels[i].broken && outside && (side>0?bar[0].low<=levels[i].p:bar[0].high>=levels[i].p))Enter(i,now);
 }}
 for(int i=0;i<8;i++){
  if(now>=levels[i].expiry){levels[i].state=3;continue;}
  if(levels[i].state!=0 || previousBid<=0)continue;
  int side=Side(i);if(side*(previousBid-levels[i].p)<0 && side*(q.bid-levels[i].p)>=0){levels[i].touched=now;levels[i].state=1;if(now>=InpTradeFrom){touches++;PrintFormat("LC_TOUCH at=%I64d i=%d level=%.8f previous=%.8f bid=%.8f",(long)now,i,levels[i].p,previousBid,q.bid);}
   if(InpEntry==0)Enter(i,now);
   else if(Own(ticket)){levels[i].state=3;if(now>=InpTradeFrom)busy++;}
  }
 }
 previousBid=q.bid;
}

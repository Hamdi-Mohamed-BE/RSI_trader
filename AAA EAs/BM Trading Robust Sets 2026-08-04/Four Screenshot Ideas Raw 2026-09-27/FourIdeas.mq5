#property strict
#property version "1.00"
#property description "Research only: four screenshot strategies, unchanged raw signals, explicit clocks and sizing."
#include <Trade/Trade.mqh>
input int InpMode=1;
input bool InpControl=false;
input double InpRiskPercent=1.0;
input double InpNotionalUSD=10000.0;
input int InpServerUtcOffsetHours=0;
input long InpMagic=9274040;
input string InpTag="smoke";
CTrade trade;
datetime lastMinute=0,lastM5=0,dueExit=0;
int dayKey=0,rangeCount=0,rangeMissing=0,entryCount=0,skipCount=0,failedCount=0,closeFailed=0,cancelFailed=0;
bool acted=false,traded=false,rangeReady=false,everBought=false;
double rangeHigh=0,rangeLow=0,tickSize=0;
int atrHandle=INVALID_HANDLE;

datetime Stamp(int y,int m,int d,int h)
{
 MqlDateTime x;ZeroMemory(x);x.year=y;x.mon=m;x.day=d;x.hour=h;return StructToTime(x);
}
int Sunday(int y,int m,int nth)
{
 MqlDateTime x;TimeToStruct(Stamp(y,m,1,0),x);return 1+(7-x.day_of_week)%7+(nth-1)*7;
}
datetime NY(datetime server)
{
 datetime utc=server-InpServerUtcOffsetHours*3600;MqlDateTime x;TimeToStruct(utc,x);
 datetime a=Stamp(x.year,3,Sunday(x.year,3,2),7),b=Stamp(x.year,11,Sunday(x.year,11,1),6);
 return utc+((utc>=a && utc<b)?-4:-5)*3600;
}
datetime Clock(datetime server){return NY(server)+(InpMode==4?0:7*3600);}
int Key(datetime local){MqlDateTime x;TimeToStruct(local,x);return x.year*10000+x.mon*100+x.day;}
int Minute(datetime local){MqlDateTime x;TimeToStruct(local,x);return x.hour*60+x.min;}
double Price(double p){return NormalizeDouble(MathRound(p/tickSize)*tickSize,_Digits);}
double Outward(double p,int side){return NormalizeDouble((side>0?MathFloor(p/tickSize+1e-8):MathCeil(p/tickSize-1e-8))*tickSize,_Digits);}
bool OwnPosition(ulong &ticket)
{
 for(int i=PositionsTotal()-1;i>=0;i--){ticket=PositionGetTicket(i);if(ticket && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)return true;}
 ticket=0;return false;
}
void Cancel()
{
 for(int i=OrdersTotal()-1;i>=0;i--){ulong tk=OrderGetTicket(i);if(!tk || OrderGetString(ORDER_SYMBOL)!=_Symbol || OrderGetInteger(ORDER_MAGIC)!=InpMagic)continue;
  if(!trade.OrderDelete(tk)){cancelFailed++;PrintFormat("IDEA_CANCEL_FAIL %I64u %u",tk,trade.ResultRetcode());}}
}
void Close()
{
 for(int i=PositionsTotal()-1;i>=0;i--){ulong tk=PositionGetTicket(i);if(!tk || PositionGetString(POSITION_SYMBOL)!=_Symbol || PositionGetInteger(POSITION_MAGIC)!=InpMagic)continue;
  if(!trade.PositionClose(tk)){closeFailed++;PrintFormat("IDEA_CLOSE_FAIL %I64u %u",tk,trade.ResultRetcode());}}
}
double Lots(int side,double entry,double stop)
{
 double lo=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),hi=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
 if(lo<=0 || hi<=0 || step<=0)return 0;
 if(stop==0){double contract=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);double raw=InpNotionalUSD/(contract*entry);double v=MathFloor(raw/step+1e-10)*step;return v<lo?0:MathMin(hi,v);}
 // Exact raw sizing helper reused from Gold NY30 study: 1% current equity, upward lot step.
 double one=0;if(!OrderCalcProfit(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,1.,entry,stop,one) || MathAbs(one)<=0)return 0;
 double raw=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100./MathAbs(one);
 return MathMax(lo,MathMin(hi,MathCeil((MathMin(raw,hi)-1e-12)/step)*step));
}
bool Geometry(int side,double entry,double stop,double target,bool pending)
{
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return false;
 double gap=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
 if(stop!=0 && side*(entry-stop)<=0)return false;
 if(target!=0 && side*(target-entry)<=0)return false;
 if(pending && side*(entry-(side>0?q.ask:q.bid))<MathMax(gap,tickSize)-1e-9)return false;
 double ref=pending?entry:(side>0?q.bid:q.ask);
 if(stop!=0 && side*(ref-stop)<gap-1e-9)return false;
 if(target!=0 && side*(target-ref)<gap-1e-9)return false;
 return true;
}
bool Enter(int side,double stop,double target,bool pending,double level,string reason)
{
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return false;
 double entry=pending?Price(level):(side>0?q.ask:q.bid);
 if(stop!=0)stop=Outward(stop,side);if(target!=0)target=Price(target);
 if(!Geometry(side,entry,stop,target,pending)){skipCount++;PrintFormat("IDEA_SKIP %s side=%d geometry entry=%.8f sl=%.8f tp=%.8f",TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),side,entry,stop,target);return false;}
 double lots=Lots(side,entry,stop),margin=0;
 if(lots<=0 || !OrderCalcMargin(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,lots,entry,margin) || margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)){skipCount++;Print("IDEA_SKIP lot_or_margin");return false;}
 double risk=0;if(stop!=0 && !OrderCalcProfit(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,lots,entry,stop,risk)){skipCount++;return false;}
 bool ok=false;
 if(pending)ok=side>0?trade.BuyStop(lots,entry,_Symbol,stop,target,ORDER_TIME_GTC,0,"Ideas "+reason):trade.SellStop(lots,entry,_Symbol,stop,target,ORDER_TIME_GTC,0,"Ideas "+reason);
 else ok=side>0?trade.Buy(lots,_Symbol,0,stop,target,"Ideas "+reason):trade.Sell(lots,_Symbol,0,stop,target,"Ideas "+reason);
 if(ok && (trade.ResultRetcode()==TRADE_RETCODE_DONE || trade.ResultRetcode()==TRADE_RETCODE_PLACED)){
  entryCount++;PrintFormat("IDEA_ORDER t=%s mode=%d control=%d side=%d pending=%d entry=%.8f sl=%.8f tp=%.8f lot=%.8f risk=%.8f eq=%.8f high=%.8f low=%.8f due=%s order=%I64u",TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),InpMode,(int)InpControl,side,(int)pending,entry,stop,target,lots,MathAbs(risk),AccountInfoDouble(ACCOUNT_EQUITY),rangeHigh,rangeLow,TimeToString(dueExit,TIME_DATE|TIME_SECONDS),trade.ResultOrder());
  if(!pending)traded=true;return true;}
 failedCount++;PrintFormat("IDEA_ENTRY_FAIL %u %s",trade.ResultRetcode(),trade.ResultRetcodeDescription());return false;
}
bool Range(datetime now,int begin,int finish)
{
 datetime local=Clock(now),mid=local-Minute(local)*60-(local%60),offset=local-now;
 MqlRates bars[];int n=CopyRates(_Symbol,PERIOD_M1,mid+begin*60-offset,mid+finish*60-offset-1,bars);
 if(n!=finish-begin){rangeMissing++;PrintFormat("IDEA_RANGE_MISSING %d count=%d expected=%d",dayKey,n,finish-begin);return false;}
 rangeHigh=bars[0].high;rangeLow=bars[0].low;
 for(int i=0;i<n;i++){if(i && bars[i].time-bars[i-1].time!=60){rangeMissing++;return false;}rangeHigh=MathMax(rangeHigh,bars[i].high);rangeLow=MathMin(rangeLow,bars[i].low);}
 rangeCount++;PrintFormat("IDEA_RANGE date=%d start=%s end=%s count=%d high=%.8f low=%.8f",dayKey,TimeToString(bars[0].time,TIME_DATE|TIME_SECONDS),TimeToString(bars[n-1].time,TIME_DATE|TIME_SECONDS),n,rangeHigh,rangeLow);
 return rangeHigh>rangeLow;
}
bool SMA25(datetime now,double &sma)
{
 MqlRates bars[];int n=CopyRates(_Symbol,PERIOD_M15,now-60*86400,now-1,bars);if(n<1)return false;
 int keys[];double closes[];int count=0;
 for(int i=0;i<n;i++){datetime local=Clock(bars[i].time);MqlDateTime d;TimeToStruct(local,d);int k=Key(local);
  if(k>=dayKey || d.day_of_week==0 || d.day_of_week==6 || bars[i].time+900>now)continue;
  if(count==0 || keys[count-1]!=k){ArrayResize(keys,count+1);ArrayResize(closes,count+1);keys[count]=k;closes[count]=bars[i].close;count++;}
  else closes[count-1]=bars[i].close;}
 if(count<25)return false;sma=0;string evidence="";
 for(int i=count-25;i<count;i++){sma+=closes[i];evidence+=IntegerToString(keys[i])+":"+DoubleToString(closes[i],_Digits)+",";}
 sma/=25;PrintFormat("IDEA_SMA date=%d mean=%.8f closes=%s",dayKey,sma,evidence);return true;
}
void OnTradeTransaction(const MqlTradeTransaction &tx,const MqlTradeRequest &req,const MqlTradeResult &res)
{
 if(tx.type!=TRADE_TRANSACTION_DEAL_ADD || !HistoryDealSelect(tx.deal))return;
 if(HistoryDealGetInteger(tx.deal,DEAL_MAGIC)!=InpMagic || HistoryDealGetString(tx.deal,DEAL_SYMBOL)!=_Symbol)return;
 if(HistoryDealGetInteger(tx.deal,DEAL_ENTRY)==DEAL_ENTRY_IN){traded=true;if(InpMode==1)Cancel();}
}
int OnInit()
{
 if(!MQLInfoInteger(MQL_TESTER)){Print("Research tester only");return INIT_FAILED;}
 if(InpMode<1 || InpMode>4 || InpRiskPercent<=0 || InpNotionalUSD<=0)return INIT_PARAMETERS_INCORRECT;
 tickSize=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);if(tickSize<=0)return INIT_FAILED;
 trade.SetExpertMagicNumber(InpMagic);trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(1000);
 if(InpMode==4){atrHandle=iATR(_Symbol,PERIOD_M5,14);if(atrHandle==INVALID_HANDLE)return INIT_FAILED;}
 PrintFormat("IDEA_SPEC symbol=%s contract=%.8f min=%.8f max=%.8f step=%.8f tick=%.8f stops=%d clockOffset=%d",_Symbol,SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),tickSize,(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),InpServerUtcOffsetHours);
 return INIT_SUCCEEDED;
}
void OnDeinit(const int reason)
{
 if(atrHandle!=INVALID_HANDLE)IndicatorRelease(atrHandle);
 PrintFormat("IDEA_SUMMARY tag=%s ranges=%d missing=%d orders=%d skips=%d entryfail=%d closefail=%d cancelfail=%d",InpTag,rangeCount,rangeMissing,entryCount,skipCount,failedCount,closeFailed,cancelFailed);
}
void OnTick()
{
 datetime now=TimeCurrent();ulong tk=0;
 if(InpMode==1 && OwnPosition(tk)){traded=true;Cancel();}
 datetime minute=now-now%60;if(minute==lastMinute)return;lastMinute=minute;
 datetime local=Clock(now);MqlDateTime d;TimeToStruct(local,d);int m=Minute(local),key=Key(local);
 if(key!=dayKey){Cancel();dayKey=key;acted=false;traded=false;rangeReady=false;rangeHigh=rangeLow=0;lastM5=0;}
 if(dueExit>0 && local>=dueExit){Close();Cancel();if(!OwnPosition(tk))dueExit=0;}
 if(d.day_of_week==0 || d.day_of_week==6)return;
 if(OwnPosition(tk))return;
 datetime midnight=local-m*60-d.sec;
 if(InpMode==1){
  if(m>=1080){Cancel();return;}
  if(m!=360 || acted || traded)return;acted=true;rangeReady=Range(now,180,360);if(!rangeReady)return;
  dueExit=midnight+1080*60;
  if(InpControl){int side=((long)(midnight/86400)%2==0)?1:-1;Enter(side,side>0?rangeLow:rangeHigh,0,false,0,"MorningControl");}
  else{Enter(1,rangeLow,0,true,rangeHigh,"Morning");Enter(-1,rangeHigh,0,true,rangeLow,"Morning");}return;
 }
 if(InpMode==2){
  if(d.day_of_week!=1 || m!=65 || acted)return;acted=true;double sma=0;MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
  if(!InpControl && !SMA25(now,sma)){skipCount++;Print("IDEA_SKIP sma_history");return;}
  PrintFormat("IDEA_FILTER date=%d bid=%.8f sma=%.8f pass=%d",dayKey,q.bid,sma,(int)(InpControl || q.bid<sma));
  if(!InpControl && q.bid>=sma)return;dueExit=midnight+86400+1430*60;Enter(1,0,0,false,0,InpControl?"TuesdayControl":"Tuesday");return;
 }
 if(InpMode==3){
  if(InpControl){if(!everBought){dueExit=0;everBought=Enter(1,0,0,false,0,"BuyHold");}return;}
  if(m!=65 || acted)return;acted=true;dueExit=midnight+1430*60;Enter(1,0,0,false,0,"DailyLong");return;
 }
 if(InpMode==4){
  if(m<585 || m>900 || traded)return;
  if(!acted){acted=true;rangeReady=Range(now,570,585);}if(!rangeReady)return;
  MqlRates b[];if(CopyRates(_Symbol,PERIOD_M5,1,1,b)!=1 || b[0].time==lastM5)return;lastM5=b[0].time;
  if(Minute(NY(b[0].time))<585 || b[0].time+300>now)return;
  int side=0;if(InpControl){if(m!=590)return;side=((long)(midnight/86400)%2==0)?1:-1;traded=true;}
  else if(b[0].close>rangeHigh)side=1;else if(b[0].close<rangeLow)side=-1;if(side==0)return;
  double atr[];if(CopyBuffer(atrHandle,0,1,1,atr)!=1 || atr[0]<=0)return;
  double stop=side>0?rangeLow-.25*atr[0]:rangeHigh+.25*atr[0];double target=side>0?rangeHigh+2*(rangeHigh-rangeLow):rangeLow-2*(rangeHigh-rangeLow);
  PrintFormat("IDEA_SIGNAL now=%s bar=%s close=%.8f atr=%.8f side=%d",TimeToString(now,TIME_DATE|TIME_SECONDS),TimeToString(b[0].time,TIME_DATE|TIME_SECONDS),b[0].close,atr[0],side);
  dueExit=midnight+955*60;Enter(side,stop,target,false,0,InpControl?"ORBControl":"NYORB");
 }
}

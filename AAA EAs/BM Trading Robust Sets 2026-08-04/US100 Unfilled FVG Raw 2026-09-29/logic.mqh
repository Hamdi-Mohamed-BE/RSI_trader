// Strategy-only code. Shared execution/ledger plumbing is snapshotted by prepare.py.
int auditFile=INVALID_HANDLE,armed=0,expired=0,touched=0,triggered=0;
bool active=false;
int displacement=0,parentSeconds=60;
ENUM_TIMEFRAMES parentTF=PERIOD_M1;
datetime ready=0,seenParent=0;
double midpoint=0,reference=0,parentATR=0;
MqlRates parentSnapshot[];
int NYMinute(datetime t){
 MqlDateTime d;TimeToStruct(t,d);int yr=d.year;
 MqlDateTime a;ZeroMemory(a);a.year=yr;a.mon=3;a.day=1;
 datetime mar=StructToTime(a);TimeToStruct(mar,a);
 datetime begin=mar+(7-a.day_of_week)%7*86400+7*86400+7*3600;
 ZeroMemory(a);a.year=yr;a.mon=11;a.day=1;datetime nov=StructToTime(a);TimeToStruct(nov,a);
 datetime end=nov+(7-a.day_of_week)%7*86400+6*3600;
 int shift=(t>=begin&&t<end)?4:5;
 TimeToStruct(t-shift*3600,d);return d.hour*60+d.min;
}
bool EntryTime(datetime t){MqlDateTime d;TimeToStruct(t,d);int m=NYMinute(t);return d.day_of_week>0&&d.day_of_week<6&&m>=570&&m<930;}
bool SameColour(MqlRates &b,int dir){return dir*(b.close-b.open)>0;}
bool Arm(MqlRates &m[]){
 MqlRates r[];int n=CopyRates(_Symbol,parentTF,1,20,r);if(n!=20)return false;
 int z=n-1;if(r[z].time==seenParent)return false;seenParent=r[z].time;
 datetime closed=r[z].time+parentSeconds;
 if(closed!=lastMinute||!EntryTime(closed)||r[z].time-r[z-1].time!=parentSeconds||r[z-1].time-r[z-2].time!=parentSeconds)return false;
 double atr=0;for(int i=z-15;i<=z-2;i++)atr+=MathMax(r[i].high-r[i].low,MathMax(MathAbs(r[i].high-r[i-1].close),MathAbs(r[i].low-r[i-1].close)));atr/=14;
 double body=r[z-1].close-r[z-1].open,range=r[z-1].high-r[z-1].low;
 if(atr<=0||MathAbs(body)<atr||MathAbs(body)<.60*range)return false;
 int dir=0;double mid=0;
 if(body>0&&r[z].low>r[z-2].high&&r[z].close<=r[z-1].high){dir=1;mid=(r[z].low+r[z-2].high)/2;}
 if(body<0&&r[z].high<r[z-2].low&&r[z].close>=r[z-1].low){dir=-1;mid=(r[z].high+r[z-2].low)/2;}
 if(dir==0)return false;
 double level=0;int k=ArraySize(m)-1;
 if(InpMode%2==0){
  int j=k;while(j>=k-19&&!SameColour(m[j],dir))j--;
  if(j<k-19)return false;
  while(j>k-19&&SameColour(m[j-1],dir))j--;
  level=m[j].open;
  if(dir*(m[k].close-level)<0||dir*(level-mid)<=0)return false;
 }
 displacement=dir;midpoint=mid;reference=level;ready=closed;parentATR=atr;
 ArrayCopy(parentSnapshot,r);active=true;armed++;return true;
}
bool Confirm(MqlRates &m[],double &level){
 int n=ArraySize(m),z=n-1;
 if(m[z].time<ready)return false;
 if(InpMode%2==0){level=reference;return displacement*(m[z-1].close-level)>=0&&displacement*(m[z].close-level)<0;}
 for(int c=z-1;c>=2&&m[c].time>=m[z].time-20*60;c--){
  if(m[c].time-m[c-1].time!=60||m[c-1].time-m[c-2].time!=60)continue;
  bool gap=displacement==1?m[c].low>m[c-2].high:m[c].high<m[c-2].low;
  if(!gap)continue;
  double edge=displacement==1?m[c-2].high:m[c-2].low;
  if(displacement*(edge-midpoint)<=0)continue;
  bool intact=true;for(int j=c+1;j<z;j++)if(displacement*(m[j].close-edge)<0){intact=false;break;}
  if(intact&&displacement*(m[z-1].close-edge)>=0&&displacement*(m[z].close-edge)<0){level=edge;return true;}
 }
 return false;
}
void Snapshot(ulong id,string kind,MqlRates &bars[]){for(int i=0;i<ArraySize(bars);i++)FileWrite(auditFile,id,kind,(long)bars[i].time,bars[i].open,bars[i].high,bars[i].low,bars[i].close);}
void EnterFVG(MqlRates &m[],double level){
 MqlTick q;if(!SymbolInfoTick(_Symbol,q)||q.bid<=0||q.ask<=0){skips++;return;}
 int rawSide=-displacement;
 double rawQuote=rawSide>0?q.ask:q.bid,target=Price(midpoint),distance=rawSide*(target-rawQuote);
 if(distance<=tickSize||displacement*(q.bid-midpoint)<=0||displacement*(q.ask-midpoint)<=0){skips++;return;}
 int s=InpControl?((Hash((uint)ready+(uint)lastMinute+InpSeed)&1)==1?1:-1):rawSide;
 double entry=s>0?q.ask:q.bid,sl=Price(entry-s*distance),tp=Price(entry+s*distance),unit=0,margin=0;
 ENUM_ORDER_TYPE type=s>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 if(!OrderCalcProfit(type,_Symbol,1,entry,sl,unit)||unit>=0){skips++;return;}
 double goal=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100;
 double volume=MathMax(minLot,MathCeil((goal/-unit-1e-10)/lotStep)*lotStep);volume=NormalizeDouble(volume,8);
 double gap=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point,ref=s>0?q.bid:q.ask;
 if(volume>SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX)||s*(ref-sl)<MathMax(gap,tickSize)||s*(tp-ref)<gap||!OrderCalcMargin(type,_Symbol,volume,entry,margin)||margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)){skips++;return;}
 bool ok=s>0?trade.Buy(volume,_Symbol,0,sl,tp,"UnfilledFVG"):trade.Sell(volume,_Symbol,0,sl,tp,"UnfilledFVG");
 if(!ok||trade.ResultRetcode()!=TRADE_RETCODE_DONE){entryFails++;PrintFormat("MS_ENTRY_FAIL code=%u",trade.ResultRetcode());return;}
 ulong ticket;if(!Own(ticket)){entryFails++;return;}int k=ArraySize(initial);ArrayResize(initial,k+1);ZeroMemory(initial[k]);
 initial[k].id=(ulong)PositionGetInteger(POSITION_IDENTIFIER);initial[k].time=(datetime)PositionGetInteger(POSITION_TIME);initial[k].side=s;
 initial[k].volume=PositionGetDouble(POSITION_VOLUME);initial[k].fill=PositionGetDouble(POSITION_PRICE_OPEN);initial[k].sl=PositionGetDouble(POSITION_SL);initial[k].tp=PositionGetDouble(POSITION_TP);initial[k].requestedRisk=goal;initial[k].atr=parentATR;
 double actual=0;if(OrderCalcProfit(type,_Symbol,initial[k].volume,initial[k].fill,initial[k].sl,actual))initial[k].risk=-actual;
 FileWrite(signalFile,initial[k].id,(long)ready,(long)m[ArraySize(m)-1].time,(long)TimeCurrent(),rawSide,s,parentSeconds,InpMode%2,midpoint,level,parentATR,entry,initial[k].fill,q.ask-q.bid);
 Snapshot(initial[k].id,"parent",parentSnapshot);Snapshot(initial[k].id,"m1",m);entries++;
}
int OnInit(){
 if(!MQLInfoInteger(MQL_TESTER)){Print("RESEARCH ONLY; tester required");return INIT_FAILED;}
 if(InpMode<0||InpMode>5||InpRR!=1||InpRiskPercent<=0||InpRiskPercent>1||_Symbol!="USTEC")return INIT_PARAMETERS_INCORRECT;
 parentTF=InpMode<2?PERIOD_M1:(InpMode<4?PERIOD_M5:PERIOD_M15);parentSeconds=PeriodSeconds(parentTF);
 tickSize=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);lotStep=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);minLot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
 if(tickSize<=0||lotStep<=0||minLot<=0)return INIT_FAILED;
 trade.SetExpertMagicNumber(InpMagic);trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(1000);
 FolderCreate("CalyxUnfilledFVG20260929",FILE_COMMON);
 trace=FileOpen("CalyxUnfilledFVG20260929\\"+InpTag+"-trace.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 signalFile=FileOpen("CalyxUnfilledFVG20260929\\"+InpTag+"-signals.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 auditFile=FileOpen("CalyxUnfilledFVG20260929\\"+InpTag+"-audit.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(trace==INVALID_HANDLE||signalFile==INVALID_HANDLE||auditFile==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(trace,"time","balance","equity");
 FileWrite(signalFile,"position_id","ready","signal_time","fill_time","raw_side","actual_side","parent_seconds","trigger","midpoint","reference","atr","quote","fill","spread");
 FileWrite(auditFile,"position_id","kind","time","open","high","low","close");
 PrintFormat("MS_SPEC symbol=%s description=%s broker=%s server=%s demo=%d currency=%s contract=%.8f min=%.8f step=%.8f tick=%.8f",_Symbol,SymbolInfoString(_Symbol,SYMBOL_DESCRIPTION),AccountInfoString(ACCOUNT_COMPANY),AccountInfoString(ACCOUNT_SERVER),AccountInfoInteger(ACCOUNT_TRADE_MODE)==ACCOUNT_TRADE_MODE_DEMO,AccountInfoString(ACCOUNT_CURRENCY),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),minLot,lotStep,tickSize);
 return INIT_SUCCEEDED;
}
void OnTick(){
 datetime now=TimeCurrent();ulong ticket;int remaining=0;bool session=Session(now,remaining);
 if(Own(ticket)&& (now-(datetime)PositionGetInteger(POSITION_TIME)>=3600||NYMinute(now)>=955||(session&&remaining<=300)))Close();
 datetime minute=now-now%60;if(minute==lastMinute)return;lastMinute=minute;
 if(now>=InpTradeFrom)FileWrite(trace,(long)now,AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY));
 if(now<InpTradeFrom)return;
 if(!EntryTime(now)||Own(ticket)||!session||remaining<1800){active=false;return;}
 MqlRates m[];int n=CopyRates(_Symbol,PERIOD_M1,1,64,m);
 if(n!=64||m[n-1].time+60!=minute||now-minute>=10){active=false;stale++;return;}
 if(active){
  if(minute-ready>1800){active=false;expired++;}
  else{
   // Check all intervening bars, including bars after any quote discontinuity.
   for(int i=0;i<n;i++)if(m[i].time>=ready&&(displacement==1?m[i].low<=midpoint:m[i].high>=midpoint)){active=false;touched++;break;}
  }
  if(active){double level=0;if(Confirm(m,level)){triggered++;EnterFVG(m,level);active=false;return;}}
 }
 if(!active)Arm(m);
}
void OnDeinit(const int why){if(trace!=INVALID_HANDLE)FileClose(trace);if(signalFile!=INVALID_HANDLE)FileClose(signalFile);if(auditFile!=INVALID_HANDLE)FileClose(auditFile);PrintFormat("MS_SUMMARY entries=%d entryFails=%d closeFails=%d skips=%d stale=%d armed=%d expired=%d touched=%d triggered=%d",entries,entryFails,closeFails,skips,stale,armed,expired,touched,triggered);}

#property copyright "Calyx relative value pairs — research only"
#property version "1.00"
#property strict
#include <Trade/Trade.mqh>
input string InpSymbolA="BTCUSD";
input string InpSymbolB="ETHUSD";
input int InpTimeframeMinutes=15;
input int InpWindow=64;
input int InpModel=0; // 0 log-ratio; 1 rolling OLS
input double InpEntryZ=2.0;
input int InpSession=0; // all, Asia UTC, London local, NY local, overlap, union
input int InpStopMode=0; // SD, spread ATR, recent adverse swing
input int InpExitMode=7; // 0..6 fixed R; 7 entry mean; 8 rolling mean; 9 timed
input double InpRR=1.0;
input int InpManagement=0; // none, BE0.5, BE1, M15 50/20, trail0.5, trail1, volatility
input int InpDirection=0; // 0 both; +1 long A/short B; -1 short A/long B
input int InpHoldHours=24;
input double InpRiskPercent=1.0; // combined basket risk, not per leg
input int InpServerUTCOffsetHours=0;
input double InpSpreadFloorA=0;
input double InpSpreadFloorB=0;
input long InpMagic=969060201;
input string InpCase="pairs-research";

CTrade trade;
bool active=false,closing=false;
int side=0,reason=0,basket=0,logfile=INVALID_HANDLE,featurefile=INVALID_HANDLE;
int rejects=0,legfail=0;
datetime lastbar=0,lastclosed=0,entrytime=0,lastm15=0;
ulong ida=0,idb=0;
double beta0=1,mu0=0,budget=0,entrybalance=0,entrya=0,entryb=0,lotsa=0,lotsb=0;
double floorR=-1e100,highR=0,initialRR=0;
double feat[];

datetime Build(int y,int m,int d,int h){MqlDateTime x;ZeroMemory(x);x.year=y;x.mon=m;x.day=d;x.hour=h;return StructToTime(x);}
int Sunday(int y,int m,int n){MqlDateTime x;TimeToStruct(Build(y,m,1,0),x);return 1+(7-x.day_of_week)%7+(n-1)*7;}
int LastSunday(int y,int m){MqlDateTime x;TimeToStruct(Build(y,m+1,1,0)-86400,x);return x.day-x.day_of_week;}
int NYOffset(datetime t){MqlDateTime x;TimeToStruct(t,x);return t>=Build(x.year,3,Sunday(x.year,3,2),7)&&t<Build(x.year,11,Sunday(x.year,11,1),6)?-4:-5;}
int LondonOffset(datetime t){MqlDateTime x;TimeToStruct(t,x);return t>=Build(x.year,3,LastSunday(x.year,3),1)&&t<Build(x.year,10,LastSunday(x.year,10),1)?1:0;}
bool Session(datetime t){t-=InpServerUTCOffsetHours*3600;MqlDateTime u,l,n;TimeToStruct(t,u);TimeToStruct(t+3600*LondonOffset(t),l);TimeToStruct(t+3600*NYOffset(t),n);bool lon=l.hour>=8&&l.hour<17,ny=n.hour>=8&&n.hour<17;switch(InpSession){case 1:return u.hour<8;case 2:return lon;case 3:return ny;case 4:return lon&&ny;case 5:return lon||ny;}return true;}
double Point(string s){return SymbolInfoDouble(s,SYMBOL_POINT);}
double Contract(string s){return SymbolInfoDouble(s,SYMBOL_TRADE_CONTRACT_SIZE);}
double RoundPrice(string s,double p){double tick=SymbolInfoDouble(s,SYMBOL_TRADE_TICK_SIZE);return NormalizeDouble(MathRound(p/tick)*tick,(int)SymbolInfoInteger(s,SYMBOL_DIGITS));}
double Lots(string s,double v){double step=SymbolInfoDouble(s,SYMBOL_VOLUME_STEP);double out=MathFloor(v/step+1e-9)*step;if(out<SymbolInfoDouble(s,SYMBOL_VOLUME_MIN)||out>SymbolInfoDouble(s,SYMBOL_VOLUME_MAX))return 0;return out;}
bool Owned(string s,ulong &ticket){for(int i=PositionsTotal()-1;i>=0;i--){ticket=PositionGetTicket(i);if(ticket&&PositionGetString(POSITION_SYMBOL)==s&&PositionGetInteger(POSITION_MAGIC)==InpMagic)return true;}ticket=0;return false;}
bool Quotes(MqlTick &a,MqlTick &b){if(!SymbolInfoTick(InpSymbolA,a)||!SymbolInfoTick(InpSymbolB,b))return false;return a.bid>0&&b.bid>0&&a.ask>=a.bid&&b.ask>=b.bid&&MathAbs((double)(a.time_msc-b.time_msc))<=30000&&TimeCurrent()-a.time<=30&&TimeCurrent()-b.time<=30;}

bool Features(datetime t)
{
   int sec=InpTimeframeMinutes*60;
   if((long)t%sec!=0)return false;
   MqlRates a[],b[];datetime begin=t-(InpWindow+12)*sec*3;
   int na=CopyRates(InpSymbolA,PERIOD_M5,begin,t-1,a),nb=CopyRates(InpSymbolB,PERIOD_M5,begin,t-1,b);
   if(na<InpWindow||nb<InpWindow)return false;
   double ca[],cb[];ArrayResize(ca,na);ArrayResize(cb,na);
   int n=0,j=0,count=0;long group=-1;datetime last=0;double ac=0,bc=0;
   for(int i=0;i<na;i++)
   {
      while(j<nb&&b[j].time<a[i].time)j++;
      if(j>=nb)break;
      if(b[j].time!=a[i].time)continue;
      long g=(long)a[i].time/sec;
      if(group>=0&&g!=group)
      {
         if(count==InpTimeframeMinutes/5){ca[n]=ac;cb[n]=bc;n++;}
         count=0;
      }
      group=g;count++;ac=a[i].close;bc=b[j].close;last=a[i].time;
   }
   if(count==InpTimeframeMinutes/5){ca[n]=ac;cb[n]=bc;n++;}else return false;
   if(last+300!=t||n<InpWindow+1)return false;
   int first=n-InpWindow-1;double mx=0,my=0;
   for(int i=first;i<n-1;i++){mx+=MathLog(cb[i]);my+=MathLog(ca[i]);}mx/=InpWindow;my/=InpWindow;
   double be=1;
   if(InpModel==1){double den=0,num=0;for(int i=first;i<n-1;i++){double x=MathLog(cb[i])-mx;den+=x*x;num+=x*(MathLog(ca[i])-my);}if(den<=1e-14)return false;be=num/den;if(be<.1||be>3)return false;}
   double mu=my-be*mx,var=0,atr=0,lo=DBL_MAX,hi=-DBL_MAX;
   for(int i=first;i<n-1;i++)
   {
      double r=MathLog(ca[i])-be*MathLog(cb[i]);var+=(r-mu)*(r-mu);
      if(i>=n-9){lo=MathMin(lo,r);hi=MathMax(hi,r);}
      if(i>=n-15){double prior=MathLog(ca[i-1])-be*MathLog(cb[i-1]);atr+=MathAbs(r-prior);}
   }
   double sd=MathSqrt(var/InpWindow),s=MathLog(ca[n-1])-be*MathLog(cb[n-1]);if(sd<=1e-8)return false;
   ArrayResize(feat,9);feat[0]=(s-mu)/sd;feat[1]=be;feat[2]=mu;feat[3]=sd;feat[4]=atr/14.;feat[5]=lo;feat[6]=hi;feat[7]=s;feat[8]=mx;
   if(featurefile!=INVALID_HANDLE)FileWrite(featurefile,(long)t,feat[0],be,mu,sd,feat[4],lo,hi,s,mx);
   return true;
}

double EntryFees()
{
   double fees=0;if(!HistorySelect(entrytime-60,TimeCurrent()+86400))return 0;
   for(int i=0;i<HistoryDealsTotal();i++){ulong d=HistoryDealGetTicket(i);ulong id=(ulong)HistoryDealGetInteger(d,DEAL_POSITION_ID);if(id>0&&(id==ida||id==idb)&&HistoryDealGetInteger(d,DEAL_ENTRY)==DEAL_ENTRY_IN)fees+=HistoryDealGetDouble(d,DEAL_COMMISSION)+HistoryDealGetDouble(d,DEAL_FEE);}
   return fees;
}

void Finalize()
{
   ulong ticket=0;if(Owned(InpSymbolA,ticket)||Owned(InpSymbolB,ticket))return;
   double net=0,swap=0,fees=0,xa=0,xb=0;datetime exit=0;int entries=0,exits=0;
   // In a multi-symbol test the secondary fill timestamp can be ahead of the
   // primary symbol's TimeCurrent. Only already-executed history deals exist.
   if(HistorySelect(entrytime-60,TimeCurrent()+86400))for(int i=0;i<HistoryDealsTotal();i++)
   {
      ulong d=HistoryDealGetTicket(i);ulong id=(ulong)HistoryDealGetInteger(d,DEAL_POSITION_ID);if(id==0||(id!=ida&&id!=idb))continue;
      net+=HistoryDealGetDouble(d,DEAL_PROFIT)+HistoryDealGetDouble(d,DEAL_SWAP)+HistoryDealGetDouble(d,DEAL_COMMISSION)+HistoryDealGetDouble(d,DEAL_FEE);
      swap+=HistoryDealGetDouble(d,DEAL_SWAP);fees+=HistoryDealGetDouble(d,DEAL_COMMISSION)+HistoryDealGetDouble(d,DEAL_FEE);
      if(HistoryDealGetInteger(d,DEAL_ENTRY)==DEAL_ENTRY_IN)entries++;
      else {exits++;exit=MathMax(exit,(datetime)HistoryDealGetInteger(d,DEAL_TIME));if(id==ida)xa=HistoryDealGetDouble(d,DEAL_PRICE);else xb=HistoryDealGetDouble(d,DEAL_PRICE);}
   }
   if(entries<1||exits<entries)return; // wait for both leg-close transactions
   if(logfile!=INVALID_HANDLE){FileWrite(logfile,basket,(long)entrytime,(long)exit,side,entrya,entryb,xa,xb,lotsa,lotsb,net,net/entrybalance,net/budget,reason,swap,fees,initialRR,budget,entries,exits);FileFlush(logfile);}
   active=false;closing=false;lastclosed=TimeCurrent();
}

void Close(int why)
{
   if(!closing){reason=why;closing=true;}
   ulong t=0;
   if(Owned(InpSymbolA,t)){trade.SetTypeFillingBySymbol(InpSymbolA);trade.PositionClose(t);}
   if(Owned(InpSymbolB,t)){trade.SetTypeFillingBySymbol(InpSymbolB);trade.PositionClose(t);}
   Finalize();
}

void Enter(datetime t)
{
   if(!Session(t)||MathAbs(feat[0])<InpEntryZ)return;
   side=feat[0]>0?-1:1;if(InpDirection!=0&&side!=InpDirection)return;
   MqlTick a,b;if(!Quotes(a,b))return;
   double be=feat[1],distance=feat[3];
   if(InpStopMode==1)distance=2.5*feat[4];
   if(InpStopMode==2)distance=(side>0?feat[7]-feat[5]:feat[6]-feat[7])+.25*feat[3];
   if(distance<=0)return;
   double spreadA=MathMax(a.ask-a.bid,InpSpreadFloorA),spreadB=MathMax(b.ask-b.bid,InpSpreadFloorB);
   double cost=spreadA/a.bid+be*spreadB/b.bid+2*(1+be)*.0001;
   distance=MathMax(distance,4*cost);
   entrybalance=AccountInfoDouble(ACCOUNT_EQUITY);budget=entrybalance*InpRiskPercent/100.;double notional=budget/(distance+cost);
   lotsa=Lots(InpSymbolA,notional/(a.bid*Contract(InpSymbolA)));lotsb=Lots(InpSymbolB,be*notional/(b.bid*Contract(InpSymbolB)));
   if(lotsa<=0||lotsb<=0){rejects++;return;}
   double qa=lotsa*Contract(InpSymbolA),qb=lotsb*Contract(InpSymbolB);
   if(MathAbs(qb*b.bid/(qa*a.bid)/be-1)>.15){rejects++;return;}
   entrya=side>0?a.ask:a.bid;entryb=side>0?b.bid:b.ask;
   double da=(budget*.5-2*qa*entrya*.0001)/qa,db=(budget*.5-2*qb*entryb*.0001)/qb;
   if(da<=0||db<=0)return;
   double sla=RoundPrice(InpSymbolA,entrya-side*da),slb=RoundPrice(InpSymbolB,entryb+side*db);
   double gapA=SymbolInfoInteger(InpSymbolA,SYMBOL_TRADE_STOPS_LEVEL)*Point(InpSymbolA),gapB=SymbolInfoInteger(InpSymbolB,SYMBOL_TRADE_STOPS_LEVEL)*Point(InpSymbolB);
   if(side>0?(sla>=a.bid-gapA||slb<=b.ask+gapB):(sla<=a.ask+gapA||slb>=b.bid-gapB)){rejects++;return;}
   beta0=be;mu0=feat[2];entrytime=TimeCurrent();ida=0;idb=0;basket++;active=true;closing=false;reason=0;
   trade.SetTypeFillingBySymbol(InpSymbolA);
   bool ok=side>0?trade.Buy(lotsa,InpSymbolA,0,sla,0,"Calyx pair A"):trade.Sell(lotsa,InpSymbolA,0,sla,0,"Calyx pair A");
   ulong ticket=0;if(!ok||!Owned(InpSymbolA,ticket)){active=false;legfail++;return;}
   ida=(ulong)PositionGetInteger(POSITION_IDENTIFIER);entrya=PositionGetDouble(POSITION_PRICE_OPEN);
   trade.SetTypeFillingBySymbol(InpSymbolB);
   ok=side>0?trade.Sell(lotsb,InpSymbolB,0,slb,0,"Calyx pair B"):trade.Buy(lotsb,InpSymbolB,0,slb,0,"Calyx pair B");
   if(ok&&Owned(InpSymbolB,ticket)){idb=(ulong)PositionGetInteger(POSITION_IDENTIFIER);entryb=PositionGetDouble(POSITION_PRICE_OPEN);}else{legfail++;Close(8);return;}
   floorR=-1e100;highR=0;lastm15=iTime(InpSymbolA,PERIOD_M15,0);initialRR=MathAbs(mu0-feat[7])*notional/budget;
}

void Manage(bool has_feature)
{
   if(!active)return;if(closing){Close(reason);return;}
   ulong ta=0,tb=0;
   bool hasa=Owned(InpSymbolA,ta);double swapa=hasa?PositionGetDouble(POSITION_SWAP):0;double pa=hasa?PositionGetDouble(POSITION_PROFIT)+swapa:0;
   bool hasb=Owned(InpSymbolB,tb);double swapb=hasb?PositionGetDouble(POSITION_SWAP):0;double pb=hasb?PositionGetDouble(POSITION_PROFIT)+swapb:0;
   if(!hasa||!hasb){Close(1);return;}
   MqlTick a,b;if(!Quotes(a,b))return;
   // Forecast exit commission from actual entry commission; final ledger is exact.
   double fees=EntryFees(),pnl=pa+pb+2*fees,r=pnl/budget;
   datetime m15=iTime(InpSymbolA,PERIOD_M15,0);
   if(InpManagement==3&&m15!=lastm15&&iTime(InpSymbolB,PERIOD_M15,0)==m15)
   {
      lastm15=m15;MqlRates ca[],cb[];
      if(CopyRates(InpSymbolA,PERIOD_M5,m15-300,m15-1,ca)==1&&CopyRates(InpSymbolB,PERIOD_M5,m15-300,m15-1,cb)==1&&m15-900>=entrytime)
      {
         double xa=ca[0].close+(side<0?ca[0].spread*Point(InpSymbolA):0),xb=cb[0].close+(side>0?cb[0].spread*Point(InpSymbolB):0);
         double pl=side*lotsa*Contract(InpSymbolA)*(xa-entrya)-side*lotsb*Contract(InpSymbolB)*(xb-entryb)+swapa+swapb+2*fees;
         if(pl/budget>=.5)floorR=MathMax(floorR,.2);
      }
   }
   if(r<=MathMax(-1.,floorR)){Close(2);return;}
   if(InpExitMode<7&&r>=InpRR){Close(3);return;}
   double spread=MathLog(a.bid)-beta0*MathLog(b.bid);
   if(InpExitMode==7&&side*(spread-mu0)>=0){Close(4);return;}
   if(InpExitMode==8&&has_feature&&side*(spread-(feat[2]+(feat[1]-beta0)*feat[8]))>=0){Close(5);return;}
   if(TimeCurrent()-entrytime>=InpHoldHours*3600){Close(6);return;}
   highR=MathMax(highR,r);
   if(InpManagement==1&&r>=.5)floorR=MathMax(floorR,0);
   if(InpManagement==2&&r>=1)floorR=MathMax(floorR,0);
   if(InpManagement==4&&r>=1)floorR=MathMax(floorR,highR-.5);
   if(InpManagement==5&&r>=1)floorR=MathMax(floorR,highR-1);
   if(InpManagement==6&&r>=1&&has_feature)floorR=MathMax(floorR,r-MathMax(.25,lotsa*Contract(InpSymbolA)*a.bid*feat[4]*2.5/budget));
}

int OnInit()
{
   // Prevent research binaries from ever trading an attached real/demo chart.
   if(!(bool)MQLInfoInteger(MQL_TESTER)){Print("Research only: use Strategy Tester, not a trading chart.");return INIT_FAILED;}
   if(InpSymbolA==InpSymbolB||InpWindow<16||InpWindow>512||InpRiskPercent!=1.||InpTimeframeMinutes<5||InpTimeframeMinutes%5!=0||InpRR<.5||InpHoldHours<1)return INIT_PARAMETERS_INCORRECT;
   if(!SymbolSelect(InpSymbolA,true)||!SymbolSelect(InpSymbolB,true))return INIT_FAILED;
   if(SymbolInfoString(InpSymbolA,SYMBOL_CURRENCY_PROFIT)!="USD"||SymbolInfoString(InpSymbolB,SYMBOL_CURRENCY_PROFIT)!="USD")return INIT_FAILED;
   trade.SetExpertMagicNumber((ulong)InpMagic);trade.SetDeviationInPoints(80);
   FolderCreate("CalyxPairs",FILE_COMMON);
   logfile=FileOpen("CalyxPairs\\"+InpCase+"-baskets.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   featurefile=FileOpen("CalyxPairs\\"+InpCase+"-features.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   if(logfile==INVALID_HANDLE||featurefile==INVALID_HANDLE)return INIT_FAILED;
   FileWrite(logfile,"basket","entry_time","exit_time","side","entry_a","entry_b","exit_a","exit_b","lots_a","lots_b","net","return_fraction","R","reason","swap","fees","entry_adaptive_RR","risk_usd","entry_fills","exit_fills");
   FileWrite(featurefile,"time","z","beta","mean","sd","atr","low","high","signal_spread","mean_log_b");
   Print("CALYX PAIRS TEST ONLY ",InpCase," combined planned risk 1%; two separate market executions; not atomic.");
   return INIT_SUCCEEDED;
}
void OnTick()
{
   datetime bar=iTime(InpSymbolA,PERIOD_M5,0);bool fresh=false;
   if(bar>lastbar&&iTime(InpSymbolB,PERIOD_M5,0)==bar)
   {
      MqlTick a,b;if(Quotes(a,b)){lastbar=bar;fresh=Features(bar);}
   }
   Manage(fresh);
   if(fresh&&!active&&TimeCurrent()-lastclosed>=600)Enter(bar);
}
double OnTester(){if(active)Close(7);Print("PAIR AUDIT baskets=",basket," rejects=",rejects," leg failures=",legfail);return AccountInfoDouble(ACCOUNT_BALANCE);}
void OnDeinit(const int reason_code){if(logfile!=INVALID_HANDLE)FileClose(logfile);if(featurefile!=INVALID_HANDLE)FileClose(featurefile);}

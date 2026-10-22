#property strict
#property version "1.00"
#property description "Research only (2026-10-21). Pairs trading: z-score of ln(A) - beta*ln(B) on D1 closes; fade at 2 sigma, exit at 0, stop at 3.5 sigma."
#property description "Chart symbol = leg A, InpSymbolB = leg B. Momentum / random-direction controls. Rules: RULES.md."
#include <Trade/Trade.mqh>

input string InpSymbolB="BTCUSD";
input int    InpLookback=60;
input double InpEntryZ=2.0;
input double InpExitZ=0.0;
input double InpStopZ=3.5;          // 0 = no stop
input double InpSizingDz=1.5;       // sizing distance in sigma (entry -> stop)
input double InpRiskPct=1.0;
input double InpMaxLegLeverage=3.0;
input int    InpHedge=0;            // 0 = beta 1 (dollar neutral); 1 = rolling OLS beta
input int    InpDirection=0;        // 0 fade (main); 1 momentum; 2 random
input int    InpSeed=1;
input int    InpMaximumDeviationPoints=100000;
input long   InpMagic=2110280;

CTrade trade;
string A,Bs;
datetime lastDay=0,openTime=0;
int pos=0,side=0,blockedSide=0;   // pos: +1 long A / short B, -1 short A / long B; side: sign of z at entry
ulong tA=0,tB=0;
double entryZ=0;
long days=0,entries=0,exitsGap=0,exitsStop=0,legFails=0,skippedSize=0,skippedBlocked=0;

bool Fresh(string s,MqlTick &q){if(!SymbolInfoTick(s,q)||q.bid<=0||q.ask<=0)return false;return TimeCurrent()-q.time<=60;}
bool InSession(string s){datetime now=TimeCurrent(),from=0,to=0;MqlDateTime d;TimeToStruct(now,d);long sec=(long)(now%86400);
   for(uint i=0;SymbolInfoSessionTrade(s,(ENUM_DAY_OF_WEEK)d.day_of_week,i,from,to);i++)if(sec>=(long)from&&sec<(long)to)return true;return false;}
double RoundLots(string s,double x){double st=SymbolInfoDouble(s,SYMBOL_VOLUME_STEP),mn=SymbolInfoDouble(s,SYMBOL_VOLUME_MIN),mx=SymbolInfoDouble(s,SYMBOL_VOLUME_MAX);
   double v=NormalizeDouble(MathRound(x/st)*st,8);if(v<mn-1e-9)return 0;return MathMin(v,mx);}

bool Spread(double &z,double &beta,double &sd){
   int n=InpLookback;double la[],lb[];ArrayResize(la,n);ArrayResize(lb,n);
   for(int i=1;i<=n;i++){datetime t=iTime(A,PERIOD_D1,i);if(t==0)return false;double ca=iClose(A,PERIOD_D1,i);
      int j=iBarShift(Bs,PERIOD_D1,t,true);if(j<0)return false;double cb=iClose(Bs,PERIOD_D1,j);if(ca<=0||cb<=0)return false;
      la[i-1]=MathLog(ca);lb[i-1]=MathLog(cb);}
   beta=1.0;
   if(InpHedge==1){double ma=0,mb=0;for(int i=0;i<n;i++){ma+=la[i];mb+=lb[i];}ma/=n;mb/=n;double cov=0,var=0;
      for(int i=0;i<n;i++){cov+=(la[i]-ma)*(lb[i]-mb);var+=(lb[i]-mb)*(lb[i]-mb);}if(var<=0)return false;beta=cov/var;if(beta<=0)return false;}
   double s[];ArrayResize(s,n);double m=0;for(int i=0;i<n;i++){s[i]=la[i]-beta*lb[i];m+=s[i];}m/=n;
   double v=0;for(int i=0;i<n;i++)v+=(s[i]-m)*(s[i]-m);sd=MathSqrt(v/(n-1));if(sd<=0)return false;
   z=(s[0]-m)/sd;return true;
}

double PairNet(ulong posA,ulong posB){
   double net=0;ulong ids[2];ids[0]=posA;ids[1]=posB;
   for(int k=0;k<2;k++){if(ids[k]==0||!HistorySelectByPosition(ids[k]))continue;
      for(int i=0;i<HistoryDealsTotal();i++){ulong d=HistoryDealGetTicket(i);
         net+=HistoryDealGetDouble(d,DEAL_PROFIT)+HistoryDealGetDouble(d,DEAL_SWAP)+HistoryDealGetDouble(d,DEAL_COMMISSION)+HistoryDealGetDouble(d,DEAL_FEE);}}
   return net;
}

void ClosePair(string reason,double z){
   ulong pa=tA,pb=tB;
   if(pa&&PositionSelectByTicket(pa)&&!trade.PositionClose(pa))legFails++;
   if(pb&&PositionSelectByTicket(pb)&&!trade.PositionClose(pb))legFails++;
   double net=PairNet(pa,pb);
   PrintFormat("PAIR_TRADE open=%I64d close=%I64d pos=%d side=%d entry_z=%.3f exit_z=%.3f reason=%s net=%.2f",(long)openTime,(long)TimeCurrent(),pos,side,entryZ,z,reason,net);
   pos=0;tA=tB=0;
}

bool OpenPair(int p,double beta,double sd,const MqlTick &qa,const MqlTick &qb){
   double eq=AccountInfoDouble(ACCOUNT_EQUITY),dz=InpStopZ>0?InpStopZ-InpEntryZ:InpSizingDz;if(InpStopZ>0)dz=MathMax(dz,0.1);else dz=InpSizingDz;
   double notA=MathMin(InpMaxLegLeverage*eq,InpRiskPct/100.0*eq/(dz*sd)),notB=MathMin(InpMaxLegLeverage*eq,beta*notA);
   double pa=p>0?qa.ask:qa.bid,pb=p>0?qb.bid:qb.ask;
   double la=RoundLots(A,notA/(pa*SymbolInfoDouble(A,SYMBOL_TRADE_CONTRACT_SIZE))),lb=RoundLots(Bs,notB/(pb*SymbolInfoDouble(Bs,SYMBOL_TRADE_CONTRACT_SIZE)));
   if(la<=0||lb<=0){skippedSize++;return false;}
   trade.SetExpertMagicNumber(InpMagic);
   bool okA=p>0?trade.Buy(la,A,0,0,0,"PAIR A"):trade.Sell(la,A,0,0,0,"PAIR A");
   if(!okA||trade.ResultRetcode()!=TRADE_RETCODE_DONE){legFails++;return false;}
   ulong da=trade.ResultDeal();HistoryDealSelect(da);tA=(ulong)HistoryDealGetInteger(da,DEAL_POSITION_ID);
   bool okB=p>0?trade.Sell(lb,Bs,0,0,0,"PAIR B"):trade.Buy(lb,Bs,0,0,0,"PAIR B");
   if(!okB||trade.ResultRetcode()!=TRADE_RETCODE_DONE){legFails++;if(PositionSelectByTicket(tA))trade.PositionClose(tA);tA=0;return false;}
   ulong db=trade.ResultDeal();HistoryDealSelect(db);tB=(ulong)HistoryDealGetInteger(db,DEAL_POSITION_ID);
   return true;
}

int OnInit(){
   A=_Symbol;Bs=InpSymbolB;
   if(Bs==A||!SymbolSelect(Bs,true)||InpLookback<10||InpEntryZ<=0||InpExitZ<0||InpExitZ>=InpEntryZ||(InpStopZ>0&&InpStopZ<=InpEntryZ)||InpDirection<0||InpDirection>2)return INIT_PARAMETERS_INCORRECT;
   if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING){Print("Hedging account required.");return INIT_FAILED;}
   trade.SetDeviationInPoints(InpMaximumDeviationPoints);MathSrand(InpSeed);
   PrintFormat("PAIR_SPEC A=%s B=%s contractA=%.2f contractB=%.2f stepA=%.2f stepB=%.2f lookback=%d entry=%.2f exit=%.2f stop=%.2f hedge=%d direction=%d seed=%d",
      A,Bs,SymbolInfoDouble(A,SYMBOL_TRADE_CONTRACT_SIZE),SymbolInfoDouble(Bs,SYMBOL_TRADE_CONTRACT_SIZE),SymbolInfoDouble(A,SYMBOL_VOLUME_STEP),SymbolInfoDouble(Bs,SYMBOL_VOLUME_STEP),
      InpLookback,InpEntryZ,InpExitZ,InpStopZ,InpHedge,InpDirection,InpSeed);
   return INIT_SUCCEEDED;
}

void OnTick(){
   datetime d0=iTime(A,PERIOD_D1,0);if(d0==0||d0==lastDay)return;
   MqlTick qa,qb;if(!Fresh(A,qa)||!Fresh(Bs,qb)||!InSession(A)||!InSession(Bs))return;
   MqlDateTime ta,tb;TimeToStruct(qa.time,ta);TimeToStruct(qb.time,tb);if(ta.day!=tb.day)return;
   double z,beta,sd;if(!Spread(z,beta,sd))return;
   lastDay=d0;days++;
   if(pos!=0){
      if(side*z<=InpExitZ){exitsGap++;ClosePair("gap_closed",z);}
      else if(InpStopZ>0&&side*z>=InpStopZ){exitsStop++;blockedSide=side;ClosePair("stop",z);}
   }
   if(pos==0){
      if(blockedSide!=0&&blockedSide*z<InpEntryZ)blockedSide=0;
      int sgn=z>=InpEntryZ?1:(z<=-InpEntryZ?-1:0);
      if(sgn!=0&&(InpStopZ<=0||sgn*z<InpStopZ)){
         if(sgn==blockedSide)skippedBlocked++;
         else{
            int p=InpDirection==0?-sgn:(InpDirection==1?sgn:(MathRand()%2==0?1:-1));
            if(OpenPair(p,beta,sd,qa,qb)){pos=p;side=sgn;entryZ=z;openTime=TimeCurrent();entries++;}
         }
      }
   }
   PrintFormat("PAIR_DAY epoch=%I64d equity=%.2f z=%.3f beta=%.3f sd=%.5f pos=%d",(long)d0,AccountInfoDouble(ACCOUNT_EQUITY),z,beta,sd,pos);
}

void OnDeinit(const int reason){
   PrintFormat("PAIR_SUMMARY days=%I64d entries=%I64d exits_gap=%I64d exits_stop=%I64d leg_fails=%I64d skipped_size=%I64d skipped_blocked=%I64d",days,entries,exitsGap,exitsStop,legFails,skippedSize,skippedBlocked);
}

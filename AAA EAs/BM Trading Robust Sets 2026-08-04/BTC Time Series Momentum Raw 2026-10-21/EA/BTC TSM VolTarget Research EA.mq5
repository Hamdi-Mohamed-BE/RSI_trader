#property strict
#property version "1.00"
#property description "Research only (2026-10-21). BTCUSD time-series momentum (sign of the 30-day return) with volatility targeting"
#property description "(size = target vol / realised vol, capped), daily signal, weekly rebalance. Benchmarks and controls via InpMode. Rules: RULES.md."
#include <Trade/Trade.mqh>

input int    InpMode=0;               // 0 long/flat; 1 long/short; 2 buy & hold 1x; 3 always long vol-targeted; 4 random long/flat
input int    InpLookbackDays=30;
input int    InpVolDays=30;
input double InpTargetVol=20.0;       // % annualised
input double InpMaxLeverage=1.0;      // notional cap, multiple of equity
input bool   InpVolTarget=true;       // false = fixed InpMaxLeverage notional while in the market
input bool   InpDailyRebalance=false; // true = resize every day instead of Mondays
input bool   InpWeeklySignal=false;   // true = signal only checked on Mondays
input double InpRebalanceBand=0.05;   // resize only if the target differs by at least this fraction
input double InpFlipProb=0.05;        // mode 4: daily probability of switching long/flat
input int    InpSeed=1;
input int    InpMaximumDeviationPoints=100000;
input long   InpMagic=2110270;

CTrade trade;
datetime lastDay=0;
int dir=0,rndState=0;
bool bhDone=false;
long days=0,flips=0,opens=0,partials=0,rebalances=0,fails=0;

double Step(){return SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);}
double RoundLots(double x){double st=Step(),mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double v=NormalizeDouble(MathRound(x/st)*st,8);if(v<mn-1e-9)return 0;return MathMin(v,mx);}
double SignedVolume(){double s=0;for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);
   if(!t||PositionGetString(POSITION_SYMBOL)!=_Symbol||PositionGetInteger(POSITION_MAGIC)!=InpMagic)continue;
   s+=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1)*PositionGetDouble(POSITION_VOLUME);}return s;}
double TargetLots(int d,double frac){MqlTick q;if(!SymbolInfoTick(_Symbol,q))return 0;double price=d>0?q.ask:q.bid,cs=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);
   if(price<=0||cs<=0)return 0;return RoundLots(frac*AccountInfoDouble(ACCOUNT_EQUITY)/(price*cs));}

bool OpenVol(bool buy,double vol,string cm){
   if(vol<=0)return false;trade.SetExpertMagicNumber(InpMagic);
   bool ok=buy?trade.Buy(vol,_Symbol,0,0,0,cm):trade.Sell(vol,_Symbol,0,0,0,cm);
   if(!ok||trade.ResultRetcode()!=TRADE_RETCODE_DONE){fails++;PrintFormat("TSM_FAIL open code=%u vol=%.2f",trade.ResultRetcode(),vol);return false;}
   opens++;return true;
}
void CloseAll(){
   for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);
      if(!t||PositionGetString(POSITION_SYMBOL)!=_Symbol||PositionGetInteger(POSITION_MAGIC)!=InpMagic)continue;
      if(!trade.PositionClose(t)||trade.ResultRetcode()!=TRADE_RETCODE_DONE){fails++;PrintFormat("TSM_FAIL close code=%u",trade.ResultRetcode());}}
}
void Reduce(double vol){
   double left=vol;
   for(int i=PositionsTotal()-1;i>=0&&left>1e-9;i--){ulong t=PositionGetTicket(i);
      if(!t||PositionGetString(POSITION_SYMBOL)!=_Symbol||PositionGetInteger(POSITION_MAGIC)!=InpMagic)continue;
      double pv=PositionGetDouble(POSITION_VOLUME),v=MathMin(pv,left);bool ok;
      if(v>=pv-1e-9)ok=trade.PositionClose(t);else ok=trade.PositionClosePartial(t,NormalizeDouble(v,8));
      if(!ok||trade.ResultRetcode()!=TRADE_RETCODE_DONE){fails++;PrintFormat("TSM_FAIL reduce code=%u",trade.ResultRetcode());return;}
      partials++;left-=v;}
}

int OnInit(){
   if(InpMode<0||InpMode>4||InpLookbackDays<2||InpVolDays<5||InpTargetVol<=0||InpMaxLeverage<=0||InpRebalanceBand<0)return INIT_PARAMETERS_INCORRECT;
   if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING){Print("Hedging account required.");return INIT_FAILED;}
   trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(InpMaximumDeviationPoints);MathSrand(InpSeed);
   PrintFormat("TSM_SPEC symbol=%s digits=%d contract=%.4f vol_min=%.2f step=%.2f mode=%d lookback=%d voldays=%d target=%.1f cap=%.2f voltarget=%d daily_rebal=%d weekly_signal=%d band=%.2f p=%.5f seed=%d",
      _Symbol,_Digits,SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),Step(),InpMode,InpLookbackDays,InpVolDays,InpTargetVol,InpMaxLeverage,
      InpVolTarget,InpDailyRebalance,InpWeeklySignal,InpRebalanceBand,InpFlipProb,InpSeed);
   return INIT_SUCCEEDED;
}

void OnTick(){
   datetime d0=iTime(_Symbol,PERIOD_D1,0);if(d0==0||d0==lastDay)return;
   int need=MathMax(InpLookbackDays,InpVolDays)+1;
   double c[];ArraySetAsSeries(c,true);if(CopyClose(_Symbol,PERIOD_D1,1,need,c)!=need)return;
   lastDay=d0;days++;
   double ret=c[0]/c[InpLookbackDays]-1.0,s=0,s2=0;int n=InpVolDays;
   for(int i=0;i<n;i++){double r=MathLog(c[i]/c[i+1]);s+=r;s2+=r*r;}
   double mean=s/n,var=(s2-n*mean*mean)/(n-1),vol=MathSqrt(MathMax(var,1e-12)*365.0);
   MqlDateTime t;TimeToStruct(d0,t);bool monday=t.day_of_week==1;
   double frac=InpVolTarget?MathMin(InpMaxLeverage,InpTargetVol/100.0/vol):InpMaxLeverage;
   if(InpMode==2){
      if(!bhDone){double lots=TargetLots(1,1.0);if(OpenVol(true,lots,"TSM BH")){bhDone=true;dir=1;}}
      PrintFormat("TSM_DAY epoch=%I64d equity=%.2f balance=%.2f ret=%.5f vol=%.4f want=1 dir=%d frac=1.0000 lots=%.2f",(long)d0,AccountInfoDouble(ACCOUNT_EQUITY),AccountInfoDouble(ACCOUNT_BALANCE),ret,vol,dir,SignedVolume());
      return;
   }
   int want;
   if(InpMode==3)want=1;
   else if(InpMode==4){if(days==1)rndState=MathRand()%2;else if(MathRand()/32768.0<InpFlipProb)rndState=1-rndState;want=rndState;}
   else want=ret>0?1:((InpMode==1&&ret<0)?-1:0);
   if(InpWeeklySignal&&!monday)want=dir;
   if(want!=dir){
      CloseAll();int was=dir;dir=0;
      if(want!=0){double lots=TargetLots(want,frac);if(OpenVol(want>0,lots,want>0?"TSM LONG":"TSM SHORT"))dir=want;}
      flips++;PrintFormat("TSM_FLIP epoch=%I64d from=%d to=%d ret=%.5f vol=%.4f frac=%.4f",(long)d0,was,dir,ret,vol,frac);
   }
   else if(dir!=0&&(monday||InpDailyRebalance)){
      double target=TargetLots(dir,frac),cur=MathAbs(SignedVolume()),diff=target-cur;
      if(target>0&&MathAbs(diff)>=InpRebalanceBand*target&&MathAbs(diff)>=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN)-1e-9){
         if(diff>0)OpenVol(dir>0,RoundLots(diff),"TSM ADD");else Reduce(RoundLots(-diff));
         rebalances++;
      }
   }
   PrintFormat("TSM_DAY epoch=%I64d equity=%.2f balance=%.2f ret=%.5f vol=%.4f want=%d dir=%d frac=%.4f lots=%.2f",(long)d0,AccountInfoDouble(ACCOUNT_EQUITY),AccountInfoDouble(ACCOUNT_BALANCE),ret,vol,want,dir,frac,SignedVolume());
}

void OnDeinit(const int reason){
   PrintFormat("TSM_SUMMARY days=%I64d flips=%I64d opens=%I64d partials=%I64d rebalances=%I64d fails=%I64d",days,flips,opens,partials,rebalances,fails);
}

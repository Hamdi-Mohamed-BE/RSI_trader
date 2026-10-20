#property strict
#property version "1.00"
#property description "Research only (2026-10-18). Friday volume profile (128 rows, 80% VA) -> weekend buy limit at VAL, sell limit at VAH,"
#property description "target the opposite edge, stop = VA width / RR beyond entry. Rules: RULES.md."
#include <Trade/Trade.mqh>

input double   InpRiskPercent=1.0;           // % of equity per order; lots rounded UP to the step (minimum lot if needed)
input int      InpRows=128;                  // volume-profile rows (TradingView "Number of rows")
input double   InpValueAreaPct=80.0;         // value area volume %
input double   InpRewardRisk=3.0;            // TP = opposite VA edge; SL distance = VA width / RR
input int      InpLevelMode=0;               // 0 = volume value area; 1 = control: Friday price range 10%/90%
input int      InpExitMode=0;                // 0 = cancel orders + close positions at Monday 00:00 UTC; 1 = hold until TP/SL
input bool     InpEnableBuy=true;
input bool     InpEnableSell=true;
input int      InpServerUtcOffsetHours=0;    // Exness server = UTC
input int      InpMaximumDeviationPoints=1000;
input long     InpMagic=1810261;

CTrade trade;
datetime weekKey=0;           // Saturday 00:00 UTC of the active weekend
bool     levelsReady=false, weekendOpen=false;
double   vah=0, val=0, poc=0;
bool     placed[2];           // 0 buy, 1 sell
int      placeFails=0, closeFails=0, cancelFails=0, skippedRisk=0, weekends=0, noLevels=0;
datetime lastClose=0;

long Off(){return (long)InpServerUtcOffsetHours*3600;}
double Price(double p){double t=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);return NormalizeDouble(MathRound(p/t)*t,_Digits);}

bool ComputeLevels(datetime fromServer,datetime toServer){
   MqlRates r[];
   int n=CopyRates(_Symbol,PERIOD_M1,fromServer,toServer-60,r);
   if(n<60){PrintFormat("WVA_NOLEVELS bars=%d from=%s",n,TimeToString(fromServer));return false;}
   double hi=-DBL_MAX,lo=DBL_MAX;
   for(int i=0;i<n;i++){hi=MathMax(hi,r[i].high);lo=MathMin(lo,r[i].low);}
   if(hi<=lo)return false;
   if(InpLevelMode==1){val=lo+0.10*(hi-lo);vah=lo+0.90*(hi-lo);poc=(hi+lo)/2;return true;}
   int R=MathMax(2,InpRows);double h=(hi-lo)/R;
   double vol[];ArrayResize(vol,R);ArrayInitialize(vol,0.0);
   for(int i=0;i<n;i++){
      double v=(double)r[i].tick_volume;if(v<=0)continue;
      double bl=r[i].low,bh=r[i].high;
      int k0=(int)MathFloor((bl-lo)/h),k1=(int)MathFloor((bh-lo)/h);
      k0=MathMax(0,MathMin(R-1,k0));k1=MathMax(0,MathMin(R-1,k1));
      if(bh-bl<=0){vol[k0]+=v;continue;}
      for(int k=k0;k<=k1;k++){
         double a=MathMax(bl,lo+k*h),b=MathMin(bh,lo+(k+1)*h);
         if(b>a)vol[k]+=v*(b-a)/(bh-bl);
      }
   }
   double total=0;int pk=0;
   for(int k=0;k<R;k++){total+=vol[k];if(vol[k]>vol[pk])pk=k;}
   if(total<=0)return false;
   double target=total*InpValueAreaPct/100.0,acc=vol[pk];int up=pk,dn=pk;
   while(acc<target&&(up<R-1||dn>0)){
      double above=up<R-1?vol[up+1]:-1.0,below=dn>0?vol[dn-1]:-1.0;
      if(above>=below){up++;acc+=vol[up];}else{dn--;acc+=vol[dn];}
   }
   vah=lo+(up+1)*h;val=lo+dn*h;poc=lo+(pk+0.5)*h;
   return vah>val;
}

bool OwnPosition(int side){
   for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);
      if(t&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==InpMagic&&
         (side<0||(side==0&&PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY)||(side==1&&PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_SELL)))return true;}
   return false;
}

void CancelOwnOrders(){
   for(int i=OrdersTotal()-1;i>=0;i--){ulong t=OrderGetTicket(i);
      if(t&&OrderGetString(ORDER_SYMBOL)==_Symbol&&OrderGetInteger(ORDER_MAGIC)==InpMagic){if(!trade.OrderDelete(t))cancelFails++;}}
}

void CloseOwnPositions(){
   datetime now=TimeCurrent();if(now-lastClose<30)return;lastClose=now;
   for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);
      if(t&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==InpMagic){
         if(!trade.PositionClose(t)||trade.ResultRetcode()!=TRADE_RETCODE_DONE){
            if(trade.ResultRetcode()!=TRADE_RETCODE_POSITION_CLOSED){closeFails++;PrintFormat("WVA_CLOSE_FAIL code=%u",trade.ResultRetcode());}}}}
}

void TryPlace(int side){
   if(placed[side])return;
   if((side==0&&!InpEnableBuy)||(side==1&&!InpEnableSell))return;
   if(InpExitMode==1&&OwnPosition(side))return;          // still holding last weekend's position on this side
   MqlTick q;if(!SymbolInfoTick(_Symbol,q)||q.bid<=0||q.ask<=0)return;
   double width=vah-val,dist=width/InpRewardRisk;
   double gap=MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*_Point;
   double entry=Price(side==0?val:vah),sl=Price(side==0?val-dist:vah+dist),tp=Price(side==0?vah:val);
   // A limit is only valid on the correct side of the market; otherwise wait for price to come back.
   if(side==0&&q.ask-entry<=gap)return;
   if(side==1&&entry-q.bid<=gap)return;
   if(dist<=gap)return;
   ENUM_ORDER_TYPE type=side==0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;double unit=0,margin=0;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,sl,unit)||unit>=0){skippedRisk++;placed[side]=true;return;}
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double goal=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   double volume=NormalizeDouble(MathMax(mn,MathCeil((goal/-unit-1e-10)/step)*step),8);
   if(volume>mx||!OrderCalcMargin(type,_Symbol,volume,entry,margin)||margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)){skippedRisk++;placed[side]=true;return;}
   string cm=(InpLevelMode==1?"WVA ctl ":"WVA ")+(side==0?"buy VAL":"sell VAH");
   bool ok=side==0?trade.BuyLimit(volume,entry,_Symbol,sl,tp,ORDER_TIME_GTC,0,cm):trade.SellLimit(volume,entry,_Symbol,sl,tp,ORDER_TIME_GTC,0,cm);
   if(!ok||(trade.ResultRetcode()!=TRADE_RETCODE_DONE&&trade.ResultRetcode()!=TRADE_RETCODE_PLACED)){placeFails++;PrintFormat("WVA_PLACE_FAIL side=%d code=%u",side,trade.ResultRetcode());return;}
   placed[side]=true;
   PrintFormat("WVA_ORDER %s entry=%.2f sl=%.2f tp=%.2f lots=%.2f risk=%.2f",side==0?"BUY_LIMIT":"SELL_LIMIT",entry,sl,tp,volume,goal);
}

int OnInit(){
   if(InpRiskPercent<=0||InpRiskPercent>5||InpRows<2||InpValueAreaPct<=0||InpValueAreaPct>=100||InpRewardRisk<=0)return INIT_PARAMETERS_INCORRECT;
   if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING){Print("Hedging account required (both sides may fill).");return INIT_FAILED;}
   trade.SetExpertMagicNumber(InpMagic);trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   placed[0]=placed[1]=false;
   PrintFormat("WVA_SPEC symbol=%s rows=%d va=%.1f rr=%.2f level_mode=%d exit_mode=%d utc_off=%d",_Symbol,InpRows,InpValueAreaPct,InpRewardRisk,InpLevelMode,InpExitMode,InpServerUtcOffsetHours);
   return INIT_SUCCEEDED;
}

void OnTick(){
   datetime now=TimeCurrent();datetime utc=now-(datetime)Off();
   MqlDateTime d;TimeToStruct(utc,d);
   bool weekend=d.day_of_week==6||d.day_of_week==0;
   if(weekend){
      datetime sat=utc-utc%86400-(d.day_of_week==0?86400:0);
      if(sat!=weekKey){
         weekKey=sat;weekendOpen=true;placed[0]=placed[1]=false;weekends++;
         datetime friFrom=sat-86400+(datetime)Off(),friTo=sat+(datetime)Off();
         levelsReady=ComputeLevels(friFrom,friTo);
         if(!levelsReady)noLevels++;
         else PrintFormat("WVA_LEVELS weekend=%s VAH=%.2f VAL=%.2f POC=%.2f width=%.2f stop=%.2f",TimeToString(sat,TIME_DATE),vah,val,poc,vah-val,(vah-val)/InpRewardRisk);
      }
      if(levelsReady){TryPlace(0);TryPlace(1);}
      return;
   }
   if(weekendOpen){                         // first tick after Monday 00:00 UTC
      CancelOwnOrders();
      if(InpExitMode==0)CloseOwnPositions();
      if(InpExitMode==1||!OwnPosition(-1))weekendOpen=false;   // keep retrying the close until flat
      levelsReady=false;
   }
}

void OnDeinit(const int reason){
   PrintFormat("WVA_SUMMARY weekends=%d no_levels=%d place_fails=%d close_fails=%d cancel_fails=%d skipped_risk=%d",weekends,noLevels,placeFails,closeFails,cancelFails,skippedRisk);
}

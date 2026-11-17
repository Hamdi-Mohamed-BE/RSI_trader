#property strict
#property version "1.00"
#property description "Research only (2026-11-12). Gold EMA Ribbon (pasted clip): H1, five EMAs aligned fastest->slowest, close on the right side of EMA200,"
#property description "stop 1.5 x ATR14, no target, exit on an H1 close beyond the slowest ribbon EMA. RULES.md. Controls: random direction / random entry."
#include <Trade/Trade.mqh>

input int    InpE1=8;
input int    InpE2=13;
input int    InpE3=21;
input int    InpE4=34;
input int    InpE5=55;
input int    InpTrendEMA=200;
input int    InpATRPeriod=14;
input double InpStopATR=1.5;
input int    InpEntryMode=0;            // 0 CROSS (alignment becomes true), 1 STATE (aligned while flat, close back beyond the slowest EMA)
input int    InpDirection=2;            // 2 both, 0 long only, 1 short only
input double InpRiskPercent=0.75;       // % of balance, lots rounded DOWN
input int    InpControl=0;              // 0 none, 1 random direction, 2 random entry (rate InpRandomRate per bar, direction = side of EMA200)
input double InpRandomRate=0.02;
input int    InpSeed=1;
input int    InpDeviationPoints=50;
input long   InpMagic=2911201;

CTrade g_trade; int hE[5],hT=INVALID_HANDLE,hA=INVALID_HANDLE; datetime g_last=0; long g_entries=0,g_exits=0,g_skipped=0;

double Val(int h,int sh){double b[1];if(CopyBuffer(h,0,sh,1,b)!=1)return EMPTY_VALUE;return b[0];}
bool HasPos(ulong &t,int &dir){
   for(int i=PositionsTotal()-1;i>=0;i--){ulong k=PositionGetTicket(i);if(k&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==InpMagic){t=k;dir=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1);return true;}}
   return false;
}
// +1 bullish order, -1 bearish order, 0 none (bar shift sh)
int Ribbon(int sh){
   double v[5];for(int i=0;i<5;i++){v[i]=Val(hE[i],sh);if(v[i]==EMPTY_VALUE)return 0;}
   bool up=v[0]>v[1]&&v[1]>v[2]&&v[2]>v[3]&&v[3]>v[4], dn=v[0]<v[1]&&v[1]<v[2]&&v[2]<v[3]&&v[3]<v[4];
   return up?1:(dn?-1:0);
}
double Lots(ENUM_ORDER_TYPE type,double e,double sl){
   double one=0;if(!OrderCalcProfit(type,_Symbol,1.0,e,sl,one)||MathAbs(one)<=0)return 0;
   double raw=AccountInfoDouble(ACCOUNT_BALANCE)*InpRiskPercent/100.0/MathAbs(one);
   double mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),st=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   double v=MathFloor(MathMin(raw,mx)/st+1e-9)*st; return (v<mn?0:v);
}
void Enter(int dir,double atr){
   MqlTick k;if(!SymbolInfoTick(_Symbol,k))return;
   int dg=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);double e=(dir>0?k.ask:k.bid),sl=NormalizeDouble(e-dir*InpStopATR*atr,dg);
   double v=Lots(dir>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,e,sl);if(v<=0){g_skipped++;return;}
   g_trade.SetExpertMagicNumber((ulong)InpMagic);g_trade.SetDeviationInPoints(InpDeviationPoints);g_trade.SetTypeFillingBySymbol(_Symbol);
   bool ok=(dir>0?g_trade.Buy(v,_Symbol,0,sl,0,"RIBBON"):g_trade.Sell(v,_Symbol,0,sl,0,"RIBBON"));
   if(ok){g_entries++;PrintFormat("RIB_ENTRY %s lots=%.2f stop=%.2f spread_pts=%d",dir>0?"buy":"sell",v,InpStopATR*atr,(int)SymbolInfoInteger(_Symbol,SYMBOL_SPREAD));}
}
int OnInit(){
   int p[5]={InpE1,InpE2,InpE3,InpE4,InpE5};
   for(int i=0;i<5;i++){hE[i]=iMA(_Symbol,PERIOD_H1,p[i],0,MODE_EMA,PRICE_CLOSE);if(hE[i]==INVALID_HANDLE)return INIT_FAILED;}
   hT=iMA(_Symbol,PERIOD_H1,InpTrendEMA,0,MODE_EMA,PRICE_CLOSE);hA=iATR(_Symbol,PERIOD_H1,InpATRPeriod);
   if(hT==INVALID_HANDLE||hA==INVALID_HANDLE||InpRiskPercent<=0)return INIT_FAILED;
   MathSrand(InpSeed);g_last=iTime(_Symbol,PERIOD_H1,0);
   PrintFormat("RIB_SPEC emas=%d/%d/%d/%d/%d trend=%d stop=%.2f mode=%d dir=%d control=%d rate=%.4f seed=%d",InpE1,InpE2,InpE3,InpE4,InpE5,InpTrendEMA,InpStopATR,InpEntryMode,InpDirection,InpControl,InpRandomRate,InpSeed);
   return INIT_SUCCEEDED;
}
void OnDeinit(const int r){PrintFormat("RIB_SUMMARY entries=%I64d exits=%I64d skipped=%I64d",g_entries,g_exits,g_skipped);}
void OnTick(){
   datetime b0=iTime(_Symbol,PERIOD_H1,0);if(b0<=0||b0==g_last)return;g_last=b0;
   double c=iClose(_Symbol,PERIOD_H1,1),slow=Val(hE[4],1),trend=Val(hT,1),atr=Val(hA,1);
   if(slow==EMPTY_VALUE||trend==EMPTY_VALUE||atr==EMPTY_VALUE||atr<=0)return;
   ulong t;int pd;
   if(HasPos(t,pd)){                                         // exit on a close beyond the slowest ribbon EMA
      if((pd>0&&c<slow)||(pd<0&&c>slow)){if(g_trade.PositionClose(t,InpDeviationPoints))g_exits++;}
      return;
   }
   int side=(c>trend?1:(c<trend?-1:0));
   if(InpControl==2){                                        // random entry control
      if(side!=0&&MathRand()/32767.0<InpRandomRate&&(InpDirection==2||(InpDirection==0&&side>0)||(InpDirection==1&&side<0)))Enter(side,atr);
      return;
   }
   int r1=Ribbon(1),r2=Ribbon(2);if(r1==0||r1!=side)return;
   if(InpEntryMode==0&&r2==r1)return;                        // CROSS: alignment must be new
   if(InpEntryMode==1&&((r1>0&&c<=slow)||(r1<0&&c>=slow)))return;
   if((InpDirection==0&&r1<0)||(InpDirection==1&&r1>0))return;
   int dir=r1;if(InpControl==1)dir=((MathRand()&1)==1?1:-1);
   Enter(dir,atr);
}

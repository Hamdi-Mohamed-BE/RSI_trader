#property strict
#property version "1.00"
#property description "Frozen raw H4 fair value gap swing reconstruction. Tester only."
#include <Trade/Trade.mqh>

input double InpRiskPercent=1.0;
input double InpRewardRisk=2.0;
input long InpMagic=91440001;
input int InpDeviationPoints=30;
input bool InpExportH4=true;

struct GapZone
{
 bool active;
 int direction;
 datetime created;
 datetime first_time;
 datetime third_time;
 double low;
 double high;
 double stop;
};

CTrade trade;
GapZone bull,bear;
datetime last_h4=0,first_tick=0,last_tick=0;
int audit_file=INVALID_HANDLE;
string prefix;

string Stamp(datetime t){return t>0?TimeToString(t,TIME_DATE|TIME_SECONDS):"";}
double TickSize(){double v=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);return v>0?v:_Point;}
double Price(double p){return NormalizeDouble(MathRound(p/TickSize())*TickSize(),_Digits);}
void Event(string name,const GapZone &z,double entry=0,double target=0,double volume=0,double risk=0,double equity=0,string detail="")
{
 if(audit_file<0)return;
 FileWrite(audit_file,Stamp(TimeCurrent()),name,z.direction,Stamp(z.created),Stamp(z.first_time),Stamp(z.third_time),z.low,z.high,entry,z.stop,target,volume,risk,equity,detail);
 FileFlush(audit_file);
}
double Lots(double raw)
{
 double minlot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),maxlot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
 if(raw<=0 || minlot<=0 || maxlot<minlot || step<=0)return 0;
 double v=MathMax(minlot,MathCeil(raw/step-1e-9)*step);
 return NormalizeDouble(MathMin(v,MathFloor(maxlot/step+1e-9)*step),8);
}
bool HasPosition()
{
 for(int i=PositionsTotal()-1;i>=0;i--)
 {
  ulong ticket=PositionGetTicket(i);
  if(ticket && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)return true;
 }
 return false;
}
bool SelfTest()
{
 MqlRates a,c;
 a.high=100;a.low=90;c.low=101;c.high=110;
 if(!(c.low>a.high))return false;
 a.low=100;a.high=110;c.high=99;c.low=90;
 if(!(c.high<a.low))return false;
 if(101>101 || 99<99)return false;
 return true;
}
void Detect()
{
 MqlRates r[];ArraySetAsSeries(r,true);
 if(CopyRates(_Symbol,PERIOD_H4,0,4,r)!=4)return;
 if(r[1].time+PeriodSeconds(PERIOD_H4)>TimeCurrent())return;
 MqlRates first=r[3],third=r[1];
 if(third.low>first.high)
 {
  GapZone z;z.active=true;z.direction=1;z.created=r[0].time;z.first_time=first.time;z.third_time=third.time;
  z.low=Price(first.high);z.high=Price(third.low);z.stop=Price(first.low-TickSize());
  if(z.stop<z.low && z.high>z.low){bull=z;Event("zone",bull);}
 }
 if(third.high<first.low)
 {
  GapZone z;z.active=true;z.direction=-1;z.created=r[0].time;z.first_time=first.time;z.third_time=third.time;
  z.low=Price(third.high);z.high=Price(first.low);z.stop=Price(first.high+TickSize());
  if(z.stop>z.high && z.high>z.low){bear=z;Event("zone",bear);}
 }
}
void TryZone(GapZone &z,const MqlTick &q)
{
 if(!z.active)return;
 double px=z.direction>0?q.ask:q.bid;
 if((z.direction>0 && px<z.low) || (z.direction<0 && px>z.high))
 {
  Event("invalidate",z,px,0,0,0,AccountInfoDouble(ACCOUNT_EQUITY),"far edge crossed");z.active=false;return;
 }
 if(px<z.low || px>z.high || HasPosition())return;
 double stop=z.stop,distance=z.direction>0?px-stop:stop-px;
 if(distance<=TickSize()){Event("rejected",z,px,0,0,0,AccountInfoDouble(ACCOUNT_EQUITY),"invalid stop distance");z.active=false;return;}
 double target=Price(px+z.direction*InpRewardRisk*distance);
 ENUM_ORDER_TYPE side=z.direction>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 double one_lot=0,equity=AccountInfoDouble(ACCOUNT_EQUITY);
 if(equity<=0 || !OrderCalcProfit(side,_Symbol,1.0,px,stop,one_lot) || one_lot>=0)
 {Event("error",z,px,target,0,0,equity,"risk calculation");z.active=false;return;}
 double requested=equity*InpRiskPercent/100.0,volume=Lots(requested/MathAbs(one_lot));
 if(volume<=0){Event("error",z,px,target,0,0,equity,"volume calculation");z.active=false;return;}
 double margin=0;
 if(!OrderCalcMargin(side,_Symbol,volume,px,margin) || margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE))
 {Event("rejected",z,px,target,volume,MathAbs(one_lot)*volume,equity,"insufficient margin");z.active=false;return;}
 trade.SetExpertMagicNumber((ulong)InpMagic);trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(InpDeviationPoints);
 bool sent=z.direction>0?trade.Buy(volume,_Symbol,0,stop,target,"H4FVG raw"):trade.Sell(volume,_Symbol,0,stop,target,"H4FVG raw");
 if(!sent || (trade.ResultRetcode()!=TRADE_RETCODE_DONE && trade.ResultRetcode()!=TRADE_RETCODE_DONE_PARTIAL))
 {Event("error",z,px,target,volume,MathAbs(one_lot)*volume,equity,trade.ResultRetcodeDescription());z.active=false;return;}
 ulong deal=trade.ResultDeal();double fill=px,actual=0,filled=volume;
 if(deal && HistoryDealSelect(deal)){fill=HistoryDealGetDouble(deal,DEAL_PRICE);filled=HistoryDealGetDouble(deal,DEAL_VOLUME);}
 if(!OrderCalcProfit(side,_Symbol,filled,fill,stop,actual))
 {Event("error",z,fill,target,filled,0,equity,"fill risk calculation");z.active=false;return;}
 Event("accepted",z,fill,target,filled,MathAbs(actual),equity,trade.ResultRetcodeDescription());z.active=false;
}
int OnInit()
{
 if(!MQLInfoInteger(MQL_TESTER)){Print("H4 FVG raw is tester-only.");return INIT_FAILED;}
 if(_Period!=PERIOD_H4 || InpRiskPercent<=0 || InpRewardRisk<=0 || !SelfTest())return INIT_PARAMETERS_INCORRECT;
 if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)return INIT_PARAMETERS_INCORRECT;
 prefix="H4FVGRaw-"+(string)InpMagic;
 audit_file=FileOpen(prefix+".csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');
 if(audit_file<0)return INIT_FAILED;
 FileWrite(audit_file,"server_time","event","direction","zone_created","first_time","third_time","zone_low","zone_high","entry","stop","target","volume","risk_cash","equity","detail");
 Print("H4 FVG RAW SELF TEST PASS contract=",SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE)," tick=",TickSize()," minlot=",SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN)," broker=",AccountInfoString(ACCOUNT_SERVER));
 return INIT_SUCCEEDED;
}
void OnTick()
{
 if(!first_tick)first_tick=TimeCurrent();last_tick=TimeCurrent();
 datetime h=iTime(_Symbol,PERIOD_H4,0);
 if(h && h!=last_h4){last_h4=h;Detect();}
 MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
 TryZone(bull,q);TryZone(bear,q);
}
double OnTester()
{
 if(InpExportH4)
 {
  MqlRates h[];int n=CopyRates(_Symbol,PERIOD_H4,(datetime)(first_tick-16*3600),last_tick,h);
  int f=FileOpen(prefix+"-PERIOD_H4.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');
  FileWrite(f,"time","open","high","low","close","tick_volume","spread","real_volume");
  for(int i=0;i<n;i++)FileWrite(f,Stamp(h[i].time),h[i].open,h[i].high,h[i].low,h[i].close,h[i].tick_volume,h[i].spread,h[i].real_volume);
  FileClose(f);
 }
 return TesterStatistics(STAT_PROFIT);
}
void OnDeinit(const int reason){if(audit_file>=0)FileClose(audit_file);}

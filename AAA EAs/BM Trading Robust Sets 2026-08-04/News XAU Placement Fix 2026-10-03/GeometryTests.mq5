#property strict
#include "NewsPulsePlacement.mqh"
int failures=0;
void Check(bool ok,string name) {if(!ok) {failures++;Print("GEOMETRY_FAIL|",name);}}
int OnInit()
{
   if(!(bool)MQLInfoInteger(MQL_TESTER)) return INIT_FAILED;
   double entry=0,sl=0,tp=0;bool market=false;
   Check(NP_PlanSide(true,4184.681,4185.621,4185.803,10,0,0,.001,true,entry,sl,tp,market),"NFP crossed buy");
   Check(market && MathAbs(entry-4185.803)<1e-6 && MathAbs(sl-4175.803)<1e-6 && tp==0,"buy SL reanchored");
   Check(NP_PlanSide(false,4177.59,4185.621,4185.803,10,0,0,.001,true,entry,sl,tp,market),"opposite stop");
   Check(!market && MathAbs(entry-4177.59)<1e-6 && MathAbs(sl-4187.59)<1e-6,"sell stays pending");
   Check(NP_PlanSide(false,4186,4185,4185.2,10,0,0,.001,true,entry,sl,tp,market) && market && sl==4195,"crossed sell -> market sell");
   Check(!NP_PlanSide(true,4184,4185,4185.2,10,0,0,.001,false,entry,sl,tp,market),"fallback off blocks crossed level");
   Check(NP_PlanSide(true,4185.3,4185,4185.2,10,5.5,1,.1,true,entry,sl,tp,market) && !market && entry>=4186.3,"broker gap moves pending out");
   Check(NP_PlanSide(true,4184,4185,4187,1,0,3,.1,true,entry,sl,tp,market) && market && sl<=4181.9+1e-6,"market SL respects spread and gap");
   Check(!NP_PlanSide(true,1,2,1,10,0,0,.001,true,entry,sl,tp,market),"invalid quote rejected");
   Print("GEOMETRY_TESTS|failures=",failures);
   return failures==0 ? INIT_SUCCEEDED : INIT_FAILED;
}
void OnTick() {}

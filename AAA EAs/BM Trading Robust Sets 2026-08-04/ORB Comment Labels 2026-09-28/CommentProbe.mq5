#property strict
#include "..\_Shared\CalyxORBComments.mqh"
int checks=0;
bool Check(const string actual,const string expected)
{
   checks++;
   if(actual!=expected || StringLen(actual)>31)
   {
      Print("ORB_LABEL_FAIL ",checks," actual=",actual," expected=",expected);
      return false;
   }
   Print("ORB_LABEL_OK ",checks," ",actual);
   return true;
}
int OnInit()
{
   if(!MQLInfoInteger(MQL_TESTER)) return INIT_FAILED;
   bool ok=true;
   ok=Check(CalyxORBTradeComment(15,PERIOD_M5,false,9,30,"",false,false),"ORB 15m M5 NY09:30") && ok;
   ok=Check(CalyxORBTradeComment(15,PERIOD_M5,false,9,30,"",true,false),"ORB 15m M5 NY09:30 VolConf") && ok;
   ok=Check(CalyxORBTradeComment(30,PERIOD_M30,false,9,30,"",false,false),"ORB 30m M30 NY09:30") && ok;
   ok=Check(CalyxORBTradeComment(5,PERIOD_M30,true,13,0,"",false,false),"ORB 5m M30 13UTC") && ok;
   ok=Check(CalyxORBTradeComment(5,PERIOD_M30,false,9,30,"",false,false),"ORB 5m M30 NY09:30") && ok;
   ok=Check(CalyxORBTradeComment(60,PERIOD_M15,true,13,0,"",false,false),"ORB 1H M15 13UTC") && ok;
   ok=Check(CalyxORBTradeComment(30,PERIOD_M5,false,9,30,"V3Retest",false,false),"ORB 30m M5 NY09:30 V3Retest") && ok;
   ok=Check(CalyxORBTradeComment(30,PERIOD_M5,false,9,30,"SelRetest",false,false),"ORB 30m M5 NY09:30 SelRetest") && ok;
   ok=Check(CalyxORBTradeComment(120,PERIOD_H1,true,13,30,"",false,false),"ORB 2H H1 13:30UTC") && ok;
   ok=Check(CalyxORBTradeComment(15,PERIOD_M5,false,9,30,"Retest",true,false),"ORB 15m M5 NY09:30 VolConf RT") && ok;
   ok=Check(CalyxORBTradeComment(30,PERIOD_M30,false,9,30,"Retest",true,false),"ORB 30m M30 NY09:30 VolConf RT") && ok;
   ok=Check(CalyxORBTradeComment(45,PERIOD_M15,true,8,0,"",false,true),"ORB 45m M15 08UTC VP") && ok;
   ok=Check(CalyxORBTradeComment(15,PERIOD_M5,false,9,30,"",true,true),"ORB 15m M5 NY09:30 VolConf VP") && ok;
   return ok ? INIT_SUCCEEDED : INIT_FAILED;
}
void OnTick() {}
double OnTester() { Print("ORB_LABEL_TESTS_PASS=",checks); return checks; }

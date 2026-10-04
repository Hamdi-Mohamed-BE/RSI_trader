// Native tester-only lifecycle test, not performance evidence.
#define OnInit OriginalInit
#define OnTick OriginalTick
#define OnTester OriginalTester
#include "CalyxHourlyProfiles.mq5"
#undef OnInit
#undef OnTick
#undef OnTester
bool exercised=false,passed=false;
int OnInit(){if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;return OriginalInit();}
void OnTick(){
 OriginalTick();if(exercised||Owned()!=1)return;
 ulong ticket=0;for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);if(t&&Own()){ticket=t;break;}}
 if(ticket==0)return;int count=accepted;
 // Emulate volatile state loss while a broker-owned position still exists.
 ArrayInitialize(lastDay,0);OriginalTick();bool restored=(accepted==count&&Owned()==1);
 // Simulate a manual close inside the entry minute, then process again.
 bool closed=trade.PositionClose(ticket);OriginalTick();
 passed=restored&&closed&&Owned()==0&&accepted==count;exercised=true;
 Print("HOURLY_FAULT restart_owned_recovery=",restored," manual_close=",closed," no_reentry=",passed);
}
double OnTester(){OriginalTester();Print("HOURLY_FAULT_COMPLETE exercised=",exercised," passed=",passed);return passed?1:-1;}

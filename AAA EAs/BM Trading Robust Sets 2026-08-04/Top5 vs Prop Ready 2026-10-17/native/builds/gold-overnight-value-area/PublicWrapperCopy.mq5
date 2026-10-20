#property strict
#define CLIENT_ID "CALYX-TOP5-20260930-01"
#define CLIENT_ISSUED ((datetime)1790789954)
#define CLIENT_EXPIRES ((datetime)1793381954)
#define CLIENT_BOUND_LOGIN ((long)0)
#define CLIENT_BOUND_SERVER ""
#define CLIENT_TEST_EXPIRY false
#include "C:/Users/hama101/Desktop/geek/ai trader/clients/_owner/top5/build/ClientGuard.mqh"
#define OnInit ClientStrategyInit
#define OnTick ClientStrategyTick
#define OnTimer ClientStrategyTimer
#include "C:/Users/hama101/Desktop/geek/ai trader/clients/_owner/top5/build/src_eb3da0e2018e.mqh"
#undef OnInit
#undef OnTick
#undef OnTimer
long ClientMagic(){return (long)InpMagic;}
int Top5PackageOnInit(){int r=ClientInit();if(r!=INIT_SUCCEEDED)return r;r=ClientStrategyInit();if(r==INIT_SUCCEEDED)EventSetTimer(1);return r;}
void Top5PackageOnTick(){ClientPulse();ClientStrategyTick();}
void Top5PackageOnTimer(){ClientPulse();ClientStrategyTimer();}

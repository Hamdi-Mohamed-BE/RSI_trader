#property strict
#define CLIENT_ID "CALYX-TOP5-20260930-01"
#define CLIENT_ISSUED ((datetime)1790789954)
#define CLIENT_EXPIRES ((datetime)1793381954)
#define CLIENT_BOUND_LOGIN ((long)0)
#define CLIENT_BOUND_SERVER ""
#define CLIENT_TEST_EXPIRY false
#include "ClientGuard.mqh"
#define OnInit ClientStrategyInit
#define OnTick ClientStrategyTick
#define OnTimer ClientStrategyTimer
#include "src_eb3da0e2018e.mqh"
#undef OnInit
#undef OnTick
#undef OnTimer
long ClientMagic(){return (long)InpMagic;}
int OnInit(){int r=ClientInit();if(r!=INIT_SUCCEEDED)return r;r=ClientStrategyInit();if(r==INIT_SUCCEEDED)EventSetTimer(1);return r;}
void OnTick(){ClientPulse();ClientStrategyTick();}
void OnTimer(){ClientPulse();ClientStrategyTimer();}

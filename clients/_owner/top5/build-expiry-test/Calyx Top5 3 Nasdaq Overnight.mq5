#property strict
#define CLIENT_ID "TOP5-EXPIRY-TEST"
#define CLIENT_ISSUED ((datetime)1790791098)
#define CLIENT_EXPIRES ((datetime)1782967470)
#define CLIENT_BOUND_LOGIN ((long)0)
#define CLIENT_BOUND_SERVER ""
#define CLIENT_TEST_EXPIRY true
#include "ClientGuard.mqh"
#define OnInit ClientStrategyInit
#define OnTick ClientStrategyTick
#define OnTimer ClientStrategyTimer
#include "src_a364caf69e2d.mqh"
#undef OnInit
#undef OnTick
#undef OnTimer
long ClientMagic(){return (long)InpMagic;}
int OnInit(){int r=ClientInit();if(r!=INIT_SUCCEEDED)return r;r=ClientStrategyInit();if(r==INIT_SUCCEEDED)EventSetTimer(1);return r;}
void OnTick(){ClientPulse();ClientStrategyTick();}
void OnTimer(){ClientPulse();ClientStrategyTimer();}

#property strict
#include "CalyxTurboGuard.mqh"
#define OnInit TURBO_StrategyInit
#define OnTick TURBO_StrategyTick
#define OnTimer TURBO_StrategyTimer
#include "src_0bc9b9d98dc3.mqh"
#undef OnInit
#undef OnTick
#undef OnTimer
int OnInit(){if(TurboInit()!=INIT_SUCCEEDED)return INIT_FAILED;return TURBO_StrategyInit();}
void OnTick(){if(TurboPulse())TURBO_StrategyTick();}

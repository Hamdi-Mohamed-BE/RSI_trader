#property strict
#include "CalyxTurboGuard.mqh"
#define OnInit TURBO_StrategyInit
#define OnTick TURBO_StrategyTick
#define OnTimer TURBO_StrategyTimer
#include "src_4b88b16fefc3.mqh"
#undef OnInit
#undef OnTick
#undef OnTimer
int OnInit(){if(TurboInit()!=INIT_SUCCEEDED)return INIT_FAILED;return TURBO_StrategyInit();}
void OnTick(){if(TurboPulse())TURBO_StrategyTick();}

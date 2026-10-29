#property strict
#include "CalyxFundedGuard.mqh"
#define OnInit FUNDED_StrategyInit
#define OnTick FUNDED_StrategyTick
#define OnTimer FUNDED_StrategyTimer
#include "src_163b4c7319d5.mqh"
#undef OnInit
#undef OnTick
#undef OnTimer
int OnInit(){if(FundedInit()!=INIT_SUCCEEDED)return INIT_FAILED;return FUNDED_StrategyInit();}
void OnTick(){if(FundedPulse())FUNDED_StrategyTick();}

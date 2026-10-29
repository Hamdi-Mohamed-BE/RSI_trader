#property strict
#include "CalyxFundedGuard.mqh"
#define OnInit FUNDED_StrategyInit
#define OnTick FUNDED_StrategyTick
#define OnTimer FUNDED_StrategyTimer
#include "src_df47e0981de0.mqh"
#undef OnInit
#undef OnTick
#undef OnTimer
int OnInit(){if(FundedInit()!=INIT_SUCCEEDED)return INIT_FAILED;return FUNDED_StrategyInit();}
void OnTick(){if(FundedPulse())FUNDED_StrategyTick();}
void OnTimer(){if(FundedPulse())FUNDED_StrategyTimer();}

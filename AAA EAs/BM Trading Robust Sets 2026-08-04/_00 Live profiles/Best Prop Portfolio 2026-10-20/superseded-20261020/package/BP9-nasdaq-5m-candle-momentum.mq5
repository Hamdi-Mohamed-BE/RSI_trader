#property strict
#include "CalyxFTMOGuard.mqh"
#define OnInit FTMO_StrategyInit
#define OnTick FTMO_StrategyTick
#define OnTimer FTMO_StrategyTimer
#include "src_0bc9b9d98dc3.mqh"
#undef OnInit
#undef OnTick
#undef OnTimer
int OnInit(){ if(FTMOInit()!=INIT_SUCCEEDED)return INIT_FAILED; return FTMO_StrategyInit(); }
void OnTick(){ if(FTMOPulse())FTMO_StrategyTick(); }

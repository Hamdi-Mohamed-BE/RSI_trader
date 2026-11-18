#property strict
#include "../../RiskSupport.mqh"
#include "CalyxNoOpposite.mqh"   // Best 1-Step 2026-11-17: no-opposite rule
#define OnInit UR_StrategyInit
#define OnTick UR_StrategyTick
#define OnTimer UR_StrategyTimer
#include "src_aaa_719b00d0a907.mqh"
#undef OnInit
#undef OnTick
#undef OnTimer
int OnInit(){if(!UR_InputsValid(InpRiskPercent))return INIT_PARAMETERS_INCORRECT;int r=UR_StrategyInit();if(r==INIT_SUCCEEDED)UR_Heartbeat(InpMagic,true);return r;}
void OnTick(){if(!UR_BindingOK())return;UR_Heartbeat(InpMagic);CNO_Tick();UR_StrategyTick();}

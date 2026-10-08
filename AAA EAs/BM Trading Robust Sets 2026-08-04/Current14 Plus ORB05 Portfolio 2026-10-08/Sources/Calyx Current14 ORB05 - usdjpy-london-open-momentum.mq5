#property strict
#include "../RiskSupport.mqh"
#define OnInit UR_StrategyInit
#define OnTick UR_StrategyTick
#define OnTimer UR_StrategyTimer
#include "src_49e38a78c57a.mqh"
#undef OnInit
#undef OnTick
#undef OnTimer
int OnInit(){if(!UR_InputsValid(InpRiskPercent))return INIT_PARAMETERS_INCORRECT;int r=UR_StrategyInit();if(r==INIT_SUCCEEDED)UR_Heartbeat(InpMagic,true);return r;}
void OnTick(){if(!UR_BindingOK())return;UR_Heartbeat(InpMagic);UR_StrategyTick();}

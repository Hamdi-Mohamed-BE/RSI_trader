#property strict
#include "../RiskSupport.mqh"
#define OnInit UR_StrategyInit
#define OnTick UR_StrategyTick
#include "src_b1_uk100-monday-dip.mqh"
#undef OnInit
#undef OnTick
int OnInit(){if(!UR_InputsValid(InpRiskPercent))return INIT_PARAMETERS_INCORRECT;int r=UR_StrategyInit();if(r==INIT_SUCCEEDED)UR_Heartbeat(InpMagic,true);return r;}
void OnTick(){if(!UR_BindingOK())return;UR_Heartbeat(InpMagic);UR_StrategyTick();}

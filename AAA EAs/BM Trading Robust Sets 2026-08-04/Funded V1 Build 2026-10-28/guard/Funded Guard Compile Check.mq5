#property strict
#include "CalyxFundedGuard.mqh"
int OnInit(){return FundedInit();}
void OnTick(){FundedPulse();}

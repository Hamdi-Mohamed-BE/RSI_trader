#property strict
// Compile check only: the guard include on its own, with the same wrapper hooks the guarded EAs will use.
#include "CalyxTurboGuard.mqh"
int OnInit(){return TurboInit();}
void OnTick(){TurboPulse();}

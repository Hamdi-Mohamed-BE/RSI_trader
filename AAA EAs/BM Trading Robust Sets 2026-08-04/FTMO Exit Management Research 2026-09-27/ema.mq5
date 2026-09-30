#property strict
#include "ExitManagement.mqh"
#define OnInit EM_BaseInit
#define OnTick EM_BaseTick
#define OnTimer EM_BaseTimer
#define OnDeinit EM_BaseDeinit
#include "snapshot\AAA Final EAs\AAA Final EMA3 EA\AAA Final EMA3 EA.mq5"
#undef OnInit
#undef OnTick
#undef OnTimer
#undef OnDeinit
int OnInit(){if(!EM_Init())return INIT_FAILED;return EM_BaseInit();}
void OnTick(){EM_Run();EM_BaseTick();EM_Run();}
void OnDeinit(const int r){EM_End();}

#property strict
#include "ExitManagement.mqh"
#include "snapshot\News Pulse Event Parameters Research 2026-09-19\NativeFullBestV2.mq5"
#undef OnInit
#undef OnTick
#undef OnTimer
#undef OnDeinit
int OnInit(){if(!EM_Init())return INIT_FAILED;return EM_BaseInit();}
void OnTick(){EM_Run();EM_BaseTick();EM_Run();}
void OnTimer(){EM_Run();EM_BaseTimer();EM_Run();}
void OnDeinit(const int r){EM_BaseDeinit(r);EM_End();}

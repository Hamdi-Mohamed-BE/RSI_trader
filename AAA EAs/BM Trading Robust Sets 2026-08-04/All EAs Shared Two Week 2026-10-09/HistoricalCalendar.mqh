// Official-source schedule; isolated tester only, not a point-in-time calendar vintage.
#ifndef CALYX_NEWS_PULSE_TESTER_CALENDAR_MQH
#define CALYX_NEWS_PULSE_TESTER_CALENDAR_MQH
#define NP_TESTER_CALENDAR_COVERAGE_START_DATE 20260925
#define NP_TESTER_CALENDAR_COVERAGE_END_DATE 20261009
#define NP_TESTER_CALENDAR_EXPECTED_EVENTS 1
long NP_GENERATED_EVENT_UTC_EPOCHS[]={1790944200};
string NP_GENERATED_EVENT_KINDS[]={"NFP"};
string NP_GeneratedCalendarProvider(){return "Official BLS + Federal Reserve; receipted chronology";}
string NP_GeneratedCalendarHash(){return "27c9329d01f259ff3ece7cf91c022502a14664cfad58c829539944e5716580df";}
string NP_GeneratedCalendarFetchedAt(){return "2026-10-09";}
int NP_GeneratedCalendarEventCount(){return ArraySize(NP_GENERATED_EVENT_UTC_EPOCHS);}
#endif

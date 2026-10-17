// Receipted official schedule in a tester-only copy; no historical AI predictions.
#ifndef CALYX_NEWS_PULSE_TESTER_CALENDAR_MQH
#define CALYX_NEWS_PULSE_TESTER_CALENDAR_MQH
#define NP_TESTER_CALENDAR_COVERAGE_START_DATE 20260816
#define NP_TESTER_CALENDAR_COVERAGE_END_DATE 20261016
#define NP_TESTER_CALENDAR_EXPECTED_EVENTS 5
long NP_GENERATED_EVENT_UTC_EPOCHS[]={1788525000,1789129800,1789581600,1790944200,1791981000};
string NP_GENERATED_EVENT_KINDS[]={"NFP","CPI","FOMC","NFP","CPI"};
string NP_GeneratedCalendarProvider(){return "Official BLS + Federal Reserve; saved receipted chronology";}
string NP_GeneratedCalendarHash(){return "70314a664d4a94fd90107b3e98ed41b224cdd432ad06a9a9e1a006901e0b9b7b";}
string NP_GeneratedCalendarFetchedAt(){return "2026-10-16";}
int NP_GeneratedCalendarEventCount(){return ArraySize(NP_GENERATED_EVENT_UTC_EPOCHS);}
#endif

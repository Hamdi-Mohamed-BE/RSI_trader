// Tester-only research extension. The EA retains its unconditional tester guard.
input int ResearchWeeklyMode=0; // 0=off, 1=Monday calendar week, 2=rolling seven days

datetime ResearchWeekStart(const datetime stamp)
{
   MqlDateTime d;
   if(!TimeToStruct(stamp,d)) return 0;
   const int daysFromMonday=(d.day_of_week+6)%7;
   d.hour=0;d.min=0;d.sec=0;
   return StructToTime(d)-daysFromMonday*86400;
}

bool ResearchWeekPermit(const int mode,const datetime now,const datetime lastEntry)
{
   if(mode==0 || lastEntry==0) return true;
   if(now<lastEntry) return false;
   if(mode==1) return ResearchWeekStart(now)>ResearchWeekStart(lastEntry);
   if(mode==2) return now-lastEntry>=7*86400;
   return false;
}

bool ResearchWeeklySelfTest()
{
   return ResearchWeekStart(D'2026.09.27 23:59:59')==D'2026.09.21 00:00:00'
      && ResearchWeekStart(D'2026.09.28 00:00:00')==D'2026.09.28 00:00:00'
      && !ResearchWeekPermit(1,D'2026.09.27 23:59:59',D'2026.09.21 00:00:00')
      && ResearchWeekPermit(1,D'2026.09.28 00:00:00',D'2026.09.27 23:59:59')
      && !ResearchWeekPermit(1,D'2026.01.01 00:00:00',D'2025.12.31 10:00:00')
      && ResearchWeekPermit(1,D'2026.01.05 00:00:00',D'2025.12.31 10:00:00')
      && !ResearchWeekPermit(1,D'2024.03.01 00:00:00',D'2024.02.29 10:00:00')
      && ResearchWeekPermit(1,D'2024.03.04 00:00:00',D'2024.02.29 10:00:00')
      && !ResearchWeekPermit(2,D'2026.09.28 09:59:59',D'2026.09.21 10:00:00')
      && ResearchWeekPermit(2,D'2026.09.28 10:00:00',D'2026.09.21 10:00:00')
      && ResearchWeekPermit(0,D'2026.09.21 10:00:00',D'2026.09.21 10:00:00')
      && ResearchWeekPermit(1,D'2026.09.21 10:00:00',0)
      && !ResearchWeekPermit(2,D'2026.09.20 10:00:00',D'2026.09.21 10:00:00');
}

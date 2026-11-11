#property strict
#property version   "1.00"
#property description "Calyx Weekend Flat (owner 2026-11-11): closes EA positions and deletes EA pending orders before every market break of 2 hours or more"
#property description "(weekends, broker session gaps) and before US / Christmas / New Year holiday closures. FTMO Standard / 1-Step FTMO Account rule. Never opens trades."
#include <Trade/Trade.mqh>

input bool   InpEnabled=true;
input int    InpLeadMinutes=30;            // go flat this many minutes before a break starts
input int    InpMinBreakMinutes=120;       // FTMO: breaks longer than 2 hours
input bool   InpHolidayRules=true;         // built-in US / Christmas / New Year rules (module docstring)
input int    InpHolidayFlatHourNY=12;      // holiday flat time, New York (12:00)
input string InpHolidayFile="CalyxHolidayFlat.csv"; // optional, MQL5\Files\Common: from_date,from_HH:MM(NY),to_date,to_HH:MM(NY),symbols(ALL or a;b;c substrings)
input bool   InpIncludeManual=false;       // also close manual trades (magic 0)
input bool   InpDeletePending=true;        // delete EA pending orders in the same window
input int    InpTimerSeconds=5;
input int    InpServerUtcOffsetHours=0;    // tester only; live uses the broker clock
input bool   InpTestOpen=false;            // TESTER ONLY: opens 0.01 test positions so the closing logic can be audited

CTrade trade;
struct Window { datetime from; datetime to; int cls; string syms; };   // cls bitmask 1 US index/metal, 2 FX, 4 other index; syms for file rules
Window g_hol[]; int g_hol_year=0; datetime g_last_report=0; long g_closed=0,g_deleted=0,g_failed=0;

//---------------------------------------------------------------- clocks
int SrvOffSec(){
   if((bool)MQLInfoInteger(MQL_TESTER)) return InpServerUtcOffsetHours*3600;
   datetime s=TimeTradeServer(),u=TimeGMT(); if(s<=0||u<=0) return InpServerUtcOffsetHours*3600;
   return (int)MathRound((double)(s-u)/1800.0)*1800;
}
datetime NthDow(int y,int m,int dow,int n){MqlDateTime t={};t.year=y;t.mon=m;t.day=1;datetime x=StructToTime(t);MqlDateTime d;TimeToStruct(x,d);return x+(datetime)((((dow-d.day_of_week)+7)%7+7*(n-1))*86400);}
datetime LastDow(int y,int m,int dow){MqlDateTime t={};t.year=y+(m==12?1:0);t.mon=(m==12?1:m+1);t.day=1;datetime x=StructToTime(t)-86400;MqlDateTime d;TimeToStruct(x,d);return x-(datetime)(((d.day_of_week-dow)+7)%7*86400);}
bool NyDst(datetime utc){MqlDateTime d;TimeToStruct(utc,d);datetime on=NthDow(d.year,3,0,2)+7*3600,off=NthDow(d.year,11,0,1)+6*3600;return utc>=on&&utc<off;}
// New York wall clock (date at 00:00 + minutes) -> server time
datetime NyToServer(datetime nyDate,int minutes){datetime guess=nyDate+minutes*60+5*3600;int off=NyDst(guess)?4:5;return nyDate+minutes*60+off*3600+SrvOffSec();}
datetime Ymd(int y,int m,int d){MqlDateTime t={};t.year=y;t.mon=m;t.day=d;return StructToTime(t);}
int Dow(datetime t){MqlDateTime d;TimeToStruct(t,d);return d.day_of_week;}
datetime Observed(datetime d){int w=Dow(d);return w==6?d-86400:(w==0?d+86400:d);}           // NYSE observance
datetime PrevWeekday(datetime d){datetime x=d-86400;while(Dow(x)==0||Dow(x)==6)x-=86400;return x;}
datetime NextWeekday(datetime d){datetime x=d+86400;while(Dow(x)==0||Dow(x)==6)x+=86400;return x;}
datetime Easter(int y){int a=y%19,b=y/100,c=y%100,d=b/4,e=b%4,f=(b+8)/25,g=(b-f+1)/3,h=(19*a+b-d-g+15)%30,i=c/4,k=c%4,l=(32+2*e+2*i-h-k)%7,m=(a+11*h+22*l)/451;int mon=(h+l-7*m+114)/31,day=((h+l-7*m+114)%31)+1;return Ymd(y,mon,day);}

void AddWin(datetime f,datetime t,int cls,string syms){int n=ArraySize(g_hol);ArrayResize(g_hol,n+1);g_hol[n].from=f;g_hol[n].to=t;g_hol[n].cls=cls;g_hol[n].syms=syms;}

void BuildHolidays(int year){
   ArrayResize(g_hol,0); g_hol_year=year; int fm=InpHolidayFlatHourNY*60;
   if(InpHolidayRules) for(int y=year-1;y<=year+1;y++){
      // early-halt holidays for US index / metal CFDs: flat at 12:00 NY on the day, back after the 18:00 NY reopen
      datetime list[7]; list[0]=NthDow(y,1,1,3); list[1]=NthDow(y,2,1,3); list[2]=LastDow(y,5,1); list[3]=Observed(Ymd(y,6,19)); list[4]=Observed(Ymd(y,7,4)); list[5]=NthDow(y,9,1,1); list[6]=NthDow(y,11,4,4);
      for(int i=0;i<7;i++) AddWin(NyToServer(list[i],fm),NyToServer(list[i],18*60+30),1,"");
      datetime tg=NthDow(y,11,4,4)+86400; AddWin(NyToServer(tg,fm),NyToServer(tg,23*60),1,"");          // day after Thanksgiving: early close, then the weekend
      datetime j3=Ymd(y,7,3); if(Dow(j3)>=1&&Dow(j3)<=4) AddWin(NyToServer(j3,fm),NyToServer(j3,18*60+30),1,"");   // July 3 early close
      // full closures: flat at 12:00 NY on the previous weekday, back the next weekday
      datetime gf=Easter(y)-2*86400; AddWin(NyToServer(PrevWeekday(gf),fm),NyToServer(NextWeekday(gf),0),1|4,"");
      datetime full[2]; full[0]=Observed(Ymd(y,12,25)); full[1]=Observed(Ymd(y+1,1,1));
      for(int i=0;i<2;i++) AddWin(NyToServer(PrevWeekday(full[i]),fm),NyToServer(NextWeekday(full[i]),0),1|2|4,"");
   }
   if(InpHolidayFile!=""){
      int h=FileOpen(InpHolidayFile,FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
      if(h!=INVALID_HANDLE){
         while(!FileIsEnding(h)){
            string a=FileReadString(h),b=FileReadString(h),c=FileReadString(h),d=FileReadString(h),s=FileReadString(h);
            if(StringLen(a)<10||StringGetCharacter(a,0)=='#') continue;
            datetime fd=StringToTime(a),td=StringToTime(c); string bh[],dh[];
            if(StringSplit(b,':',bh)!=2||StringSplit(d,':',dh)!=2) continue;
            AddWin(NyToServer(fd,(int)StringToInteger(bh[0])*60+(int)StringToInteger(bh[1])),NyToServer(td,(int)StringToInteger(dh[0])*60+(int)StringToInteger(dh[1])),0,(s==""?"ALL":s));
         }
         FileClose(h);
      }
   }
}

//---------------------------------------------------------------- symbol classes
bool Has(string s,string k){return StringFind(s,k)>=0;}
int SymClass(string sym){
   string s=sym; StringToUpper(s);
   if(Has(s,"BTC")||Has(s,"ETH")||Has(s,"XRP")||Has(s,"SOL")||Has(s,"LTC")) return 0;                         // crypto: session gaps only
   if(Has(s,"XAU")||Has(s,"XAG")||Has(s,"GOLD")||Has(s,"SILVER")||Has(s,"XPT")||Has(s,"XPD")||Has(s,"OIL")||Has(s,"WTI")) return 1;
   if(Has(s,"US30")||Has(s,"US100")||Has(s,"USTEC")||Has(s,"NAS")||Has(s,"NDX")||Has(s,"US500")||Has(s,"SPX")||Has(s,"SP500")||Has(s,"DJ")||Has(s,"US2000")||Has(s,"RUS")) return 1;
   ENUM_SYMBOL_CALC_MODE m=(ENUM_SYMBOL_CALC_MODE)SymbolInfoInteger(sym,SYMBOL_TRADE_CALC_MODE);
   if(m==SYMBOL_CALC_MODE_FOREX||m==SYMBOL_CALC_MODE_FOREX_NO_LEVERAGE) return 2;
   return 4;
}
bool HolidayWindow(string sym,datetime t,datetime &until){
   int c=SymClass(sym); string s=sym; StringToUpper(s);
   for(int i=0;i<ArraySize(g_hol);i++){
      if(t<g_hol[i].from||t>=g_hol[i].to) continue;
      if(g_hol[i].cls!=0){ if((g_hol[i].cls&c)!=0){until=g_hol[i].to;return true;} continue; }
      if(g_hol[i].syms=="ALL"&&c!=0){until=g_hol[i].to;return true;}
      string parts[]; int n=StringSplit(g_hol[i].syms,';',parts);
      for(int k=0;k<n;k++){string p=parts[k];StringToUpper(p);if(p!=""&&Has(s,p)){until=g_hol[i].to;return true;}}
   }
   return false;
}

//---------------------------------------------------------------- session gaps (server time)
// Returns true when t is inside [break start - lead, next session start) of a break >= InpMinBreakMinutes, or when the market is in such a break now.
bool SessionWindow(string sym,datetime t,datetime &breakStart){
   long iv_from[],iv_to[]; ArrayResize(iv_from,0); ArrayResize(iv_to,0);
   for(int d=0;d<7;d++) for(uint k=0;k<10;k++){
      datetime f,e; if(!SymbolInfoSessionTrade(sym,(ENUM_DAY_OF_WEEK)d,k,f,e)) break;
      long a=(long)d*86400+(long)f,b=(long)d*86400+(long)e; if(e==0||(long)e>=86400) b=(long)d*86400+86400; if(b<=a) continue;
      int n=ArraySize(iv_from); ArrayResize(iv_from,n+1); ArrayResize(iv_to,n+1); iv_from[n]=a; iv_to[n]=b;
   }
   int n=ArraySize(iv_from); if(n==0) return false;
   for(int i=0;i<n;i++) for(int j=i+1;j<n;j++) if(iv_from[j]<iv_from[i]){long x=iv_from[i];iv_from[i]=iv_from[j];iv_from[j]=x;x=iv_to[i];iv_to[i]=iv_to[j];iv_to[j]=x;}
   // merge contiguous pieces (a session over midnight is split by day)
   long mf[],mt[]; ArrayResize(mf,0); ArrayResize(mt,0);
   for(int i=0;i<n;i++){int m=ArraySize(mf); if(m>0&&iv_from[i]<=mt[m-1]+60){mt[m-1]=MathMax(mt[m-1],iv_to[i]);continue;} ArrayResize(mf,m+1);ArrayResize(mt,m+1);mf[m]=iv_from[i];mt[m]=iv_to[i];}
   int m=ArraySize(mf); if(m>1&&mf[0]==0&&mt[m-1]>=604800-60){mf[0]=mf[m-1]-604800;ArrayResize(mf,m-1);ArrayResize(mt,m-1);m--;}  // wraps over Saturday/Sunday midnight
   MqlDateTime dt; TimeToStruct(t,dt); datetime weekStart=t-(dt.day_of_week*86400+dt.hour*3600+dt.min*60+dt.sec); long w=(long)(t-weekStart);
   for(int pass=0;pass<2;pass++) for(int i=0;i<m;i++){
      long a=mf[i]+pass*604800,b=mt[i]+pass*604800,na=(i+1<m?mf[i+1]:mf[0]+604800)+pass*604800; long gap=na-b;
      if(w>=a&&w<b){ if(gap>=InpMinBreakMinutes*60&&w>=b-InpLeadMinutes*60){breakStart=weekStart+(datetime)b;return true;} return false; }
      if(w>=b&&w<na){ if(gap>=InpMinBreakMinutes*60){breakStart=weekStart+(datetime)b;return true;} return false; }
   }
   return false;
}

// Backstop (tester audit 2026-11-11): broker session tables are fixed in server time and can end Friday an hour after the real summer close.
// FX / metals / index CFDs close for the weekend at 17:00 New York in both seasons, so every non-crypto symbol is flat from Friday 17:00 NY - lead until Sunday 17:00 NY.
bool WeeklyNyWindow(string sym,datetime t){
   if(SymClass(sym)==0) return false;
   datetime utc=t-SrvOffSec(); datetime nyt=utc-(NyDst(utc)?4:5)*3600; MqlDateTime n; TimeToStruct(nyt,n); int m=n.hour*60+n.min;
   if(n.day_of_week==5) return m>=17*60-InpLeadMinutes;
   if(n.day_of_week==6) return true;
   if(n.day_of_week==0) return m<17*60;
   return false;
}

bool FlatNow(string sym,datetime t,string &why){
   datetime x=0;
   if(WeeklyNyWindow(sym,t)){why="weekend (Friday 17:00 New York close)";return true;}
   if(SessionWindow(sym,t,x)){why="break at "+TimeToString(x,TIME_DATE|TIME_MINUTES)+" server";return true;}
   if(HolidayWindow(sym,t,x)){why="holiday window until "+TimeToString(x,TIME_DATE|TIME_MINUTES)+" server";return true;}
   return false;
}

//---------------------------------------------------------------- actions
void Sweep(){
   if(!InpEnabled) return;
   datetime t=TimeTradeServer(); if((bool)MQLInfoInteger(MQL_TESTER)||t<=0) t=TimeCurrent();
   MqlDateTime d; TimeToStruct(t,d); if(d.year!=g_hol_year) BuildHolidays(d.year);
   for(int i=PositionsTotal()-1;i>=0;i--){
      ulong tk=PositionGetTicket(i); if(tk==0) continue;
      long mg=PositionGetInteger(POSITION_MAGIC); if(mg==0&&!InpIncludeManual) continue;
      string sym=PositionGetString(POSITION_SYMBOL),why; if(!FlatNow(sym,t,why)) continue;
      if(trade.PositionClose(tk,1000)&&(trade.ResultRetcode()==TRADE_RETCODE_DONE||trade.ResultRetcode()==TRADE_RETCODE_PLACED)){g_closed++;PrintFormat("CWF_CLOSE ticket=%I64u symbol=%s magic=%I64d %s",tk,sym,mg,why);}
      else {g_failed++; if(t-g_last_report>300){g_last_report=t;PrintFormat("CWF_CLOSE_FAIL ticket=%I64u symbol=%s code=%u %s (retrying)",tk,sym,trade.ResultRetcode(),why);}}
   }
   if(InpDeletePending) for(int i=OrdersTotal()-1;i>=0;i--){
      ulong tk=OrderGetTicket(i); if(tk==0) continue;
      long mg=OrderGetInteger(ORDER_MAGIC); if(mg==0&&!InpIncludeManual) continue;
      string sym=OrderGetString(ORDER_SYMBOL),why; if(!FlatNow(sym,t,why)) continue;
      if(trade.OrderDelete(tk)){g_deleted++;PrintFormat("CWF_DELETE order=%I64u symbol=%s magic=%I64d %s",tk,sym,mg,why);}
   }
}

void TestOpen(){                                     // tester audit only: open 0.01 at 11:00 NY every weekday and keep it (the helper must close it before breaks / holidays)
   if(!InpTestOpen||!(bool)MQLInfoInteger(MQL_TESTER)) return;
   static int lastKey=0; datetime t=TimeCurrent(); datetime utc=t-SrvOffSec(); datetime ny=utc-(NyDst(utc)?4:5)*3600; MqlDateTime n; TimeToStruct(ny,n);
   int key=n.year*10000+n.mon*100+n.day; if(key==lastKey||n.hour!=11||n.day_of_week==0||n.day_of_week==6) return;
   if(PositionsTotal()>0) return; lastKey=key; trade.SetExpertMagicNumber(77777); if(trade.Buy(SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),_Symbol)) PrintFormat("CWF_TEST_OPEN %s",TimeToString(t));
}

int OnInit(){
   if(InpLeadMinutes<0||InpMinBreakMinutes<1||InpTimerSeconds<1) return INIT_PARAMETERS_INCORRECT;
   trade.SetDeviationInPoints(1000); trade.SetAsyncMode(false);
   MqlDateTime d; TimeToStruct(TimeCurrent(),d); BuildHolidays(d.year);
   EventSetTimer(InpTimerSeconds);
   PrintFormat("CWF_SPEC enabled=%d lead=%d min_break=%d holidays=%d windows=%d file=%s manual=%d pending=%d srv_utc_offset_h=%.1f",InpEnabled,InpLeadMinutes,InpMinBreakMinutes,InpHolidayRules,ArraySize(g_hol),InpHolidayFile,InpIncludeManual,InpDeletePending,SrvOffSec()/3600.0);
   Sweep(); return INIT_SUCCEEDED;
}
void OnDeinit(const int r){EventKillTimer();PrintFormat("CWF_SUMMARY closed=%I64d deleted=%I64d failed_attempts=%I64d",g_closed,g_deleted,g_failed);}
void OnTimer(){Sweep();}
void OnTick(){TestOpen();Sweep();}

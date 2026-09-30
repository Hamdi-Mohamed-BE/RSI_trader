#property strict
#property version "1.00"
#property description "Passive research-only quote-clock and session coverage audit. Never sends orders."
input int InpProbe=1;
int monthKey=0,minutes=0,at0105=0,mon0105=0,at2350=0,at0600=0,at1800=0,atNY1555=0;
datetime lastMinute=0,first=0,last=0;
datetime Stamp(int y,int m,int d,int h){MqlDateTime x;ZeroMemory(x);x.year=y;x.mon=m;x.day=d;x.hour=h;return StructToTime(x);}
int Sunday(int y,int m,int n){MqlDateTime x;TimeToStruct(Stamp(y,m,1,0),x);return 1+(7-x.day_of_week)%7+(n-1)*7;}
datetime NY(datetime utc){MqlDateTime x;TimeToStruct(utc,x);return utc+((utc>=Stamp(x.year,3,Sunday(x.year,3,2),7) && utc<Stamp(x.year,11,Sunday(x.year,11,1),6))?-4:-5)*3600;}
void Flush(){if(monthKey)PrintFormat("CLOCK_MONTH|%s|%d|%d|%d|%d|%d|%d|%d|%d|%s|%s",_Symbol,monthKey,minutes,at0105,mon0105,at2350,at0600,at1800,atNY1555,TimeToString(first,TIME_DATE|TIME_SECONDS),TimeToString(last,TIME_DATE|TIME_SECONDS));}
int OnInit(){
 if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;
 for(int d=0;d<7;d++)for(uint i=0;i<10;i++){
  datetime a=0,b=0;if(!SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)d,i,a,b))break;
  PrintFormat("CLOCK_TRADE_SESSION|%s|%d|%d|%d|%d",_Symbol,d,(int)i,(int)a,(int)b);
 }
 return INIT_SUCCEEDED;
}
void OnTick(){
 datetime now=TimeCurrent(),minute=now-now%60;if(minute==lastMinute)return;lastMinute=minute;
 MqlDateTime u,d,n;TimeToStruct(now,u);TimeToStruct(NY(now)+7*3600,d);TimeToStruct(NY(now),n);
 int key=u.year*100+u.mon;if(key!=monthKey){Flush();monthKey=key;minutes=at0105=mon0105=at2350=at0600=at1800=atNY1555=0;first=now;}
 minutes++;last=now;
 if(d.day_of_week>=1 && d.day_of_week<=5){
  if(d.hour==1 && d.min==5){at0105++;if(d.day_of_week==1)mon0105++;}
  if(d.hour==23 && d.min==50)at2350++;
  if(d.hour==6 && d.min==0)at0600++;
  if(d.hour==18 && d.min==0)at1800++;
 }
 if(n.day_of_week>=1 && n.day_of_week<=5 && n.hour==15 && n.min==55)atNY1555++;
}
void OnDeinit(const int reason){Flush();}

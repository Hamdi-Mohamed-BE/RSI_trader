#property copyright "Calyx research: in-play opening range break (Lance's ORB video transcript supplied by the user); rules are our own reading"
#property version   "1.00"
#property strict

// Raw rules fixed 2026-09-25 before any test. Multi-symbol: one EA on one chart trades the whole universe.
//   Opening range : M5 bars 09:30-10:00 New York, wick high/low.
//   In-play       : at 10:00 NY rank the universe by opening relative volume RV = OR tick volume / average OR tick
//                   volume of the previous InpRVDays sessions; keep RV >= InpMinRelVol, take the top InpTopN.
//                   Control (InpUniverseMode=1): InpTopN symbols picked by a deterministic daily hash, no RV filter.
//   Gap           : (first 09:30 bar open - previous D1 close) / ATR(14, D1); its sign drives the direction variants.
//   Entry         : first M5 close beyond OR high (long) / low (short) between 10:00 and InpEntryEndMinuteNY;
//                   one trade per symbol per day. Direction: both / only with the gap / only against the gap.
//   Stop          : opposite side of the OR. Skip if OR > InpMaxORATR x ATR(D1) or stop < 3 x spread.
//   Exit          : end of day (earlier of InpFlatMinuteNY New York and InpFlatMinuteUTC UTC) or InpRewardRisk target.
//   Sizing        : InpRiskPercent of equity per trade (lots rounded up per portfolio policy).

enum ENUM_IP_UNIVERSE { IP_UNIVERSE_IN_PLAY=0, IP_UNIVERSE_CONTROL_RANDOM=1 };
enum ENUM_IP_DIRECTION { IP_DIR_BOTH=0, IP_DIR_WITH_GAP=1, IP_DIR_AGAINST_GAP=2 };

input group "Trading"
input bool   InpEnableTrading=true;
input double InpRiskPercent=1.0;
input long   InpMagic=1092507;
input bool   InpAdaptivePortfolioControls=false;
input bool   InpServerClockEET=false;          // Exness server clock is UTC

input group "In-play ORB"
input string InpSymbols="AAPL,AMD,AMZN,AVGO,GOOGL,INTC,JPM,META,MSFT,NFLX,NVDA,TSLA";
input ENUM_IP_UNIVERSE  InpUniverseMode=IP_UNIVERSE_IN_PLAY;
input ENUM_IP_DIRECTION InpDirectionMode=IP_DIR_BOTH;
input int    InpTopN=2;
input double InpMinRelVol=1.5;
input int    InpRVDays=14;
input double InpMaxORATR=2.0;
input double InpRewardRisk=0.0;                // 0 = no target (exit at end of day)
input int    InpEntryEndMinuteNY=840;          // 14:00
input int    InpFlatMinuteNY=940;              // 15:40
input int    InpFlatMinuteUTC=1180;            // 19:40 (older Exness stock data closes 19:45 UTC)

#include "AAA_Final_Common.mqh"

string   g_sym[];
int      g_atr[];
bool     g_active[];
bool     g_done[];
double   g_orh[], g_orl[], g_gap[], g_rv[];
int      g_day_key=0;
bool     g_ranked=false;
datetime g_ip_last_bar=0;

int IP_NYMinute(const datetime server_time) { MqlDateTime p; TimeToStruct(AAA_ToNewYork(server_time),p); return p.hour*60+p.min; }
int IP_NYDateKey(const datetime server_time) { MqlDateTime p; TimeToStruct(AAA_ToNewYork(server_time),p); return p.year*10000+p.mon*100+p.day; }
int IP_UTCMinute(const datetime server_time) { MqlDateTime p; TimeToStruct(AAA_ToUTC(server_time),p); return p.hour*60+p.min; }

int OnInit()
{
   AAA_TesterServerOffsetMode=(InpServerClockEET ? 1 : 0);
   string parts[];
   int n=StringSplit(InpSymbols,',',parts);
   if(n<=0 || InpTopN<1 || InpRiskPercent<=0.0) return INIT_PARAMETERS_INCORRECT;
   ArrayResize(g_sym,n); ArrayResize(g_atr,n); ArrayResize(g_active,n); ArrayResize(g_done,n);
   ArrayResize(g_orh,n); ArrayResize(g_orl,n); ArrayResize(g_gap,n); ArrayResize(g_rv,n);
   for(int i=0;i<n;i++)
     {
      StringTrimLeft(parts[i]); StringTrimRight(parts[i]);
      g_sym[i]=parts[i];
      if(!SymbolSelect(g_sym[i],true)) { PrintFormat("IPORB: symbol %s not available",g_sym[i]); return INIT_FAILED; }
      g_atr[i]=iATR(g_sym[i],PERIOD_D1,14);
      if(g_atr[i]==INVALID_HANDLE) return INIT_FAILED;
     }
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   for(int i=0;i<ArraySize(g_atr);i++) IndicatorRelease(g_atr[i]);
}

// Opening-range stats for one symbol: today's OR high/low/volume and the average OR volume of prior sessions.
bool IP_OpeningStats(const string sym,const int today_key,double &orh,double &orl,double &or_open,double &today_vol,double &avg_vol)
{
   MqlRates bars[];
   ArraySetAsSeries(bars,false);
   datetime from=TimeCurrent()-(InpRVDays*2+10)*86400;
   int n=CopyRates(sym,PERIOD_M5,from,TimeCurrent(),bars);
   if(n<=0) return false;
   orh=-DBL_MAX; orl=DBL_MAX; or_open=0.0; today_vol=0.0;
   int keys[]; double vols[]; int days=0;
   ArrayResize(keys,0); ArrayResize(vols,0);
   for(int i=0;i<n;i++)
     {
      int m=IP_NYMinute(bars[i].time);
      if(m<570 || m>=600) continue;
      int key=IP_NYDateKey(bars[i].time);
      if(key==today_key)
        {
         if(or_open==0.0) or_open=bars[i].open;
         orh=MathMax(orh,bars[i].high); orl=MathMin(orl,bars[i].low);
         today_vol+=(double)bars[i].tick_volume;
         continue;
        }
      if(key>today_key) continue;
      if(days==0 || keys[days-1]!=key)
        {
         ArrayResize(keys,days+1); ArrayResize(vols,days+1);
         keys[days]=key; vols[days]=0.0; days++;
        }
      vols[days-1]+=(double)bars[i].tick_volume;
     }
   if(or_open==0.0 || orh<=orl || days<InpRVDays) return false;
   double sum=0.0;
   for(int d=days-InpRVDays;d<days;d++) sum+=vols[d];
   avg_vol=sum/InpRVDays;
   return avg_vol>0.0;
}

ulong IP_Hash(const int day_key,const int i)
{
   ulong x=(ulong)day_key*1000003+(ulong)(i+1)*2654435761;
   x^=(x>>13); x*=0x5bd1e995; x^=(x>>15);
   return x;
}

void IP_RankDay(const int today_key)
{
   int n=ArraySize(g_sym);
   double score[];
   ArrayResize(score,n);
   for(int i=0;i<n;i++)
     {
      g_active[i]=false; g_done[i]=false; score[i]=-1.0; g_rv[i]=0.0; g_gap[i]=0.0;
      double orh,orl,op,tv,av;
      if(!IP_OpeningStats(g_sym[i],today_key,orh,orl,op,tv,av)) continue;
      double atr=AAA_BufferValue(g_atr[i],0,1);
      double prev=iClose(g_sym[i],PERIOD_D1,1);
      if(atr==EMPTY_VALUE || atr<=0.0 || prev<=0.0) continue;
      if(orh-orl>InpMaxORATR*atr) continue;
      g_orh[i]=orh; g_orl[i]=orl; g_rv[i]=tv/av; g_gap[i]=(op-prev)/atr;
      if(InpUniverseMode==IP_UNIVERSE_IN_PLAY)
        { if(g_rv[i]>=InpMinRelVol) score[i]=g_rv[i]; }
      else
         score[i]=(double)(IP_Hash(today_key,i)%1000000);
     }
   for(int k=0;k<InpTopN;k++)
     {
      int best=-1;
      for(int i=0;i<n;i++) if(!g_active[i] && score[i]>=0.0 && (best<0 || score[i]>score[best])) best=i;
      if(best<0) break;
      g_active[best]=true;
      PrintFormat("IPORB %d pick %s RV %.2f gap %.2f ATR OR %.5f-%.5f",today_key,g_sym[best],g_rv[best],g_gap[best],g_orl[best],g_orh[best]);
     }
}

bool IP_HasPosition(const string sym)
{
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong t=PositionGetTicket(i);
      if(t!=0 && PositionGetString(POSITION_SYMBOL)==sym && PositionGetInteger(POSITION_MAGIC)==InpMagic) return true;
     }
   return false;
}

void IP_CloseAll()
{
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong t=PositionGetTicket(i);
      if(t==0 || PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);
      AAA_Trade.PositionClose(t);
     }
}

bool IP_Send(const string sym,const int direction,const double stop,const string comment)
{
   MqlTick tick;
   if(!SymbolInfoTick(sym,tick)) return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double sl=AAA_Price(sym,stop);
   double risk=direction*(entry-sl);
   if(risk<=0.0 || risk<3.0*(tick.ask-tick.bid)) return false;
   double tp=(InpRewardRisk>0.0 ? AAA_Price(sym,entry+direction*risk*InpRewardRisk) : 0.0);
   double lots=AAA_LotsForRisk(sym,(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL),entry,sl,InpRiskPercent);
   if(lots<=0.0) { PrintFormat("IPORB skip %s: lot size 0",sym); return false; }
   AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);
   AAA_Trade.SetTypeFillingBySymbol(sym);
   AAA_Trade.SetDeviationInPoints(50);
   return (direction>0 ? AAA_Trade.Buy(lots,sym,0.0,sl,tp,comment) : AAA_Trade.Sell(lots,sym,0.0,sl,tp,comment));
}

void OnTick()
{
   if(!InpEnableTrading || !AAA_NewBar(_Symbol,PERIOD_M5,g_ip_last_bar)) return;
   datetime now=TimeCurrent();
   MqlDateTime d; TimeToStruct(AAA_ToNewYork(now),d);
   if(d.day_of_week==0 || d.day_of_week==6) return;
   int ny=IP_NYMinute(now), utc=IP_UTCMinute(now), key=IP_NYDateKey(now);
   if(ny>=InpFlatMinuteNY || utc>=InpFlatMinuteUTC) { IP_CloseAll(); return; }
   if(key!=g_day_key) { g_day_key=key; g_ranked=false; }
   if(ny<600) return;
   if(!g_ranked) { IP_RankDay(key); g_ranked=true; }
   if(ny>InpEntryEndMinuteNY || utc>=InpFlatMinuteUTC-60) return;
   for(int i=0;i<ArraySize(g_sym);i++)
     {
      if(!g_active[i] || g_done[i] || IP_HasPosition(g_sym[i])) continue;
      MqlRates b[];
      ArraySetAsSeries(b,true);
      if(CopyRates(g_sym[i],PERIOD_M5,1,1,b)!=1) continue;
      if(IP_NYDateKey(b[0].time)!=key || IP_NYMinute(b[0].time)<600) continue;
      int direction=(b[0].close>g_orh[i] ? 1 : (b[0].close<g_orl[i] ? -1 : 0));
      if(direction==0) continue;
      int gap_sign=(g_gap[i]>0.0 ? 1 : (g_gap[i]<0.0 ? -1 : 0));
      g_done[i]=true;   // first break decides the day for this symbol
      if(InpDirectionMode==IP_DIR_WITH_GAP && direction!=gap_sign) continue;
      if(InpDirectionMode==IP_DIR_AGAINST_GAP && direction!=-gap_sign) continue;
      double stop=(direction>0 ? g_orl[i] : g_orh[i]);
      IP_Send(g_sym[i],direction,stop,StringFormat("IPORB %s RV%.1f",(direction>0 ? "long" : "short"),g_rv[i]));
     }
}

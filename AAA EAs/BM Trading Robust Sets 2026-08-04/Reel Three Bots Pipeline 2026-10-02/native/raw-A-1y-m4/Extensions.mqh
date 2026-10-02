// Included inside RRModule. All indicator reads are completed-bar reads.
int ix,atr14H,adxH,emaH,h4H,d1H,ema20H,dayEntries,priceSkips,closedSkips,partialSkips,cancelFails,partialCount,trailCount;
datetime featureDay,channelBar,confirmBar,lastManageClose,rangeWatchBar;
double channelHi,channelLo,confirmSL,confirmTP,confirmLevel,rangeHi,rangeLo,pendingBudget;
int confirmSide,lastRuleSide;bool confirming,rangeWatching;
struct Initial{ulong id;double sl,tp,entry,risk,budget,volume,best;bool partial;};
Initial initial[];
double P(int k){return Cases[ix][k];}
ENUM_TIMEFRAMES Frame(int v){if(v==1)return PERIOD_M1;if(v==3)return PERIOD_M3;if(v==5)return PERIOD_M5;if(v==15)return PERIOD_M15;if(v==30)return PERIOD_M30;if(v==60)return PERIOD_H1;if(v==240)return PERIOD_H4;return PERIOD_H1;}
ENUM_TIMEFRAMES TF(){return Frame((int)P(1));}
ENUM_TIMEFRAMES CTF(){return Frame((int)P(27));}
ENUM_TIMEFRAMES ATF(){return BOT==3?CTF():TF();}
double Buf(int h,int b=0,int shift=1){double a[];return h!=INVALID_HANDLE&&CopyBuffer(h,b,shift,1,a)==1?a[0]:0;}
double ATR(){return Buf(atr14H);}
int RandSide(datetime t){uint x=(uint)(t/60)+Seed+(uint)BOT;x^=x>>16;x*=0x7feb352d;x^=x>>15;x*=0x846ca68b;x^=x>>16;return (x&1)!=0?1:-1;}
int SundayNY(int y,int m,int n){MqlDateTime d={};d.year=y;d.mon=m;d.day=1;TimeToStruct(StructToTime(d),d);return 1+(7-d.day_of_week)%7+7*(n-1);}
datetime NewYork(datetime t){MqlDateTime d;TimeToStruct(t,d);int y=d.year;d.mon=3;d.day=SundayNY(y,3,2);d.hour=7;d.min=d.sec=0;datetime a=StructToTime(d);d.mon=11;d.day=SundayNY(y,11,1);d.hour=6;datetime b=StructToTime(d);return t+(t>=a&&t<b?-4:-5)*3600;}
bool SessionOK(datetime t){int k=(int)P(11),u=(int)(t%86400),n=(int)(NewYork(t)%86400);if(k==1)return u<28800;if(k==2)return u>=25200&&u<57600;if(k==3)return n>=34200&&n<57600;if(k==4)return u>=43200&&u<57600;if(k==5)return n>=34200&&n<39600;return true;}
bool CalendarOK(datetime t){MqlDateTime d;TimeToStruct(t,d);int k=(int)P(14);return !((k==1||k==3)&&d.day_of_week==1)&&!((k==2||k==3)&&d.day_of_week==5);}
bool FilterOK(int side){int k=(int)P(13);double e=0,c=iClose(m_symbol,ATF(),1);if(k==0)return true;
 if(k==1){e=Buf(emaH);return e>0&&side*(c-e)>0&&side*(e-Buf(emaH,0,2))>0;}
 if(k==2){e=Buf(h4H);return e>0&&side*(iClose(m_symbol,PERIOD_H4,1)-e)>0;}
 if(k==3)return Buf(adxH)>0&&Buf(adxH)>=P(31);
 if(k==4)return side*(Buf(adxH,1)-Buf(adxH,2))>0;
 if(k==5){double a[];int n=CopyBuffer(atr14H,0,1,100,a);if(n!=100)return false;int less=0;for(int j=0;j<99;j++)if(a[j]<a[99])less++;double pct=100.0*less/99;return pct>=P(32)&&pct<=P(33);}
 if(k==6){MqlTick q;return SymbolInfoTick(m_symbol,q)&&ATR()>0&&q.ask-q.bid<=.1*ATR();}
 if(k==7){e=Buf(d1H);return e>0&&side*(iClose(m_symbol,PERIOD_D1,1)-e)>0;}
 if(k==8)return Buf(adxH)>=P(31)&&side*(Buf(adxH,1)-Buf(adxH,2))>0;return false;
}
bool Admit(int side){datetime t=TimeCurrent();int d=(int)P(12);return t>=InpTradeFrom&&SessionOK(t)&&CalendarOK(t)&&!(d==1&&side<0)&&!(d==2&&side>0)&&(P(15)<=0||dayEntries<(int)P(15))&&FilterOK(side);}
bool HasOrder(){for(int j=OrdersTotal()-1;j>=0;j--){ulong t=OrderGetTicket(j);if(t&&OrderGetInteger(ORDER_MAGIC)==InpMagic&&OrderGetString(ORDER_SYMBOL)==m_symbol)return true;}return false;}
void Features(int caseIndex){ix=caseIndex;atr14H=adxH=emaH=h4H=d1H=ema20H=INVALID_HANDLE;featureDay=channelBar=confirmBar=rangeWatchBar=lastManageClose=0;
 dayEntries=priceSkips=closedSkips=partialSkips=cancelFails=partialCount=trailCount=0;ArrayResize(initial,0);channelHi=channelLo=confirmSL=confirmTP=confirmLevel=rangeHi=rangeLo=pendingBudget=0;confirmSide=lastRuleSide=0;confirming=rangeWatching=false;
 atr14H=iATR(m_symbol,ATF(),14);int f=(int)P(13);if(f==1)emaH=iMA(m_symbol,ATF(),200,0,MODE_EMA,PRICE_CLOSE);
 if(f==2)h4H=iMA(m_symbol,PERIOD_H4,50,0,MODE_EMA,PRICE_CLOSE);if(f==3||f==4||f==8)adxH=iADX(m_symbol,ATF(),14);
 if(f==7)d1H=iMA(m_symbol,PERIOD_D1,50,0,MODE_EMA,PRICE_CLOSE);if((int)P(7)==4)ema20H=iMA(m_symbol,ATF(),20,0,MODE_EMA,PRICE_CLOSE);
}
void ReleaseFeatures(){if(atr14H!=INVALID_HANDLE)IndicatorRelease(atr14H);if(adxH!=INVALID_HANDLE)IndicatorRelease(adxH);if(emaH!=INVALID_HANDLE)IndicatorRelease(emaH);if(h4H!=INVALID_HANDLE)IndicatorRelease(h4H);if(d1H!=INVALID_HANDLE)IndicatorRelease(d1H);if(ema20H!=INVALID_HANDLE)IndicatorRelease(ema20H);}
void Capture(){for(int j=PositionsTotal()-1;j>=0;j--){ulong t=PositionGetTicket(j);if(!t||PositionGetInteger(POSITION_MAGIC)!=InpMagic||PositionGetString(POSITION_SYMBOL)!=m_symbol)continue;
 ulong id=(ulong)PositionGetInteger(POSITION_IDENTIFIER);bool found=false;for(int k=0;k<ArraySize(initial);k++)if(initial[k].id==id){found=true;break;}if(found)continue;
 int k=ArraySize(initial);ArrayResize(initial,k+1);ZeroMemory(initial[k]);initial[k].id=id;initial[k].sl=PositionGetDouble(POSITION_SL);initial[k].tp=PositionGetDouble(POSITION_TP);initial[k].entry=PositionGetDouble(POSITION_PRICE_OPEN);initial[k].volume=PositionGetDouble(POSITION_VOLUME);initial[k].best=initial[k].entry;initial[k].budget=pendingBudget>0?pendingBudget:InpFixedRiskUSD;
 double profit=0;int side=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1;if(OrderCalcProfit(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,m_symbol,initial[k].volume,initial[k].entry,initial[k].sl,profit))initial[k].risk=-profit;
 }}
bool StopsFor(int side,double entry,double &sl,double &tp){int kind=(int)P(4);if(kind==0)return side*(entry-sl)>0;double dist=0;
 if(kind==1)dist=entry*P(5)/100;if(kind==2)dist=ATR()*P(5);
 if(kind==3||kind==4){int n=kind==3?5:20;MqlRates r[];if(CopyRates(m_symbol,ATF(),1,n,r)!=n)return false;double extreme=side>0?DBL_MAX:-DBL_MAX;for(int j=0;j<n;j++)extreme=side>0?MathMin(extreme,r[j].low):MathMax(extreme,r[j].high);sl=Price(extreme-side*.1*ATR());dist=side*(entry-sl);}
 else sl=Price(entry-side*dist);if(dist<=0)return false;tp=P(6)>0?Price(entry+side*(entry-sl)*side*P(6)):0;return true;
}
bool Execute(int side,double sl,double tp,string why,bool confirmed=false){if(!Admit(side)||CountPositions()>=(int)P(25)||HasOrder())return false;
 MqlTick q;if(!SymbolInfoTick(m_symbol,q))return false;int mode=(int)P(2);
 if(mode==1&&!confirmed){confirming=true;confirmSide=side;confirmSL=sl;confirmTP=tp;confirmBar=iTime(m_symbol,TF(),0);confirmLevel=side>0?iHigh(m_symbol,TF(),1):iLow(m_symbol,TF(),1);return false;}
 double entry=side>0?q.ask:q.bid;bool pending=mode>=2&&!confirmed;if(pending)entry=Price(entry+side*(mode==3?1:-1)*P(3)*ATR());
 if(!StopsFor(side,entry,sl,tp))return false;double v=Lots(side,entry,sl);if(v<=0)return false;
 double gap=MathMax(tickSize,SymbolInfoInteger(m_symbol,SYMBOL_TRADE_STOPS_LEVEL)*SymbolInfoDouble(m_symbol,SYMBOL_POINT));
 if(pending){double ref=side>0?q.ask:q.bid;if((mode==3?side*(entry-ref):side*(ref-entry))<gap||side*(entry-sl)<gap||(tp>0&&side*(tp-entry)<gap))return false;}
 else if(!ValidStops(side,sl,tp,q))return false;
 pendingBudget=InpFixedRiskUSD;bool ok=false;
 if(!pending)ok=side>0?trade.Buy(v,m_symbol,0,sl,tp,why):trade.Sell(v,m_symbol,0,sl,tp,why);
 else{datetime expiry=TimeCurrent()+4*PeriodSeconds(TF());if(mode==3)ok=side>0?trade.BuyStop(v,entry,m_symbol,sl,tp,ORDER_TIME_SPECIFIED,expiry,why):trade.SellStop(v,entry,m_symbol,sl,tp,ORDER_TIME_SPECIFIED,expiry,why);else ok=side>0?trade.BuyLimit(v,entry,m_symbol,sl,tp,ORDER_TIME_SPECIFIED,expiry,why):trade.SellLimit(v,entry,m_symbol,sl,tp,ORDER_TIME_SPECIFIED,expiry,why);}
 uint code=trade.ResultRetcode();if(!ok||(code!=TRADE_RETCODE_DONE&&code!=TRADE_RETCODE_PLACED)){if(code==10018)closedSkips++;else if(code==10015)priceSkips++;else{entryFails++;PrintFormat("RP_ENTRY_FAIL module=%d code=%u",BOT,code);}return false;}Capture();return true;
}
void Manage(){datetime now=TimeCurrent(),day=now-now%86400;if(day!=featureDay){featureDay=day;dayEntries=0;}
 Capture();if(confirming&&iTime(m_symbol,TF(),0)>confirmBar){MqlRates r[];if(CopyRates(m_symbol,TF(),1,1,r)==1){confirming=false;if(confirmSide*(r[0].close-confirmLevel)>0)Execute(confirmSide,confirmSL,confirmTP,"RP Confirm",true);}}
 if(rangeWatching&&iTime(m_symbol,TF(),0)!=rangeWatchBar){rangeWatchBar=iTime(m_symbol,TF(),0);double c=iClose(m_symbol,TF(),1);int side=c>rangeHi?1:(c<rangeLo?-1:0);if(side){if(Control)side=RandSide(now);double sl=side>0?rangeLo:rangeHi;double px=side>0?rangeHi:rangeLo;double tp=P(6)>0?Price(px+side*MathAbs(px-sl)*P(6)):0;if(Execute(side,sl,tp,"RP Range Confirm",true))rangeWatching=false;}}
 MqlDateTime dt;TimeToStruct(now,dt);bool flat=false;int fk=(int)P(17);
 if(fk){for(uint k=0;k<20;k++){datetime a,b;if(!SymbolInfoSessionTrade(m_symbol,(ENUM_DAY_OF_WEEK)dt.day_of_week,k,a,b))break;int hi=(int)((long)b%86400);if(hi==0)hi=86400;if((now%86400)>=hi-900&&(now%86400)<hi&&(fk==1||dt.day_of_week==5))flat=true;}}
 for(int j=PositionsTotal()-1;j>=0;j--){ulong t=PositionGetTicket(j);if(!t||PositionGetInteger(POSITION_MAGIC)!=InpMagic||PositionGetString(POSITION_SYMBOL)!=m_symbol)continue;
 int side=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1;ulong id=(ulong)PositionGetInteger(POSITION_IDENTIFIER);int k=-1;for(int z=0;z<ArraySize(initial);z++)if(initial[z].id==id){k=z;break;}if(k<0)continue;
 if(flat||((int)P(10)==1&&P(16)>0&&now-(datetime)PositionGetInteger(POSITION_TIME)>=P(16)*PeriodSeconds(TF()))){if(now-lastManageClose>=30){lastManageClose=now;if(!trade.PositionClose(t)||trade.ResultRetcode()!=TRADE_RETCODE_DONE){if(trade.ResultRetcode()==10018)closedSkips++;else closeFails++;}}continue;}
 MqlTick q;if(!SymbolInfoTick(m_symbol,q))continue;double px=side>0?q.bid:q.ask,entry=initial[k].entry,R=MathAbs(entry-initial[k].sl),sl=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP);if(R<=0)continue;
 initial[k].best=side>0?MathMax(initial[k].best,px):MathMin(initial[k].best,px);
 if((int)P(10)==3&&!initial[k].partial&&side*(px-entry)>=R){double vol=PositionGetDouble(POSITION_VOLUME),part=NormalizeDouble(MathFloor((vol*.5+1e-12)/lotStep)*lotStep,8);if(part>=minLot&&vol-part>=minLot){if(trade.PositionClosePartial(t,part)&&trade.ResultRetcode()==TRADE_RETCODE_DONE){initial[k].partial=true;partialCount++;}else if(trade.ResultRetcode()==10018)closedSkips++;else closeFails++;}else{initial[k].partial=true;partialSkips++;}}
 int tr=(int)P(7);if(tr==0||tr==9||side*(initial[k].best-entry)<P(8)*R)continue;double want=0;
 if(tr==1)want=entry;if(tr==2)want=px-side*P(9)*ATR();if(tr==3)want=px-side*entry*P(9)/100;if(tr==4)want=Buf(ema20H);
 if(tr==5){MqlRates r[];if(CopyRates(m_symbol,ATF(),1,5,r)!=5)continue;want=side>0?DBL_MAX:-DBL_MAX;for(int a=0;a<5;a++)want=side>0?MathMin(want,r[a].low):MathMax(want,r[a].high);}
 if(tr==6)want=initial[k].best-side*3*ATR();if(tr==7){double gain=MathFloor(side*(initial[k].best-entry)/(.2*R))*.2*R;want=entry+side*gain*.5;}
 want=Price(want);if(want<=0||side*(want-sl)<=tickSize/2||!ValidStops(side,want,tp,q))continue;bool changed=trade.PositionModify(t,want,tp);if(changed&&trade.ResultRetcode()==TRADE_RETCODE_DONE)trailCount++;else if(trade.ResultRetcode()!=TRADE_RETCODE_NO_CHANGES){if(trade.ResultRetcode()==10018)closedSkips++;else modifyFails++;}
 }
}
void RangeFeature(datetime now){datetime rt=ReferenceTime(now),day=rt-rt%86400;int sec=(int)(rt-day);MqlDateTime d;TimeToStruct(rt,d);
 if(day!=lastDay){lastDay=day;dailyDone=false;rangeWatching=false;}
 ulong t;if(OwnPos(t)){dailyDone=true;CancelOrders();if(CountPositions()>1)ocoRaces++;}
 int flat=(int)(P(24)*3600),end=(int)(P(23)*3600);
 if((flat>0&&sec>=flat)||sec>=23*3600){if(flat>0)Flat();else CancelOrders();dailyDone=true;rangeWatching=false;return;}
 if(P(26)>0&&dailyDone&&!OwnPos(t)&&!HasOrder()&&dayEntries>0&&dayEntries<(int)P(15))dailyDone=false;
 if(now<InpTradeFrom||d.day_of_week==0||d.day_of_week==6||dailyDone||sec<end)return;
 if(dayEntries==0&&sec>=end+300){dailyDone=true;expiredSkips++;return;}
 int off=RefOffset(now-InpBrokerUtcOffsetHours*3600)-InpBrokerUtcOffsetHours;
 datetime start=day+(int)(P(22)*3600)-off*3600,finish=day+end-off*3600;MqlRates r[];int n=CopyRates(m_symbol,TF(),start,finish-1,r);if(n<=0){dataSkips++;return;}
 double hi=-DBL_MAX,lo=DBL_MAX;for(int i=0;i<n;i++){hi=MathMax(hi,r[i].high);lo=MathMin(lo,r[i].low);}hi=Price(hi);lo=Price(lo);dailyDone=true;candidates++;
 MqlTick q;if(!SymbolInfoTick(m_symbol,q)||hi<=lo)return;double gap=MathMax(tickSize,SymbolInfoInteger(m_symbol,SYMBOL_TRADE_STOPS_LEVEL)*SymbolInfoDouble(m_symbol,SYMBOL_POINT));
 if(hi-q.ask<gap||q.bid-lo<gap)return;
 if(Control){int side=RandSide(now);double px=side>0?q.ask:q.bid,sl=Price(px-side*(hi-lo)),tp=P(6)>0?Price(px+side*(hi-lo)*P(6)):0;Execute(side,sl,tp,"RP Range Control",true);return;}
 if((int)P(2)==1){rangeWatching=true;rangeHi=hi;rangeLo=lo;return;}
 if((int)P(2)>=2){int side=(q.bid+q.ask)/2>(hi+lo)/2?1:-1;double sl=side>0?lo:hi,tp=P(6)>0?Price((side>0?hi:lo)+side*(hi-lo)*P(6)):0;Execute(side,sl,tp,"RP Range Offset");return;}
 double bsl=Price(hi-(hi-lo)*P(5)),ssl=Price(lo+(hi-lo)*P(5)),btp=P(6)>0?Price(hi+(hi-bsl)*P(6)):0,stp=P(6)>0?Price(lo-(ssl-lo)*P(6)):0;
 if(!StopsFor(1,hi,bsl,btp)||!StopsFor(-1,lo,ssl,stp))return;double bv=Lots(1,hi,bsl),sv=Lots(-1,lo,ssl);if(bv<=0||sv<=0)return;
 datetime expiry=day+(flat>0?flat:18*3600)-off*3600;pendingBudget=InpFixedRiskUSD;
 bool buy=Admit(1),sell=Admit(-1),b=false,s=false;if(!buy&&!sell)return;
 if(buy){b=trade.BuyStop(bv,hi,m_symbol,bsl,btp,ORDER_TIME_SPECIFIED,expiry,"RR Range Buy")&&(trade.ResultRetcode()==TRADE_RETCODE_PLACED||trade.ResultRetcode()==TRADE_RETCODE_DONE);if(!b){if(trade.ResultRetcode()==10015)priceSkips++;else if(trade.ResultRetcode()==10018)closedSkips++;else entryFails++;return;}}
 if(sell)s=trade.SellStop(sv,lo,m_symbol,ssl,stp,ORDER_TIME_SPECIFIED,expiry,"RR Range Sell")&&(trade.ResultRetcode()==TRADE_RETCODE_PLACED||trade.ResultRetcode()==TRADE_RETCODE_DONE);
 if(sell&&!s){if(trade.ResultRetcode()==10015)priceSkips++;else if(trade.ResultRetcode()==10018)closedSkips++;else entryFails++;CancelOrders();}
}
void DonFeature(datetime now){datetime current=iTime(m_symbol,TF(),0);if(current<=0||current==lastBar)return;
 datetime cb=iTime(m_symbol,CTF(),0);int count=(int)P(19);MqlRates h[],m[];if(cb!=channelBar){if(CopyRates(m_symbol,CTF(),1,count,h)!=count){dataSkips++;return;}channelHi=-DBL_MAX;channelLo=DBL_MAX;for(int j=0;j<count;j++){channelHi=MathMax(channelHi,h[j].high);channelLo=MathMin(channelLo,h[j].low);}channelBar=cb;}
 if(CopyRates(m_symbol,TF(),1,2,m)!=2){dataSkips++;return;}lastBar=current;double mid=(channelHi+channelLo)/2;
 if(m[0].close>=mid&&m[1].close<mid)buyArmed=true;if(m[0].close<=mid&&m[1].close>mid)sellArmed=true;
 if(now<InpTradeFrom||now-current>=PeriodSeconds(TF()))return;int raw=buyArmed&&m[1].close>channelHi?1:(sellArmed&&m[1].close<channelLo?-1:0);if(!raw)return;
 candidates++;if(CountPositions()>=(int)P(25)){existingSkips++;return;}int side=Control?RandSide(now):raw;MqlTick q;if(!SymbolInfoTick(m_symbol,q))return;double entry=side>0?q.ask:q.bid;
 lastRuleSide=raw;if(Execute(side,Price(entry*(1-side*P(5)/100)),P(6)>0?Price(entry*(1+side*P(5)*P(6)/100)):0,"RR Donchian")){if(raw>0)buyArmed=false;else sellArmed=false;}
}

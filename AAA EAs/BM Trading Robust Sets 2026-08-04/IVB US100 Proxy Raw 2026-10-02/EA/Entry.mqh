void OnTick(){datetime now=TimeCurrent();ManageClose(now);Trace();if(now<InpTradeFrom)return;
 datetime bar=iTime(_Symbol,PERIOD_M5,0);if(bar<=0||bar==lastBar)return;lastBar=bar;
 MqlDateTime ny;TimeToStruct(NewYork(now),ny);if(ny.day_of_week<1||ny.day_of_week>5)return;
 int key=DateKey(now);if(key!=dayKey){dayKey=key;rangeHigh=rangeLow=0;}
 int minute=MinuteNY(now);if(minute<545||minute>=840||FlatDue(now)||usedDay==dayKey)return;
 if(rangeHigh==0){datetime anchor=now-(NewYork(now)-(BuildTime(ny.year,ny.mon,ny.day,0)+510*60));MqlRates rb[];
  if(CopyRates(_Symbol,PERIOD_M5,anchor,anchor+5*300,rb)!=6)return;
  for(int i=0;i<6;i++)if(rb[i].time!=anchor+i*300||rb[i].time+300>now)return;
  rangeHigh=rb[0].high;rangeLow=rb[0].low;for(int i=1;i<6;i++){rangeHigh=MathMax(rangeHigh,rb[i].high);rangeLow=MathMin(rangeLow,rb[i].low);}ranges++;}
 MqlRates r[];if(CopyRates(_Symbol,PERIOD_M5,1,1,r)!=1||r[0].time+300!=bar||r[0].close<=rangeHigh)return;
 int shift=iBarShift(_Symbol,PERIOD_M1,r[0].time-1,false);if(shift<0)return;double seed=iClose(_Symbol,PERIOD_M1,shift);if(seed<=0)return;
 MqlTick qt[];int count=CopyTicksRange(_Symbol,qt,COPY_TICKS_INFO,(ulong)r[0].time*1000,(ulong)bar*1000-1);if(count<=0){tickErrors++;return;}
 long up=0,down=0;double last=seed;for(int i=0;i<count;i++){if(qt[i].bid<=0)continue;if(qt[i].bid>last)up++;else if(qt[i].bid<last)down++;last=qt[i].bid;}
 if(up-down<200)return;usedDay=dayKey;signals++;
 ulong ticket;if(OwnPosition(ticket)){skips++;return;}MqlTick q;if(!SymbolInfoTick(_Symbol,q)){skips++;return;}
 double entry=q.ask,stop=Price(rangeLow),dist=entry-stop,tp=Price(entry+dist);
 double minimum=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;int until=0;
 if(dist<=0||q.bid-stop<=minimum||tp-q.bid<=minimum||!Session(now,until)){skips++;return;}
 double budget=AccountInfoDouble(ACCOUNT_BALANCE)*InpRiskPercent/100,lot=Lots(ORDER_TYPE_BUY,entry,stop,budget);if(lot<=0){skips++;return;}
 double quoted=0;if(!OrderCalcProfit(ORDER_TYPE_BUY,_Symbol,lot,entry,stop,quoted)){skips++;return;}
 bool ok=trade.Buy(lot,_Symbol,0,stop,tp,"IVB quote delta proxy");
 FileWrite(audit,(long)now,(long)r[0].time,1,rangeHigh,rangeLow,r[0].close,entry,stop,tp,budget,lot,MathAbs(quoted),trade.ResultRetcode(),seed,up,down);
 for(int i=0;i<count;i++)if(qt[i].bid>0)FileWrite(ticksFile,(long)r[0].time,qt[i].time_msc,qt[i].bid);
 if(ok&&trade.ResultRetcode()==TRADE_RETCODE_DONE){ulong deal=trade.ResultDeal();if(HistoryDealSelect(deal)){int ix=ArraySize(initial);ArrayResize(initial,ix+1);initial[ix].id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);initial[ix].sl=stop;initial[ix].tp=tp;initial[ix].budget=budget;double p=HistoryDealGetDouble(deal,DEAL_PRICE),v=HistoryDealGetDouble(deal,DEAL_VOLUME),risk=0;if(OrderCalcProfit(ORDER_TYPE_BUY,_Symbol,v,p,stop,risk))initial[ix].risk=MathAbs(risk);}}
 else entryFails++;}

#property strict
#property version "1.00"
#property description "Tester-only BTC history exporter. No trading calls. Packed little-endian 52-byte records."
input datetime InpExportFrom=D'2018.01.01 00:00';
input datetime InpExportTo=D'2026.10.17 00:00';
input string InpTag="";
bool exported=false;
string Folder(){return "BTCWeekendPipeline20261017\\"+InpTag;}
bool ValidTag(){return StringLen(InpTag)>0 && StringFind(InpTag,"..")<0 && StringFind(InpTag,"\\")<0 && StringFind(InpTag,"/")<0;}
int OnInit()
{
 if(!MQLInfoInteger(MQL_TESTER) || _Symbol!="BTCUSD" || !ValidTag() || InpExportTo<=InpExportFrom)return INIT_PARAMETERS_INCORRECT;
 FolderCreate("BTCWeekendPipeline20261017",FILE_COMMON);FolderCreate(Folder(),FILE_COMMON);
 return INIT_SUCCEEDED;
}
void OnTick(){}
datetime NextMonth(datetime at)
{
 MqlDateTime d;TimeToStruct(at,d);d.day=1;d.hour=0;d.min=0;d.sec=0;
 d.mon++;if(d.mon>12){d.mon=1;d.year++;}return StructToTime(d);
}
bool ExportOne(ENUM_TIMEFRAMES tf,string label,int status)
{
 int file=FileOpen(Folder()+"\\BTCUSD-"+label+".bin",FILE_WRITE|FILE_BIN|FILE_COMMON);
 if(file==INVALID_HANDLE){PrintFormat("BW_EXPORT_ERROR open %s %d",label,GetLastError());return false;}
 long rows=0;datetime first=0,last=0,previous=0;int failed=0,empty=0;
 datetime effective_to=(datetime)MathMin((double)InpExportTo,(double)(TimeCurrent()+1));
 for(datetime start=InpExportFrom;start<effective_to;)
 {
  datetime until=(datetime)MathMin((double)NextMonth(start),(double)effective_to);
  MqlRates bars[];ResetLastError();int n=CopyRates(_Symbol,tf,start,until-1,bars);
  for(int retry=0;retry<10 && n<0;retry++){Sleep(50);ResetLastError();n=CopyRates(_Symbol,tf,start,until-1,bars);}
  if(n<0){failed++;PrintFormat("BW_EXPORT_COPY_ERROR %s %I64d %d",label,(long)start,GetLastError());}
  else if(n==0)empty++;
  for(int i=0;i<n;i++)
  {
   if(bars[i].time<InpExportFrom || bars[i].time>=InpExportTo || bars[i].time>=effective_to || bars[i].time<=previous)continue;
   if(rows==0)first=bars[i].time;last=bars[i].time;previous=last;
   FileWriteLong(file,(long)bars[i].time);
   FileWriteDouble(file,bars[i].open);FileWriteDouble(file,bars[i].high);FileWriteDouble(file,bars[i].low);FileWriteDouble(file,bars[i].close);
   FileWriteLong(file,(long)bars[i].tick_volume);FileWriteInteger(file,(int)bars[i].spread,INT_VALUE);rows++;
  }
  start=until;
 }
 FileClose(file);
 FileWrite(status,label,rows,(long)InpExportFrom,(long)InpExportTo,(long)first,(long)last,(long)TimeCurrent(),empty,failed,52);
 PrintFormat("BW_EXPORT_DONE tf=%s rows=%I64d first=%I64d last=%I64d failures=%d",label,rows,(long)first,(long)last,failed);
 return rows>0 && failed==0;
}
double OnTester()
{
 if(!MQLInfoInteger(MQL_TESTER) || exported)return 0;exported=true;
 int status=FileOpen(Folder()+"\\export-status.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(status==INVALID_HANDLE)return 0;
 FileWrite(status,"timeframe","rows","requested_from","requested_to_exclusive","actual_first","actual_last","last_simulated_epoch","empty_chunks","failed_chunks","record_bytes");
 bool ok=ExportOne(PERIOD_M1,"M1",status);ok=ExportOne(PERIOD_M5,"M5",status)&&ok;ok=ExportOne(PERIOD_H1,"H1",status)&&ok;ok=ExportOne(PERIOD_D1,"D1",status)&&ok;FileClose(status);
 int spec=FileOpen(Folder()+"\\specification.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(spec==INVALID_HANDLE)return 0;
 FileWrite(spec,"symbol","point","digits","tick_size","tick_value_profit","tick_value_loss","contract_size","volume_min","volume_step","volume_max","swap_mode","swap_long","swap_short","swap_rollover3days","stops_level","freeze_level","profit_currency","margin_currency");
 FileWrite(spec,_Symbol,_Point,_Digits,SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE_PROFIT),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE_LOSS),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),SymbolInfoInteger(_Symbol,SYMBOL_SWAP_MODE),SymbolInfoDouble(_Symbol,SYMBOL_SWAP_LONG),SymbolInfoDouble(_Symbol,SYMBOL_SWAP_SHORT),SymbolInfoInteger(_Symbol,SYMBOL_SWAP_ROLLOVER3DAYS),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL),SymbolInfoString(_Symbol,SYMBOL_CURRENCY_PROFIT),SymbolInfoString(_Symbol,SYMBOL_CURRENCY_MARGIN));FileClose(spec);
 if(ok)Print("BW_EXPORT_COMPLETE");else Print("BW_EXPORT_INCOMPLETE");return ok?1:0;
}

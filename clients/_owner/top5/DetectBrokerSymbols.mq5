#property strict
#property description "Read-only broker symbol discovery for the Calyx installer. No orders, no DLLs."
string Clean(string s){StringReplace(s,"\t"," ");StringReplace(s,"\r"," ");StringReplace(s,"\n"," ");StringReplace(s,"\"","'");return s;}
string discovery_stem="";
void DiscoveryError(string message){
 Print("CALYX_DISCOVERY_ERROR: ",message);
 if(discovery_stem=="")return;
 int f=FileOpen(discovery_stem+".error.tmp",FILE_WRITE|FILE_TXT|FILE_UNICODE);
 if(f!=INVALID_HANDLE){FileWriteString(f,message);FileClose(f);FileMove(discovery_stem+".error.tmp",0,discovery_stem+".error",FILE_REWRITE);}
}
// Errors go directly to the waiting BAT, never a modal dialog or generic timeout.
#define Alert DiscoveryError
void OnStart(){
 int request=FileOpen("CalyxTop5\\discovery-request.txt",FILE_READ|FILE_TXT|FILE_UNICODE);
 if(request==INVALID_HANDLE){Alert("Start Install Top 5.bat first, then run this detector when prompted.");return;}
 string nonce=FileReadString(request);long login=StringToInteger(FileReadString(request));string server=FileReadString(request);FileClose(request);
 if(StringLen(nonce)!=32){Alert("Invalid discovery request.");return;}
 for(int c=0;c<32;c++)if(StringFind("0123456789abcdef",StringSubstr(nonce,c,1))<0){Alert("Invalid request token.");return;}
 discovery_stem="CalyxTop5\\symbols-"+nonce;
 int started=FileOpen(discovery_stem+".started",FILE_WRITE|FILE_TXT|FILE_UNICODE);
 if(started!=INVALID_HANDLE){FileWriteString(started,"Detector running; waiting for a stable broker connection.");FileClose(started);}
 int stable=0;
 for(int attempt=0;attempt<120 && !IsStopped();attempt++){
  if(TerminalInfoInteger(TERMINAL_CONNECTED)){
   if(login!=AccountInfoInteger(ACCOUNT_LOGIN)||server!=AccountInfoString(ACCOUNT_SERVER)){Alert("Active account/server changed during setup. No client EAs attached. Keep the intended account selected and retry.");return;}
   stable++;
   if(stable>=6)break;
  }else stable=0;
  Sleep(500);
 }
 if(stable<6){Alert("Broker connection did not stabilize within 60 seconds. No client EAs attached.");return;}
 if(login!=AccountInfoInteger(ACCOUNT_LOGIN)||server!=AccountInfoString(ACCOUNT_SERVER)){Alert("Wrong active account/server. Return to the BAT and check your account confirmation.");return;}
 string stem="CalyxTop5\\symbols-"+nonce;
 int f=FileOpen(stem+".tmp",FILE_WRITE|FILE_CSV|FILE_UNICODE,'\t');
 if(f==INVALID_HANDLE){Alert("Cannot write the symbol snapshot. Check MT5 data-folder permissions.");return;}
 FileWrite(f,"schema","nonce","login","server","account_currency","margin_mode","generated_utc","name","description","path","base","profit","calc","trade","custom","expiry","contract","tick_size","volume_min","volume_step","selected");
 int total=SymbolsTotal(false),written=0;datetime generated=TimeGMT();
 for(int i=0;i<total;i++){
  string s=SymbolName(i,false);if(s=="")continue;
  uint bytes=FileWrite(f,"1",nonce,login,Clean(server),AccountInfoString(ACCOUNT_CURRENCY),AccountInfoInteger(ACCOUNT_MARGIN_MODE),(long)generated,
    Clean(s),Clean(SymbolInfoString(s,SYMBOL_DESCRIPTION)),Clean(SymbolInfoString(s,SYMBOL_PATH)),Clean(SymbolInfoString(s,SYMBOL_CURRENCY_BASE)),Clean(SymbolInfoString(s,SYMBOL_CURRENCY_PROFIT)),
    EnumToString((ENUM_SYMBOL_CALC_MODE)SymbolInfoInteger(s,SYMBOL_TRADE_CALC_MODE)),EnumToString((ENUM_SYMBOL_TRADE_MODE)SymbolInfoInteger(s,SYMBOL_TRADE_MODE)),
    SymbolInfoInteger(s,SYMBOL_CUSTOM),SymbolInfoInteger(s,SYMBOL_EXPIRATION_TIME),DoubleToString(SymbolInfoDouble(s,SYMBOL_TRADE_CONTRACT_SIZE),8),
    DoubleToString(SymbolInfoDouble(s,SYMBOL_TRADE_TICK_SIZE),10),DoubleToString(SymbolInfoDouble(s,SYMBOL_VOLUME_MIN),8),DoubleToString(SymbolInfoDouble(s,SYMBOL_VOLUME_STEP),8),SymbolInfoInteger(s,SYMBOL_SELECT));
  if(bytes==0){FileClose(f);Alert("Incomplete symbol export. Run detector again.");return;}written++;
 }
 FileFlush(f);FileClose(f);
 if(written==0||login!=AccountInfoInteger(ACCOUNT_LOGIN)||server!=AccountInfoString(ACCOUNT_SERVER)||!TerminalInfoInteger(TERMINAL_CONNECTED)){Alert("Account changed, disconnected, or empty symbol list. Run detector again.");return;}
 if(!FileMove(stem+".tmp",0,stem+".tsv",FILE_REWRITE)){Alert("Cannot finish symbol export. Run detector again.");return;}
 Print("CALYX_DISCOVERY_OK: ",written," broker symbols exported. No trading/account settings changed.");
 Print("Calyx: symbol detection complete. No trades were placed.");
}

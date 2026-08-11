#property strict
#property version   "1.000"
#property description "Safety-gated follower executor for the local AAA Copier pipe."

#include <AAA/CopierProtocol.mqh>

input bool   InpExecutionEnabled = false;
input bool   InpDemoAccountsOnly = true;
input string InpFollowerAccountId = "";
input string InpFollowerPipeName  = "";
input ulong  InpCopierMagic       = 99001001;
input int    InpPollMs             = 100;

int g_pipe = INVALID_HANDLE;

bool SafetyReady()
{
   if(!InpExecutionEnabled)
      return false;
   if(InpDemoAccountsOnly && AccountInfoInteger(ACCOUNT_TRADE_MODE) != ACCOUNT_TRADE_MODE_DEMO)
      return false;
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED))
      return false;
   return StringLen(InpFollowerAccountId) == 36 && StringLen(InpFollowerPipeName) > 0;
}

bool ConnectExecutor()
{
   if(g_pipe != INVALID_HANDLE)
      return true;
   return AAA_OpenPipe(InpFollowerPipeName, g_pipe);
}

void SendRejection(const string command, const string error)
{
   const string job_uid = AAA_JsonString(command, "job_uid");
   const string response = StringFormat(
      "{\"protocol_version\":1,\"message_type\":\"execution_ack\","
      "\"job_uid\":\"%s\",\"follower_account_id\":\"%s\","
      "\"status\":\"rejected\",\"error\":\"%s\",\"received_at\":\"%s\"}",
      job_uid, InpFollowerAccountId, AAA_JsonEscape(error), AAA_IsoUtc(TimeGMT()));
   AAA_WriteLine(g_pipe, response);
}

void ProcessCommand(const string command)
{
   if(AAA_JsonString(command, "follower_account_id") != InpFollowerAccountId)
   {
      SendRejection(command, "Command account does not match this terminal.");
      return;
   }
   if(!SafetyReady())
   {
      SendRejection(command, "Executor safety gate is disabled or this is not an allowed demo account.");
      return;
   }

   // This first integration agent intentionally acknowledges only its safety
   // boundary. Order execution is enabled after the Python/EA demo qualification
   // suite proves reconnect, deduplication, symbol, and ticket mapping behavior.
   SendRejection(command, "Executor order placement awaits demo-terminal qualification.");
}

int OnInit()
{
   EventSetMillisecondTimer(MathMax(50, InpPollMs));
   Print("AAA Follower Executor loaded with execution disabled by default.");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   if(g_pipe != INVALID_HANDLE)
      FileClose(g_pipe);
   g_pipe = INVALID_HANDLE;
}

void OnTimer()
{
   if(!ConnectExecutor())
      return;
   if(FileSize(g_pipe) <= 0)
      return;
   FileSeek(g_pipe, 0, SEEK_SET);
   const string command = FileReadString(g_pipe);
   if(StringLen(command) > 0)
      ProcessCommand(command);
}

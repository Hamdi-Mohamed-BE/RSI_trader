#property strict
#property version   "1.000"
#property description "Publishes normalized master deal events to the local AAA Copier pipe."

#include <AAA/CopierProtocol.mqh>

input bool   InpPublisherEnabled = false;
input string InpSourceAccountId  = "";
input string InpMasterPipeName   = "aaa_trade_copier_master";
input int    InpReconnectMs      = 500;

int g_pipe = INVALID_HANDLE;
ulong g_sequence = 0;

bool ConnectPublisher()
{
   if(g_pipe != INVALID_HANDLE)
      return true;
   if(!AAA_OpenPipe(InpMasterPipeName, g_pipe))
      return false;
   Print("AAA Master Publisher connected to ", InpMasterPipeName);
   return true;
}

int OnInit()
{
   MathSrand((int)(GetTickCount() ^ AccountInfoInteger(ACCOUNT_LOGIN)));
   if(!InpPublisherEnabled)
      Print("AAA Master Publisher is disabled. Enable it only on the selected demo master.");
   if(StringLen(InpSourceAccountId) != 36)
      Print("Set InpSourceAccountId to the account UUID shown by the dashboard.");
   EventSetMillisecondTimer(MathMax(100, InpReconnectMs));
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
   if(InpPublisherEnabled && StringLen(InpSourceAccountId) == 36)
      ConnectPublisher();
}

void OnTradeTransaction(const MqlTradeTransaction &transaction,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
{
   if(!InpPublisherEnabled || StringLen(InpSourceAccountId) != 36)
      return;
   if(transaction.type != TRADE_TRANSACTION_DEAL_ADD || transaction.deal == 0)
      return;
   if(!HistoryDealSelect(transaction.deal))
      return;

   const long deal_type = HistoryDealGetInteger(transaction.deal, DEAL_TYPE);
   if(deal_type != DEAL_TYPE_BUY && deal_type != DEAL_TYPE_SELL)
      return;
   const long entry_type = HistoryDealGetInteger(transaction.deal, DEAL_ENTRY);
   string action = "market_open";
   if(entry_type == DEAL_ENTRY_OUT || entry_type == DEAL_ENTRY_OUT_BY)
      action = PositionSelectByTicket(transaction.position) ? "partial_close" : "close";
   else if(entry_type == DEAL_ENTRY_INOUT)
      action = "reverse";

   double stop_loss = 0.0;
   double take_profit = 0.0;
   if(PositionSelectByTicket(transaction.position))
   {
      stop_loss = PositionGetDouble(POSITION_SL);
      take_profit = PositionGetDouble(POSITION_TP);
   }

   if(!ConnectPublisher())
      return;
   g_sequence++;
   const string symbol = HistoryDealGetString(transaction.deal, DEAL_SYMBOL);
   const string side = deal_type == DEAL_TYPE_BUY ? "buy" : "sell";
   const string payload = StringFormat(
      "{\"protocol_version\":1,\"message_type\":\"source_trade\","
      "\"event_uid\":\"%s\",\"sequence\":%I64u,\"source_account_id\":\"%s\","
      "\"source_order_id\":\"%I64u\",\"source_position_id\":\"%I64u\","
      "\"action\":\"%s\",\"side\":\"%s\",\"symbol\":\"%s\","
      "\"volume\":%.8f,\"entry_price\":%.10f,\"stop_loss\":%s,\"take_profit\":%s,"
      "\"magic_number\":%I64d,\"comment\":\"%s\",\"occurred_at\":\"%s\"}",
      AAA_NewUuid(), g_sequence, InpSourceAccountId,
      transaction.order, transaction.position, action, side, AAA_JsonEscape(symbol),
      HistoryDealGetDouble(transaction.deal, DEAL_VOLUME),
      HistoryDealGetDouble(transaction.deal, DEAL_PRICE),
      stop_loss > 0 ? DoubleToString(stop_loss, 10) : "null",
      take_profit > 0 ? DoubleToString(take_profit, 10) : "null",
      HistoryDealGetInteger(transaction.deal, DEAL_MAGIC),
      AAA_JsonEscape(HistoryDealGetString(transaction.deal, DEAL_COMMENT)),
      AAA_IsoUtc(TimeGMT()));

   if(!AAA_WriteLine(g_pipe, payload))
   {
      FileClose(g_pipe);
      g_pipe = INVALID_HANDLE;
      Print("AAA Master Publisher pipe write failed: ", GetLastError());
   }
}

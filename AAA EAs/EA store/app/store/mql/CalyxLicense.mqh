//+------------------------------------------------------------------+
//| CalyxLicense.mqh — online license activation for Calyx store builds
//|
//| Included by the generated store wrapper BEFORE the original strategy
//| source. The strategy code itself is not modified: the wrapper renames
//| its OnInit/OnTick/OnTimer/... through #define and calls them only
//| after this module has confirmed the license.
//|
//| * Strategy Tester / optimization: bypassed completely (no requests,
//|   the original callbacks run unchanged).
//| * Live: POST to CALYX_LICENSE_URL on start, then every 24 hours.
//|   The answer is HMAC-SHA256 signed with a per-build secret and bound to
//|   a fresh nonce, so a forged "allowed" answer is rejected.
//| * Offline grace: 72 hours since the last successful check on this
//|   terminal (kept in a signed terminal global variable).
//| * Denied / grace expired: prints the reason and calls ExpertRemove().
//|   Positions or orders already open are then no longer managed by the EA.
//+------------------------------------------------------------------+
#ifndef CALYX_LICENSE_MQH
#define CALYX_LICENSE_MQH

#ifndef CALYX_BUILD_ID
#error "CALYX_BUILD_ID must be defined by the store wrapper"
#endif
#ifndef CALYX_BUILD_SECRET
#error "CALYX_BUILD_SECRET must be defined by the store wrapper"
#endif
#ifndef CALYX_LICENSE_URL
#define CALYX_LICENSE_URL "https://calyx.duckdns.org/api/license/check"
#endif
#ifndef CALYX_LICENSE_ORIGIN
#define CALYX_LICENSE_ORIGIN "https://calyx.duckdns.org"
#endif

input string InpCalyxLicenseKey = "";   // Calyx license key (from your order page)
input string InpCalyxProduct    = "";   // Calyx product id (pre-filled, do not change)

#define CALYX_RESULT_DENIED      0
#define CALYX_RESULT_ALLOWED     1
#define CALYX_RESULT_UNREACHABLE 2

#define CALYX_RECHECK_SECONDS  86400   // re-check every 24 hours
#define CALYX_GRACE_SECONDS    259200  // 72 hours offline grace
#define CALYX_RETRY_SECONDS    900     // retry spacing after a failed re-check
#define CALYX_PENDING_SECONDS  60      // retry spacing before the first activation
#define CALYX_TIMEOUT_MS       7000

bool     g_calyxVerified      = false;
bool     g_calyxStopped       = false;
bool     g_calyxStrategyReady = false;
long     g_calyxMagic         = 0;
datetime g_calyxLastAttempt   = 0;
datetime g_calyxLastOk        = 0;
int      g_calyxNonceCounter  = 0;
bool     g_calyxAllowListHint = false;

bool CalyxIsTester()
  {
   return (MQLInfoInteger(MQL_TESTER) != 0 || MQLInfoInteger(MQL_OPTIMIZATION) != 0 ||
           MQLInfoInteger(MQL_VISUAL_MODE) != 0 || MQLInfoInteger(MQL_FRAME_MODE) != 0);
  }

bool CalyxStrategyReady()      { return g_calyxStrategyReady; }
void CalyxMarkStrategyReady()  { g_calyxStrategyReady = true; }

//--- hashing helpers -------------------------------------------------
string CalyxHex(const uchar &bytes[])
  {
   string out = "";
   int n = ArraySize(bytes);
   for(int i = 0; i < n; i++)
      out += StringFormat("%02x", bytes[i]);
   return out;
  }

int CalyxUtf8(const string text, uchar &bytes[])
  {
   ArrayResize(bytes, 0);
   int n = StringToCharArray(text, bytes, 0, WHOLE_ARRAY, CP_UTF8);
   if(n > 0 && bytes[n - 1] == 0)
      n--;
   if(n < 0)
      n = 0;
   ArrayResize(bytes, n);
   return n;
  }

bool CalyxSha256(const uchar &data[], uchar &digest[])
  {
   uchar unusedKey[];
   ArrayResize(digest, 0);
   return (CryptEncode(CRYPT_HASH_SHA256, data, unusedKey, digest) == 32);
  }

string CalyxSha256Hex(const string text)
  {
   uchar data[], digest[];
   CalyxUtf8(text, data);
   if(!CalyxSha256(data, digest))
      return "";
   return CalyxHex(digest);
  }

string CalyxHmacSha256Hex(const string key, const string message)
  {
   uchar k[];
   int keyLength = CalyxUtf8(key, k);
   if(keyLength > 64)
     {
      uchar hashed[];
      if(!CalyxSha256(k, hashed))
         return "";
      ArrayResize(k, 32);
      for(int h = 0; h < 32; h++)
         k[h] = hashed[h];
      keyLength = 32;
     }
   uchar msg[];
   int messageLength = CalyxUtf8(message, msg);

   uchar inner[];
   ArrayResize(inner, 64 + messageLength);
   uchar outer[];
   ArrayResize(outer, 64 + 32);
   for(int i = 0; i < 64; i++)
     {
      uchar b = (uchar)(i < keyLength ? k[i] : 0);
      inner[i] = (uchar)(b ^ 0x36);
      outer[i] = (uchar)(b ^ 0x5c);
     }
   for(int m = 0; m < messageLength; m++)
      inner[64 + m] = msg[m];

   uchar innerDigest[];
   if(!CalyxSha256(inner, innerDigest))
      return "";
   for(int d = 0; d < 32; d++)
      outer[64 + d] = innerDigest[d];
   uchar outerDigest[];
   if(!CalyxSha256(outer, outerDigest))
      return "";
   return CalyxHex(outerDigest);
  }

//--- small JSON helpers (the server answers with flat, quote-free JSON) --
string CalyxJsonString(const string json, const string key)
  {
   string pattern = "\"" + key + "\":\"";
   int start = StringFind(json, pattern);
   if(start < 0)
      return "";
   start += StringLen(pattern);
   int finish = StringFind(json, "\"", start);
   if(finish < 0)
      return "";
   return StringSubstr(json, start, finish - start);
  }

string CalyxJsonRaw(const string json, const string key)
  {
   string pattern = "\"" + key + "\":";
   int start = StringFind(json, pattern);
   if(start < 0)
      return "";
   start += StringLen(pattern);
   int length = StringLen(json);
   int finish = start;
   while(finish < length)
     {
      ushort c = StringGetCharacter(json, finish);
      if(c == ',' || c == '}')
         break;
      finish++;
     }
   string value = StringSubstr(json, start, finish - start);
   StringTrimLeft(value);
   StringTrimRight(value);
   return value;
  }

string CalyxJsonEscape(const string text)
  {
   string out = "";
   int n = StringLen(text);
   for(int i = 0; i < n; i++)
     {
      ushort c = StringGetCharacter(text, i);
      if(c == '"' || c == '\\')
         out += "\\" + ShortToString(c);
      else if(c < 32)
         out += " ";
      else
         out += ShortToString(c);
     }
   return out;
  }

//--- persistent "last successful check" (signed global variable) -------
string CalyxStateName()
  {
   string seed = CALYX_BUILD_ID + "|" + InpCalyxLicenseKey + "|" + IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN));
   return "CalyxLic_" + StringSubstr(CalyxSha256Hex(seed), 0, 20);
  }

double CalyxStateSignature(const string name, const datetime when)
  {
   string mac = CalyxHmacSha256Hex(CALYX_BUILD_SECRET, "state|" + name + "|" + IntegerToString((long)when));
   long value = 0;
   for(int i = 0; i < 8 && i < StringLen(mac); i++)
     {
      ushort c = StringGetCharacter(mac, i);
      int digit = (c >= '0' && c <= '9') ? (int)(c - '0') : (int)(c - 'a') + 10;
      value = value * 16 + digit;
     }
   return (double)value;
  }

datetime CalyxLoadLastOk()
  {
   string name = CalyxStateName();
   if(!GlobalVariableCheck(name + "_t") || !GlobalVariableCheck(name + "_s"))
      return 0;
   datetime when = (datetime)(long)GlobalVariableGet(name + "_t");
   if(GlobalVariableGet(name + "_s") != CalyxStateSignature(name, when))
      return 0;
   return when;
  }

void CalyxSaveLastOk(const datetime when)
  {
   string name = CalyxStateName();
   GlobalVariableSet(name + "_t", (double)(long)when);
   GlobalVariableSet(name + "_s", CalyxStateSignature(name, when));
  }

//--- messages -------------------------------------------------------
void CalyxPrintAllowList()
  {
   if(g_calyxAllowListHint)
      return;
   g_calyxAllowListHint = true;
   Print("Calyx license: MT5 blocked the activation request. In MetaTrader 5 open Tools > Options > Expert Advisors, ",
         "tick 'Allow WebRequest for listed URL', add ", CALYX_LICENSE_ORIGIN, " and press OK. The EA retries automatically.");
  }

void CalyxStop(const string code, const string message)
  {
   if(g_calyxStopped)
      return;
   g_calyxStopped = true;
   g_calyxVerified = false;
   string text = "Calyx license DENIED (" + code + "): " + message;
   Print(text);
   Print("Calyx license: the EA is being removed from this chart. Positions or pending orders it already opened are ",
         "NO LONGER MANAGED by it (stop-loss/take-profit orders already at the broker remain). ",
         "Check your license on your Calyx order page or contact support.");
   Alert(text);
   ExpertRemove();
  }

string CalyxNonce()
  {
   g_calyxNonceCounter++;
   string seed = StringFormat("%I64u|%I64d|%I64d|%d|%s", GetMicrosecondCount(), (long)TimeLocal(), ChartID(),
                              g_calyxNonceCounter, InpCalyxLicenseKey);
   return StringSubstr(CalyxSha256Hex(seed), 0, 32);
  }

//--- the online check ------------------------------------------------
int CalyxCheckOnline(string &code, string &message)
  {
   code = "";
   message = "";
   long login = AccountInfoInteger(ACCOUNT_LOGIN);
   if(login <= 0)
     {
      code = "not_logged_in";
      message = "the terminal is not logged in to a trading account yet";
      return CALYX_RESULT_UNREACHABLE;
     }
   g_calyxLastAttempt = TimeGMT();
   string server = AccountInfoString(ACCOUNT_SERVER);
   long tradeMode = AccountInfoInteger(ACCOUNT_TRADE_MODE);
   string mode = (tradeMode == ACCOUNT_TRADE_MODE_REAL ? "real" : (tradeMode == ACCOUNT_TRADE_MODE_CONTEST ? "contest" : "demo"));
   string nonce = CalyxNonce();
   string body = "{\"key\":\"" + CalyxJsonEscape(InpCalyxLicenseKey) + "\"" +
                 ",\"login\":" + IntegerToString(login) +
                 ",\"server\":\"" + CalyxJsonEscape(server) + "\"" +
                 ",\"trade_mode\":\"" + mode + "\"" +
                 ",\"product\":\"" + CalyxJsonEscape(InpCalyxProduct) + "\"" +
                 ",\"build\":\"" + CALYX_BUILD_ID + "\"" +
                 ",\"magic\":" + IntegerToString(g_calyxMagic) +
                 ",\"nonce\":\"" + nonce + "\"" +
                 ",\"terminal_build\":" + IntegerToString(TerminalInfoInteger(TERMINAL_BUILD)) + "}";
   char post[];
   int length = StringToCharArray(body, post, 0, WHOLE_ARRAY, CP_UTF8);
   if(length > 0 && post[length - 1] == 0)
      ArrayResize(post, length - 1);
   char response[];
   string responseHeaders;
   ResetLastError();
   int status = WebRequest("POST", CALYX_LICENSE_URL, "Content-Type: application/json\r\nAccept: application/json\r\n",
                           CALYX_TIMEOUT_MS, post, response, responseHeaders);
   if(status == -1)
     {
      int error = GetLastError();
      code = "webrequest_" + IntegerToString(error);
      message = "WebRequest failed";
      if(error == 4014)
         CalyxPrintAllowList();
      return CALYX_RESULT_UNREACHABLE;
     }
   string text = CharArrayToString(response, 0, WHOLE_ARRAY, CP_UTF8);
   if(status != 200)
     {
      code = "http_" + IntegerToString(status);
      message = CalyxJsonString(text, "message");
      return CALYX_RESULT_UNREACHABLE;
     }
   string allowedRaw = CalyxJsonRaw(text, "allowed");
   code = CalyxJsonString(text, "code");
   message = CalyxJsonString(text, "message");
   string ts = CalyxJsonRaw(text, "ts");
   string echoedNonce = CalyxJsonString(text, "nonce");
   string signature = CalyxJsonString(text, "sig");
   string allowedFlag = (allowedRaw == "true" ? "1" : "0");
   string signedText = nonce + "|" + InpCalyxLicenseKey + "|" + IntegerToString(login) + "|" + CALYX_BUILD_ID + "|" +
                       allowedFlag + "|" + code + "|" + ts;
   string expected = CalyxHmacSha256Hex(CALYX_BUILD_SECRET, signedText);
   if(echoedNonce != nonce || expected == "" || signature != expected)
     {
      code = "bad_signature";
      message = "the activation answer could not be verified";
      return CALYX_RESULT_UNREACHABLE;
     }
   if(allowedRaw == "true")
     {
      g_calyxLastOk = TimeGMT();
      CalyxSaveLastOk(g_calyxLastOk);
      return CALYX_RESULT_ALLOWED;
     }
   return CALYX_RESULT_DENIED;
  }

//--- lifecycle used by the wrapper ------------------------------------
// Returns CALYX_RESULT_ALLOWED (start strategy), CALYX_RESULT_DENIED (EA removed)
// or CALYX_RESULT_UNREACHABLE (waiting for the first activation; strategy not started).
int CalyxLicenseInit(const long magic)
  {
   g_calyxMagic = magic;
   g_calyxStopped = false;
   g_calyxVerified = false;
   string key = InpCalyxLicenseKey;
   StringTrimLeft(key);
   StringTrimRight(key);
   if(StringLen(key) == 0)
     {
      CalyxStop("missing_key", "enter your license key in the input InpCalyxLicenseKey (it is pre-filled in the SET from your order page)");
      return CALYX_RESULT_DENIED;
     }
   g_calyxLastOk = CalyxLoadLastOk();
   string code, message;
   int result = CalyxCheckOnline(code, message);
   if(result == CALYX_RESULT_ALLOWED)
     {
      g_calyxVerified = true;
      Print("Calyx license: activated for account ", AccountInfoInteger(ACCOUNT_LOGIN), " (", CALYX_BUILD_ID, ").");
      return CALYX_RESULT_ALLOWED;
     }
   if(result == CALYX_RESULT_DENIED)
     {
      CalyxStop(code, message);
      return CALYX_RESULT_DENIED;
     }
   datetime now = TimeGMT();
   if(g_calyxLastOk > 0 && now - g_calyxLastOk <= CALYX_GRACE_SECONDS)
     {
      g_calyxVerified = true;
      Print("Calyx license: activation server not reachable (", code, "); offline grace active for ",
            DoubleToString((CALYX_GRACE_SECONDS - (now - g_calyxLastOk)) / 3600.0, 1), " more hours.");
      return CALYX_RESULT_ALLOWED;
     }
   Print("Calyx license: waiting for the first successful activation (", code, ": ", message,
         "). The strategy starts automatically once the license is confirmed; it does not trade before that.");
   return CALYX_RESULT_UNREACHABLE;
  }

// Called on every tick/timer. Returns CALYX_RESULT_ALLOWED when the strategy may run.
int CalyxLicensePulse()
  {
   if(g_calyxStopped)
      return CALYX_RESULT_DENIED;
   datetime now = TimeGMT();
   string code, message;
   if(!g_calyxVerified)
     {
      if(now - g_calyxLastAttempt < CALYX_PENDING_SECONDS)
         return CALYX_RESULT_UNREACHABLE;
      int pending = CalyxCheckOnline(code, message);
      if(pending == CALYX_RESULT_ALLOWED)
        {
         g_calyxVerified = true;
         Print("Calyx license: activated for account ", AccountInfoInteger(ACCOUNT_LOGIN), " (", CALYX_BUILD_ID, ").");
         return CALYX_RESULT_ALLOWED;
        }
      if(pending == CALYX_RESULT_DENIED)
        {
         CalyxStop(code, message);
         return CALYX_RESULT_DENIED;
        }
      return CALYX_RESULT_UNREACHABLE;
     }
   if(now - g_calyxLastOk >= CALYX_RECHECK_SECONDS && now - g_calyxLastAttempt >= CALYX_RETRY_SECONDS)
     {
      int result = CalyxCheckOnline(code, message);
      if(result == CALYX_RESULT_DENIED)
        {
         CalyxStop(code, message);
         return CALYX_RESULT_DENIED;
        }
      if(result == CALYX_RESULT_UNREACHABLE)
        {
         if(now - g_calyxLastOk > CALYX_GRACE_SECONDS)
           {
            CalyxStop("grace_expired", "no successful license check for more than 72 hours (" + code + ")");
            return CALYX_RESULT_DENIED;
           }
         Print("Calyx license: re-check failed (", code, "); offline grace remaining ",
               DoubleToString((CALYX_GRACE_SECONDS - (now - g_calyxLastOk)) / 3600.0, 1), " hours.");
        }
     }
   return CALYX_RESULT_ALLOWED;
  }

#endif // CALYX_LICENSE_MQH

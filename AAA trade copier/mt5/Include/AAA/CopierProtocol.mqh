#ifndef AAA_COPIER_PROTOCOL_MQH
#define AAA_COPIER_PROTOCOL_MQH

string AAA_JsonEscape(string value)
{
   StringReplace(value, "\\", "\\\\");
   StringReplace(value, "\"", "\\\"");
   StringReplace(value, "\r", "\\r");
   StringReplace(value, "\n", "\\n");
   return value;
}

string AAA_PipePath(const string pipe_name)
{
   return "\\\\.\\pipe\\" + pipe_name;
}

bool AAA_OpenPipe(const string pipe_name, int &handle)
{
   ResetLastError();
   handle = FileOpen(AAA_PipePath(pipe_name), FILE_READ | FILE_WRITE | FILE_BIN | FILE_ANSI);
   return handle != INVALID_HANDLE;
}

bool AAA_WriteLine(const int handle, const string payload)
{
   if(handle == INVALID_HANDLE)
      return false;
   FileSeek(handle, 0, SEEK_SET);
   const uint written = FileWriteString(handle, payload + "\n");
   FileFlush(handle);
   return written > 0;
}

string AAA_IsoUtc(const datetime value)
{
   MqlDateTime parts;
   TimeToStruct(value, parts);
   return StringFormat("%04d-%02d-%02dT%02d:%02d:%02dZ",
                       parts.year, parts.mon, parts.day, parts.hour, parts.min, parts.sec);
}

string AAA_NewUuid()
{
   const uint tick = GetTickCount();
   const uint micros = (uint)(GetMicrosecondCount() & 0xFFFFFFFF);
   const uint account = (uint)(AccountInfoInteger(ACCOUNT_LOGIN) & 0xFFFFFFFF);
   const uint random_a = (uint)MathRand();
   const uint random_b = (uint)MathRand();
   return StringFormat("%08X-%04X-4%03X-A%03X-%04X%08X",
                       tick ^ account,
                       (micros >> 16) & 0xFFFF,
                       random_a & 0x0FFF,
                       random_b & 0x0FFF,
                       micros & 0xFFFF,
                       tick ^ random_a ^ random_b);
}

string AAA_JsonString(const string json, const string key, const string fallback = "")
{
   const string marker = "\"" + key + "\":\"";
   const int start = StringFind(json, marker);
   if(start < 0)
      return fallback;
   const int value_start = start + StringLen(marker);
   const int value_end = StringFind(json, "\"", value_start);
   if(value_end < value_start)
      return fallback;
   return StringSubstr(json, value_start, value_end - value_start);
}

double AAA_JsonNumber(const string json, const string key, const double fallback = 0.0)
{
   const string marker = "\"" + key + "\":";
   const int start = StringFind(json, marker);
   if(start < 0)
      return fallback;
   const int value_start = start + StringLen(marker);
   int value_end = value_start;
   while(value_end < StringLen(json))
   {
      const ushort character = StringGetCharacter(json, value_end);
      if(character == ',' || character == '}')
         break;
      value_end++;
   }
   return StringToDouble(StringSubstr(json, value_start, value_end - value_start));
}

#endif

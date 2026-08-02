# Exness live update

1. Extract `exness-auto-discovery-fix.zip` into the bot folder and replace the
   existing files.
2. In `.env`, set:

   `CANONICAL_SYMBOL=AUTO`

3. Keep the Exness MT5 terminal open and logged in, then run:

   `uv run nasdaq-weakness account`

4. Confirm that the output shows the Exness server and a resolved symbol such
   as `USTEC`, `USTECm`, or the exact suffix used by that account.
5. Only after that check succeeds, start `run_live.bat`.

The live worker now initializes the already-open MT5 terminal before it scans
the broker catalogue. It prints the connected server, login, balance, and the
automatically resolved Nasdaq-100 symbol at startup.

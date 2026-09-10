# MT5 Gold News V9 EA - Expert Builder Specification

## 1. Objective

Build a MetaTrader 5 Expert Advisor that consumes the existing local Gold News
V9 prediction service and, when explicitly enabled, trades the immediate
XAUUSD reaction to three USD events:

- NFP
- CPI
- FOMC statement

PPI and GDP are intentionally unsupported. The EA must reject them even if they
appear in an external calendar.

The Python application remains the owner of signal generation. The EA owns
order validation, execution, position management, recovery, and logging. Do not
port or duplicate the model logic in MQL5.

## 2. Current Research Configuration

The current one-year 1% risk replay uses:

| Setting | Value |
|---|---|
| Prediction snapshot | T-15 minutes |
| Entry time | T-5 seconds |
| Direction | POSITIVE = buy XAUUSD, NEGATIVE = sell XAUUSD |
| Initial stop | $4.00 in XAUUSD price, measured from actual fill |
| Take profit | None |
| Trailing stop | None |
| Time exit | T+900 seconds, or 15 minutes after release |
| Position size | 1% of current balance at the nominal $4.00 stop |
| Events | NFP, CPI, FOMC |
| Simulated starting balance | $10,000 |

The $4.00 setting is a gold price distance, not a fixed $4 account loss. The EA
must use OrderCalcProfit to find the one-lot cash loss between the estimated
entry and stop, then size the lot so that this nominal loss equals 1% of current
balance. It must not assume a contract size. Stop gaps can make the realized
loss exceed 1%.

The September 10, 2025 through September 9, 2026 replay produced 29 trades,
48.28% trade win rate, 8.19 profit factor, 153.05% return, 4.53% maximum
closed-balance drawdown, and 10.53% maximum tick-equity drawdown. The direction
model itself was correct on 21/29 releases, or 72.41%. Full details are in
NEWS_V9_RISK_1PCT_1Y_RESULTS.md.

These settings are a retrospective research result, not a profit guarantee.
Live news execution can be materially worse because of spread expansion,
latency, rejection, price gaps, and stop slippage.

## 3. Existing Project and Model Files

Project root:

    C:\Users\hama101\Desktop\geek\ai trader\AI news

Paths relative to that root:

| Purpose | Relative path |
|---|---|
| Start local prediction server | run.bat |
| FastAPI application | app.py |
| Prediction pipeline | predict_news.py |
| V9 direction wrapper | news_v9_direction.py |
| Train/rebuild V9 | train_news_v9_direction.py |
| V9 direction artifact | models\gold_news_v9_direction.joblib |
| V8 move-range artifact | models\gold_news_v8_move_range.joblib |
| Locked prediction records | predictions\ |
| Three-month V9 report | NEWS_V9_DIRECTION_3M_RESULTS.md |
| Three-month V9 data | news_v9_direction_3m_results.json |
| One-year V9 report | NEWS_V9_DIRECTION_1Y_RESULTS.md |
| One-year 1% risk runner | run_news_v9_risk_1pct_1y.bat |
| One-year 1% risk report | NEWS_V9_RISK_1PCT_1Y_RESULTS.md |
| One-year 1% risk data | news_v9_risk_1pct_1y_results.json |
| One-year 1% risk trades | news_v9_risk_1pct_1y_trades.csv |

The direction artifact has been rebuilt as artifact version 9 with:

    supported_events = ["NFP", "CPI", "FOMC"]
    extended_event_rules = {}

Suggested EA deliverables:

    mt5\GoldNewsV9EA.mq5
    mt5\GoldNewsV9EA.ex5
    mt5\GoldNewsV9EA-Research.set
    mt5\GoldNewsV9EA-Safer.set
    mt5\README.md
    mt5\fixtures\

## 4. Starting the Python Service

Run:

    C:\Users\hama101\Desktop\geek\ai trader\AI news\run.bat

The launcher installs/synchronizes dependencies, builds missing artifacts, and
starts the local server. Defaults:

    http://127.0.0.1:8799

The settings come from:

    C:\Users\hama101\Desktop\geek\ai trader\AI news\.env

Relevant settings:

    MT5_PATH=C:\Program Files\MetaTrader 5\terminal64.exe
    XAU_SYMBOL=XAUUSD
    APP_HOST=127.0.0.1
    APP_PORT=8799

Keep APP_HOST on 127.0.0.1. The service is local and should not be exposed to
the internet.

In MT5, add this URL under Tools > Options > Expert Advisors > Allow WebRequest
for listed URL:

    http://127.0.0.1:8799

## 5. Local HTTP Contract

### 5.1 Health check

Request:

    GET http://127.0.0.1:8799/api/health

Before arming an event, require:

- HTTP 200.
- status is ok.
- models.gold_direction_v9_action_tier is true.
- models.gold_move_range_v8 is true.
- trade_execution is false. This confirms that Python is prediction-only; it is
  not an error.

### 5.2 Upcoming events

Request:

    GET http://127.0.0.1:8799/api/upcoming?days=7

The service filters its output to NFP, CPI, and FOMC. The EA must filter the
response again and require an exact supported event name.

Automatic calendar discovery is preferred, but the EA must also provide a
manual UTC event input for testing and for calendar-source outages. Manual
entries must still be restricted to the three supported event names.

### 5.3 Prediction request

Request:

    POST http://127.0.0.1:8799/api/predict
    Content-Type: application/x-www-form-urlencoded

Required form fields:

    event=NFP
    release=2026-09-04T12%3A30%3A00Z

Optional point-in-time context:

    forecast=75K
    previous=73K
    source_url=https%3A%2F%2Fexample.com%2Frelease

FOMC may also include:

    fomc_current_lower=5.25
    fomc_current_upper=5.50
    fomc_cut_50_probability=0
    fomc_cut_25_probability=12.5
    fomc_hold_probability=82.0
    fomc_hike_25_probability=5.5
    fomc_hike_50_probability=0

All values must be observations available before the release. Do not insert
the published actual or any post-release revisions.

The prediction endpoint accepts requests only 8 to 30 minutes before release.
The production scheduler should request once at T-15 minutes and retain that
response in EA state.

Required response fields:

| JSON field | Meaning |
|---|---|
| generated_at_utc | When the signal was generated |
| event | Canonical event name |
| release_time_utc | Exact event timestamp |
| minutes_before_release | Actual prediction lead |
| symbol | XAUUSD symbol resolved by Python |
| gold_impact | POSITIVE or NEGATIVE |
| prediction | Same directional output |
| confidence_pct | Bounded reliability score |
| confidence_tier | STANDARD or LOW |
| action_tier | TRADE or LOW_CONFIDENCE |
| expected_impulse_range_usd | Informational move-range object |
| model.active_call_allowed | Whether the older validation gate passed |
| model.artifact_version | Must equal 9 |
| model.trained_through | Last release included by the artifact |
| execution_capability | Must be false |
| saved_to | Permanent local prediction record |

The expected move range is informational. It must not alter the frozen entry,
stop, or exit rules unless a separate configuration is tested and approved.

### 5.4 Command-line fallback

HTTP is the preferred integration. It avoids DLLs and fragile process-output
capture from MQL5.

For manual diagnostics only:

    cd /d "C:\Users\hama101\Desktop\geek\ai trader\AI news"
    ".venv\Scripts\python.exe" predict_news.py --event NFP --release "2026-09-04T12:30:00Z" --forecast "75K" --previous "73K"

If the virtual environment is unavailable:

    uv run python predict_news.py --event NFP --release "2026-09-04T12:30:00Z" --forecast "75K" --previous "73K"

Do not make the EA spawn Python directly unless the HTTP method is impossible.

## 6. UTC and Event Identity

Every event must have a deterministic identifier:

    EVENT_ID = EVENT_NAME + "_" + RELEASE_UTC_AS_YYYYMMDDTHHMMSSZ

Example:

    NFP_20260904T123000Z

Use UTC for every comparison. Do not compare the news time directly with
broker server time or local Windows time. Use TimeGMT for live scheduling and
store the parsed release timestamp as UTC.

The event name and release time returned by Python must exactly match the
requested event. Reject the response on any mismatch.

FOMC means the statement/rate decision timestamp. The press conference is a
separate later shock and must not create another position.

## 7. EA State Machine

Use one state per EVENT_ID:

    IDLE
      -> SCHEDULED
      -> REQUESTING_PREDICTION
      -> ARMED
      -> ENTRY_SENT
      -> POSITION_OPEN
      -> EXIT_SENT
      -> CLOSED

Failure states:

    SKIPPED
    EXPIRED
    ERROR

State behavior:

1. IDLE: no supported event is being handled.
2. SCHEDULED: exact event name and UTC release time are known.
3. REQUESTING_PREDICTION: call the API at T-15 minutes.
4. ARMED: a valid, persistent prediction is stored in memory and terminal
   Global Variables.
5. ENTRY_SENT: at T-5 seconds, send one market order in the predicted direction.
6. POSITION_OPEN: confirm the resulting position/deal and manage only that
   position.
7. EXIT_SENT: at T+900 seconds, request a full close.
8. CLOSED: record the final deal, costs, slippage, P/L, and reason.

Never move backward from ENTRY_SENT to ARMED. This prevents duplicate orders
after uncertain trade responses or terminal restarts.

## 8. Signal Validation

Arm an event only when all checks pass:

- Event is exactly NFP, CPI, or FOMC.
- Release time is in the future.
- Response event equals requested event.
- Response release_time_utc equals scheduled UTC release time.
- generated_at_utc is before release.
- Signal age is no more than MaxSignalAgeMinutes.
- model.artifact_version equals 9.
- gold_impact is exactly POSITIVE or NEGATIVE.
- prediction equals gold_impact.
- execution_capability is false.
- Symbol can be resolved on the active account.
- No existing EA trade or completed EVENT_ID exists.
- Automated trading and terminal connectivity are available.

Action-tier behavior:

- When TradeLowConfidence is false, accept only action_tier = TRADE.
- When TradeLowConfidence is true, accept TRADE and LOW_CONFIDENCE.
- The historical full-coverage replay traded both tiers.
- The safer preset must default TradeLowConfidence to false.

Do not infer a direction from confidence, probabilities, text explanations, or
the move-range signs. Use only gold_impact.

## 9. Order Timing

Use EventSetMillisecondTimer so the EA can evaluate time more frequently than
one second. A 100 ms timer is sufficient.

At release UTC minus EntryLeadSeconds:

1. Refresh the symbol tick.
2. Re-run spread, margin, volume, session, and symbol checks.
3. Calculate the requested lot.
4. Send exactly one market order.
5. Persist ENTRY_SENT before attempting any retry.
6. Confirm the trade result using the order/deal identifiers and trade history.

Default:

    EntryLeadSeconds = 5

If the order is not accepted before release, do not chase it after release.
Set the event to EXPIRED. A separate research mode may test other timing, but
the production default must remain frozen.

## 10. Direction and Price Rules

POSITIVE gold impact:

    Side = BUY
    Requested price = current Ask
    Initial SL = actual fill price - StopDistanceUSD

NEGATIVE gold impact:

    Side = SELL
    Requested price = current Bid
    Initial SL = actual fill price + StopDistanceUSD

Default:

    StopDistanceUSD = 4.00

Normalize every price to SYMBOL_DIGITS. Respect SYMBOL_TRADE_STOPS_LEVEL and
SYMBOL_TRADE_FREEZE_LEVEL. If the broker does not allow the stop with the
entry order, send the market order and immediately add the stop using the
confirmed fill price. If that modification fails, close the position and mark
the event ERROR_UNPROTECTED_POSITION.

Do not place a take profit. Do not trail. At release UTC plus 900 seconds, close
the complete EA-owned position at market.

## 11. Position Sizing

Primary 1% risk sizing:

    risk_cash = AccountInfoDouble(ACCOUNT_BALANCE) * RiskPercent / 100
    estimated_entry = Ask for buy, Bid for sell
    estimated_stop = estimated_entry minus/plus StopDistanceUSD
    one_lot_loss = abs(OrderCalcProfit(side, symbol, 1.0,
                                      estimated_entry, estimated_stop))
    requested_lot = risk_cash / one_lot_loss

Defaults:

    PositionSizingMode = SIZE_RISK_PERCENT
    RiskPercent = 1.00

If OrderCalcProfit fails or returns a non-positive loss, skip the event. Never
replace missing broker metadata with a guessed contract size.

Optional legacy sizing, retained only to reproduce older reports:

    units = floor(AccountInfoDouble(ACCOUNT_BALANCE) / BalanceStepUSD)
    requested_lot = units * LotsPerBalanceStep
    BalanceStepUSD = 100.00
    LotsPerBalanceStep = 0.06

Then:

1. Cap requested lot at MaxLot.
2. Normalize downward to SYMBOL_VOLUME_STEP.
3. Require at least SYMBOL_VOLUME_MIN.
4. Cap at SYMBOL_VOLUME_MAX.
5. Use OrderCalcMargin for the exact direction and current entry price.
6. Require enough free margin after MarginReservePercent.
7. Recalculate the estimated stop cash loss after lot normalization.
8. Require normalized nominal risk to be no greater than the risk budget.
9. Display and log the risk budget and estimated cash loss before sending.
10. After the fill, calculate the accepted stop from the actual fill and log its
    cash risk. If the stop gaps, record actual loss and realized R separately.

Never assume the account leverage or contract size. Read both from the active
terminal and symbol. The EA must not reduce a rejected order repeatedly until
something fills unless EnableAutoLotReduction is explicitly enabled. When it is
enabled, normalize down one volume step at a time and log the final lot.

## 12. Spread, Slippage, and Broker Checks

Immediately before entry, calculate:

    spread_price = Ask - Bid
    spread_points = spread_price / SYMBOL_POINT

Inputs:

    MaxSpreadUSD
    MaxSpreadPoints
    MaxDeviationPoints

When both spread limits are positive, require both. A value of zero disables
that limit. The safer preset should enforce a tested limit. The research preset
may disable spread rejection to reproduce the historical replay, but it must
still log spread.

Use the symbol's supported filling mode. Inspect the MqlTradeResult retcode,
order, deal, price, bid, ask, and comment. TRADE_RETCODE_DONE is success.
TRADE_RETCODE_PLACED requires subsequent deal confirmation. Never treat a
nonzero order ticket alone as proof of a filled position.

Calculate realized entry slippage against the tick captured immediately before
OrderSend. Log price slippage and cash impact.

## 13. Netting and Hedging Accounts

The EA must support both modes:

- Hedging: identify the position by ticket, magic number, symbol, and EVENT_ID.
- Netting: refuse entry if an unrelated XAUUSD position already exists, unless
  AllowNettingMerge is explicitly enabled. Default it to false.

Manage only trades whose magic number and comment belong to this EA. Never
modify or close manual trades or positions from another EA.

Suggested comment:

    GNV9|NFP_20260904T123000Z|POS

Keep the comment short enough for broker limits and store the full EVENT_ID
separately.

## 14. Required Inputs

Suggested MQL5 inputs:

    enum ENUM_POSITION_SIZING_MODE
      {
       SIZE_RISK_PERCENT = 0,
       SIZE_LEGACY_BALANCE_STEP = 1,
       SIZE_FIXED_LOT = 2
      };

    input bool   EnableTrading = false;
    input bool   RequireDemoAccount = true;
    input long   MagicNumber = 90915001;
    input string ApiBaseUrl = "http://127.0.0.1:8799";
    input int    HttpTimeoutMs = 5000;
    input int    PredictionLeadMinutes = 15;
    input int    EntryLeadSeconds = 5;
    input int    ExitAfterReleaseSeconds = 900;
    input double StopDistanceUSD = 4.00;
    input ENUM_POSITION_SIZING_MODE PositionSizingMode = SIZE_RISK_PERCENT;
    input double RiskPercent = 1.00;
    input double BalanceStepUSD = 100.00;
    input double LotsPerBalanceStep = 0.06;
    input double FixedLot = 0.01;
    input double MaxLot = 0.60;
    input double MarginReservePercent = 10.0;
    input double MaxSpreadUSD = 0.0;
    input int    MaxSpreadPoints = 0;
    input int    MaxDeviationPoints = 100;
    input int    MaxSignalAgeMinutes = 20;
    input bool   TradeLowConfidence = false;
    input bool   EnableNFP = true;
    input bool   EnableCPI = true;
    input bool   EnableFOMC = true;
    input bool   EnableAutoLotReduction = false;
    input bool   AllowNettingMerge = false;
    input bool   CloseUnprotectedPosition = true;
    input bool   UseAutomaticCalendar = true;
    input string ManualEvent = "";
    input string ManualReleaseUTC = "";
    input bool   ReplayMode = false;
    input string ReplayFixtureFile = "";

No input may enable PPI or GDP.

## 15. Persistence and Restart Recovery

Persist at least:

- EVENT_ID.
- State.
- Prediction direction.
- Action tier.
- Confidence.
- Prediction generation UTC.
- Release UTC.
- ENTRY_SENT flag.
- Order/deal/position identifiers.
- Actual fill price and lot.
- Planned stop and exit time.

Use terminal Global Variables for compact durable state and a CSV or binary
file for the complete record.

On OnInit:

1. Load persisted state.
2. Search open positions and pending orders by magic number and EVENT_ID.
3. Search recent history if ENTRY_SENT exists but no open position is found.
4. Resume management of an existing EA position.
5. Never re-enter an event already marked ENTRY_SENT, CLOSED, SKIPPED, EXPIRED,
   or ERROR.
6. If a position is open and its time exit has passed, close it immediately.

On terminal disconnect, retain state. On reconnect, reconcile before sending
anything.

## 16. Error and Fail-Closed Rules

Skip the event without trading when:

- Python service is unavailable.
- Model health is not ready.
- Prediction arrives outside the 8 to 30 minute window.
- Response is malformed or mismatched.
- Prediction is stale.
- Event is unsupported.
- Signal is low-confidence and TradeLowConfidence is false.
- XAUUSD cannot be resolved.
- Market is closed or symbol trading is disabled.
- Spread exceeds a configured limit.
- Volume or margin validation fails.
- Another event or position conflicts.
- Entry time was missed.
- Trading permission is disabled.

The EA must show the exact skip reason in the Experts log and its own event log.
It must never guess a missing direction, release time, price, lot, or symbol.

## 17. Symbol Resolution

Do not hard-code that the broker symbol is exactly XAUUSD. Resolve in this
order:

1. Exact UserSymbol input when provided.
2. Exact XAUUSD.
3. A visible symbol whose normalized name begins with XAUUSD.
4. A visible symbol whose normalized name contains XAUUSD.

Normalization may remove dots, spaces, hyphens, underscores, and case.
Examples include XAUUSD.a, XAUUSDm, and XAUUSD-pro.

Reject ambiguous matches and show the candidates. Python and the EA should
resolve the same active-account instrument.

## 18. Logs and Audit Record

Write one event row and one or more execution rows. Include:

- EVENT_ID and event.
- Release UTC.
- Prediction request and response UTC.
- Direction, action tier, confidence, model version, and trained-through date.
- Expected move range.
- Account server, login hash or masked login, leverage, margin mode.
- Broker symbol, digits, point, contract size, volume limits, stop level.
- Tick time, bid, ask, spread at validation and entry.
- Requested lot, accepted lot, estimated margin, estimated stop cash loss.
- Requested price, fill price, entry slippage.
- Stop request and accepted stop.
- Entry and exit retcodes, order/deal/position tickets.
- Exit reason, exit price, gross P/L, commission, swap, and net P/L.
- Balance and equity before and after.
- Every rejection, retry, state transition, and recovery action.

Store logs under MQL5\Files\GoldNewsV9EA and also print concise state changes to
the Experts log.

## 19. Strategy Tester and Replay Mode

MT5 Strategy Tester cannot be assumed to access WebRequest reliably. Add a
ReplayMode that reads immutable fixture JSON files from MQL5\Files. Each fixture
must contain the same required fields as the live API response plus a known
release UTC.

Replay mode must:

- Use tester time for scheduling.
- Never call the internet or Python.
- Preserve the T-15 prediction and T-5 entry timing.
- Use tester ticks for fills, stops, and T+15 exit.
- Write the same audit schema as live mode.
- Refuse fixture events other than NFP, CPI, and FOMC.

Fixture files should be generated from locked records under the project's
predictions folder, not recreated after observing the event outcome.

## 20. Acceptance Tests

The builder should demonstrate:

1. MQ5 compiles with zero errors and zero warnings.
2. Trading is disabled by default.
3. PPI and GDP are rejected.
4. POSITIVE creates one buy and NEGATIVE creates one sell.
5. An event cannot create a duplicate trade after restart.
6. Entry is sent once at T-5 seconds and never chased after release.
7. Stop is based on confirmed fill, not the earlier quote.
8. Position closes at T+900 seconds.
9. Lot calculation rounds downward and respects min/max/step.
10. Insufficient margin fails closed.
11. High spread fails closed when limits are configured.
12. Symbol suffixes resolve correctly and ambiguity is rejected.
13. Netting and hedging behavior is verified.
14. A rejected or unprotected trade is handled and logged.
15. Server outage, timeout, malformed JSON, stale response, and UTC mismatch all
    produce no trade.
16. Low-confidence behavior follows its input exactly.
17. Replay fixtures reproduce the expected event sequence.
18. The EA never manages another strategy's or a manual position.

## 21. Builder Pseudocode

    OnInit:
        validate inputs
        resolve XAUUSD
        restore durable state
        reconcile positions and history
        start 100 ms timer

    OnTimer:
        now_utc = TimeGMT()
        reconcile any unresolved ENTRY_SENT state

        if no current event:
            discover next enabled NFP/CPI/FOMC event
            persist SCHEDULED state

        if state == SCHEDULED and now_utc >= release_utc - 15 minutes:
            verify API health
            request prediction once
            validate event, UTC, model version, direction, tier, and age
            if valid:
                persist ARMED state and complete response
            else:
                persist SKIPPED with reason

        if state == ARMED and now_utc >= release_utc - 5 seconds:
            if now_utc >= release_utc:
                persist EXPIRED
                return
            validate tick, spread, volume, margin, symbol, and permissions
            persist ENTRY_SENT before order dispatch
            send one market order
            confirm deal or reconcile history
            attach $4 stop from actual fill
            persist POSITION_OPEN

        if state == POSITION_OPEN:
            verify stop remains present
            if now_utc >= release_utc + 900 seconds:
                close full EA-owned position
                persist CLOSED and final audit

    OnTradeTransaction:
        map transactions by magic number and EVENT_ID
        update confirmed tickets, fills, stop, costs, and state
        never create an entry from this handler

    OnDeinit:
        persist state
        stop timer

## 22. Two Presets

One-year 1% risk reproduction:

    EnableTrading = false until manually enabled on demo
    TradeLowConfidence = true
    StopDistanceUSD = 4.00
    EntryLeadSeconds = 5
    ExitAfterReleaseSeconds = 900
    PositionSizingMode = SIZE_RISK_PERCENT
    RiskPercent = 1.00
    MaxSpreadUSD = 0
    MaxSpreadPoints = 0

Safer forward-validation preset:

    EnableTrading = false
    RequireDemoAccount = true
    TradeLowConfidence = false
    PositionSizingMode = SIZE_RISK_PERCENT
    RiskPercent = 0.25 to 0.50
    MaxLot = a deliberately small user-defined cap
    MarginReservePercent = at least 20
    MaxSpreadUSD = broker-tested limit
    EnableAutoLotReduction = false

The 1% reproduction preset is the only preset intended to reproduce the
one-year table. The safer preset intentionally changes risk and coverage and
will not reproduce the historical P/L.

## 23. Final Scope Guard

The completed EA must contain a hard-coded allowlist:

    NFP, CPI, FOMC

Calendar text, API output, manual input, fixture files, or future model artifacts
must not bypass that allowlist without a reviewed source-code change and a new
backtest.

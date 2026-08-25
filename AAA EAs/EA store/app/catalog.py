from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from pydantic import BaseModel, ConfigDict


STORE_ROOT = Path(__file__).resolve().parents[1]
EAS_ROOT = STORE_ROOT.parent
PACKAGE_ROOT = EAS_ROOT / "BM Trading Robust Sets 2026-08-04"
INSTALLER_PATH = PACKAGE_ROOT / "_Auto Deploy" / "Install-BMTradingPortfolio.ps1"
WHATSAPP_NUMBER = "21693830957"

TIMEFRAMES = {1: "M1", 5: "M5", 15: "M15", 60: "H1", 240: "H4", 1440: "D1"}


class Evidence(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    label: str
    period: str
    return_pct: float
    profit_factor: float
    drawdown_pct: float
    win_rate_pct: float
    trades: int
    history_quality: str = "Not stated"
    source_note: str
    chart_path: Path | None = None
    status: str = "Research"
    caution: str | None = None


class LogicStep(BaseModel):
    title: str
    detail: str


class Product(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    label: str
    installer_label: str
    slug: str
    canonical: str
    timeframe: str
    period_minutes: int
    expert: str
    expert_source: str
    set_source: str
    optional_symbol: bool = False
    category: str
    asset_group: str
    strategy: str
    tagline: str
    description: str
    session: str
    risk_note: str
    logic_audit: str
    logic_audit_note: str
    logic: list[LogicStep]
    limitations: list[str]
    price: int
    accent: str
    featured: bool = False
    development: bool = False
    evidence: Evidence | None = None
    one_year_evidence: Evidence | None = None
    one_year_return_pct: float | None = None
    one_year_note: str | None = None
    buy_url: str = ""


CORE_META: dict[str, dict[str, Any]] = {
    "LTA Volume Profile": {
        "strategy": "Momentum at auction reference levels",
        "tagline": "D1/H1 trend momentum entered from H4 zones or prior-day and prior-week profile levels.",
        "description": "The active XAUUSD M15 preset is a momentum-only model. It first establishes direction, then requires price to revisit a qualified H4 supply/demand zone or a prior-day/prior-week POC, VAH or VAL before one of two enabled candle confirmations can trigger a market order.",
        "session": "No session filter / M15 execution",
        "logic_audit": "Source-code verified",
        "logic_audit_note": "Readable MQ5 source, the full execution engine and the exact active BAT preset were reviewed together.",
        "logic": [
            {"title": "Establish the allowed direction", "detail": "Auto bias reads D1 first and falls back to H1. Direction is based on 20-versus-50 average closes plus recent structure. The active Momentum archetype rejects trades against the H1 trend."},
            {"title": "Build the reference map", "detail": "The EA calculates 64-bin, 70% value-area profiles for the previous day and previous week. It also finds H4 zones formed by a three-bar base followed by an ATR- and tick-volume-qualified expansion that breaks earlier structure. The optional rolling swing profile is disabled."},
            {"title": "Require a recent revisit", "detail": "A zone or profile level must have been touched and held within the last five M15 bars, using a 0.24 ATR proximity buffer. Supply/demand is checked first, followed by prior-week and then prior-day POC, VAH and VAL."},
            {"title": "Confirm with an enabled entry model", "detail": "Only EM1 Double Wick and EM4 Continuation are active. EM1 needs a level touch, a rejection wick of at least 25% of candle range and a directional flip. EM4 needs a touch in the first two bars and a third candle that closes through both. The confirmation bar must have at least its 20-bar average tick volume."},
            {"title": "Place a structural 3R trade", "detail": "Entry is at market. The stop sits beyond the confirming candles and, for a zone trade, beyond the zone, with a 0.12 ATR buffer. The take profit is three times the initial stop distance."},
            {"title": "Apply the active safety rules", "detail": "Each trade risks 1% of current equity, both directions are enabled and only one position is allowed per symbol. New entries pause after two consecutive losses while daily P/L is non-positive. Session, break-even and time-based dead-trade exits are disabled in this preset."},
        ],
        "risk_note": "Dynamic 1% of current equity per trade, capped at 1% by the active preset. Position size is rounded down and the trade is skipped if the broker minimum lot would exceed the requested risk.",
        "price": 399,
        "accent": "cyan",
    },
    "ORB Volume Profile": {
        "strategy": "New York opening-range breakout",
        "tagline": "A direct 15-minute New York ORB filtered by range quality and broker quote activity.",
        "description": "The active XAUUSD M5 preset trades direct breaks of the 09:30-09:45 New York opening range. It does build and display a tick-activity profile, but POC, value-area and boundary-node filters are deliberately OFF in the validated preset; VWAP and EMA filters are also OFF.",
        "session": "09:30 New York / weekdays",
        "logic_audit": "Source-code verified",
        "logic_audit_note": "Readable MQ5 source and the active visual-profile BAT preset were reviewed. Display-only features are separated from entry filters below.",
        "logic": [
            {"title": "Build the 15-minute New York range", "detail": "At 09:45 New York time, the EA takes the high and low of 09:30-09:45 from M1 bars. The range must measure between 0.20 and 1.20 times M15 ATR(14). Server offset and US daylight saving are handled automatically."},
            {"title": "Confirm active opening activity", "detail": "Opening-window tick volume must be at least 0.60 times the median volume of the same window across the previous 20 valid weekdays. This is broker quote activity, not centralized exchange volume."},
            {"title": "Calculate profile levels for display", "detail": "Quote ticks from 08:00 through 09:45 are distributed into 48 price bins to draw POC, VAH and VAL for a 70% value area. In the active preset all three profile entry filters are OFF, so these lines are visual context only."},
            {"title": "Qualify a direct M5 breakout", "detail": "During the next 120 minutes, a closed M5 candle must have at least a 55% body, at least 0.80 relative tick volume versus its prior 20 bars, and close beyond the range by 0.03 ATR in its own direction. Retest mode, VWAP and EMA trend filtering are disabled."},
            {"title": "Use the opposite range boundary as the stop", "detail": "The EA enters at market. Stop loss is beyond the opposite side of the opening range by 0.10 ATR; signals needing more than 2.0 ATR of stop distance are rejected. Take profit is 2.5R and spread may not exceed 12% of the opening-range width."},
            {"title": "Manage one trade for the session", "detail": "Risk is 1% of current equity. The stop moves to entry at +1R, candle trailing is disabled, no second trade is allowed that New York date, and any open position is closed at 15:55 New York."},
        ],
        "risk_note": "Dynamic 1% of current equity, sized from entry to the opposite-range stop. Gap, spread and execution slippage can make realized risk differ from the calculation.",
        "price": 449,
        "accent": "emerald",
        "featured": True,
    },
    "US100 ORB 0.5R": {
        "strategy": "Selective New York opening-range retest",
        "tagline": "A high-selectivity US100 ORB using relative tick volume, VWAP, candle quality and a fixed 0.5R target.",
        "description": "The active USTEC M5 preset builds the first 30 minutes of the New York cash session, waits for a qualified breakout and accepts an entry only when the next closed M5 candle retests the broken boundary. It deliberately trades infrequently in exchange for a historically high closed-trade win rate.",
        "session": "09:30-11:30 New York / M5",
        "logic_audit": "Source-code verified",
        "logic_audit_note": "Readable MQ5 source, the selected 0.5R preset, optimization constraints and native MT5 validation reports were reviewed together.",
        "logic": [
            {"title": "Build the 30-minute New York opening range", "detail": "The EA measures the USTEC high, low and broker tick activity from 09:30 through 10:00 New York time, with automatic US daylight-saving and live broker-server conversion."},
            {"title": "Reject weak or abnormal opening sessions", "detail": "Opening activity must reach 0.60 of its 20-session median and opening-range width must remain between 0.05 and 0.35 of the historical daily ATR, removing very quiet and unusually expanded opens."},
            {"title": "Demand a strong volume-backed breakout", "detail": "A completed M5 breakout candle needs at least 0.70 relative tick volume, a real body covering at least 75% of its range, a small daily-ATR boundary buffer and directional agreement with session VWAP."},
            {"title": "Enter only on the immediate retest", "detail": "The selected preset allows one closed M5 retest bar after the breakout. Price must return to the broken range edge without exceeding the configured pre-retest excursion or tolerance limits."},
            {"title": "Apply the time-direction schedule", "detail": "Both directions are permitted from 10:00 to 10:29 New York, only longs from 10:30 to 10:59, and only shorts from 11:00 until the 11:30 entry cutoff."},
            {"title": "Risk to the opposite range and target 0.5R", "detail": "The stop is placed beyond the opposite opening-range boundary with a five-percent range buffer, excessive ATR-sized stops and wide spreads are rejected, take profit is 0.5R, and exposure is closed by 15:55 New York."},
        ],
        "risk_note": "The BAT version uses the installer's adaptive equity-risk percentage and disables the research-only USD 300 fixed-risk override. The exact one-year comparison used 1% risk; a smaller shared portfolio risk is appropriate when several EAs run together.",
        "price": 449,
        "accent": "mint",
        "featured": True,
    },
    "US100 ORB 2R": {
        "strategy": "Selective New York opening-range retest",
        "tagline": "The higher-payoff US100 ORB variant, targeting 2R after a volume- and VWAP-qualified retest.",
        "description": "The active USTEC M5 preset builds the first 30 minutes of the New York cash session, waits for a strong breakout and permits up to three completed M5 candles for a retest entry. It uses the same selective time-direction schedule as the 0.5R edition, but demands stronger breakout activity and manages the position toward a 2R target.",
        "session": "09:30-11:30 New York / M5",
        "logic_audit": "Source-code verified",
        "logic_audit_note": "Readable MQ5 source, the V3 2R preset and its native MT5 validation reports were reviewed together.",
        "logic": [
            {"title": "Build the 30-minute New York opening range", "detail": "The EA measures the USTEC high, low and broker tick activity from 09:30 through 10:00 New York time, using automatic US daylight-saving and live broker-server conversion."},
            {"title": "Reject weak or abnormal opening sessions", "detail": "Opening activity must reach 0.60 of its 20-session median and range width must remain between 0.05 and 0.35 of the historical daily ATR, excluding unusually quiet or expanded opens."},
            {"title": "Demand the stronger 2R breakout threshold", "detail": "A completed M5 breakout candle needs at least 0.90 relative tick volume, a body covering at least 75% of its range, a daily-ATR boundary buffer and directional agreement with session VWAP."},
            {"title": "Allow a measured three-bar retest window", "detail": "After the qualified breakout, as many as three completed M5 candles may retest the broken opening-range edge, but excessive pre-retest excursion or a tolerance violation cancels the setup."},
            {"title": "Apply the selective time-direction schedule", "detail": "Both directions are permitted from 10:00 to 10:29 New York, only longs from 10:30 to 10:59, and only shorts from 11:00 until the 11:30 entry cutoff."},
            {"title": "Protect at 1R and target 2R", "detail": "The stop starts beyond the opposite range boundary with a five-percent buffer, moves to break-even at 1R, targets 2R, rejects excessive stop or spread conditions and closes exposure by 15:55 New York."},
        ],
        "risk_note": "Dynamic equity risk controlled by the installer's adaptive percentage, defaulting to 1%. The 2R and 0.5R editions can signal on the same session, so their combined risk must be treated as additive.",
        "price": 449,
        "accent": "cyan",
        "featured": True,
    },
    "ATR Candle Breakout": {
        "strategy": "Large-candle momentum",
        "tagline": "Trades exceptionally large H1 gold candles that finish near their directional extreme.",
        "description": "This vendor EA is available only as a compiled EX5. Its manual and active inputs show a closed-candle momentum model: a candle must be unusually large versus ATR, have enough real body and finish near its high or low. Internal source-level implementation details cannot be independently inspected in this package.",
        "session": "H1 / time filter disabled",
        "logic_audit": "Input-audited binary",
        "logic_audit_note": "The vendor manual and exact BAT preset were reviewed. No MQ5 source exists locally, so claims are limited to documented behavior and visible inputs.",
        "logic": [
            {"title": "Scan each closed H1 candle", "detail": "The active signal timeframe is H1 and its volatility baseline is ATR over 250 bars."},
            {"title": "Demand an extreme expansion", "detail": "A signal candle must be at least 2.5 times ATR and its real body must occupy at least 20% of the full high-low range."},
            {"title": "Require a strong directional close", "detail": "A bullish candidate must finish near its own high and a bearish candidate near its own low; the permitted distance is 25% of candle range. Trend, higher-timeframe ATR, time-of-day and support/resistance filters are all disabled in the active preset."},
            {"title": "Enter in the expansion direction", "detail": "The vendor manual defines buys from qualified bullish candles and sells from qualified bearish candles. Because the product is EX5-only, the exact order-call timing cannot be source-audited here."},
            {"title": "Use percentage-of-price exits", "detail": "Stop loss is 0.5% of entry price and take profit is 2.0% of entry price, producing a nominal 4:1 reward-to-risk distance before spread and slippage. Trailing stop is disabled."},
            {"title": "Size from a fixed cash-risk input", "detail": "The EA itself consumes a fixed account-currency risk amount. The installer rewrites that amount to approximately 1% of detected balance at deployment; it does not continuously compound with equity unless reinstalled."},
        ],
        "risk_note": "Approximately 1% of the balance detected when the BAT is installed, expressed as a fixed cash-risk input. It is not continuously recalculated from live equity inside the compiled EA.",
        "price": 399,
        "accent": "amber",
        "featured": True,
    },
    "AAA Final Asia Breakout": {
        "strategy": "Asia-range close and retest breakout",
        "tagline": "An H1 gold breakout of the 00:00-08:00 UTC range with a same-candle threshold retest.",
        "description": "The source code defines a precise session breakout, not a generic Asia model. It measures the 00:00-08:00 UTC range, then accepts only an H1 candle that closes outside a buffered boundary while its wick also touches that breakout threshold.",
        "session": "08:00-13:59 UTC / H1",
        "logic_audit": "Source-code verified",
        "logic_audit_note": "The strategy wrapper, shared execution engine and exact active preset were reviewed.",
        "logic": [
            {"title": "Measure the Asian range", "detail": "M15 bars from 00:00 through 07:59 UTC define the current day's high, low and midpoint. Broker time is converted to UTC; the preset uses the EET/EEST tester clock model."},
            {"title": "Evaluate only the London transition", "detail": "Signals are checked on each new H1 bar from 08:00 through 13:59 UTC. The EA allows no new setup if it already has exposure or has opened a trade that UTC day."},
            {"title": "Require a buffered close and touch", "detail": "The buffer is 3% of the Asian range. A buy requires the closed H1 candle above range high plus buffer while that candle's low touched the threshold. A sell is the mirror condition below range low."},
            {"title": "Enter at market with a midpoint stop", "detail": "The order is sent when the confirming H1 candle has closed. Both long and short stops are placed at the Asian range midpoint."},
            {"title": "Target 3R", "detail": "Take profit is three times the distance from market entry to the midpoint stop. Lot size targets 1% of current account equity."},
            {"title": "Trail only after a large move", "detail": "The source hard-codes trailing to start at +2R and then keep the stop 0.5R behind current price. These values override the generic 1.5R/1R fields visible elsewhere in the shared input panel."},
        ],
        "risk_note": "Dynamic 1% of current equity with one trade per UTC day. Actual loss can exceed the planned amount if price gaps through the midpoint stop.",
        "price": 249,
        "accent": "violet",
    },
    "AAA Final DmC": {
        "strategy": "Previous-day body rejection",
        "tagline": "Trades H1 rejection candles at the real-body edges of the previous daily candle.",
        "description": "The installed DmC source does not implement a multi-stage displacement/FVG model. It uses the open and close of the previous D1 candle as two reaction levels and enters when the last H1 candle probes one edge, closes back through it and finishes in the reversal direction.",
        "session": "All sessions / H1",
        "logic_audit": "Source-code verified",
        "logic_audit_note": "The wrapper, shared strategy engine and exact XAUUSD preset were reviewed. The public explanation follows the implemented conditions rather than the strategy name.",
        "logic": [
            {"title": "Map yesterday's real body", "detail": "The EA takes the higher and lower of the previous D1 open and close. Daily wicks are not used as the reaction levels."},
            {"title": "Look for a lower-body rejection", "detail": "A buy requires the previous closed H1 candle to trade at or below the lower body edge, close back above it and be bullish."},
            {"title": "Look for an upper-body rejection", "detail": "A sell requires the previous closed H1 candle to trade at or above the upper body edge, close back below it and be bearish."},
            {"title": "Limit frequency", "detail": "Checks happen once per new H1 bar. The EA will not enter while it has an order or position and will not open more than one trade per UTC day."},
            {"title": "Use a fixed XAUUSD price-distance stop", "detail": "The active stop is 22.5 XAUUSD price units below a buy entry or above a sell entry. The take profit is 1.7 times that initial risk distance."},
            {"title": "Size from current equity", "detail": "Volume targets 1% of current equity through the broker's contract calculation. The generic trailing inputs are not called by this strategy, so the active DmC implementation does not trail."},
        ],
        "risk_note": "Dynamic 1% of current equity with a 22.5-price-unit stop and 1.7R target. There is no spread cap or trailing logic in the active DmC code path.",
        "price": 199,
        "accent": "rose",
    },
    "Go Long": {
        "strategy": "Timed daily long",
        "tagline": "A deliberately simple US30 system that buys once at a fixed server time and exits the same day.",
        "description": "The active preset has no directional indicator or new-high requirement: it is a time-based long-only strategy. The vendor binary opens a buy at the configured server time, protects it with a percentage stop and closes it near the end of the server day.",
        "session": "01:05-23:50 broker server time",
        "logic_audit": "Input-audited binary",
        "logic_audit_note": "The vendor manual and active preset were reviewed. The EX5 has no local MQ5 source, so undocumented internal checks cannot be independently verified.",
        "logic": [
            {"title": "Long side only", "detail": "The vendor manual states that the EA only opens buy positions, intended for markets such as index CFDs that have a persistent upward tendency."},
            {"title": "Enter at 01:05 server time", "detail": "The active preset opens at 01:05 broker server time. 'Wait for new day high' is OFF, so a new daily high is not required before entry."},
            {"title": "Use no profit target", "detail": "Take-profit calculation is OFF. Break-even and classic trailing-stop calculation are also OFF."},
            {"title": "Protect with a percentage stop", "detail": "The base preset stop is 0.76430161% of the position's open price. The auto installer recalculates the exact hard-stop percentage for the connected broker contract when targeting its planned cash risk."},
            {"title": "Close at 23:50 server time", "detail": "Same-day time closure is enabled, so any surviving US30 position is instructed to close at 23:50 broker server time."},
            {"title": "Deploy with broker-specific size", "detail": "The installer forces fixed-volume mode and writes a broker-specific lot size plus hard stop designed around approximately 1% of detected balance at deployment."},
        ],
        "risk_note": "Approximately 1% of detected balance at installation, implemented with a fixed lot and broker-specific hard-stop percentage. It is not continuous equity-percent sizing inside the compiled EA.",
        "price": 179,
        "accent": "blue",
    },
    "AAA Final EMA3": {
        "strategy": "Three-EMA trend breakout",
        "tagline": "An H4 five-bar breakout gated by EMA 20/50 alignment and the slope of EMA 200.",
        "description": "EMA3 combines trend alignment with a small Donchian-style structure break. It waits for the completed H4 candle to close beyond the previous five bars while EMA 20, EMA 50 and a rising or falling EMA 200 agree with the direction.",
        "session": "All sessions / H4",
        "logic_audit": "Source-code verified",
        "logic_audit_note": "The wrapper, shared strategy engine and active XAUUSD H4 preset were reviewed.",
        "logic": [
            {"title": "Define the five-bar structure", "detail": "At every new H4 bar, the EA finds the highest high and lowest low of the five candles before the just-closed signal candle."},
            {"title": "Require the three-EMA trend", "detail": "For a buy, EMA 20 must be above EMA 50, the signal close must be above EMA 200, and EMA 200 must be above its value six H4 bars earlier. A sell uses the exact inverse."},
            {"title": "Demand a closing breakout", "detail": "The just-closed H4 candle must finish above the five-bar high for a long or below the five-bar low for a short. A wick through the level without a closing break is insufficient."},
            {"title": "Enter at market", "detail": "The order is submitted at the first tick of the new H4 bar, provided there is no existing position or pending order for this EA and symbol."},
            {"title": "Use the opposite five-bar extreme", "detail": "Long stop loss is the five-bar low; short stop loss is the five-bar high. Take profit is 1.7 times the entry-to-stop distance."},
            {"title": "Trail after +1.5R", "detail": "At +1.5R, the stop begins following current price at a distance of 1R. Each trade is dynamically sized to 1% of current equity."},
        ],
        "risk_note": "Dynamic 1% of current equity, with the stop at the opposite five-bar extreme and a 1.7R target. Wide H4 structures produce smaller volume and gaps can exceed the planned loss.",
        "price": 349,
        "accent": "lime",
        "featured": True,
    },
    "AAA Final XAU Weakness": {
        "strategy": "Repeated-level continuation breakout",
        "tagline": "M15 pending breakouts from equal highs or lows after a strong directional impulse.",
        "description": "Despite its name, the active code is not a general weakness oscillator or reversal model. It searches recent M15 bars for two similar highs or two similar lows and, after a qualifying prior impulse, places a stop order for continuation through that repeated level.",
        "session": "No session filter / M15",
        "logic_audit": "Source-code verified",
        "logic_audit_note": "The wrapper, shared strategy engine and active XAUUSD M15 preset were reviewed.",
        "logic": [
            {"title": "Find a repeated M15 level", "detail": "The EA scans 36 bars for two highs or two lows separated by at least four candles. The two prices must be within 0.20 ATR(14). If both exist, the source checks the equal-high case first."},
            {"title": "Confirm the preceding impulse", "detail": "A repeated high is tradable only after an upward move of at least 2 ATR; a repeated low requires a downward move of at least 2 ATR. The impulse is measured from older bars around the first level."},
            {"title": "Place a continuation stop", "detail": "For equal highs, a buy stop is placed 0.05 ATR above resistance. For equal lows, a sell stop is placed 0.05 ATR below support."},
            {"title": "Anchor the stop to the intervening range", "detail": "The long stop goes below the lowest price in the pattern range by 0.05 ATR; the short stop goes above its highest price by the same buffer. Target is fixed at 2R."},
            {"title": "Expire stale orders", "detail": "The pending order expires after eight M15 bars, or two hours. No new setup is evaluated while that order or its resulting position remains active; same-magic cleanup removes any stray pending order after a fill."},
            {"title": "Size but do not trail", "detail": "Each setup targets 1% of current equity. The generic trailing input is visible but this strategy code path never calls the trailing function. There is no session or once-per-day filter."},
        ],
        "risk_note": "Dynamic 1% of current equity per pending setup with a structure-based stop and 2R target. This preset has no spread cap and no trailing stop in its active code path.",
        "price": 149,
        "accent": "red",
    },
    "Nasdaq Overnight": {
        "strategy": "Overnight anomaly",
        "tagline": "Long Nasdaq after a negative New York close, then exit one minute before the next cash open.",
        "description": "This is a long-only close-to-open anomaly implementation. It reconstructs the New York cash session from M1 data, compares today's 16:00 close with the previous trading day's 16:00 close, and buys only when that return is negative.",
        "session": "16:00 to 09:29 New York",
        "logic_audit": "Source-code verified",
        "logic_audit_note": "Readable MQ5 source and the active USTEC preset were reviewed, including exact US daylight-saving conversion.",
        "logic": [
            {"title": "Rebuild the completed cash session", "detail": "The EA reads 09:30-15:59 New York M1 bars and requires at least 300 session bars. It also finds the prior trading day's 15:59 close."},
            {"title": "Require a negative close-to-close day", "detail": "The active definition is today's 16:00 cash close below the previous trading day's close. Threshold is 0%, so any strictly negative return qualifies."},
            {"title": "Buy just after 16:00 New York", "detail": "One long may be opened during the ten-minute window beginning at the cash close. Friday entries are allowed and may be held through the weekend."},
            {"title": "Use an emergency stop only", "detail": "The protective stop is 2% below entry price. There is no take profit; the position remains exposed to overnight gaps."},
            {"title": "Exit before the next cash open", "detail": "A position from an earlier New York date is closed beginning at 09:29, with a 31-minute permitted exit window."},
            {"title": "Handle account and clock differences", "detail": "Lot size targets 1% of current equity to the 2% emergency stop. Broker-to-UTC offset and exact modern New York DST rules are resolved automatically in live trading."},
        ],
        "risk_note": "Dynamic 1% of current equity to a stop 2% below entry. Weekend and overnight gaps can bypass that stop, so realized risk is not capped at exactly 1%.",
        "price": 229,
        "accent": "indigo",
    },
    "Turnaround Tuesday": {
        "strategy": "Calendar effect",
        "tagline": "A long-only Monday-to-Tuesday Nasdaq hold with a daily 9-period moving-average gate.",
        "description": "The vendor strategy buys early-week setbacks for a Tuesday recovery. In the active preset it can open a long on Monday at 01:05 server time, subject to a D1 9-period simple moving-average filter, and closes on Tuesday at 23:50.",
        "session": "Monday 01:05 to Tuesday 23:50 server time",
        "logic_audit": "Input-audited binary",
        "logic_audit_note": "The vendor manual and active preset were reviewed. No MQ5 source exists locally, so the exact MA comparison tick and any undocumented checks cannot be source-audited.",
        "logic": [
            {"title": "Long-only early-week setup", "detail": "The vendor manual defines only buy trades, intended to capture a recovery after an early-week setback."},
            {"title": "Apply the daily MA gate", "detail": "The active filter is a 9-period simple moving average on D1, calculated from the open price. The manual states that price must be on the correct long side of that average."},
            {"title": "Enter Monday at 01:05", "detail": "Open day is Monday and the configured entry time is 01:05 broker server time. Waiting for a new daily high is disabled."},
            {"title": "Hold without a profit target", "detail": "Take profit, break-even and classic trailing stop are all disabled in the active preset."},
            {"title": "Use a hard percentage stop", "detail": "The base hard stop is 0.75241337% of entry price. During automatic deployment the installer can rewrite the percentage for the broker contract and chosen fixed lot."},
            {"title": "Exit Tuesday at 23:50", "detail": "Any surviving position is instructed to close at 23:50 server time on Tuesday. The installer chooses a fixed lot and stop intended to approximate 1% of detected balance at installation."},
        ],
        "risk_note": "Approximately 1% of detected balance at installation via broker-specific fixed lot and hard-stop percentage. The compiled EA does not continuously resize from current equity.",
        "price": 149,
        "accent": "orange",
    },
    "AAA Final US100 Weakness": {
        "strategy": "10:00 reference-pair reversal",
        "tagline": "Contrarian USTEC OCO orders around the 09:15 candle after the 10:00 New York candle closes.",
        "description": "The active implementation is a precise time-and-reference pattern. It compares the direction of the M15 candle opened at 10:00 New York with the 09:15 candle and the 03:00-08:00 New York range, then places two opposite-direction pending entries around the 09:15 high and low.",
        "session": "10:15-12:00 New York / M15",
        "logic_audit": "Source-code verified",
        "logic_audit_note": "The wrapper, shared strategy engine and active USTEC M15 preset were reviewed.",
        "logic": [
            {"title": "Capture two reference structures", "detail": "The EA records the exact 09:15 New York M15 candle high/low and the full 03:00-08:00 New York session high/low."},
            {"title": "Evaluate the 10:00 candle after it closes", "detail": "At the new bar around 10:15, the just-closed candle must have opened at exactly 10:00 New York. The strategy is allowed only once per UTC day and only when no order or position already exists."},
            {"title": "Fade bullish strength", "detail": "If the 10:00 candle is bullish and the early-session high is above the 09:15 high, the EA prepares shorts: a sell limit at the 09:15 high and a sell stop at the 09:15 low."},
            {"title": "Fade bearish weakness", "detail": "If the 10:00 candle is bearish and the early-session low is below the 09:15 low, the EA prepares longs: a buy limit at the 09:15 low and a buy stop at the 09:15 high."},
            {"title": "Use a common session-extreme stop", "detail": "Both short orders share the 03:00-08:00 high as stop; both long orders share that session's low. Each target is 1.7R and each order receives half of the 1% risk budget."},
            {"title": "Operate as OCO until noon", "detail": "Orders expire at 12:00 New York. Once one becomes a position, the remaining pending order is deleted. The active code has no trailing stop even though generic trailing fields appear in the input panel."},
        ],
        "risk_note": "Two pending orders are each sized at 0.5% of current equity, for 1% planned setup risk. OCO cleanup begins after a fill, so fast gaps or simultaneous fills can produce different realized exposure.",
        "price": 149,
        "accent": "pink",
    },
    "Nasdaq 5M Open EMA ATR": {
        "strategy": "Literal US-open EMA/ATR hold",
        "tagline": "Trade the first Nasdaq M5 close against EMA 12 and hold until the ATR stop or trail ends the position.",
        "description": "This is the literal version of the one-candle US-open experiment. After the 09:30-09:35 New York M5 candle closes, it buys above EMA 12 or sells below EMA 12. It has no take profit and no session-close exit: a 3x ATR initial stop and 4x ATR ratcheting trail are the only exits.",
        "session": "09:30 New York",
        "logic_audit": "Source-code verified",
        "logic_audit_note": "Readable MQ5 source and the exact literal-hold BAT preset were reviewed. ATR(14) is the volatility indicator; 3 and 4 are stop-distance multipliers, not ATR periods.",
        "logic": [
            {"title": "Wait for the opening candle to finish", "detail": "The signal is evaluated only when the closed M5 candle is timestamped 09:30 New York, meaning entry occurs just after the 09:30-09:35 bar has completed. Weekends are rejected and New York DST is calculated automatically."},
            {"title": "Make one EMA decision", "detail": "Close above the 12-period M5 EMA triggers a long; close below it triggers a short. Equality produces no trade. Both directions are active and only one entry is allowed per New York date."},
            {"title": "Set a 3x ATR emergency stop", "detail": "The initial stop is three times M5 ATR(14) from entry, widened only when required by the broker's minimum stop or freeze distance. No fixed take profit is placed."},
            {"title": "Begin the 4x ATR trail immediately", "detail": "TrailStartR is zero. The EA tracks the most favorable M5 high or low since entry and proposes a stop four times the current M5 ATR(14) behind that extreme."},
            {"title": "Only ratchet the stop", "detail": "A trailing update is accepted only if it improves the existing stop and remains outside the broker freeze/stops distance. The trail never loosens."},
            {"title": "Hold until volatility exits the trade", "detail": "Session closing is disabled, so a surviving position may continue overnight or across a weekend until its hard stop or improving ATR trail closes it. Only one entry is permitted per New York date and live risk is 1% of current equity."},
        ],
        "risk_note": "Dynamic 1% of current equity to a 3x ATR(14) initial stop. There is no take profit or time exit; overnight and weekend gaps can exceed the intended risk, and the public one-year maximum equity drawdown was 20.91%.",
        "price": 499,
        "accent": "cyan",
        "featured": True,
    },
    "AAA Final News Pulse - NFP CPI FOMC - LONG ONLY ROBUST 60s": {
        "strategy": "Scheduled news momentum",
        "tagline": "One long-only XAUUSD buy-stop placed 30 seconds before selected US macro releases.",
        "description": "The active preset is not a two-sided straddle. It watches NFP, CPI and FOMC in MT5's USD economic calendar, waits for a fresh broker-stamped quote, and places only a buy stop shortly before release. It has no take profit and closes all remaining exposure 60 seconds after the event.",
        "session": "NFP, CPI and FOMC",
        "logic_audit": "Source-code verified",
        "logic_audit_note": "Readable News Pulse v2.11 source and the active long-only 60-second BAT preset were reviewed. Live and tester event discovery are intentionally different.",
        "logic": [
            {"title": "Find only target USD events", "detail": "Live trading scans the native MT5 economic calendar for non-private Nonfarm Payrolls, Consumer Price Index, FOMC statements or Federal Reserve rate decisions. It looks ahead eight days and refreshes the cached event every 300 seconds."},
            {"title": "Anchor timing to the broker", "detail": "Calendar timestamps and quote timestamps are both broker-server time. VPS local timezone is ignored. Placement is blocked unless the terminal is connected and the latest quote arrived within five seconds."},
            {"title": "Place one buy stop at T-30 seconds", "detail": "During the final 30 seconds before release, the active long-only preset places a buy stop 6.0 XAUUSD price units above Ask. The sell side is disabled."},
            {"title": "Attach a 6.0-unit hard stop", "detail": "Stop loss is 6.0 XAUUSD price units below the pending entry. Volume targets 1% of current equity to that stop. No take profit is attached."},
            {"title": "Trail after +1.5R", "detail": "Once favorable movement reaches 9.0 price units, the EA may ratchet the stop to 15.0 price units behind current Bid. Because that trail is wider than the trigger gain, it improves the original stop only as price moves farther."},
            {"title": "Force a short event lifecycle", "detail": "At T+60 seconds the EA deletes any unfilled pending order and closes any open News Pulse position. State is stored by account, symbol and magic number so the lifecycle can recover after a terminal restart."},
        ],
        "risk_note": "Dynamic 1% of current equity to the 6.0-unit stop before release. News gaps, slippage, rejected modifications or a market that jumps over the stop can cause materially larger realized loss.",
        "price": 549,
        "accent": "yellow",
        "featured": True,
    },
}


def slugify(value: str) -> str:
    value = value.lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def _extract_string(block: str, name: str) -> str:
    match = re.search(rf"\b{name}\s*=\s*'([^']*)'", block)
    return match.group(1) if match else ""


def parse_installer_items() -> list[dict[str, Any]]:
    """Parse the literal portfolio entries from the active installer's Get-PortfolioItems."""
    text = INSTALLER_PATH.read_text(encoding="utf-8-sig")
    start = text.index("$items = @(")
    end = text.index("\n    foreach ($item in $items)", start)
    section = text[start:end]
    blocks = re.findall(r"\[pscustomobject\]@\{(.*?)\n\s{8}\}(?:,|\s*$)", section, re.DOTALL | re.MULTILINE)
    items: list[dict[str, Any]] = []
    for block in blocks:
        label = _extract_string(block, "Label")
        if not label:
            continue
        period_match = re.search(r"\bPeriod\s*=\s*(\d+)", block)
        set_source = _extract_string(block, "SetSource")
        if not set_source and re.search(r"\bSetSource\s*=\s*\$atrSet", block):
            set_source = "ATR Candle Breakout EA\\RETEST PASSED 2026-08-07 - ATR Candle Breakout - XAUUSD H1 - 1pct.set"
        items.append(
            {
                "label": label,
                "canonical": _extract_string(block, "Canonical"),
                "period_minutes": int(period_match.group(1)) if period_match else 0,
                "expert": _extract_string(block, "Expert"),
                "expert_source": _extract_string(block, "ExpertSource"),
                "set_source": set_source,
                "optional_symbol": bool(re.search(r"\bOptionalSymbol\s*=\s*\$true", block)),
            }
        )
    if not items:
        raise RuntimeError(f"No portfolio items could be parsed from {INSTALLER_PATH}")
    return items


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _status_for(pf: float, return_pct: float, drawdown: float, trades: int) -> str:
    if pf >= 1.20 and return_pct > 0 and drawdown <= 25 and trades >= 25:
        return "Validated evidence"
    if pf >= 1.0 and return_pct > 0:
        return "Research evidence"
    return "Experimental"


def _one_year_evidence() -> dict[str, Evidence]:
    path = PACKAGE_ROOT / "Active BAT Backtest 2026-08-12" / "portfolio-results.json"
    if not path.exists():
        return {}
    data = _load_json(path)
    result: dict[str, Evidence] = {}
    aliases = {
        "13-aaa-final-news-pulse": "AAA Final News Pulse - NFP CPI FOMC - LONG ONLY ROBUST 60s",
    }
    for row in data.get("bots", []):
        label = aliases.get(row.get("id", ""), row["label"])
        pf = float(row["profit_factor"])
        ret = float(row["return_pct"])
        dd = float(row["equity_dd_pct"])
        trades = int(row["trades"])
        result[label] = Evidence(
            label="Latest complete one-year MT5 backtest",
            period="2025-08-11 to 2026-08-10",
            return_pct=ret,
            profit_factor=pf,
            drawdown_pct=dd,
            win_rate_pct=float(row["win_rate_pct"]),
            trades=trades,
            history_quality=str(row.get("history_quality", "99%")),
            source_note="Exness, every-tick modelling from synchronized broker M1 history, random execution delay and the exact active BAT preset.",
            chart_path=Path(row["chart_path"]) if row.get("chart_path") else None,
            status=_status_for(pf, ret, dd, trades),
            caution="One historical year is not a guarantee of future performance.",
        )
    return result


def _nasdaq_open_one_year_evidence() -> Evidence | None:
    path = PACKAGE_ROOT / "Nasdaq 5M Open EMA ATR Research 2026-08-20" / "literal-hold-results.json"
    if not path.exists():
        return None
    rows = _load_json(path)
    row = next((item for item in rows if item.get("case") == "literal-hold-website-one-year"), None)
    if row is None:
        return None
    profit_factor = float(row["profit_factor"])
    return_pct = float(row["return_pct"])
    drawdown = float(row["equity_dd_pct"])
    trades = int(row["trades"])
    chart = Path(str(row["graph"]))
    return Evidence(
        label="Latest complete one-year MT5 backtest",
        period="2025-08-11 to 2026-08-10",
        return_pct=return_pct,
        profit_factor=profit_factor,
        drawdown_pct=drawdown,
        win_rate_pct=float(row["win_rate"]),
        trades=trades,
        history_quality=f"{row.get('history_quality_pct', 100):.0f}%",
        source_note="Exness USTEC, synchronized Every Tick MT5 test with commission, swap and random execution delay using the literal EMA12 / ATR3 / Trail4 hold preset.",
        chart_path=chart if chart.exists() else None,
        status=_status_for(profit_factor, return_pct, drawdown, trades),
        caution="One historical year is not a guarantee of future performance.",
    )


def _us100_orb_one_year_evidence(version: str) -> Evidence | None:
    result_files = {
        "0.5R": "native-rr05-bat-one-year-results.json",
        "2R": "native-v3-time-direction-results.json",
    }
    path = PACKAGE_ROOT / "US100 Selective ORB Research 2026-08-21" / result_files[version]
    if not path.exists():
        return None
    rows = _load_json(path)
    row = next((item for item in rows if item.get("case") == "one-year-2025-2026"), None)
    if row is None:
        return None
    chart = Path(str(row["graph"]))
    trade_count = int(row["trades"])
    caution = (
        f"Only {trade_count} trades occurred in this one-year window, so the displayed win rate and profit factor "
        "are not statistically dependable."
    )
    return Evidence(
        label="Latest complete one-year MT5 backtest",
        period="2025-08-11 to 2026-08-10" if version == "0.5R" else "2025-08-21 to 2026-08-20",
        return_pct=float(row["return_pct"]),
        profit_factor=float(row["profit_factor"]),
        drawdown_pct=float(row["equity_dd_pct"]),
        win_rate_pct=float(row["win_rate"]),
        trades=trade_count,
        history_quality=f"{float(row.get('history_quality_pct', 100)):.0f}%",
        source_note=f"Exness USTEC M5, synchronized MT5 Every Tick history, random execution delay and the exact {version} BAT adaptive-risk preset at 1% risk.",
        chart_path=chart if chart.exists() else None,
        status=_status_for(float(row["profit_factor"]), float(row["return_pct"]), float(row["equity_dd_pct"]), trade_count),
        caution=caution,
    )


def _meta_for(item: dict[str, Any]) -> dict[str, Any]:
    label = item["label"]
    canonical = item["canonical"]
    if label in CORE_META:
        meta = dict(CORE_META[label])
    elif label.startswith("Auction Stock "):
        ticker = label.removeprefix("Auction Stock ")
        meta = {
            "strategy": "Auction-market stock swing",
            "tagline": f"Value-area breakout and retest execution for {ticker}.",
            "description": f"Applies the shared Auction Market Value Area engine to {ticker}, using composite value, migration and breakout/retest conditions with the stock-specific BAT preset.",
            "session": "US equity session / swing",
            "logic_audit": "Development logic summary",
            "logic_audit_note": "This entry remains under development and is not offered as a completed product.",
            "logic": [
                {"title": "Build a composite profile", "detail": "Creates tick-activity POC, VAH and VAL reference levels from the configured lookback."},
                {"title": "Measure value migration", "detail": "Classifies whether composite value is balanced or moving directionally."},
                {"title": "Wait for break and retest", "detail": "Requires the stock-specific breakout and return conditions from the development preset."},
                {"title": "Use preset-defined management", "detail": "Stop, target and maximum hold are supplied by the instrument preset."},
            ],
            "risk_note": "Development preset; risk and execution behavior are not offered as production-ready.",
            "price": 149,
            "accent": "sky",
        }
    elif label.startswith("Auction Market "):
        instrument = label.removeprefix("Auction Market ")
        meta = {
            "strategy": "Auction-market value area",
            "tagline": f"Composite value and breakout/retest logic for {instrument}.",
            "description": f"Applies the objective technical layer of an auction-market framework to {instrument}: composite profile location, value migration and break/retest execution.",
            "session": "H4/D1 swing",
            "logic_audit": "Development logic summary",
            "logic_audit_note": "This entry remains under development and is not offered as a completed product.",
            "logic": [
                {"title": "Build composite value", "detail": "Calculates POC, VAH and VAL over the configured technical lookback."},
                {"title": "Classify value behavior", "detail": "Measures whether value is balanced or migrating."},
                {"title": "Wait for auction confirmation", "detail": "Looks for the configured failed-auction or break-and-retest condition."},
                {"title": "Apply instrument management", "detail": "Target and maximum hold come from the symbol-specific development preset."},
            ],
            "risk_note": "Development preset; risk and execution behavior are not offered as production-ready.",
            "price": 229 if instrument not in {"XAU", "XAG"} else 299,
            "accent": "teal",
        }
    else:
        meta = {
            "strategy": "Rules-based MT5 automation",
            "tagline": f"The active {canonical} configuration from the installer.",
            "description": "This page is generated from the current active BAT portfolio entry and its supplied settings file.",
            "session": "Preset-defined",
            "logic_audit": "Preset summary",
            "logic_audit_note": "A dedicated source-level explanation has not yet been connected for this entry.",
            "logic": [
                {"title": "Read market context", "detail": "Uses the symbol and timeframe configured by the installer."},
                {"title": "Wait for a deterministic signal", "detail": "Entry behavior is controlled by the supplied EA and preset."},
                {"title": "Calculate deployment size", "detail": "Risk inputs are supplied by the active installer configuration."},
                {"title": "Manage the position", "detail": "Stops, targets and exits follow the EA's configured rules."},
            ],
            "risk_note": "Preset-defined risk; verify the generated settings on the connected broker before live use.",
            "price": 199,
            "accent": "slate",
        }
    if canonical in {"XAUUSD", "XAGUSD"}:
        category, asset_group = "Metals", "metals"
    elif canonical in {"USTEC", "US30", "SP500"}:
        category, asset_group = "Indices", "indices"
    elif canonical in {"BTCUSD", "ETHUSD"}:
        category, asset_group = "Crypto", "crypto"
    else:
        category, asset_group = "Stocks", "stocks"
    meta["category"] = category
    meta["asset_group"] = asset_group
    return meta


def _buy_url(label: str, price: int) -> str:
    text = (
        f"Hello Hama, I want to buy {label} for USD {price}. "
        "Please confirm compatibility, license terms and delivery details."
    )
    return f"https://wa.me/{WHATSAPP_NUMBER}?text={quote_plus(text)}"


@lru_cache(maxsize=1)
def get_catalog() -> list[Product]:
    one_year = _one_year_evidence()
    nasdaq_open = _nasdaq_open_one_year_evidence()
    us100_orb_rr05 = _us100_orb_one_year_evidence("0.5R")
    us100_orb_rr20 = _us100_orb_one_year_evidence("2R")
    products: list[Product] = []
    for item in parse_installer_items():
        meta = _meta_for(item)
        evidence = one_year.get(item["label"])
        if item["label"] == "Nasdaq 5M Open EMA ATR":
            evidence = nasdaq_open
        elif item["label"] == "US100 ORB 0.5R":
            evidence = us100_orb_rr05
        elif item["label"] == "US100 ORB 2R":
            evidence = us100_orb_rr20
        one_year_result = evidence
        limitations = [
            "Historical returns are not guaranteed and live execution can differ.",
            "Broker symbol names, spread, slippage and contract size affect results.",
        ]
        if item["optional_symbol"]:
            limitations.append("This BAT entry is optional and only installs when the broker exposes a compatible symbol.")
        if evidence and evidence.caution:
            limitations.append(evidence.caution)
        price = int(meta["price"])
        display_label = (
            "News Pulse"
            if item["label"].startswith("AAA Final News Pulse")
            else re.sub(r"^AAA Final\s+", "", item["label"]).strip()
        )
        development = item["label"].startswith("Auction ")
        products.append(
            Product(
                label=display_label,
                installer_label=item["label"],
                canonical=item["canonical"],
                period_minutes=item["period_minutes"],
                expert=item["expert"],
                expert_source=item["expert_source"],
                set_source=item["set_source"],
                optional_symbol=item["optional_symbol"],
                slug=slugify(display_label),
                timeframe=TIMEFRAMES.get(item["period_minutes"], f"{item['period_minutes']}m"),
                category=meta["category"],
                asset_group=meta["asset_group"],
                strategy=meta["strategy"],
                tagline=meta["tagline"],
                description=meta["description"],
                session=meta["session"],
                risk_note=meta["risk_note"],
                logic_audit=meta["logic_audit"],
                logic_audit_note=meta["logic_audit_note"],
                logic=meta["logic"],
                limitations=limitations,
                price=price,
                accent=meta["accent"],
                featured=bool(meta.get("featured", False)),
                development=development,
                evidence=evidence,
                one_year_evidence=one_year_result,
                one_year_return_pct=one_year_result.return_pct if one_year_result else None,
                one_year_note=None,
                buy_url="" if development else _buy_url(display_label, price),
            )
        )
    return products


def get_sellable_catalog() -> list[Product]:
    return [product for product in get_catalog() if not product.development]


def get_development_catalog() -> list[Product]:
    return [product for product in get_catalog() if product.development]


def get_product(slug: str) -> Product | None:
    return next((product for product in get_sellable_catalog() if product.slug == slug), None)


def package_buy_url(package_name: str, price: int) -> str:
    text = (
        f"Hello Hama, I am interested in the {package_name} for USD {price}. "
        "Please confirm the included EAs, compatibility, license and delivery terms."
    )
    return f"https://wa.me/{WHATSAPP_NUMBER}?text={quote_plus(text)}"

// Calyx Nasdaq 5M for Quantower (futures: NQ / MNQ). Port of the production MT5 EA
// "Nasdaq 5M DI Wide ATR EA" (Nasdaq 5M Carry Replace Deployment 2026-11-09, EX5 2488443f62a8) with the Best 1-Step inputs.
// Owner 2026-11-19: "let's start with the 5m bot". Rules, one for one (see ../RULES.md):
//   * M5 bars. When the 09:30 New York bar closes (Mon-Fri), direction = close vs EMA(12) of closes on that bar (close above = long, below = short).
//   * Optional DI filter (MT5 iADX +DI / -DI, period 14) on the same bar; OFF by default (profile default).
//   * At most one entry per New York date. Carry = REPLACE: a position still open at the signal is closed and today's signal taken.
//   * Market entry, stop = entry -/+ 6 x ATR(14) of the signal bar (MT5 iATR = simple average of true range). No take profit.
//   * Trailing: once open profit >= 1R (initial risk), stop = best price since entry -/+ 6 x ATR(14) of the current bar; only tightens.
//   * No session-end close (holds overnight) unless FlatTimeNY is set (futures prop firms: e.g. 16:09 = 15:09 CT).
//   * Risk: % of account balance per trade; contracts rounded DOWN (skip if < 1) by default; MT5 rounded UP (option).
// Indicators are computed here from the bars with MT5's formulas (not Quantower's built-ins) so signals match our MT5 backtests.
// Futures accounts net per contract: run this on a contract no other bot trades on the same account.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using TradingPlatform.BusinessLayer;

namespace CalyxQuantower
{
    public sealed class CalyxNasdaq5M : Strategy, ICurrentAccount, ICurrentSymbol
    {
        [InputParameter("Symbol (NQ or MNQ front month)", 0)]
        public Symbol CurrentSymbol { get; set; }

        [InputParameter("Account", 1)]
        public Account CurrentAccount { get; set; }

        [InputParameter("Risk % of balance per trade", 2, 0.01, 5.0, 0.01, 2)]
        public double RiskPercent { get; set; } = 0.375;   // Best 1-Step: 0.5% x 0.75 Nasdaq factor

        [InputParameter("Round contracts up (MT5 behaviour)", 3)]
        public bool RoundUp { get; set; } = false;

        [InputParameter("Max contracts", 4, 1, 100, 1, 0)]
        public int MaxContracts { get; set; } = 10;

        [InputParameter("Require DI agreement", 5)]
        public bool RequireDI { get; set; } = false;

        [InputParameter("Allow long", 6)]
        public bool AllowLong { get; set; } = true;

        [InputParameter("Allow short", 7)]
        public bool AllowShort { get; set; } = true;

        [InputParameter("EMA period", 8, 2, 500, 1, 0)]
        public int EmaPeriod { get; set; } = 12;

        [InputParameter("ATR period", 9, 2, 500, 1, 0)]
        public int AtrPeriod { get; set; } = 14;

        [InputParameter("DI period", 10, 2, 500, 1, 0)]
        public int DiPeriod { get; set; } = 14;

        [InputParameter("Initial stop (x ATR)", 11, 0.1, 50, 0.1, 2)]
        public double InitialStopAtr { get; set; } = 6.0;

        [InputParameter("Trailing stop (x ATR)", 12, 0.1, 50, 0.1, 2)]
        public double TrailingAtr { get; set; } = 6.0;

        [InputParameter("Trail starts at (R)", 13, 0, 20, 0.1, 2)]
        public double TrailStartR { get; set; } = 1.0;

        [InputParameter("Signal bar hour NY", 14, 0, 23, 1, 0)]
        public int SignalHourNY { get; set; } = 9;

        [InputParameter("Signal bar minute NY", 15, 0, 59, 1, 0)]
        public int SignalMinuteNY { get; set; } = 30;

        [InputParameter("Carry: 0 skip, 2 replace, 3 replace if opposite", 16, 0, 3, 1, 0)]
        public int CarryMode { get; set; } = 2;

        [InputParameter("Flat time NY (HHMM, -1 = hold overnight)", 17, -1, 2359, 1, 0)]
        public int FlatTimeNY { get; set; } = -1;

        [InputParameter("Trading enabled (OFF = signals only, no orders)", 18)]
        public bool TradingEnabled { get; set; } = false;

        [InputParameter("History days to load", 19, 3, 60, 1, 0)]
        public int HistoryDays { get; set; } = 10;

        private HistoricalData hd;
        private string positionId;          // the position this strategy opened (futures accounts net per contract)
        private int lastEntryKey;           // New York yyyymmdd of the last entry (one entry per NY date)
        private double initialRisk;         // price distance entry - initial stop
        private DateTime entryTimeUtc;
        private int entryDirection;
        private DateTime lastManageUtc = DateTime.MinValue;
        private readonly object sync = new object();

        public CalyxNasdaq5M() : base()
        {
            this.Name = "Calyx Nasdaq 5M";
            this.Description = "Port of the Calyx MT5 Nasdaq 5M EA (09:30 NY bar vs EMA12, ATR6 stop, ATR6 trail from +1R, replace carry).";
        }

        protected override void OnRun()
        {
            if (this.CurrentSymbol == null || this.CurrentAccount == null) { this.Log("Choose a symbol and an account.", StrategyLoggingLevel.Error); this.Stop(); return; }
            this.CurrentSymbol = Core.Instance.GetSymbol(this.CurrentSymbol.CreateInfo());
            this.CurrentAccount = Core.Instance.GetAccount(this.CurrentAccount.CreateInfo());
            LoadState();
            this.hd = this.CurrentSymbol.GetHistory(Period.MIN5, this.CurrentSymbol.HistoryType, Now().AddDays(-this.HistoryDays));
            this.hd.NewHistoryItem += this.OnNewBar;
            this.CurrentSymbol.NewLast += this.OnNewLast;
            this.CurrentSymbol.NewQuote += this.OnNewQuote;
            Core.Instance.PositionRemoved += this.OnPositionRemoved;
            this.Log(string.Format(CultureInfo.InvariantCulture, "Started on {0}, account {1}, risk {2}%, DI {3}, trading {4}, flat {5}. Bars loaded: {6}.",
                this.CurrentSymbol.Name, this.CurrentAccount.Name, this.RiskPercent, this.RequireDI ? "ON" : "OFF", this.TradingEnabled ? "ON" : "OFF (signals only)",
                this.FlatTimeNY < 0 ? "hold overnight" : this.FlatTimeNY.ToString("0000"), this.hd.Count), StrategyLoggingLevel.Info);
        }

        protected override void OnStop()
        {
            if (this.hd != null) { this.hd.NewHistoryItem -= this.OnNewBar; this.hd.Dispose(); this.hd = null; }
            if (this.CurrentSymbol != null) { this.CurrentSymbol.NewLast -= this.OnNewLast; this.CurrentSymbol.NewQuote -= this.OnNewQuote; }
            Core.Instance.PositionRemoved -= this.OnPositionRemoved;
            SaveState();
        }

        // ---------- bars (index 0 = oldest) ----------
        private List<N5Bar> Bars()
        {
            var list = new List<N5Bar>();
            if (this.hd == null) return list;
            for (int i = this.hd.Count - 1; i >= 0; i--)          // SeekOriginHistory.End: 0 = newest
                if (this.hd[i, SeekOriginHistory.End] is HistoryItemBar b) list.Add(new N5Bar(b.TimeLeft, b.Open, b.High, b.Low, b.Close));
            return list;
        }

        // ---------- signal: runs when a new M5 bar starts, i.e. the previous bar just closed ----------
        private void OnNewBar(object sender, HistoryEventArgs e)
        {
            lock (this.sync)
            {
                try { ProcessClosedBar(); }
                catch (Exception ex) { this.Log("Signal error: " + ex.Message, StrategyLoggingLevel.Error); }
            }
        }

        private void ProcessClosedBar()
        {
            var b = Bars();
            if (b.Count < Math.Max(this.EmaPeriod, this.AtrPeriod) + 3) return;
            int s = b.Count - 2;                                     // the bar that just closed (the last one is forming)
            if (!N5Logic.IsSignalBar(b[s], this.SignalHourNY, this.SignalMinuteNY)) return;
            int key = N5Logic.NyDateKey(N5Logic.ToNY(b[s].TimeUtc));
            Position held = OurPosition();
            if (held != null && this.CarryMode == 0) { this.Log("09:30 signal skipped: previous trade still open (carry 0).", StrategyLoggingLevel.Info); return; }
            if (this.lastEntryKey == key) return;

            var sig = N5Logic.Evaluate(b, s, this.EmaPeriod, this.AtrPeriod, this.DiPeriod, this.RequireDI, this.AllowLong, this.AllowShort);
            if (sig.Direction == 0) { this.Log("09:30 NY: no entry (" + sig.Reason + ").", StrategyLoggingLevel.Info); return; }
            int dir = sig.Direction; double ema = sig.Ema, atr = sig.Atr;
            this.Log(string.Format(CultureInfo.InvariantCulture, "09:30 NY signal {0}: close {1} vs EMA{2} {3:F2}, ATR{4} {5:F2}.", dir > 0 ? "LONG" : "SHORT",
                b[s].Close, this.EmaPeriod, ema, this.AtrPeriod, atr), StrategyLoggingLevel.Info);

            if (!this.TradingEnabled) { this.lastEntryKey = key; SaveState(); return; }
            if (held != null)
            {
                int heldDir = held.Side == Side.Buy ? 1 : -1;
                if (this.CarryMode == 3 && heldDir == dir) return;
                var close = held.Close();
                if (close.Status != TradingOperationResultStatus.Success) { this.Log("Carry close failed: " + close.Message, StrategyLoggingLevel.Error); return; }
                this.positionId = null;
            }
            else if (ForeignPosition() != null) { this.Log("Entry refused: a position on this contract/account was not opened by this strategy (futures accounts net per contract).", StrategyLoggingLevel.Error); return; }
            Enter(dir, atr, key);
        }

        private void Enter(int dir, double atr, int key)
        {
            double price = dir > 0 ? this.CurrentSymbol.Ask : this.CurrentSymbol.Bid;
            if (price <= 0 || double.IsNaN(price)) { this.Log("No quote; entry skipped.", StrategyLoggingLevel.Error); return; }
            double stop = this.CurrentSymbol.RoundPriceToTickSize(price - dir * this.InitialStopAtr * atr, double.NaN);
            double risk = Math.Abs(price - stop);
            double tick = this.CurrentSymbol.TickSize, tickCost = this.CurrentSymbol.GetTickCost(price);
            if (risk <= 0 || tick <= 0 || tickCost <= 0) { this.Log("Invalid stop / tick data; entry skipped.", StrategyLoggingLevel.Error); return; }
            double perContract = risk / tick * tickCost, budget = this.CurrentAccount.Balance * this.RiskPercent / 100.0;
            double raw = budget / perContract;
            int qty = (int)(this.RoundUp ? Math.Ceiling(raw - 1e-9) : Math.Floor(raw + 1e-9));
            qty = Math.Min(qty, this.MaxContracts);
            if (qty < 1) { this.Log(string.Format(CultureInfo.InvariantCulture, "Entry skipped: 1 contract risks {0:F0} > budget {1:F0}.", perContract, budget), StrategyLoggingLevel.Info); this.lastEntryKey = key; SaveState(); return; }
            var market = Core.Instance.OrderTypes.FirstOrDefault(x => x.ConnectionId == this.CurrentSymbol.ConnectionId && x.Behavior == OrderTypeBehavior.Market);
            if (market == null) { this.Log("No market order type on this connection.", StrategyLoggingLevel.Error); return; }
            var result = Core.Instance.PlaceOrder(new PlaceOrderRequestParameters
            {
                Account = this.CurrentAccount,
                Symbol = this.CurrentSymbol,
                Side = dir > 0 ? Side.Buy : Side.Sell,
                OrderTypeId = market.Id,
                Quantity = qty,
                StopLoss = SlTpHolder.CreateSL(stop, PriceMeasurement.Absolute),
                Comment = "Calyx N5M"
            });
            if (result.Status != TradingOperationResultStatus.Success) { this.Log("Entry rejected: " + result.Message, StrategyLoggingLevel.Error); return; }
            this.lastEntryKey = key; this.initialRisk = risk; this.entryTimeUtc = Now(); this.entryDirection = dir; this.positionId = null;
            SaveState();
            this.Log(string.Format(CultureInfo.InvariantCulture, "ENTRY {0} {1} x {2} at ~{3}, stop {4} (risk {5:F0} = {6:F2}% of balance).", dir > 0 ? "BUY" : "SELL", qty,
                this.CurrentSymbol.Name, price, stop, qty * perContract, 100 * qty * perContract / this.CurrentAccount.Balance), StrategyLoggingLevel.Trading);
        }

        // ---------- positions ----------
        // platform clock: simulated time in Backtest & Optimize, real UTC time live
        private static DateTime Now() => Core.Instance.TimeUtils.DateTimeUtcNow;

        private IEnumerable<Position> PositionsHere() =>
            Core.Instance.Positions.Where(p => p.Symbol == this.CurrentSymbol && p.Account == this.CurrentAccount);

        private Position OurPosition()
        {
            var here = PositionsHere().ToList();
            if (this.positionId != null) return here.FirstOrDefault(p => p.Id == this.positionId);
            // just after an entry the id is not known yet: adopt the position opened after our entry, in our direction
            var p0 = here.FirstOrDefault(p => this.entryDirection != 0 && (p.Side == Side.Buy ? 1 : -1) == this.entryDirection && p.OpenTime >= this.entryTimeUtc.AddMinutes(-1));
            if (p0 != null) { this.positionId = p0.Id; SaveState(); }
            return p0;
        }

        private Position ForeignPosition() => PositionsHere().FirstOrDefault(p => p.Id != this.positionId);

        private void OnPositionRemoved(Position p)
        {
            if (p != null && p.Id == this.positionId) { this.Log("Position closed: " + p.Id, StrategyLoggingLevel.Trading); this.positionId = null; this.entryDirection = 0; SaveState(); }
        }

        // ---------- management on every price update (throttled to 1 s) ----------
        private void OnNewLast(Symbol s, Last l) => Manage();
        private void OnNewQuote(Symbol s, Quote q) => Manage();

        private void Manage()
        {
            if (!this.TradingEnabled) return;
            DateTime now = Now();
            if ((now - this.lastManageUtc).TotalSeconds < 1) return;
            this.lastManageUtc = now;
            lock (this.sync)
            {
                try { ManagePosition(); }
                catch (Exception ex) { this.Log("Manage error: " + ex.Message, StrategyLoggingLevel.Error); }
            }
        }

        private void ManagePosition()
        {
            var pos = OurPosition();
            if (pos == null) return;
            bool buy = pos.Side == Side.Buy;
            if (this.FlatTimeNY >= 0)
            {
                var ny = N5Logic.ToNY(Now());
                if (ny.DayOfWeek != DayOfWeek.Saturday && ny.DayOfWeek != DayOfWeek.Sunday && ny.Hour * 100 + ny.Minute >= this.FlatTimeNY)
                {
                    var r = pos.Close();
                    this.Log("Flat-time close: " + r.Status, StrategyLoggingLevel.Trading);
                    return;
                }
            }
            if (this.TrailingAtr <= 0) return;
            double current = buy ? this.CurrentSymbol.Bid : this.CurrentSymbol.Ask;
            double risk = this.initialRisk > 0 ? this.initialRisk : Math.Abs(pos.OpenPrice - (StopOrder(pos)?.TriggerPrice ?? pos.OpenPrice));
            if (risk <= 0 || current <= 0) return;
            double favorable = buy ? current - pos.OpenPrice : pos.OpenPrice - current;
            if (this.TrailStartR > 0 && favorable < this.TrailStartR * risk) return;

            var b = Bars(); if (b.Count < this.AtrPeriod + 2) return;
            double atr = N5Logic.Atr(b, this.AtrPeriod)[b.Count - 1];              // current (forming) bar, as MT5 iATR shift 0
            if (atr <= 0) return;
            DateTime opened = pos.OpenTime;
            double extreme = current;
            for (int i = b.Count - 1; i >= 0; i--)                          // M5 bars from the bar containing the entry
            {
                extreme = buy ? Math.Max(extreme, b[i].High) : Math.Min(extreme, b[i].Low);
                if (b[i].TimeUtc <= opened) break;
            }
            double candidate = this.CurrentSymbol.RoundPriceToTickSize(extreme + (buy ? -1 : 1) * this.TrailingAtr * atr, double.NaN);
            var sl = StopOrder(pos);
            if (sl == null) { this.Log("No stop order found for the position; trail not applied.", StrategyLoggingLevel.Error); return; }
            double stop = sl.TriggerPrice, t = this.CurrentSymbol.TickSize;
            bool improves = buy ? candidate > stop + t / 2 && candidate < current : candidate < stop - t / 2 && candidate > current;
            if (!improves) return;
            var res = Core.Instance.ModifyOrder(new ModifyOrderRequestParameters(sl) { TriggerPrice = candidate });
            if (res.Status == TradingOperationResultStatus.Success) this.Log(string.Format(CultureInfo.InvariantCulture, "Trail stop {0} -> {1}", stop, candidate), StrategyLoggingLevel.Trading);
            else this.Log("Trail modify failed: " + res.Message, StrategyLoggingLevel.Error);
        }

        private Order StopOrder(Position pos) =>
            Core.Instance.Orders.FirstOrDefault(o => o.PositionId == pos.Id && o.OrderType != null && o.OrderType.Behavior == OrderTypeBehavior.Stop);

        // ---------- restart-safe state (one small text file per strategy instance) ----------
        private string StateFile()
        {
            string dir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "CalyxQuantower");
            Directory.CreateDirectory(dir);
            string acc = this.CurrentAccount?.Id ?? "na", sym = this.CurrentSymbol?.Name ?? "na";
            foreach (char c in Path.GetInvalidFileNameChars()) { acc = acc.Replace(c, '_'); sym = sym.Replace(c, '_'); }
            return Path.Combine(dir, "n5m-" + acc + "-" + sym + ".txt");
        }

        private void SaveState()
        {
            try
            {
                File.WriteAllText(StateFile(), string.Join("|", this.positionId ?? "", this.lastEntryKey.ToString(CultureInfo.InvariantCulture),
                    this.initialRisk.ToString("R", CultureInfo.InvariantCulture), this.entryDirection.ToString(CultureInfo.InvariantCulture),
                    this.entryTimeUtc.Ticks.ToString(CultureInfo.InvariantCulture)));
            }
            catch (Exception ex) { this.Log("State save failed: " + ex.Message, StrategyLoggingLevel.Error); }
        }

        private void LoadState()
        {
            try
            {
                string f = StateFile(); if (!File.Exists(f)) return;
                var x = File.ReadAllText(f).Split('|'); if (x.Length < 5) return;
                this.positionId = x[0].Length > 0 ? x[0] : null;
                this.lastEntryKey = int.Parse(x[1], CultureInfo.InvariantCulture);
                this.initialRisk = double.Parse(x[2], CultureInfo.InvariantCulture);
                this.entryDirection = int.Parse(x[3], CultureInfo.InvariantCulture);
                this.entryTimeUtc = new DateTime(long.Parse(x[4], CultureInfo.InvariantCulture), DateTimeKind.Utc);
                if (this.positionId != null && !PositionsHere().Any(p => p.Id == this.positionId)) this.positionId = null;
                this.Log("State restored: last entry " + this.lastEntryKey + (this.positionId != null ? ", managing position " + this.positionId : ""), StrategyLoggingLevel.Info);
            }
            catch (Exception ex) { this.Log("State load failed: " + ex.Message, StrategyLoggingLevel.Error); }
        }
    }
}

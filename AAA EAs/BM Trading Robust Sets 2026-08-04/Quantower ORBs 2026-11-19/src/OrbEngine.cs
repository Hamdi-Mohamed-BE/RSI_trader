// Generic Calyx ORB engine - port of the MT5 "Evidence-driven opening range breakout research EA" v1.20 (src_df47e0981de0.mqh, shared by
// Packages/ORB-only and Packages/Edge10). Ported: session/range/volume filters, direct and retest entries, VWAP and EMA-trend options, the
// three stop modes, fixed target, break-even, candle trail, flat time, research UTC session gate and the dynamic trailing SL (src_e24726d64fb4.mqh).
// NOT ported (unused by every preset): tick-activity volume profile filters, paper-tick stop entry, Markov regime filter.
using System;
using System.Collections.Generic;

namespace CalyxQuantower.Orbs
{
    public sealed class OrbSettings
    {
        public string Name = "ORB";
        public bool SessionUtc;                    // false = New York clock, true = UTC clock
        public int SessionHour = 9, SessionMinute = 30, OpeningRangeMinutes = 15, TradeWindowMinutes = 120, FlatHour = 15, FlatMinute = 55;
        public bool WeekdaysOnly = true;
        public int SignalTf = 5;
        public int RelativeVolumeDays = 20; public double MinOpeningRelativeVolume = 0.8;
        public int BarVolumeLookback = 20; public double MinBreakoutRelativeVolume = 1.1;
        public int AtrTf = 15, AtrPeriod = 14; public double MinRangeAtr = 0.35, MaxRangeAtr = 1.8;
        public bool RequireVwap; public bool UseEmaTrend; public int FastEma = 20, SlowEma = 50;
        public bool RetestEntry; public int TradeDirection;   // 0 both, 1 long only, 2 short only
        public bool RequireOpeningCandleDirection;
        public double BreakoutBodyMinimum = 0.55, BreakoutBufferAtr = 0.03; public int RetestBars = 3; public double RetestToleranceAtr = 0.15, RetestBodyMinimum = 0.3;
        public int StopMode = 1;                   // 0 signal candle, 1 opposite range, 2 daily ATR
        public double StopBufferAtr = 0.1, MaximumStopAtr = 2.0, DailyAtrStopFraction = 0.1;
        public bool UseFixedTarget = true; public double RewardRisk = 0.5, BreakEvenAtR, TrailStartAtR, TrailCandleBufferAtr = 0.1;
        public double MaxSpreadRangePercent = 12.0;
        public int ResearchSession;                // 0 all, 1 Asia 0-8, 2 London 7-12, 3 New York 13-21, 4 overlap 13-16 (UTC)
        public bool UseDynamicTrailing; public double DynamicTriggerFraction = 0.5, DynamicLockFraction = 0.2;

        // ---- presets = the exact MT5 package inputs ----
        public static OrbSettings Us100H1Orb13Utc() => new OrbSettings   // Packages/ORB-only us100-h1-orb-13utc (USTEC M15)
        {
            Name = "US100 H1 ORB 13UTC", SessionUtc = true, SessionHour = 13, SessionMinute = 0, OpeningRangeMinutes = 60, TradeWindowMinutes = 60, FlatHour = 20, FlatMinute = 0,
            SignalTf = 15, MinOpeningRelativeVolume = 0.5, MinBreakoutRelativeVolume = 0.7, AtrTf = 60, MinRangeAtr = 0.35, MaxRangeAtr = 4.0,
            StopMode = 1, MaximumStopAtr = 3.0, RewardRisk = 0.5, BreakEvenAtR = 0.0, ResearchSession = 0
        };
        public static OrbSettings Us100NyM30() => new OrbSettings        // us100-orb-new-york-m30 (USTEC M30)
        {
            Name = "US100 ORB New York M30", SessionHour = 9, SessionMinute = 30, OpeningRangeMinutes = 5, TradeWindowMinutes = 180, FlatHour = 15, FlatMinute = 55,
            SignalTf = 30, MinOpeningRelativeVolume = 0.6, MinBreakoutRelativeVolume = 0.8, AtrTf = 15, MinRangeAtr = 0.2, MaxRangeAtr = 1.8,
            StopMode = 1, MaximumStopAtr = 2.0, RewardRisk = 0.5, BreakEvenAtR = 0.0, ResearchSession = 3
        };
        public static OrbSettings XauNyM30() => new OrbSettings          // xau-orb-new-york-m30 (XAUUSD M30)
        {
            Name = "XAU ORB New York M30", SessionHour = 9, SessionMinute = 30, OpeningRangeMinutes = 30, TradeWindowMinutes = 180, FlatHour = 15, FlatMinute = 55,
            SignalTf = 30, MinOpeningRelativeVolume = 0.6, MinBreakoutRelativeVolume = 0.8, AtrTf = 15, MinRangeAtr = 0.2, MaxRangeAtr = 1.8,
            StopMode = 1, MaximumStopAtr = 2.0, RewardRisk = 0.5, BreakEvenAtR = 0.5, ResearchSession = 3
        };
        /// <summary>Best 1-Step / Edge10 ORB VP Volume Confirmed (XAUUSD M5): 2.5R + dynamic trailing. rr05 = the funded_v1 0.5R version (no dynamic trail).</summary>
        public static OrbSettings OrbVpVolumeConfirmed(bool rr05) => new OrbSettings
        {
            Name = rr05 ? "ORB VP Volume Confirmed 0.5R" : "ORB VP Volume Confirmed 2.5R", SessionHour = 9, SessionMinute = 30, OpeningRangeMinutes = 15, TradeWindowMinutes = 120,
            FlatHour = 15, FlatMinute = 55, SignalTf = 5, MinOpeningRelativeVolume = 0.8, MinBreakoutRelativeVolume = 1.1, AtrTf = 15, MinRangeAtr = 0.2, MaxRangeAtr = 1.2,
            StopMode = 1, MaximumStopAtr = 2.0, RewardRisk = rr05 ? 0.5 : 2.5, BreakEvenAtR = 1.0, ResearchSession = 0, UseDynamicTrailing = !rr05
        };
    }

    public sealed class OrbEngine : IEngine
    {
        private readonly OrbSettings s;
        public OrbEngine(OrbSettings settings) { s = settings; }
        public string Name => s.Name;
        public int[] Timeframes => new[] { 1, s.SignalTf, s.AtrTf, 15 };
        public int HistoryDays => 45;

        private DateTime lastSignalBar = DateTime.MinValue, lastM15 = DateTime.MinValue, lastRangeTry = DateTime.MinValue;
        private int sessionKey; private bool rangeReady, tradedToday;
        private double rangeHigh, rangeLow, rangeOpen, rangeClose, atr, initialRisk, dtsDistance; private int openingDirection;
        private int breakoutDir, breakoutAge; private DateTime dtsTrackedOpen = DateTime.MinValue;
        private const string Scope = "orb";

        private DateTime ToSession(DateTime utc) => s.SessionUtc ? utc : Clock.ToNY(utc);
        private DateTime SessionToUtc(DateTime sessionDate, int h, int mi) =>
            s.SessionUtc ? new DateTime(sessionDate.Year, sessionDate.Month, sessionDate.Day, h, mi, 0, DateTimeKind.Utc) : Clock.NyToUtc(sessionDate, h, mi);
        private DateTime Anchor(DateTime sessionDate) => SessionToUtc(sessionDate, s.SessionHour, s.SessionMinute);

        public void OnTick(IMarket m)
        {
            DateTime now = m.NowUtc; if (now == default) return;
            if (s.UseDynamicTrailing) ManageDynamicTrailing(m);
            DateTime ns = ToSession(now);
            var sig = m.Bars(s.SignalTf); if (sig.Count < 2) return;
            DateTime current = sig[sig.Count - 1].T; bool newBar = current != lastSignalBar; if (newBar) lastSignalBar = current;
            int key = Clock.Key(ns);
            if (key != sessionKey) ResetSession(m, key);
            ManagePosition(m, ns, newBar);
            if (tradedToday) return;
            if (s.WeekdaysOnly && !Clock.Weekday(ns)) return;
            DateTime rs = Anchor(ns.Date), re = rs.AddMinutes(s.OpeningRangeMinutes), te = re.AddMinutes(s.TradeWindowMinutes);
            if (now < re || now >= te) return;
            if (!rangeReady)
            {
                if (lastRangeTry == current) return;               // MT5 retries every tick; the result only changes when data changes: once per signal bar
                lastRangeTry = current;
                if (!BuildOpeningRange(m, ns.Date)) return;
            }
            if (!newBar) return;
            EvaluateClosedBar(m, rs, re, te);
        }

        private void ResetSession(IMarket m, int key)
        {
            sessionKey = key; rangeReady = false; tradedToday = m.HadEntryOnKey(Scope, key); lastRangeTry = DateTime.MinValue;
            rangeHigh = rangeLow = rangeOpen = rangeClose = atr = 0; openingDirection = 0; breakoutDir = 0; breakoutAge = 0;
        }

        private double OpeningWindow(IMarket m, DateTime sessionDate, out double hi, out double lo, out int bars, out double wo, out double wc)
        {
            DateTime from = Anchor(sessionDate), to = from.AddMinutes(s.OpeningRangeMinutes).AddSeconds(-1);
            var r = Series.Between(m.Bars(1), from, to); bars = r.Count; hi = lo = wo = wc = 0;
            if (bars <= 0) return 0;
            hi = double.MinValue; lo = double.MaxValue; wo = r[0].O; wc = r[bars - 1].C; double v = 0;
            foreach (var x in r) { hi = Math.Max(hi, x.H); lo = Math.Min(lo, x.L); v += x.V; }
            return v;
        }

        private double PreviousOpeningVolumeMedian(IMarket m, DateTime sessionDate)
        {
            var samples = new List<double>(); DateTime d = sessionDate; int attempts = 0;
            while (samples.Count < s.RelativeVolumeDays && attempts < s.RelativeVolumeDays * 3 + 15)
            {
                d = d.AddDays(-1); attempts++;
                if (s.WeekdaysOnly && !Clock.Weekday(d)) continue;
                double v = OpeningWindow(m, d, out _, out _, out int bars, out _, out _);
                if (bars < Math.Max(1, s.OpeningRangeMinutes / 2) || v <= 0) continue;
                samples.Add(v);
            }
            return Series.Median(samples);
        }

        private bool LastClosed(IMarket m, int tf, out IReadOnlyList<Bar> b, out int i) { b = m.Bars(tf); i = b.Count - 2; return i >= 1; }

        private bool BuildOpeningRange(IMarket m, DateTime sessionDate)
        {
            double vol = OpeningWindow(m, sessionDate, out rangeHigh, out rangeLow, out int bars, out rangeOpen, out rangeClose);
            if (bars < Math.Max(1, s.OpeningRangeMinutes / 2) || vol <= 0 || rangeHigh <= rangeLow) return false;
            if (!LastClosed(m, s.AtrTf, out var ab, out int ai)) return false;
            atr = Ind.Atr(ab, s.AtrPeriod, ai); if (atr <= 0) return false;
            double median = PreviousOpeningVolumeMedian(m, sessionDate); if (median <= 0) return false;
            double relVol = vol / median;
            openingDirection = rangeClose > rangeOpen ? 1 : rangeClose < rangeOpen ? -1 : 0;
            double ratio = (rangeHigh - rangeLow) / atr;
            if (ratio < s.MinRangeAtr || ratio > s.MaxRangeAtr) return false;
            if (relVol < s.MinOpeningRelativeVolume) return false;
            rangeReady = true;
            m.Log($"{s.Name}: range {rangeLow}-{rangeHigh} ({ratio:F2} ATR), opening rel. volume {relVol:F2}.");
            return true;
        }

        private double BarRelativeVolume(IMarket m, Bar signal)
        {
            var prior = Series.Between(m.Bars(s.SignalTf), signal.T.AddMinutes(-(s.BarVolumeLookback + 5) * s.SignalTf), signal.T.AddSeconds(-1));
            if (prior.Count <= 0) return 0;
            int use = Math.Min(prior.Count, s.BarVolumeLookback); var v = new List<double>();
            for (int i = prior.Count - use; i < prior.Count; i++) v.Add(prior[i].V);
            double med = Series.Median(v);
            return med > 0 ? signal.V / med : 0;
        }

        private double SessionVwap(IMarket m, DateTime from, DateTime through)
        {
            double w = 0, vol = 0;
            foreach (var x in Series.Between(m.Bars(s.SignalTf), from, through)) { w += (x.H + x.L + x.C) / 3.0 * x.V; vol += x.V; }
            return vol > 0 ? w / vol : 0;
        }

        private bool TrendAllows(IMarket m, int dir)
        {
            if (!s.UseEmaTrend) return true;
            if (!LastClosed(m, s.AtrTf, out var b, out int i)) return false;
            double f = Ind.Ema(b, s.FastEma, i), sl = Ind.Ema(b, s.SlowEma, i);
            return dir > 0 ? f > sl : f < sl;
        }

        private bool DirectionAllows(int dir)
        {
            if (s.TradeDirection == 1 && dir < 0) return false;
            if (s.TradeDirection == 2 && dir > 0) return false;
            if (s.RequireOpeningCandleDirection && dir != openingDirection) return false;
            return true;
        }

        private bool SessionGate(DateTime utc)
        {
            if (s.ResearchSession == 0) return true;
            int md = Clock.MinuteOfDay(utc);
            switch (s.ResearchSession)
            {
                case 1: return md >= 0 && md < 480;
                case 2: return md >= 420 && md < 720;
                case 3: return md >= 780 && md < 1260;
                case 4: return md >= 780 && md < 960;
                default: return true;
            }
        }

        private bool EnterTrade(IMarket m, int dir, Bar signal)
        {
            if (!SessionGate(m.NowUtc) || tradedToday) return false;
            if (rangeHigh <= rangeLow || (m.Ask - m.Bid) / (rangeHigh - rangeLow) * 100.0 > s.MaxSpreadRangePercent) return false;
            if (m.Position != null) return false;
            double entry = dir > 0 ? m.Ask : m.Bid, buffer = s.StopBufferAtr * atr, stop;
            if (s.StopMode == 2)
            {
                var day = Series.DailyUtc(m.Bars(15)); int di = day.Count - 2;          // MT5 iATR(D1) shift 1, UTC days
                double datr = Ind.Atr(day, s.AtrPeriod, di); if (datr <= 0) return false;
                stop = entry - dir * s.DailyAtrStopFraction * datr;
            }
            else if (s.StopMode == 1) stop = dir > 0 ? rangeLow - buffer : rangeHigh + buffer;
            else stop = dir > 0 ? signal.L - buffer : signal.H + buffer;
            stop = Round(m, stop);
            double risk = dir > 0 ? entry - stop : stop - entry;
            if (risk <= 0 || risk > s.MaximumStopAtr * atr) { m.Log($"{s.Name}: entry skipped, stop distance {risk:F2} vs max {s.MaximumStopAtr * atr:F2}."); return false; }
            double target = s.UseFixedTarget ? Round(m, entry + dir * s.RewardRisk * risk) : 0;
            if (!m.Enter(dir, stop, target, s.Name)) return false;
            tradedToday = true; initialRisk = risk; m.MarkEntry(Scope, sessionKey);
            return true;
        }

        private bool IsRetest(int dir, Bar b)
        {
            double tol = s.RetestToleranceAtr * atr;
            if (Series.Body(b) < s.RetestBodyMinimum) return false;
            if (dir > 0) return b.L <= rangeHigh + tol && b.L >= rangeHigh - 2 * tol && b.C >= rangeHigh && b.C > b.O;
            return b.H >= rangeLow - tol && b.H <= rangeLow + 2 * tol && b.C <= rangeLow && b.C < b.O;
        }

        private void EvaluateClosedBar(IMarket m, DateTime rs, DateTime re, DateTime te)
        {
            var sig = m.Bars(s.SignalTf); var bar = sig[sig.Count - 2];
            if (bar.T < re || bar.T >= te) return;
            if (breakoutDir != 0)
            {
                breakoutAge++;
                if (breakoutAge > s.RetestBars) { breakoutDir = 0; return; }
                if (IsRetest(breakoutDir, bar)) { int d = breakoutDir; breakoutDir = 0; EnterTrade(m, d, bar); }
                return;
            }
            if (Series.Body(bar) < s.BreakoutBodyMinimum) return;
            if (BarRelativeVolume(m, bar) < s.MinBreakoutRelativeVolume) return;
            double buffer = s.BreakoutBufferAtr * atr; int dir = 0;
            if (bar.C > rangeHigh + buffer && bar.C > bar.O) dir = 1;
            else if (bar.C < rangeLow - buffer && bar.C < bar.O) dir = -1;
            if (dir == 0 || !DirectionAllows(dir) || !TrendAllows(m, dir)) return;
            if (s.RequireVwap)
            {
                double vw = SessionVwap(m, rs, bar.T.AddMinutes(s.SignalTf).AddSeconds(-1));
                if (vw <= 0 || (dir > 0 && bar.C <= vw) || (dir < 0 && bar.C >= vw)) return;
            }
            if (!s.RetestEntry) EnterTrade(m, dir, bar);
            else { breakoutDir = dir; breakoutAge = 0; }
        }

        private void ManagePosition(IMarket m, DateTime ns, bool newBar)
        {
            var p = m.Position; if (p == null) return;
            if (Clock.MinuteOfDay(ns) >= s.FlatHour * 60 + s.FlatMinute) { m.Close(s.Name + " flat time"); return; }
            double current = p.Dir > 0 ? m.Bid : m.Ask, risk = initialRisk;
            if (risk <= 0 && p.Stop > 0) risk = Math.Abs(p.Entry - p.Stop);
            if (risk <= 0) return;
            double profit = p.Dir > 0 ? current - p.Entry : p.Entry - current, cand = p.Stop;
            if (s.BreakEvenAtR > 0 && profit >= s.BreakEvenAtR * risk)
            {
                if (p.Dir > 0 && (cand <= 0 || cand < p.Entry)) cand = p.Entry;
                if (p.Dir < 0 && (cand <= 0 || cand > p.Entry)) cand = p.Entry;
            }
            if (newBar && s.TrailStartAtR > 0 && profit >= s.TrailStartAtR * risk)
            {
                var sig = m.Bars(s.SignalTf); var c = sig[sig.Count - 2];
                double trail = Round(m, p.Dir > 0 ? c.L - s.TrailCandleBufferAtr * atr : c.H + s.TrailCandleBufferAtr * atr);
                if (p.Dir > 0 && trail > cand && trail < m.Bid) cand = trail;
                if (p.Dir < 0 && (cand <= 0 || trail < cand) && trail > m.Ask) cand = trail;
            }
            if (cand > 0 && Math.Abs(cand - p.Stop) >= m.TickSize) m.ModifyStop(Round(m, cand));
        }

        private void ManageDynamicTrailing(IMarket m)
        {
            var p = m.Position;
            if (p == null) { dtsTrackedOpen = DateTime.MinValue; }
            else if (dtsTrackedOpen != p.OpenUtc)                 // first sight of this position: remember its target distance
            {
                dtsTrackedOpen = p.OpenUtc;
                dtsDistance = p.Target > 0 ? Math.Abs(p.Target - p.Entry) : (p.Stop > 0 ? Math.Abs(p.Entry - p.Stop) : 0);
            }
            var b = m.Bars(15); if (b.Count < 2) return;
            DateTime cur = b[b.Count - 1].T;
            if (lastM15 == DateTime.MinValue) { lastM15 = cur; return; }
            if (cur == lastM15) return;
            lastM15 = cur;
            if (p == null || dtsDistance <= m.TickSize) return;
            double closed = b[b.Count - 2].C, desired;
            if (p.Dir > 0)
            {
                if (closed < p.Entry + s.DynamicTriggerFraction * dtsDistance) return;
                desired = Math.Min(p.Entry + s.DynamicLockFraction * dtsDistance, m.Bid - m.TickSize);
                if (desired <= p.Entry || (p.Stop > 0 && desired <= p.Stop + m.TickSize / 2)) return;
            }
            else
            {
                if (closed > p.Entry - s.DynamicTriggerFraction * dtsDistance) return;
                desired = Math.Max(p.Entry - s.DynamicLockFraction * dtsDistance, m.Ask + m.TickSize);
                if (desired >= p.Entry || (p.Stop > 0 && desired >= p.Stop - m.TickSize / 2)) return;
            }
            m.ModifyStop(Round(m, desired));
        }

        private static double Round(IMarket m, double price) => m.TickSize > 0 ? Math.Round(price / m.TickSize) * m.TickSize : price;
    }
}

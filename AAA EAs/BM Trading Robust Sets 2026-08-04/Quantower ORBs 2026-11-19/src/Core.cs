// Calyx bots for Quantower - shared core (no Quantower dependency). 2026-11-19.
// Bars, New York clock, MT5-exact indicators and the market interface the engines run on. The same engine code runs inside
// Quantower (QuantowerAdapter.cs) and in the offline bar-replay simulator used for the MT5 parity checks (test/).
using System;
using System.Collections.Generic;

namespace CalyxQuantower.Orbs
{
    public struct Bar
    {
        public DateTime T;          // open time, UTC
        public double O, H, L, C, V;  // V = volume (MT5 tick volume in the parity test; exchange volume in Quantower)
        public Bar(DateTime t, double o, double h, double l, double c, double v) { T = t; O = o; H = h; L = l; C = c; V = v; }
    }

    public sealed class PositionInfo
    {
        public int Dir;                 // +1 long, -1 short
        public double Entry, Stop, Target;   // Stop / Target 0 = none
        public DateTime OpenUtc;
        public double Quantity;
    }

    /// <summary>What an engine can see and do. Times are UTC; bars per timeframe in minutes (1, 5, 15, 30, 60), index 0 = oldest, last = forming.</summary>
    public interface IMarket
    {
        DateTime NowUtc { get; }
        IReadOnlyList<Bar> Bars(int minutes);
        double Bid { get; }
        double Ask { get; }
        double TickSize { get; }
        PositionInfo Position { get; }                       // this bot's open position, or null
        bool Enter(int dir, double stop, double target, string tag);   // market order; target 0 = none
        bool ModifyStop(double stop);
        bool Close(string reason);
        bool HadEntryOnKey(string scope, int dateKey);        // restart-safe "already traded on this session date"
        void MarkEntry(string scope, int dateKey);
        void Log(string message);
    }

    public interface IEngine
    {
        string Name { get; }
        int[] Timeframes { get; }         // bar sizes the engine reads (minutes); the adapter loads them
        int HistoryDays { get; }          // history needed
        void OnTick(IMarket m);           // called on every price update / timer and once per minute in the simulator
    }

    public static class Clock
    {
        public static readonly TimeZoneInfo NewYork = Find();

        private static TimeZoneInfo Find()
        {
            try { return TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time"); }
            catch { return TimeZoneInfo.FindSystemTimeZoneById("America/New_York"); }
        }

        public static DateTime ToNY(DateTime utc) => TimeZoneInfo.ConvertTimeFromUtc(DateTime.SpecifyKind(utc, DateTimeKind.Utc), NewYork);

        /// <summary>UTC time of a New York wall-clock time on the given NY date.</summary>
        public static DateTime NyToUtc(DateTime nyDate, int hour, int minute)
        {
            var local = new DateTime(nyDate.Year, nyDate.Month, nyDate.Day, hour, minute, 0, DateTimeKind.Unspecified);
            return TimeZoneInfo.ConvertTimeToUtc(local, NewYork);
        }

        public static int Key(DateTime d) => d.Year * 10000 + d.Month * 100 + d.Day;
        public static bool Weekday(DateTime d) => d.DayOfWeek != DayOfWeek.Saturday && d.DayOfWeek != DayOfWeek.Sunday;
        public static int MinuteOfDay(DateTime d) => d.Hour * 60 + d.Minute;
    }

    public static class Series
    {
        /// <summary>Index of the bar with this exact open time, or -1 (MT5 iBarShift exact=true, but as list index).</summary>
        public static int IndexAt(IReadOnlyList<Bar> b, DateTime t)
        {
            int lo = 0, hi = b.Count - 1;
            while (lo <= hi) { int mid = (lo + hi) >> 1; if (b[mid].T == t) return mid; if (b[mid].T < t) lo = mid + 1; else hi = mid - 1; }
            return -1;
        }

        /// <summary>Index of the last bar with open time &lt;= t, or -1 (MT5 iBarShift exact=false).</summary>
        public static int IndexAtOrBefore(IReadOnlyList<Bar> b, DateTime t)
        {
            int lo = 0, hi = b.Count - 1, ans = -1;
            while (lo <= hi) { int mid = (lo + hi) >> 1; if (b[mid].T <= t) { ans = mid; lo = mid + 1; } else hi = mid - 1; }
            return ans;
        }

        /// <summary>Bars with open time in [from, to] (MT5 CopyRates(from, to)).</summary>
        public static List<Bar> Between(IReadOnlyList<Bar> b, DateTime from, DateTime to)
        {
            var r = new List<Bar>();
            int lo = 0, hi = b.Count - 1, start = b.Count;
            while (lo <= hi) { int mid = (lo + hi) >> 1; if (b[mid].T >= from) { start = mid; hi = mid - 1; } else lo = mid + 1; }
            for (int i = start; i < b.Count && b[i].T <= to; i++) r.Add(b[i]);
            return r;
        }

        public static double Median(List<double> v)
        {
            if (v.Count == 0) return 0;
            v.Sort();
            return v.Count % 2 == 1 ? v[v.Count / 2] : (v[v.Count / 2 - 1] + v[v.Count / 2]) * 0.5;
        }

        public static double Body(Bar b) { double w = b.H - b.L; return w > 0 ? Math.Abs(b.C - b.O) / w : 0; }

        /// <summary>Daily bars by UTC day (MT5 D1 on a UTC-server broker), built from intraday bars. Last = current (forming) day.</summary>
        public static List<Bar> DailyUtc(IReadOnlyList<Bar> intraday)
        {
            var d = new List<Bar>();
            foreach (var x in intraday)
            {
                var day = x.T.Date;
                if (d.Count == 0 || d[d.Count - 1].T != day) d.Add(new Bar(day, x.O, x.H, x.L, x.C, x.V));
                else { var y = d[d.Count - 1]; y.H = Math.Max(y.H, x.H); y.L = Math.Min(y.L, x.L); y.C = x.C; y.V += x.V; d[d.Count - 1] = y; }
            }
            return d;
        }
    }

    /// <summary>MT5 indicator formulas.</summary>
    public static class Ind
    {
        public static double TrueRange(IReadOnlyList<Bar> b, int i) =>
            i == 0 ? b[0].H - b[0].L : Math.Max(b[i].H, b[i - 1].C) - Math.Min(b[i].L, b[i - 1].C);

        /// <summary>iATR at index i: simple average of the true range over n bars ending at i.</summary>
        public static double Atr(IReadOnlyList<Bar> b, int n, int i)
        {
            if (i < n - 1 || i >= b.Count) return 0;
            double s = 0; for (int k = i - n + 1; k <= i; k++) s += TrueRange(b, k);
            return s / n;
        }

        /// <summary>iMA EMA of closes at index i (seed = first close of the list).</summary>
        public static double Ema(IReadOnlyList<Bar> b, int n, int i)
        {
            double a = 2.0 / (n + 1), e = b[0].C;
            for (int k = 1; k <= i; k++) e = b[k].C * a + e * (1 - a);
            return e;
        }

        /// <summary>iADX main line (ADX) at index i, MT5 ADX.mq5: +DI/-DI = EMA(100*DM/TR), DX = 100|+DI--DI|/(+DI+-DI), ADX = EMA(DX); buffers start at 0.</summary>
        public static double Adx(IReadOnlyList<Bar> b, int n, int i)
        {
            double a = 2.0 / (n + 1), pdi = 0, mdi = 0, adx = 0;
            for (int k = 1; k <= i; k++)
            {
                double up = b[k].H - b[k - 1].H, dn = b[k - 1].L - b[k].L;
                if (up < 0) up = 0;
                if (dn < 0) dn = 0;
                if (up > dn) dn = 0; else if (up < dn) up = 0; else { up = 0; dn = 0; }
                double tr = Math.Max(b[k].H, b[k - 1].C) - Math.Min(b[k].L, b[k - 1].C);
                double p = tr != 0 ? 100.0 * up / tr : 0, m = tr != 0 ? 100.0 * dn / tr : 0;
                pdi = p * a + pdi * (1 - a); mdi = m * a + mdi * (1 - a);
                double dx = pdi + mdi != 0 ? 100.0 * Math.Abs(pdi - mdi) / (pdi + mdi) : 0;
                adx = dx * a + adx * (1 - a);
            }
            return adx;
        }
    }
}

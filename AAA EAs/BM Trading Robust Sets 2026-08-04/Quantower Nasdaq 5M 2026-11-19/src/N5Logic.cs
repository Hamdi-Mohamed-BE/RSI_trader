// Pure signal maths for Calyx Nasdaq 5M (no Quantower dependency), shared by the strategy and the parity test.
// Formulas follow MT5: iMA EMA (seed = first close, alpha 2/(n+1)), iATR (simple average of true range), iADX +DI/-DI (100*DM/TR, EMA 2/(n+1)).
using System;
using System.Collections.Generic;

namespace CalyxQuantower
{
    public struct N5Bar
    {
        public DateTime TimeUtc; public double Open, High, Low, Close;
        public N5Bar(DateTime t, double o, double h, double l, double c) { TimeUtc = t; Open = o; High = h; Low = l; Close = c; }
    }

    public struct N5Signal
    {
        public int Direction;      // +1 long, -1 short, 0 none
        public double Ema, Atr, PlusDi, MinusDi;
        public string Reason;
    }

    public static class N5Logic
    {
        public static readonly TimeZoneInfo NewYork = FindNewYork();

        private static TimeZoneInfo FindNewYork()
        {
            try { return TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time"); }
            catch { return TimeZoneInfo.FindSystemTimeZoneById("America/New_York"); }
        }

        public static DateTime ToNY(DateTime utc) => TimeZoneInfo.ConvertTimeFromUtc(DateTime.SpecifyKind(utc, DateTimeKind.Utc), NewYork);
        public static int NyDateKey(DateTime ny) => ny.Year * 10000 + ny.Month * 100 + ny.Day;

        public static double[] Ema(IReadOnlyList<N5Bar> b, int n)
        {
            var e = new double[b.Count]; double a = 2.0 / (n + 1);
            for (int i = 0; i < b.Count; i++) e[i] = i == 0 ? b[0].Close : b[i].Close * a + e[i - 1] * (1 - a);
            return e;
        }

        public static double[] Atr(IReadOnlyList<N5Bar> b, int n)
        {
            var tr = new double[b.Count]; var atr = new double[b.Count]; double sum = 0;
            for (int i = 0; i < b.Count; i++)
            {
                tr[i] = i == 0 ? b[i].High - b[i].Low : Math.Max(b[i].High, b[i - 1].Close) - Math.Min(b[i].Low, b[i - 1].Close);
                sum += tr[i]; if (i >= n) sum -= tr[i - n];
                atr[i] = i >= n - 1 ? sum / n : 0;
            }
            return atr;
        }

        public static void Di(IReadOnlyList<N5Bar> b, int n, out double[] plus, out double[] minus)
        {
            plus = new double[b.Count]; minus = new double[b.Count]; double a = 2.0 / (n + 1);
            for (int i = 1; i < b.Count; i++)
            {
                double up = b[i].High - b[i - 1].High, dn = b[i - 1].Low - b[i].Low;
                if (up < 0) up = 0;
                if (dn < 0) dn = 0;
                if (up > dn) dn = 0; else if (up < dn) up = 0; else { up = 0; dn = 0; }
                double tr = Math.Max(b[i].High, b[i - 1].Close) - Math.Min(b[i].Low, b[i - 1].Close);
                double p = tr != 0 ? 100.0 * up / tr : 0, m = tr != 0 ? 100.0 * dn / tr : 0;
                plus[i] = i == 1 ? p : p * a + plus[i - 1] * (1 - a);
                minus[i] = i == 1 ? m : m * a + minus[i - 1] * (1 - a);
            }
        }

        /// <summary>True when bar s is the New York signal bar (Mon-Fri, hh:mm open time).</summary>
        public static bool IsSignalBar(N5Bar bar, int hourNY, int minuteNY)
        {
            var ny = ToNY(bar.TimeUtc);
            return ny.DayOfWeek != DayOfWeek.Saturday && ny.DayOfWeek != DayOfWeek.Sunday && ny.Hour == hourNY && ny.Minute == minuteNY;
        }

        /// <summary>Direction on closed bar s: close vs EMA, optional DI agreement. Mirrors ProcessNewBar of the MT5 EA.</summary>
        public static N5Signal Evaluate(IReadOnlyList<N5Bar> b, int s, int emaPeriod, int atrPeriod, int diPeriod, bool requireDI, bool allowLong, bool allowShort)
        {
            var sig = new N5Signal();
            double[] ema = Ema(b, emaPeriod), atr = Atr(b, atrPeriod);
            sig.Ema = ema[s]; sig.Atr = atr[s];
            if (sig.Atr <= 0) { sig.Reason = "no ATR"; return sig; }
            int dir = b[s].Close > sig.Ema ? 1 : b[s].Close < sig.Ema ? -1 : 0;
            if (dir == 0 || (dir > 0 && !allowLong) || (dir < 0 && !allowShort)) { sig.Reason = "no direction"; return sig; }
            if (requireDI)
            {
                Di(b, diPeriod, out var p, out var m); sig.PlusDi = p[s]; sig.MinusDi = m[s];
                if (dir > 0 ? !(p[s] > m[s]) : !(m[s] > p[s])) { sig.Reason = "DI disagrees"; return sig; }
            }
            sig.Direction = dir; sig.Reason = "ok";
            return sig;
        }
    }
}

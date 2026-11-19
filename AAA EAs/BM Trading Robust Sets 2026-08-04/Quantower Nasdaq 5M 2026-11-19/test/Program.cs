// Usage: ParityTest <bars.csv> <out.csv> [requireDI true|false]
// Reads M5 bars (time_utc,open,high,low,close; MT5 server time = UTC), evaluates every New York 09:30 bar with N5Logic,
// writes date_ny,direction,atr,ema,stop_distance (= 6 x ATR), close.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using CalyxQuantower;

var inv = CultureInfo.InvariantCulture;
var bars = new List<N5Bar>();
foreach (var line in File.ReadLines(args[0]))
{
    if (line.StartsWith("time")) continue;
    var p = line.Split(',');
    bars.Add(new N5Bar(DateTime.SpecifyKind(DateTime.ParseExact(p[0], "yyyy-MM-dd HH:mm", inv), DateTimeKind.Utc),
        double.Parse(p[1], inv), double.Parse(p[2], inv), double.Parse(p[3], inv), double.Parse(p[4], inv)));
}
bool di = args.Length > 2 && args[2] == "true";
using var w = new StreamWriter(args[1]);
w.WriteLine("date_ny,direction,atr,ema,stop_distance,close,reason");
int n = 0;
for (int s = 50; s < bars.Count - 1; s++)
{
    if (!N5Logic.IsSignalBar(bars[s], 9, 30)) continue;
    // the strategy evaluates on the bars loaded so far (history up to and including bar s)
    var view = bars.GetRange(0, s + 1);
    var sig = N5Logic.Evaluate(view, s, 12, 14, 14, di, true, true);
    var ny = N5Logic.ToNY(bars[s].TimeUtc);
    w.WriteLine(string.Join(",", ny.ToString("yyyy-MM-dd", inv), sig.Direction, sig.Atr.ToString("R", inv), sig.Ema.ToString("R", inv),
        (6.0 * sig.Atr).ToString("R", inv), bars[s].Close.ToString("R", inv), sig.Reason)); n++;
}
Console.WriteLine($"bars {bars.Count}, signal days {n}");

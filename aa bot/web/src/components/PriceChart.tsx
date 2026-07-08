import { useEffect, useRef, useState } from "react";
import { CandlestickSeries, ColorType, createChart, type IPriceLine, type UTCTimestamp } from "lightweight-charts";
import type { Candle, ProductState } from "../types";

const timeframes = [
  ["M5", 300], ["M15", 900], ["H1", 3600], ["H6", 21600], ["D1", 86400]
] as const;

export function PriceChart({ state }: { state: ProductState }) {
  const host = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ReturnType<typeof createChart> | null>(null);
  const seriesRef = useRef<ReturnType<ReturnType<typeof createChart>["addSeries"]> | null>(null);
  const priceLines = useRef<IPriceLine[]>([]);
  const [granularity, setGranularity] = useState(300);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!host.current) return;
    const chart = createChart(host.current, {
      layout: { background: { type: ColorType.Solid, color: "#0a0f16" }, textColor: "#8795a7", fontFamily: "Inter, system-ui" },
      grid: { vertLines: { color: "#14202d" }, horzLines: { color: "#14202d" } },
      rightPriceScale: { borderColor: "#243242" }, timeScale: { borderColor: "#243242", timeVisible: true },
      crosshair: { vertLine: { color: "#587089" }, horzLine: { color: "#587089" } },
      width: host.current.clientWidth, height: 410
    });
    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#20d3a4", downColor: "#f15c6c", wickUpColor: "#20d3a4", wickDownColor: "#f15c6c", borderVisible: false
    });
    chartRef.current = chart;
    seriesRef.current = series;
    const observer = new ResizeObserver(() => chart.applyOptions({ width: host.current?.clientWidth ?? 800 }));
    observer.observe(host.current);
    return () => { observer.disconnect(); chart.remove(); chartRef.current = null; seriesRef.current = null; };
  }, []);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/products/${state.productId}/candles?granularity=${granularity}`)
      .then((response) => response.json())
      .then((candles: Candle[]) => {
        seriesRef.current?.setData(candles.map((candle) => ({ ...candle, time: candle.time as UTCTimestamp })));
        chartRef.current?.timeScale().fitContent();
      })
      .finally(() => setLoading(false));
  }, [state.productId, granularity]);

  useEffect(() => {
    const series = seriesRef.current;
    if (!series) return;
    for (const line of priceLines.current) series.removePriceLine(line);
    priceLines.current = [];
    const add = (price: number | null, title: string, color: string, style = 2) => {
      if (!price) return;
      priceLines.current.push(series.createPriceLine({ price, title, color, lineWidth: 1, lineStyle: style, axisLabelVisible: true }));
    };
    add(state.profile.vah, "LIVE VAH", "#4f8cff");
    add(state.profile.poc, "LIVE POC", "#f6c85f");
    add(state.profile.val, "LIVE VAL", "#4f8cff");
    for (const zone of state.plan.zones) {
      const color = ["DEMAND", "VAL", "LIQUIDITY_LOW"].includes(zone.kind) ? "#20d3a4" : ["SUPPLY", "VAH", "LIQUIDITY_HIGH"].includes(zone.kind) ? "#f15c6c" : "#f6c85f";
      add(zone.low, `${zone.timeframe} ${zone.kind}`, color, 1);
      if (zone.high !== zone.low) add(zone.high, "", color, 1);
    }
  }, [state.profile, state.plan.zones]);

  return <section className="panel chart-panel">
    <div className="panel-head">
      <div><span className="eyebrow">Coinbase spot</span><h2>{state.productId}</h2></div>
      <div className="timeframes">{timeframes.map(([label, value]) => <button key={label} className={granularity === value ? "active" : ""} onClick={() => setGranularity(value)}>{label}</button>)}</div>
    </div>
    <div className="chart-wrap" ref={host}>{loading && <div className="chart-loading">Loading candles…</div>}</div>
  </section>;
}

import { useMemo, useState } from "react";
import { BarChart3, FlaskConical, LoaderCircle, Play, ShieldAlert, TrendingDown, TrendingUp } from "lucide-react";

interface BacktestTrade { id: number; direction: "long" | "short"; grade: "A" | "A+"; model: "EM1" | "EM2" | "EM3" | "EM4" | "H4R"; entryTime: number; exitTime: number; entry: number; stop: number; target: number; exit: number; resultR: number; pnl: number; exitReason: string; holdBars: number }
interface BacktestResult {
  input: { riskPct: number; accountSize: number };
  data: { from: number; to: number; bars: number };
  metrics: { trades: number; wins: number; losses: number; winRate: number; netR: number; expectancyR: number; profitFactor: number | null; maxDrawdownR: number; maxConsecutiveLosses: number; averageHoldBars: number; startingBalance: number; endingBalance: number; returnPct: number };
  equity: Array<{ time: number; balance: number; cumulativeR: number }>;
  trades: BacktestTrade[]; notes: string[];
}

const fmt = (value: number) => value.toLocaleString(undefined, { maximumFractionDigits: 2 });

function EquityCurve({ result }: { result: BacktestResult }) {
  const points = useMemo(() => {
    const values = [{ balance: result.metrics.startingBalance }, ...result.equity];
    const min = Math.min(...values.map((item) => item.balance));
    const max = Math.max(...values.map((item) => item.balance));
    return values.map((item, index) => {
      const x = values.length === 1 ? 0 : index / (values.length - 1) * 760;
      const y = 180 - (item.balance - min) / Math.max(1, max - min) * 150;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ");
  }, [result]);
  return <div className="equity-chart"><svg viewBox="0 0 760 200" preserveAspectRatio="none"><defs><linearGradient id="equityFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#20d3a4" stopOpacity=".32"/><stop offset="1" stopColor="#20d3a4" stopOpacity="0"/></linearGradient></defs><polyline points={`0,190 ${points} 760,190`} fill="url(#equityFill)" stroke="none"/><polyline points={points} fill="none" stroke="#20d3a4" strokeWidth="2" vectorEffect="non-scaling-stroke"/></svg></div>;
}

export function BacktestPage({ products, defaultAccount = 50_000, defaultRisk = 0.5 }: { products: string[]; defaultAccount?: number; defaultRisk?: number }) {
  const optimizedMarket = products.includes("BTC-USD") ? "BTC-USD" : products[0] ?? "BTC-USD";
  const [form, setForm] = useState({ strategyMode: "h4-retest", productId: optimizedMarket, granularity: 300, bars: 17280, direction: "both", model: "all", quality: "A", lookback: "24", targetR: "2", riskPct: String(defaultRisk), accountSize: String(defaultAccount), maxHoldBars: "120", sessionFilter: "NY_EXT", trendFilter: "strict" });
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const numericPayload = () => ({
    ...form,
    lookback: Number(form.lookback), targetR: Number(form.targetR), riskPct: Number(form.riskPct),
    accountSize: Number(form.accountSize), maxHoldBars: Number(form.maxHoldBars)
  });
  const validate = () => {
    const value = numericPayload();
    if (value.strategyMode === "h4-retest" && value.granularity !== 300) return "4H retest mode must use M5 candles.";
    if (value.strategyMode === "h4-retest" && value.bars < 2500) return "Use at least 2,500 M5 candles for 4H retest mode.";
    if (!Number.isFinite(value.lookback) || value.lookback < 20 || value.lookback > 120) return "Profile lookback must be between 20 and 120 bars.";
    if (!Number.isFinite(value.targetR) || value.targetR < 1.5 || value.targetR > 5) return "Target R must be between 1.5 and 5.";
    if (!Number.isFinite(value.maxHoldBars) || value.maxHoldBars < 4 || value.maxHoldBars > 120) return "Max hold must be between 4 and 120 bars.";
    if (!Number.isFinite(value.accountSize) || value.accountSize <= 0) return "Account size must be greater than zero.";
    if (!Number.isFinite(value.riskPct) || value.riskPct <= 0 || value.riskPct > 10) return "Risk must be greater than 0% and no more than 10% for research.";
    return "";
  };
  const run = async () => {
    const validationError = validate();
    if (validationError) { setError(validationError); return; }
    setLoading(true); setError(""); setResult(null);
    try {
      const response = await fetch("/api/backtest", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(numericPayload()) });
      const body = await response.json();
      if (!response.ok) {
        const fields = body.error?.fieldErrors ? Object.entries(body.error.fieldErrors).flatMap(([field, messages]) => (messages as string[]).map((message) => `${field}: ${message}`)) : [];
        throw new Error(typeof body.error === "string" ? body.error : fields.join(" · ") || "Backtest request failed");
      }
      setResult(body);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Backtest failed"); }
    finally { setLoading(false); }
  };
  const set = (key: keyof typeof form, value: string | number) => { setForm({ ...form, [key]: value }); setError(""); setResult(null); };
  const isH4Retest = form.strategyMode === "h4-retest";
  return <div className="page-stack">
    <section className="panel backtest-hero"><div><span className="eyebrow">Research laboratory · filtered 4H retest setup</span><h2>LTA backtest lab</h2><p>Default: BTC M5 · 4H first-90m retest · NY extended · strict H1/H4 trend filter · split TP1 then runner to BE.</p></div><div className="research-warning"><ShieldAlert/><span><strong>Research first</strong><em>Use this to prove edge before we let any bot place live orders.</em></span></div></section>
    <section className="panel backtest-controls"><div className="panel-head compact"><div><span className="eyebrow">Experiment</span><h3><FlaskConical size={17}/> Parameters</h3></div><button className="primary run-button" onClick={run} disabled={loading}>{loading ? <LoaderCircle className="spin"/> : <Play/>}{loading ? "Running…" : "Run backtest"}</button></div>
      <div className="backtest-fields">
        <label><span>Strategy mode</span><select value={form.strategyMode} onChange={(e) => {
          const mode = e.target.value;
          setForm({
            ...form,
            strategyMode: mode,
            granularity: mode === "h4-retest" ? 300 : 3600,
            bars: mode === "h4-retest" ? 17280 : 1440,
            direction: mode === "h4-retest" ? "both" : form.direction,
            targetR: mode === "h4-retest" ? "2" : form.targetR
          });
          setError(""); setResult(null);
        }}><option value="h4-retest">4H 90m retest</option><option value="lta">LTA EM1–EM4</option></select></label>
        <label><span>Market</span><select value={form.productId} onChange={(e) => set("productId", e.target.value)}>{products.map((product) => <option key={product}>{product}</option>)}</select></label>
        <label><span>Timeframe</span><select value={form.granularity} onChange={(e) => set("granularity", Number(e.target.value))}><option value="300">M5</option><option value="900">M15</option><option value="3600">H1</option><option value="21600">H6</option><option value="86400">D1</option></select></label>
        <label><span>History</span><select value={form.bars} onChange={(e) => set("bars", Number(e.target.value))}><option value="300">300 bars</option><option value="600">600 bars</option><option value="1200">1,200 bars</option><option value="1440">1,440 bars · 60 days on H1</option><option value="8640">8,640 bars · 30 days on M5</option><option value="17280">17,280 bars · 60 days on M5</option></select></label>
        <label><span>Direction</span><select value={form.direction} onChange={(e) => set("direction", e.target.value)}><option value="both">Both</option><option value="long">Long only</option><option value="short">Short only</option></select></label>
        {!isH4Retest && <label><span>Entry model</span><select value={form.model} onChange={(e) => set("model", e.target.value)}><option value="all">All EM models</option><option>EM1</option><option>EM2</option><option>EM3</option><option>EM4</option></select></label>}
        {!isH4Retest && <label><span>Quality</span><select value={form.quality} onChange={(e) => set("quality", e.target.value)}><option value="A+">A+ only</option><option value="A">A and A+</option></select></label>}
        {isH4Retest && <label><span>Session filter</span><select value={form.sessionFilter} onChange={(e) => set("sessionFilter", e.target.value)}><option value="ALL">All sessions</option><option value="ASIA">Asia</option><option value="LONDON">London</option><option value="NY">New York</option><option value="LONDON_NY">London + NY</option><option value="NY_EXT">NY extended</option></select></label>}
        {isH4Retest && <label><span>Trend filter</span><select value={form.trendFilter} onChange={(e) => set("trendFilter", e.target.value)}><option value="strict">Strict H1 + H4</option><option value="trend">H1 trend</option><option value="raw">No trend filter</option></select></label>}
        {!isH4Retest && <label><span>Profile lookback</span><input type="number" min="20" max="120" value={form.lookback} onChange={(e) => set("lookback", e.target.value)}/></label>}
        <label><span>{isH4Retest ? "Runner fallback R" : "Minimum target R"}</span><input type="number" min="1.5" max="5" step="0.5" value={form.targetR} onChange={(e) => set("targetR", e.target.value)}/></label>
        <label><span>Max hold bars</span><input type="number" min="4" max="120" value={form.maxHoldBars} onChange={(e) => set("maxHoldBars", e.target.value)}/></label>
        <label><span>Account USD</span><input type="number" min="1" value={form.accountSize} onChange={(e) => set("accountSize", e.target.value)}/></label>
        <label><span>Risk %</span><input type="number" min="0.01" max="10" step="0.05" value={form.riskPct} onChange={(e) => set("riskPct", e.target.value)}/>{Number(form.riskPct) > 1 && <em className="research-only">Research only — live policy remains 1% maximum.</em>}</label>
      </div>{error && <div className="backtest-error">{error}</div>}
    </section>

    {!result ? <section className="panel empty-backtest"><BarChart3/><h3>No test run yet</h3><p>Choose parameters and run the historical simulation.</p></section> : <>
      <section className="backtest-metrics">
        <div className="panel"><span>Net result</span><strong className={result.metrics.netR >= 0 ? "green" : "red"}>{result.metrics.netR.toFixed(2)}R</strong><em>{result.metrics.returnPct.toFixed(2)}%</em></div>
        <div className="panel"><span>Win rate</span><strong>{result.metrics.winRate.toFixed(1)}%</strong><em>{result.metrics.wins}W / {result.metrics.losses}L</em></div>
        <div className="panel"><span>Profit factor</span><strong>{result.metrics.profitFactor === null ? "∞" : result.metrics.profitFactor.toFixed(2)}</strong><em>{result.metrics.trades} trades</em></div>
        <div className="panel"><span>Expectancy</span><strong>{result.metrics.expectancyR.toFixed(2)}R</strong><em>per trade</em></div>
        <div className="panel"><span>Max drawdown</span><strong className="red">{result.metrics.maxDrawdownR.toFixed(2)}R</strong><em>{result.metrics.maxConsecutiveLosses} losses max</em></div>
        <div className="panel"><span>Ending balance</span><strong>${fmt(result.metrics.endingBalance)}</strong><em>from ${fmt(result.metrics.startingBalance)}</em></div>
      </section>
      <section className="panel equity-panel"><div className="panel-head compact"><div><span className="eyebrow">Compounded at {result.input.riskPct}% risk</span><h3>{result.metrics.netR >= 0 ? <TrendingUp/> : <TrendingDown/>} Equity curve</h3></div><span>{new Date(result.data.from * 1000).toLocaleDateString()} — {new Date(result.data.to * 1000).toLocaleDateString()}</span></div><EquityCurve result={result}/></section>
      <section className="panel trade-log"><div className="panel-head compact"><div><span className="eyebrow">Conservative fills</span><h3>Trade log</h3></div><span>{result.data.bars} candles</span></div><div className="trade-table-wrap"><table><thead><tr><th>#</th><th>Date</th><th>Side</th><th>Model</th><th>Grade</th><th>Entry</th><th>Stop</th><th>Target</th><th>Exit</th><th>Result</th><th>Reason</th></tr></thead><tbody>{result.trades.slice().reverse().slice(0, 40).map((trade) => <tr key={trade.id}><td>{trade.id}</td><td>{new Date(trade.entryTime * 1000).toLocaleString()}</td><td className={trade.direction === "long" ? "green" : "red"}>{trade.direction}</td><td>{trade.model}</td><td>{trade.grade}</td><td>{fmt(trade.entry)}</td><td>{fmt(trade.stop)}</td><td>{fmt(trade.target)}</td><td>{fmt(trade.exit)}</td><td className={trade.resultR > 0 ? "green" : "red"}>{trade.resultR.toFixed(2)}R</td><td>{trade.exitReason}</td></tr>)}</tbody></table></div><div className="backtest-notes">{result.notes.map((note) => <p key={note}>• {note}</p>)}</div></section>
    </>}
  </div>;
}

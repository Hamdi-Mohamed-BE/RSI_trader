import { useEffect, useMemo, useState } from "react";
import { Activity, BookOpen, CircleDollarSign, Database, FlaskConical, Radio, Settings, ShieldCheck, Wifi, WifiOff } from "lucide-react";
import { BacktestPage } from "./components/BacktestPage";
import { useMarketStream } from "./hooks/useMarketStream";
import { MicroMetrics } from "./components/MicroMetrics";
import { OrderBook } from "./components/OrderBook";
import { PlanEditor } from "./components/PlanEditor";
import { PriceChart } from "./components/PriceChart";
import { ProfileCard } from "./components/ProfileCard";
import { RiskCalculator } from "./components/RiskCalculator";
import { SetupCard } from "./components/SetupCard";
import { PlaybookPage } from "./components/PlaybookPage";
import { RiskPage } from "./components/RiskPage";

interface SettingsState { executionEnabled: boolean; integrations: Record<string, boolean>; safety: { mode: string; maxRiskPct: number; spotShortingEnabled: boolean } }

const formatPrice = (value: number | null) => value?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? "—";

export function App() {
  const { states, connected, savePlan } = useMarketStream();
  const products = useMemo(() => Object.values(states), [states]);
  const [selectedId, setSelectedId] = useState("BTC-USD");
  const [settings, setSettings] = useState<SettingsState | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [page, setPage] = useState<"terminal" | "playbook" | "risk" | "backtest">("terminal");
  const selected = states[selectedId] ?? products[0];
  useEffect(() => { fetch("/api/settings").then((response) => response.json()).then(setSettings).catch(() => undefined); }, []);
  useEffect(() => { if (!states[selectedId] && products[0]) setSelectedId(products[0].productId); }, [products, selectedId, states]);
  const titles = { terminal: "Crypto market terminal", playbook: "LTA playbook", risk: "Risk command center", backtest: "Strategy backtest" };

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark">HF</div><div><strong>HamaForex</strong><span>LTA · MBO Terminal</span></div></div>
      <nav>
        <button className={page === "terminal" ? "active" : ""} onClick={() => setPage("terminal")}><Activity size={18} /> Terminal</button>
        <button className={page === "playbook" ? "active" : ""} onClick={() => setPage("playbook")}><BookOpen size={18} /> Playbook</button>
        <button className={page === "risk" ? "active" : ""} onClick={() => setPage("risk")}><CircleDollarSign size={18} /> Risk</button>
        <button className={page === "backtest" ? "active" : ""} onClick={() => setPage("backtest")}><FlaskConical size={18} /> Backtest</button>
        <button onClick={() => setShowSettings(true)}><Settings size={18} /> Settings</button>
      </nav>
      <div className="core-rule"><ShieldCheck size={18} /><strong>Core rule</strong><p>Trade the LTA zone only when the order book proves the reaction is real.</p></div>
      <div className="mode-badge"><span className="pulse" /><div><strong>{settings?.safety.mode ?? "analysis/paper"}</strong><span>Execution locked</span></div></div>
    </aside>

    <main>
      <header>
        <div><span className="eyebrow">Execution intelligence</span><h1>{titles[page]}</h1></div>
        <div className="header-actions"><span className={`connection ${connected ? "online" : "offline"}`}>{connected ? <Wifi size={15} /> : <WifiOff size={15} />}{connected ? "Live stream" : "Reconnecting"}</span><button className="icon-button" onClick={() => setShowSettings(true)}><Settings size={17} /></button></div>
      </header>

      <section className="watchlist">
        {products.map((product) => <button key={product.productId} onClick={() => setSelectedId(product.productId)} className={selectedId === product.productId ? "selected" : ""}>
          <div><span className={`coin ${product.productId.startsWith("BTC") ? "btc" : "eth"}`}>{product.productId.slice(0, 1)}</span><strong>{product.productId}</strong></div>
          <b>{formatPrice(product.ticker.price)}</b><span className={`mini-grade grade-${product.setup.grade.replaceAll(" ", "-").toLowerCase()}`}>{product.setup.grade}</span>
        </button>)}
      </section>

      {!selected ? <div className="loading-screen"><Radio /> Connecting to Coinbase…</div> : page === "terminal" ? <>
        <SetupCard state={selected} />
        <MicroMetrics state={selected} />
        <div className="terminal-grid"><PriceChart state={selected} /><OrderBook state={selected} /></div>
        <div className="analysis-grid"><PlanEditor state={selected} onSave={savePlan} /><ProfileCard state={selected} /><RiskCalculator accountSize={selected.plan.accountSize} riskPct={selected.plan.riskPct} /></div>
      </> : page === "playbook" ? <PlaybookPage state={selected} onSave={savePlan}/>
        : page === "risk" ? <RiskPage state={selected}/>
        : <BacktestPage products={products.map((product) => product.productId)} defaultAccount={selected.plan.accountSize} defaultRisk={selected.plan.riskPct}/>} 
    </main>

    {showSettings && <div className="drawer-backdrop" onClick={() => setShowSettings(false)}><aside className="drawer" onClick={(event) => event.stopPropagation()}>
      <div className="panel-head"><div><span className="eyebrow">Environment</span><h2>System readiness</h2></div><button className="icon-button" onClick={() => setShowSettings(false)}>×</button></div>
      <div className="settings-list"><div><Database /><span>Coinbase public data</span><strong className="green">No key needed</strong></div>{Object.entries(settings?.integrations ?? {}).map(([key, ready]) => <div key={key}><Settings /><span>{key}</span><strong className={ready ? "green" : "neutral"}>{ready ? "Ready" : "Key pending"}</strong></div>)}</div>
      <div className="safety-box"><ShieldCheck /><div><strong>Live execution is disabled</strong><p>The API rejects orders until credentials are added and ENABLE_LIVE_EXECUTION is explicitly changed.</p></div></div>
    </aside></div>}
  </div>;
}

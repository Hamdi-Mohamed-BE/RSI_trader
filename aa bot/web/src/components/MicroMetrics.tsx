import { Activity, AlertTriangle, ArrowDownRight, ArrowUpRight, Layers3, RefreshCw } from "lucide-react";
import type { ProductState } from "../types";

const signed = (value: number) => `${value > 0 ? "+" : ""}${value.toFixed(3)}`;

export function MicroMetrics({ state }: { state: ProductState }) {
  const items = [
    { label: "MBO score", value: state.micro.score.toString(), tone: state.micro.score > 20 ? "green" : state.micro.score < -20 ? "red" : "neutral", icon: Activity },
    { label: "Book imbalance", value: `${(state.micro.imbalance * 100).toFixed(1)}%`, tone: state.micro.imbalance > 0.1 ? "green" : state.micro.imbalance < -0.1 ? "red" : "neutral", icon: Layers3 },
    { label: "Delta · 5s", value: signed(state.micro.delta5s), tone: state.micro.delta5s > 0 ? "green" : "red", icon: state.micro.delta5s > 0 ? ArrowUpRight : ArrowDownRight },
    { label: "Delta · 30s", value: signed(state.micro.delta30s), tone: state.micro.delta30s > 0 ? "green" : "red", icon: state.micro.delta30s > 0 ? ArrowUpRight : ArrowDownRight },
    { label: "Bid / ask refresh", value: `${state.micro.bidRefreshes} / ${state.micro.askRefreshes}`, tone: "neutral", icon: RefreshCw },
    { label: "Absorption", value: state.micro.absorption.toUpperCase(), tone: state.micro.absorption === "long" ? "green" : state.micro.absorption === "short" ? "red" : "neutral", icon: Activity }
  ];
  return <section className="metric-grid">
    {items.map((item) => <div className="metric panel" key={item.label}>
      <div className={`metric-icon ${item.tone}`}><item.icon size={16} /></div>
      <span>{item.label}</span><strong className={item.tone}>{item.value}</strong>
    </div>)}
    {state.micro.spoofWarning && <div className="spoof-alert"><AlertTriangle size={16} /> Liquidity pull warning on the {state.micro.spoofSide ?? "unknown"} side</div>}
  </section>;
}

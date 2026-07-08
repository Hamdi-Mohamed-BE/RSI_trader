import { Ban, CheckCircle2, CircleDot, Crosshair, ShieldAlert, Target } from "lucide-react";
import type { ProductState } from "../types";

const price = (value: number | null) => value === null ? "—" : value.toLocaleString(undefined, { maximumFractionDigits: 2 });

export function SetupCard({ state }: { state: ProductState }) {
  const setup = state.setup;
  return <section className={`panel setup-card grade-${setup.grade.replaceAll(" ", "-").toLowerCase()}`}>
    <div className="setup-top">
      <div><span className="eyebrow">LTA setup + order-book confirmation</span><h2>{setup.pattern}</h2><p className="setup-context">{setup.marketPhase} · {setup.zone ? `${setup.zone.source} ${setup.zone.timeframe} ${setup.zone.kind}` : "no qualified location"}</p></div>
      <div className="grade"><strong>{setup.grade}</strong><span>{setup.score}/100 · {setup.status}</span></div>
    </div>
    <div className="trade-strip">
      <div><Crosshair size={15} /><span>Direction</span><strong>{setup.direction.toUpperCase()}</strong></div>
      <div><Target size={15} /><span>Entry</span><strong>{price(setup.entry)}</strong></div>
      <div><ShieldAlert size={15} /><span>Stop</span><strong>{price(setup.stop)}</strong></div>
      <div><Target size={15} /><span>Real targets</span><strong>{setup.targetDetails.map((item) => `${price(item.price)} (${item.rr.toFixed(1)}R)`).join(" · ") || "—"}</strong></div>
      <div><span>Nearest R:R</span><strong>{setup.rr ? `${setup.rr.toFixed(2)}R` : "—"}</strong></div>
    </div>
    <div className="live-gates">
      {setup.gates.map((gate) => <div key={gate.name} className={gate.passed ? "passed" : "pending"}>{gate.passed ? <CheckCircle2/> : <CircleDot/>}<span><strong>{gate.name}</strong><em>{gate.detail}</em></span></div>)}
    </div>
    <div className="setup-columns">
      <div><h4><CheckCircle2 size={15} /> Book management</h4><ul>{setup.management.map((reason) => <li key={reason}>{reason}</li>)}</ul></div>
      <div><h4><Ban size={15} /> Cancel if</h4><ul>{setup.cancelConditions.map((reason) => <li key={reason}>{reason}</li>)}</ul></div>
    </div>
  </section>;
}

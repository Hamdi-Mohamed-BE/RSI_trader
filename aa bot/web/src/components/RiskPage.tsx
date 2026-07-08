import { AlertTriangle, Gauge, LockKeyhole, ShieldCheck } from "lucide-react";
import type { ProductState } from "../types";
import { RiskCalculator } from "./RiskCalculator";

export function RiskPage({ state }: { state: ProductState }) {
  const riskAmount = state.plan.accountSize * state.plan.riskPct / 100;
  return <div className="page-stack">
    <section className="risk-hero panel"><div><span className="eyebrow">LTA 2/2/2 protection</span><h2>Risk command center</h2><p>Minimum 2R, maximum 2% in the book, and stop after two consecutive losses. This platform keeps the safer 1% live-policy ceiling.</p></div><div className="risk-budget"><span>Planned risk</span><strong>${riskAmount.toFixed(2)}</strong><em>{state.plan.riskPct}% of ${state.plan.accountSize.toLocaleString()}</em></div></section>
    <div className="risk-page-grid"><RiskCalculator accountSize={state.plan.accountSize} riskPct={state.plan.riskPct}/>
      <section className="panel guardrails"><div className="panel-head compact"><div><span className="eyebrow">Automatic discipline</span><h3><LockKeyhole size={17}/> Guardrails</h3></div></div><div className="guardrail-list">
        <div><ShieldCheck/><span><strong>Per-trade ceiling</strong><em>1.00% platform cap · book max 2%</em></span></div>
        <div><AlertTriangle/><span><strong>Two-strike rule</strong><em>Two consecutive losses, then stop</em></span></div>
        <div><Gauge/><span><strong>Phase-aware</strong><em>Contrarian ≤1% · momentum may use more only after proof</em></span></div>
        <div><LockKeyhole/><span><strong>Execution lock</strong><em>Live orders remain disabled</em></span></div>
      </div></section>
    </div>
    <section className="panel risk-matrix"><div className="panel-head compact"><div><span className="eyebrow">Sizing policy</span><h3>Setup-to-risk matrix</h3></div></div><table><thead><tr><th>Grade</th><th>Permission</th><th>Suggested risk</th><th>Minimum R:R</th><th>Management</th></tr></thead><tbody>
      <tr><td><b className="green">A+</b></td><td>Trade only when every gate passes</td><td>0.50–1.00% platform policy</td><td>Nearest real level ≥2R</td><td>Momentum gets room; no automatic BE at 1R</td></tr>
      <tr><td><b className="green">A</b></td><td>Armed; wait for order-book proof</td><td>0.25–0.50%</td><td>Nearest real level ≥2R</td><td>Contrarian moves to BE at 1R before macro shift</td></tr>
      <tr><td><b className="red">B or lower</b></td><td>No trade</td><td>0%</td><td>—</td><td>Journal the idea; do not fund it</td></tr>
    </tbody></table></section>
  </div>;
}

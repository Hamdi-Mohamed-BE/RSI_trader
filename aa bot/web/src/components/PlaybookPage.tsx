import { ArrowRight, BookOpen, CheckCircle2, CircleDot, ShieldCheck, Waves } from "lucide-react";
import type { ProductState } from "../types";
import { PlanEditor } from "./PlanEditor";

const models = [
  { id: "EM1", name: "Double Wick", text: "At POC, VAH or VAL: first touch and rejection, second retest/flip, then enter only after the confirmation closes. Stop beyond the wick." },
  { id: "EM2", name: "Internal Swing", text: "After the key level is mitigated, profile the lower-timeframe reaction swing. Wait for its POC/VA edge, then require EM1 and a structure break." },
  { id: "EM3", name: "Internal Structure", text: "Mitigate the key level first, then require an internal high/low break. CME manipulation is a strong version of this model." },
  { id: "EM4", name: "Continuation", text: "For a predefined momentum bias: liquidity trap, touch/hesitation, flip, and third-candle confirmation. Best with CERC and strong volume." }
];

export function PlaybookPage({ state, onSave }: { state: ProductState; onSave: Parameters<typeof PlanEditor>[0]["onSave"] }) {
  return <div className="page-stack">
    <section className="panel playbook-hero">
      <div><span className="eyebrow">Book implementation</span><h2>The LTA execution framework</h2><p>Macro supply/demand defines bias. Completed profiles define location. EM1–EM4 define entry. Order flow verifies the reaction.</p></div>
      <div className="framework-flow"><span>Macro bias</span><ArrowRight /><span>HTF zone</span><ArrowRight /><span>PD/EPD/PW/Fixed/Swing</span><ArrowRight /><span>EM1–EM4</span><ArrowRight /><strong>MBO proof</strong></div>
    </section>
    <div className="playbook-grid">
      <section className="panel gate-card"><div className="panel-head compact"><div><span className="eyebrow">Live qualification</span><h3><ShieldCheck size={17}/> A+ gates · {state.productId}</h3></div><strong className={`gate-grade grade-${state.setup.grade.replaceAll(" ", "-").toLowerCase()}`}>{state.setup.grade}</strong></div>
        <div className="gate-list">{state.setup.gates.map((gate) => <div key={gate.name}><span className={gate.passed ? "passed" : "pending"}>{gate.passed ? <CheckCircle2/> : <CircleDot/>}</span><strong>{gate.name}</strong><em>{gate.detail}</em></div>)}</div>
      </section>
      <section className="panel rule-card"><div className="panel-head compact"><div><span className="eyebrow">Non-negotiables</span><h3><BookOpen size={17}/> Book rules</h3></div></div>
        <ul><li>Order flow confirms location; it never creates a trade.</li><li>Prefer PD, EPD and PW over an early developing current profile.</li><li>Repeated taps require EM2/EM3 or stronger confirmation.</li><li>Low volume requires a higher-timeframe close.</li><li>Targets are real opposing levels, never invented R multiples.</li><li>Minimum 2R; maximum 2% risk; stop after two losses.</li><li>Contrarian: generally 1% risk and breakeven at 1R.</li><li>Momentum: allow more room only when macro structure has shifted.</li></ul>
      </section>
    </div>
    <section className="model-grid">{models.map((model) => <article className="panel model-card" key={model.id}><span>{model.id}</span><Waves/><h3>{model.name}</h3><p>{model.text}</p></article>)}</section>
    <section className="panel pattern-guide"><div><strong>CERC</strong><span>Consolidation → Expansion → Retracement → Continuation. Use the retracement into fixed/profile value for continuation.</span></div><div><strong>CME</strong><span>Consolidation → Manipulation → Expansion. The false break traps liquidity before the real directional move.</span></div></section>
    <PlanEditor state={state} onSave={onSave}/>
  </div>;
}

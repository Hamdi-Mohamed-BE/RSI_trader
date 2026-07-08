import { useEffect, useState } from "react";
import { Plus, Save, Trash2 } from "lucide-react";
import type { LtaZone, ProductPlan, ProductState, ProfileSource, ZoneKind } from "../types";

const kinds: ZoneKind[] = ["POC", "VAH", "VAL", "DEMAND", "SUPPLY", "LIQUIDITY_HIGH", "LIQUIDITY_LOW"];
const timeframes: LtaZone["timeframe"][] = ["W1", "D1", "H4", "H1", "M30", "M15", "M5"];
const sources: ProfileSource[] = ["HTF_ZONE", "PD", "EPD", "PW", "FIXED", "SWING", "LTF_SWING", "LIVE"];

export function PlanEditor({ state, onSave }: { state: ProductState; onSave: (plan: ProductPlan) => Promise<void> }) {
  const [plan, setPlan] = useState(state.plan);
  const [zone, setZone] = useState<Omit<LtaZone, "id">>({
    kind: "VAH", low: 0, high: 0, timeframe: "H1", fresh: true, source: "PD", taps: 0, tookOutOpposingZone: false
  });
  const [status, setStatus] = useState("");
  useEffect(() => setPlan(state.plan), [state.productId, state.plan]);

  const addZone = () => {
    if (!zone.low || !zone.high || zone.high < zone.low) return setStatus("Enter a valid zone range.");
    setPlan({ ...plan, zones: [...plan.zones, { ...zone, id: crypto.randomUUID(), fresh: zone.taps <= 1 }] });
    setZone({ ...zone, low: 0, high: 0, note: "" });
    setStatus("");
  };
  const save = async () => {
    try { await onSave(plan); setStatus("Plan saved."); }
    catch (error) { setStatus(error instanceof Error ? error.message : "Could not save."); }
  };
  return <section className="panel plan-editor">
    <div className="panel-head compact"><div><span className="eyebrow">Book-aligned context layer</span><h3>LTA execution plan</h3></div><button className="primary small" onClick={save}><Save size={15} /> Save</button></div>
    <p className="helper">Order flow confirms an LTA setup; it never creates one. Mark the macro zone, profile source, pattern and execution stage first.</p>
    <div className="plan-fields">
      <label><span>HTF bias</span><select value={plan.bias} onChange={(event) => setPlan({ ...plan, bias: event.target.value as ProductPlan["bias"] })}><option>bullish</option><option>bearish</option><option>neutral</option></select></label>
      <label><span>Structure</span><select value={plan.structure} onChange={(event) => setPlan({ ...plan, structure: event.target.value as ProductPlan["structure"] })}><option>range</option><option>reclaim</option><option>rejection</option><option>breakout</option><option>breakdown</option></select></label>
      <label><span>Session</span><select value={plan.session} onChange={(event) => setPlan({ ...plan, session: event.target.value as ProductPlan["session"] })}><option>Asia</option><option>London</option><option>New York</option><option>Off-hours</option></select></label>
      <label><span>Direction</span><select value={plan.preferredDirection} onChange={(event) => setPlan({ ...plan, preferredDirection: event.target.value as ProductPlan["preferredDirection"] })}><option>both</option><option>long</option><option>short</option><option>none</option></select></label>
      <label><span>Market phase</span><select value={plan.marketPhase} onChange={(event) => setPlan({ ...plan, marketPhase: event.target.value as ProductPlan["marketPhase"] })}><option>momentum</option><option>contrarian</option></select></label>
      <label><span>Auction pattern</span><select value={plan.auctionPattern} onChange={(event) => setPlan({ ...plan, auctionPattern: event.target.value as ProductPlan["auctionPattern"] })}><option>UNSET</option><option>RANGE</option><option>CERC</option><option>CME</option></select></label>
      <label><span>Entry model</span><select value={plan.entryModel} onChange={(event) => setPlan({ ...plan, entryModel: event.target.value as ProductPlan["entryModel"] })}><option>AUTO</option><option>EM1</option><option>EM2</option><option>EM3</option><option>EM4</option></select></label>
      <label><span>Execution stage</span><select value={plan.executionStage} onChange={(event) => setPlan({ ...plan, executionStage: event.target.value as ProductPlan["executionStage"] })}><option>waiting</option><option>touched</option><option>flipped</option><option>confirmed</option></select></label>
      <label><span>Volume</span><select value={plan.volumeCondition} onChange={(event) => setPlan({ ...plan, volumeCondition: event.target.value as ProductPlan["volumeCondition"] })}><option>low</option><option>normal</option><option>high</option></select></label>
      <label><span>Session phase</span><select value={plan.sessionPhase} onChange={(event) => setPlan({ ...plan, sessionPhase: event.target.value as ProductPlan["sessionPhase"] })}><option>normal</option><option>pre-open</option><option>late</option></select></label>
      <label><span>News risk</span><select value={plan.newsRisk} onChange={(event) => setPlan({ ...plan, newsRisk: event.target.value as ProductPlan["newsRisk"] })}><option>clear</option><option>caution</option><option>red</option></select></label>
    </div>
    <div className="zone-builder">
      <select value={zone.kind} onChange={(event) => setZone({ ...zone, kind: event.target.value as ZoneKind })}>{kinds.map((kind) => <option key={kind}>{kind}</option>)}</select>
      <select value={zone.timeframe} onChange={(event) => setZone({ ...zone, timeframe: event.target.value as LtaZone["timeframe"] })}>{timeframes.map((tf) => <option key={tf}>{tf}</option>)}</select>
      <select value={zone.source} onChange={(event) => setZone({ ...zone, source: event.target.value as ProfileSource })}>{sources.map((source) => <option key={source}>{source}</option>)}</select>
      <input type="number" placeholder="Low" value={zone.low || ""} onChange={(event) => setZone({ ...zone, low: Number(event.target.value) })} />
      <input type="number" placeholder="High" value={zone.high || ""} onChange={(event) => setZone({ ...zone, high: Number(event.target.value) })} />
      <input type="number" min="0" max="20" title="Number of prior taps" placeholder="Taps" value={zone.taps} onChange={(event) => setZone({ ...zone, taps: Number(event.target.value) })} />
      <label className="zone-check"><input type="checkbox" checked={zone.tookOutOpposingZone} onChange={(event) => setZone({ ...zone, tookOutOpposingZone: event.target.checked })}/><span>Control zone</span></label>
      <button className="icon-button" title="Add zone" onClick={addZone}><Plus size={17} /></button>
    </div>
    <div className="zones">
      {plan.zones.length === 0 && <div className="empty">Add HTF supply/demand, then PD, EPD, PW, fixed or swing profile levels.</div>}
      {plan.zones.map((item) => <div className="zone" key={item.id}>
        <span className={`zone-kind ${item.kind.toLowerCase()}`}>{item.kind}</span><strong>{item.low.toLocaleString()}–{item.high.toLocaleString()}</strong><span>{item.source} · {item.timeframe} · {item.taps} tap{item.taps === 1 ? "" : "s"}{item.tookOutOpposingZone ? " · control" : ""}</span>
        <button onClick={() => setPlan({ ...plan, zones: plan.zones.filter((current) => current.id !== item.id) })}><Trash2 size={14} /></button>
      </div>)}
    </div>
    {status && <div className="form-status">{status}</div>}
  </section>;
}

import { useMemo, useState } from "react";
import { Calculator } from "lucide-react";

export function RiskCalculator({ accountSize = 50_000, riskPct = 0.5 }: { accountSize?: number; riskPct?: number }) {
  const [values, setValues] = useState({ accountSize, riskPct, entry: 0, stop: 0, target: 0 });
  const result = useMemo(() => {
    const riskPerUnit = Math.abs(values.entry - values.stop);
    if (!values.accountSize || !values.riskPct || !riskPerUnit) return null;
    const riskAmount = values.accountSize * values.riskPct / 100;
    return {
      riskAmount,
      quantity: riskAmount / riskPerUnit,
      notional: riskAmount / riskPerUnit * values.entry,
      rr: values.target ? Math.abs(values.target - values.entry) / riskPerUnit : 0
    };
  }, [values]);
  const field = (key: keyof typeof values, label: string) => <label><span>{label}</span><input type="number" value={values[key] || ""} onChange={(event) => setValues({ ...values, [key]: Number(event.target.value) })} /></label>;
  return <section className="panel risk-card">
    <div className="panel-head compact"><div><span className="eyebrow">Position sizing</span><h3><Calculator size={18} /> Risk calculator</h3></div></div>
    <div className="risk-fields">{field("accountSize", "Account USD")}{field("riskPct", "Risk %")}{field("entry", "Entry")}{field("stop", "Stop")}{field("target", "Target")}</div>
    <div className="risk-results">
      <div><span>Risk</span><strong>${result?.riskAmount.toFixed(2) ?? "—"}</strong></div>
      <div><span>Spot quantity</span><strong>{result?.quantity.toFixed(6) ?? "—"}</strong></div>
      <div><span>Notional</span><strong>${result?.notional.toFixed(0) ?? "—"}</strong></div>
      <div><span>Reward</span><strong className={(result?.rr ?? 0) >= 2 ? "green" : "red"}>{result ? `${result.rr.toFixed(2)}R` : "—"}</strong></div>
    </div>
  </section>;
}

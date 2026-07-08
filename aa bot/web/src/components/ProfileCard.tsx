import type { ProductState } from "../types";

const fmt = (value: number | null) => value ? value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : "Collecting…";

export function ProfileCard({ state }: { state: ProductState }) {
  const max = Math.max(0, ...state.profile.buckets.map((bucket) => bucket.volume));
  return <section className="panel profile-card">
    <div className="panel-head compact"><div><span className="eyebrow">Live trades since connection</span><h3>Rolling volume profile</h3></div><span className="value-area">70% VA</span></div>
    <div className="profile-levels"><div><span>VAH</span><strong>{fmt(state.profile.vah)}</strong></div><div className="poc"><span>POC</span><strong>{fmt(state.profile.poc)}</strong></div><div><span>VAL</span><strong>{fmt(state.profile.val)}</strong></div></div>
    <div className="profile-bars">{state.profile.buckets.slice(-28).reverse().map((bucket) => <div key={bucket.price}><span>{bucket.price.toFixed(1)}</span><i style={{ width: `${max ? bucket.volume / max * 100 : 0}%` }} /></div>)}</div>
    <p className="helper">Use your completed TradingView profile for planning. This live profile is an execution aid, not a replacement.</p>
  </section>;
}

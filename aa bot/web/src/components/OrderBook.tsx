import type { PriceLevel, ProductState } from "../types";

const fmt = (value: number, digits = 2) => value.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });

function Row({ level, side, max }: { level: PriceLevel; side: "bid" | "ask"; max: number }) {
  const depth = max ? level.size / max * 100 : 0;
  return <div className={`book-row ${side}`}>
    <div className="depth" style={{ width: `${depth}%` }} />
    <span>{fmt(level.price)}</span><span>{level.size.toFixed(5)}</span><span>{level.orders || "—"}</span>
  </div>;
}

export function OrderBook({ state }: { state: ProductState }) {
  const asks = [...state.book.asks].slice(0, 10).reverse();
  const bids = state.book.bids.slice(0, 10);
  const max = Math.max(0, ...asks.map((level) => level.size), ...bids.map((level) => level.size));
  const spread = state.ticker.ask && state.ticker.bid ? state.ticker.ask - state.ticker.bid : 0;
  return <section className="panel orderbook">
    <div className="panel-head compact"><div><span className="eyebrow">{state.mode === "full" ? "Level 3 / MBO" : "Level 2 fallback"}</span><h3>Order book</h3></div><span className={`status-dot ${state.status}`}>{state.status}</span></div>
    <div className="book-header"><span>Price</span><span>Size</span><span>Orders</span></div>
    <div>{asks.map((level) => <Row key={`a${level.price}`} level={level} side="ask" max={max} />)}</div>
    <div className="spread"><strong>{state.ticker.price ? fmt(state.ticker.price) : "—"}</strong><span>Spread {spread.toFixed(2)} · {state.micro.spreadBps.toFixed(2)} bps</span></div>
    <div>{bids.map((level) => <Row key={`b${level.price}`} level={level} side="bid" max={max} />)}</div>
  </section>;
}

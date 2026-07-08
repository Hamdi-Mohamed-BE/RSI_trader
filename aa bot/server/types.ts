export type Side = "buy" | "sell";
export type Bias = "bullish" | "bearish" | "neutral";
export type StructureState = "reclaim" | "rejection" | "breakout" | "breakdown" | "range";
export type ZoneKind = "POC" | "VAH" | "VAL" | "DEMAND" | "SUPPLY" | "LIQUIDITY_HIGH" | "LIQUIDITY_LOW";
export type ProfileSource = "LIVE" | "PD" | "EPD" | "PW" | "FIXED" | "SWING" | "LTF_SWING" | "HTF_ZONE";
export type EntryModel = "AUTO" | "EM1" | "EM2" | "EM3" | "EM4";
export type AuctionPattern = "UNSET" | "RANGE" | "CERC" | "CME";
export type MarketPhase = "contrarian" | "momentum";
export type ExecutionStage = "waiting" | "touched" | "flipped" | "confirmed";
export type VolumeCondition = "low" | "normal" | "high";
export type NewsRisk = "clear" | "caution" | "red";

export interface MboOrder {
  id: string;
  side: Side;
  price: number;
  size: number;
}

export interface PriceLevel {
  price: number;
  size: number;
  orders: number;
}

export interface BookView {
  bids: PriceLevel[];
  asks: PriceLevel[];
  sequence: number;
  mode: "full" | "level2";
  synced: boolean;
}

export interface TradePrint {
  time: number;
  price: number;
  size: number;
  aggressor: Side;
  makerOrderId?: string;
}

export interface CoinbaseFullEvent {
  type: string;
  product_id?: string;
  sequence?: number;
  order_id?: string;
  maker_order_id?: string;
  side?: Side;
  price?: string;
  size?: string;
  remaining_size?: string;
  new_size?: string;
  time?: string;
  reason?: string;
  changes?: Array<[Side, string, string]>;
  bids?: Array<[string, string]>;
  asks?: Array<[string, string]>;
}

export interface MicrostructureSignal {
  timestamp: number;
  score: number;
  imbalance: number;
  delta5s: number;
  delta30s: number;
  bidRefreshes: number;
  askRefreshes: number;
  absorption: "long" | "short" | "none";
  spoofWarning: boolean;
  spoofSide: Side | null;
  stackedBidLevels: number;
  stackedAskLevels: number;
  spreadBps: number;
  reasons: string[];
}

export interface VolumeProfile {
  poc: number | null;
  vah: number | null;
  val: number | null;
  totalVolume: number;
  buckets: Array<{ price: number; volume: number }>;
  startedAt: number | null;
}

export interface LtaZone {
  id: string;
  kind: ZoneKind;
  low: number;
  high: number;
  timeframe: "W1" | "D1" | "H4" | "H1" | "M30" | "M15" | "M5";
  fresh: boolean;
  source: ProfileSource;
  taps: number;
  tookOutOpposingZone: boolean;
  note?: string;
}

export interface ProductPlan {
  productId: string;
  bias: Bias;
  structure: StructureState;
  session: "Asia" | "London" | "New York" | "Off-hours";
  sessionPhase: "normal" | "pre-open" | "late";
  newsRisk: NewsRisk;
  volumeCondition: VolumeCondition;
  marketPhase: MarketPhase;
  auctionPattern: AuctionPattern;
  entryModel: EntryModel;
  executionStage: ExecutionStage;
  zones: LtaZone[];
  accountSize: number;
  riskPct: number;
  preferredDirection: "long" | "short" | "both" | "none";
}

export interface RankedSetup {
  direction: "long" | "short" | "none";
  grade: "A+" | "A" | "B" | "NO TRADE";
  score: number;
  status: "PRE-IDEA" | "ARMED" | "TRIGGERED" | "NO TRADE";
  pattern: string;
  entryModel: Exclude<EntryModel, "AUTO"> | null;
  marketPhase: MarketPhase;
  zone: LtaZone | null;
  entry: number | null;
  stop: number | null;
  targets: number[];
  rr: number | null;
  gates: Array<{ name: string; passed: boolean; detail: string }>;
  targetDetails: Array<{ price: number; label: string; rr: number }>;
  management: string[];
  reasons: string[];
  cancelConditions: string[];
}

export interface ProductState {
  productId: string;
  status: "connecting" | "syncing" | "live" | "fallback" | "reconnecting" | "error";
  mode: "full" | "level2";
  lastMessageAt: number | null;
  reconnects: number;
  sequenceGaps: number;
  ticker: { price: number | null; bid: number | null; ask: number | null };
  book: BookView;
  micro: MicrostructureSignal;
  profile: VolumeProfile;
  plan: ProductPlan;
  setup: RankedSetup;
}

from enum import StrEnum


class AccountRole(StrEnum):
    MASTER_CANDIDATE = "master_candidate"
    FOLLOWER = "follower"


class AccountState(StrEnum):
    DISABLED = "disabled"
    PAUSED = "paused"
    MONITOR_ONLY = "monitor_only"
    ACTIVE = "active"


class ExecutionMode(StrEnum):
    MONITOR = "monitor"
    DEMO = "demo"
    LIVE = "live"


class TerminalHealth(StrEnum):
    UNKNOWN = "unknown"
    STARTING = "starting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"


class TradeAction(StrEnum):
    MARKET_OPEN = "market_open"
    PENDING_CREATE = "pending_create"
    MODIFY = "modify"
    PARTIAL_CLOSE = "partial_close"
    CLOSE = "close"
    CANCEL = "cancel"
    REVERSE = "reverse"


class Side(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class RiskMode(StrEnum):
    MIRROR_LOTS = "mirror_lots"
    STOP_PERCENT = "stop_percent"
    FIXED_CASH = "fixed_cash"
    EQUITY_PROPORTIONAL = "equity_proportional"
    FIXED_LOTS = "fixed_lots"


class JobStatus(StrEnum):
    QUEUED = "queued"
    DISPATCHED = "dispatched"
    ACKNOWLEDGED = "acknowledged"
    FILLED = "filled"
    REJECTED = "rejected"
    FAILED = "failed"


class AuditSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

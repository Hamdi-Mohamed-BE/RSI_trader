from contextlib import contextmanager
from types import SimpleNamespace

from nasdaq_weakness import live


def test_live_worker_initializes_mt5_before_symbol_discovery(monkeypatch):
    events = []

    @contextmanager
    def fake_connection():
        events.append("connected")
        yield
        events.append("shutdown")

    config = SimpleNamespace(live_allowed=True)
    monkeypatch.setattr(live, "connection", fake_connection)
    monkeypatch.setattr(
        live,
        "_run_live_connected",
        lambda cfg, cycles: events.append((cfg, cycles)),
    )

    live.run_live(config, cycles=1)

    assert events == ["connected", (config, 1), "shutdown"]

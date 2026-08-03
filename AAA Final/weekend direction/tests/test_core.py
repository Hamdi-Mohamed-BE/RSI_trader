from datetime import datetime, timezone
import json

from weekend_direction.core import infer_weekly_timing, model_validated, momentum_signal, risk_sized_volume


def test_rejected_model_forces_false(tmp_path) -> None:
    path = tmp_path / "metadata.json"
    path.write_text(json.dumps({"selected_model": {"deployment_status": "rejected"}}))
    assert not model_validated(path, {"validated": False})


def test_threshold_uses_prior_returns_only() -> None:
    signal = momentum_signal(current_return=0.10, prior_returns=[0.01] * 20, quantile=0.70, close_utc=datetime(2026, 8, 7, tzinfo=timezone.utc))
    assert signal is not None and signal.side == "BUY"


def test_weekly_timing_is_inferred_from_gaps() -> None:
    base = int(datetime(2026, 1, 2, 21, 59, tzinfo=timezone.utc).timestamp())
    times = []
    for week in range(6):
        close = base + week * 7 * 86400
        times.extend([close - 60, close, close + 51 * 3600])
    timing = infer_weekly_timing(times)
    assert timing.observations >= 4


def test_min_lot_never_overrisks() -> None:
    assert risk_sized_volume(5, 1000, 0.01, 10, 0.01) is None

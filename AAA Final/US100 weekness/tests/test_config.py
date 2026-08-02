from pathlib import Path

import pytest

from nasdaq_weakness.config import Config, load_config


def test_requested_half_percent_risk_is_valid(tmp_path: Path):
    Config(project_dir=tmp_path, risk_pct=0.5).validate()


def test_risk_above_one_hundred_percent_is_rejected(tmp_path: Path):
    with pytest.raises(ValueError):
        Config(project_dir=tmp_path, risk_pct=100.01).validate()


def test_target_is_capped_at_one_point_seven_r(tmp_path: Path):
    config = Config(project_dir=tmp_path, target_rr=3.0, max_target_rr=1.7)
    assert config.effective_target_rr == 1.7


def test_broker_symbol_casing_is_preserved(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("CANONICAL_SYMBOL", "USTEC_x100m")
    assert load_config(tmp_path).canonical_symbol == "USTEC_x100m"

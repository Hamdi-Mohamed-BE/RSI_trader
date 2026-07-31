from pathlib import Path

import pytest

from nasdaq_weakness.config import Config


def test_requested_two_percent_risk_is_valid(tmp_path: Path):
    Config(project_dir=tmp_path, risk_pct=2.0).validate()


def test_risk_above_two_percent_is_rejected(tmp_path: Path):
    with pytest.raises(ValueError):
        Config(project_dir=tmp_path, risk_pct=2.01).validate()

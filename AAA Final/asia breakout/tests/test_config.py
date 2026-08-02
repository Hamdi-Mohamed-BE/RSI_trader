import json

from asia_breakout.config import load_config


def test_symbol_strategy_file_overrides_shared_defaults(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "basket.json"
    config_path.write_text(
        json.dumps(
            {
                "TEST": {
                    "strategy": {
                        "entry_mode": "close_retest",
                        "stop_mode": "opposite",
                        "rr": 5.0,
                        "exit_mode": "trailing",
                        "trail_start_r": 2.0,
                        "trail_distance_r": 1.0,
                        "buffer_range_fraction": 0.0,
                        "min_range_adr_fraction": 0.05,
                        "max_range_adr_fraction": 1.0,
                        "retest_bars": 4,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            (
                "RR=1.5",
                "SYMBOLS=TEST",
                "SYMBOL_CONFIG_PATH=basket.json",
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("SYMBOL_CONFIG_PATH", raising=False)

    config = load_config(env_path)

    assert config.strategy.rr == 1.5
    assert config.strategy_for("TEST").rr == 1.7
    assert config.strategy_for("TEST").exit_mode == "trailing"

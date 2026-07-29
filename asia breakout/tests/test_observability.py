from asia_breakout.observability import render_table


def test_render_table_displays_signal_fields() -> None:
    output = render_table(
        [
            {
                "instrument": "XAUUSD",
                "order": "BUY_STOP",
                "entry": 2400.0,
                "status": "DRY_RUN",
            }
        ],
        ("instrument", "order", "entry", "status"),
    )
    assert "XAUUSD" in output
    assert "BUY_STOP" in output
    assert "DRY_RUN" in output

import pandas as pd

from naw_lta.providers.databento import DatabentoProvider


def test_available_end_error_is_parsed_with_safety_minute():
    message = (
        "The dataset has data available up to '2026-07-01 23:40:00+00:00'. "
        "The end is after the available range."
    )
    result = DatabentoProvider._available_end_from_error(message)
    assert result == pd.Timestamp("2026-07-01T23:39:00Z").to_pydatetime()

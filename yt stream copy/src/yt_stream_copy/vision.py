from __future__ import annotations

import re
from pathlib import Path
from typing import Any


_engine = None


def read_trading_screen(path: str | Path) -> dict[str, Any]:
    """OCR a stream frame and return only conservative, explicitly labelled trade levels."""
    global _engine
    if _engine is None:
        from rapidocr import RapidOCR
        _engine = RapidOCR()
    result = _engine(str(path))
    texts = [str(item) for item in (result.txts or ())]
    scores = list(result.scores or ())
    reliable = [text for text, score in zip(texts, scores) if float(score) >= 0.55]
    joined = " | ".join(reliable)

    def level(labels: str) -> float | None:
        match = re.search(rf"(?:{labels})\s*[:=@-]?\s*([$]?\d{{3,6}}(?:[,.]\d+)?)", joined, re.I)
        return float(match.group(1).replace("$", "").replace(",", ".")) if match else None

    prices: list[float] = []
    for token in re.findall(r"(?<!\d)(\d{3,6}(?:[,.]\d{1,3})?)(?!\d)", joined):
        value = float(token.replace(",", "."))
        if 100 <= value <= 1_000_000 and value not in prices:
            prices.append(value)
    return {
        "text": joined,
        "prices": prices[:30],
        "entry": level(r"entry|open|price"),
        "stop_loss": level(r"stop(?: loss)?|s/?l"),
        "take_profit": level(r"take profit|target|t/?p"),
    }

from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path


class PredictionService:
    """Prediction-only bridge. It never changes model execution_capability."""

    def __init__(self, ai_root: Path, output_root: Path) -> None:
        spec = importlib.util.spec_from_file_location("ai_news_predict_news", ai_root / "predict_news.py")
        if spec is None or spec.loader is None:
            raise RuntimeError("Could not load AI news prediction module")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.module = module
        self.output_root = output_root

    def predict(self, event: str, release: datetime, stage: str, forecast: str | None, previous: str | None) -> dict:
        output = self.output_root / stage
        output.mkdir(parents=True, exist_ok=True)
        self.module.PREDICTION_DIR = output
        result = self.module.make_prediction(event=event, release_utc=release.astimezone(timezone.utc), forecast=forecast, previous=previous)
        if result.get("execution_capability") is not False:
            raise RuntimeError("Prediction artifact unexpectedly claims execution capability")
        generated = datetime.fromisoformat(str(result["generated_at_utc"]).replace("Z", "+00:00"))
        if generated >= release:
            raise RuntimeError("Post-release prediction rejected")
        path = Path(result["saved_to"])
        path.with_suffix(".sealed.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result

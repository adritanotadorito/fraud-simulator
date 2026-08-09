import logging
import os
from typing import Dict
from app.models.schemas import EngineScoreResponse

logger = logging.getLogger(__name__)

MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "ml", "models", "isolation_forest.pkl"
)

# Typical value ranges for anomaly detection
TYPICAL_RANGES = {
    "amount": (5.0, 500.0),
    "velocity": (0.0, 3.0),
    "amount_zscore": (0.0, 2.0),
    "device_change": (0.0, 0.0),
    "geo_velocity": (0.0, 200.0),
    "biometric_deviation": (0.0, 0.3),
    "hour_of_day": (6.0, 22.0),
    "is_new_merchant": (0.0, 0.0),
}


class IsolationForestScorer:
    """Isolation Forest Scorer — uses Adrita's trained model when available."""

    def __init__(self):
        self.model = None
        self.model_loaded = False
        self._load_model()

    def _load_model(self):
        """Attempt to load Adrita's trained Isolation Forest model."""
        try:
            import joblib
            resolved = os.path.abspath(MODEL_PATH)
            if os.path.exists(resolved):
                self.model = joblib.load(resolved)
                self.model_loaded = True
                logger.info(f"Isolation Forest model loaded from {resolved}")
            else:
                logger.warning(f"Isolation Forest model not found at {resolved}, using heuristic")
        except Exception as e:
            logger.warning(f"Failed to load Isolation Forest model: {e}, using heuristic")

    def _predict_with_model(self, features: Dict[str, float]) -> float:
        """Run through Adrita's real Isolation Forest."""
        try:
            import pandas as pd

            feature_df = pd.DataFrame([{
                "Amount": features.get("amount", 0),
                "amount_zscore": features.get("amount_zscore", 0),
                "transaction_velocity": features.get("velocity", 0),
                "device_change_flag": int(features.get("device_change", 0)),
                "geo_velocity": features.get("geo_velocity", 0),
                "biometric_deviation": features.get("biometric_deviation", 0),
                "time_diff": 0,
            }])

            # Pad missing columns
            if hasattr(self.model, "feature_names_in_"):
                for col in self.model.feature_names_in_:
                    if col not in feature_df.columns:
                        feature_df[col] = 0.0
                feature_df = feature_df[self.model.feature_names_in_]

            prediction = self.model.predict(feature_df)[0]
            # Isolation Forest returns -1 for anomaly, 1 for normal
            return 1.0 if prediction == -1 else 0.0
        except Exception as e:
            logger.warning(f"Isolation Forest prediction failed: {e}, using heuristic")
            return self._heuristic_score(features)

    def _heuristic_score(self, features: Dict[str, float]) -> float:
        """Heuristic fallback based on out-of-range features."""
        out_of_range = 0
        total = 0
        for key, (low, high) in TYPICAL_RANGES.items():
            val = features.get(key)
            if val is not None:
                total += 1
                if val < low or val > high:
                    out_of_range += 1
        if total == 0:
            return 0.1
        return min(out_of_range / max(total, 1) * 1.5, 1.0)

    def score(self, features: Dict[str, float]) -> EngineScoreResponse:
        """Score using real model or heuristic fallback."""
        if self.model_loaded and self.model is not None:
            anomaly_score = self._predict_with_model(features)
            model_type = "trained_isolation_forest"
        else:
            anomaly_score = self._heuristic_score(features)
            model_type = "heuristic_stub"

        signals = []
        if anomaly_score > 0.6:
            signals.append("Anomalous transaction pattern")
        elif anomaly_score > 0.3:
            signals.append("Slightly unusual pattern")
        else:
            signals.append("Normal behavioral pattern")

        return EngineScoreResponse(
            score=round(anomaly_score, 4),
            confidence=0.75 if self.model_loaded else 0.6,
            signals=signals,
            details={
                "model_type": model_type,
                "is_stub": not self.model_loaded,
            }
        )

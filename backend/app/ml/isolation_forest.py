import logging
from typing import Dict
from app.models.schemas import EngineScoreResponse

logger = logging.getLogger(__name__)


class IsolationForestScorer:
    """STUB: Heuristic anomaly scorer simulating Isolation Forest."""

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

    def score(self, features: Dict[str, float]) -> EngineScoreResponse:
        """Compute anomaly score based on how many features are out of range."""
        out_of_range = 0
        total_features = 0

        for key, (low, high) in self.TYPICAL_RANGES.items():
            val = features.get(key)
            if val is not None:
                total_features += 1
                if val < low or val > high:
                    out_of_range += 1

        if total_features == 0:
            return EngineScoreResponse(
                score=0.1, confidence=0.4,
                signals=["Insufficient features for anomaly detection"],
                details={}
            )

        anomaly_score = min(out_of_range / max(total_features, 1) * 1.5, 1.0)

        signals = []
        if anomaly_score > 0.6:
            signals.append("Anomalous transaction pattern")
        elif anomaly_score > 0.3:
            signals.append("Slightly unusual pattern")
        else:
            signals.append("Normal behavioral pattern")

        return EngineScoreResponse(
            score=round(anomaly_score, 4), confidence=0.6,
            signals=signals,
            details={"out_of_range_features": out_of_range, "total_features": total_features}
        )

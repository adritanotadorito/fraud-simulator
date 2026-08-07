import random
import logging
from typing import Dict, Any, Optional
from app.models.schemas import EngineScoreResponse

logger = logging.getLogger(__name__)


class XGBoostScorer:
    """STUB: Heuristic-based scorer simulating XGBoost until Adrita's real model is ready."""

    def __init__(self):
        self.model_loaded = False

    def load_model(self):
        """Attempt to load a trained model from disk."""
        self.model_loaded = False

    def extract_features(
        self, transaction, session=None, device=None, user_history=None
    ) -> Dict[str, float]:
        """Extract feature dict from raw data. All inputs can be dicts."""
        def g(obj, key, default=0.0):
            if obj is None:
                return default
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        amount = float(g(transaction, "amount", 0))

        bio = {}
        if session:
            bio = g(session, "biometrics", {})
            if hasattr(bio, "model_dump"):
                bio = bio.model_dump()
            elif not isinstance(bio, dict):
                bio = {}

        return {
            "amount": amount,
            "velocity": 1.0,
            "amount_zscore": min(amount / 1000.0, 5.0),
            "device_change": 1.0 if g(device, "vpn_flag", False) or g(device, "emulator_flag", False) else 0.0,
            "geo_velocity": 0.0,
            "biometric_deviation": float(bio.get("mouse_pattern_deviation", 0.1) if isinstance(bio, dict) else 0.1),
            "hour_of_day": 12.0,
            "is_new_merchant": 0.0,
        }

    def score(self, features: Dict[str, float]) -> EngineScoreResponse:
        """Score using weighted heuristic (simulates XGBoost)."""
        amount_risk = min(features.get("amount", 0) / 10000.0, 1.0)
        velocity_risk = min(features.get("velocity", 0) / 5.0, 1.0)
        device_risk = features.get("device_change", 0.0)
        geo_risk = min(features.get("geo_velocity", 0) / 1000.0, 1.0)
        biometric_risk = min(features.get("biometric_deviation", 0), 1.0)

        base_score = (
            amount_risk * 0.25
            + velocity_risk * 0.2
            + device_risk * 0.15
            + geo_risk * 0.2
            + biometric_risk * 0.2
        )

        noise = random.uniform(-0.05, 0.05)
        final_score = max(0.0, min(base_score + noise, 1.0))

        signals = []
        if amount_risk > 0.6:
            signals.append("High amount risk (XGB)")
        if velocity_risk > 0.6:
            signals.append("High velocity risk (XGB)")
        if device_risk > 0.5:
            signals.append("Device change risk (XGB)")
        if biometric_risk > 0.5:
            signals.append("Biometric deviation (XGB)")
        if not signals:
            signals.append("Normal transaction pattern (XGB)")

        return EngineScoreResponse(
            score=round(final_score, 4), confidence=0.7,
            signals=signals, details={"is_stub": True}
        )

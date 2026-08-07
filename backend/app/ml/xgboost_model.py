import logging
import os
import random
from typing import Dict, Any, Optional
from app.models.schemas import EngineScoreResponse

logger = logging.getLogger(__name__)

# Path to Adrita's trained model
MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "ml", "models", "fraud_model.pkl"
)


class XGBoostScorer:
    """XGBoost Model Scorer — uses Adrita's trained model when available, falls back to heuristic."""

    def __init__(self):
        self.model = None
        self.model_loaded = False
        self._load_model()

    def _load_model(self):
        """Attempt to load Adrita's trained XGBoost model."""
        try:
            import joblib
            resolved = os.path.abspath(MODEL_PATH)
            if os.path.exists(resolved):
                self.model = joblib.load(resolved)
                self.model_loaded = True
                logger.info(f"XGBoost model loaded from {resolved}")
            else:
                logger.warning(f"XGBoost model not found at {resolved}, using heuristic")
        except Exception as e:
            logger.warning(f"Failed to load XGBoost model: {e}, using heuristic")
            self.model_loaded = False

    def extract_features(
        self, transaction, session=None, device=None, user_history=None
    ) -> Dict[str, float]:
        """Extract features compatible with both real model and heuristic."""
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

    def _predict_with_model(self, features: Dict[str, float]) -> float:
        """Run prediction through Adrita's real XGBoost model."""
        try:
            import pandas as pd
            import numpy as np

            # Map our feature names to Adrita's training feature names
            # Her model was trained on creditcard.csv with engineered features
            # We build a compatible feature vector
            feature_df = pd.DataFrame([{
                "Amount": features.get("amount", 0),
                "amount_zscore": features.get("amount_zscore", 0),
                "transaction_velocity": features.get("velocity", 0),
                "device_change_flag": int(features.get("device_change", 0)),
                "geo_velocity": features.get("geo_velocity", 0),
                "biometric_deviation": features.get("biometric_deviation", 0),
                "time_diff": 0,
            }])

            # Pad remaining columns the model expects with zeros (V1-V28, Time, etc.)
            model_features = self.model.get_booster().feature_names
            if model_features:
                for col in model_features:
                    if col not in feature_df.columns:
                        feature_df[col] = 0.0
                feature_df = feature_df[model_features]

            proba = self.model.predict_proba(feature_df)[0][1]
            return float(proba)
        except Exception as e:
            logger.warning(f"Real model prediction failed: {e}, falling back to heuristic")
            return self._heuristic_score(features)

    def _heuristic_score(self, features: Dict[str, float]) -> float:
        """Heuristic fallback scoring."""
        amount_risk = min(features.get("amount", 0) / 10000.0, 1.0)
        velocity_risk = min(features.get("velocity", 0) / 5.0, 1.0)
        device_risk = features.get("device_change", 0.0)
        geo_risk = min(features.get("geo_velocity", 0) / 1000.0, 1.0)
        biometric_risk = min(features.get("biometric_deviation", 0), 1.0)

        base = (
            amount_risk * 0.25 + velocity_risk * 0.2 + device_risk * 0.15
            + geo_risk * 0.2 + biometric_risk * 0.2
        )
        noise = random.uniform(-0.05, 0.05)
        return max(0.0, min(base + noise, 1.0))

    def score(self, features: Dict[str, float]) -> EngineScoreResponse:
        """Score using real model if available, else heuristic."""
        if self.model_loaded and self.model is not None:
            final_score = self._predict_with_model(features)
            model_type = "trained_xgboost"
        else:
            final_score = self._heuristic_score(features)
            model_type = "heuristic_stub"

        signals = []
        if final_score > 0.7:
            signals.append("High fraud probability (XGB)")
        elif final_score > 0.4:
            signals.append("Moderate fraud risk (XGB)")
        else:
            signals.append("Normal transaction pattern (XGB)")

        amount_risk = min(features.get("amount", 0) / 10000.0, 1.0)
        if amount_risk > 0.6:
            signals.append("High amount risk (XGB)")
        if features.get("device_change", 0) > 0.5:
            signals.append("Device change risk (XGB)")

        return EngineScoreResponse(
            score=round(final_score, 4),
            confidence=0.85 if self.model_loaded else 0.7,
            signals=signals,
            details={"model_type": model_type, "is_stub": not self.model_loaded}
        )

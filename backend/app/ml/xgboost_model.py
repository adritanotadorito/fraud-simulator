import logging
import os
import random
from typing import Dict, Any, Optional
from app.models.schemas import EngineScoreResponse

logger = logging.getLogger(__name__)

# Path to trained model (9-feature version — see ml/retrain_models.py)
MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "ml", "models", "fraud_model.pkl"
)

# The 9 features the retrained model expects — must match retrain_models.py::FEATURES
MODEL_FEATURES = [
    "amount",
    "amount_zscore",
    "transaction_velocity",
    "time_diff",
    "device_change_flag",
    "geo_velocity",
    "biometric_deviation",
    "hour_of_day",
    "is_new_merchant",
]


class XGBoostScorer:
    """XGBoost Model Scorer — uses the 9-feature retrained model when available, falls back to heuristic."""

    def __init__(self):
        self.model = None
        self.model_loaded = False
        self._load_model()

    def _load_model(self):
        """Attempt to load the retrained XGBoost model."""
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
        """Extract the 9 features the retrained model expects.

        All of these are derivable at inference time from real/uploaded data.
        """
        def g(obj, key, default=0.0):
            if obj is None:
                return default
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        amount = float(g(transaction, "amount", 0))

        # Biometrics
        bio = {}
        if session:
            bio = g(session, "biometrics", {})
            if hasattr(bio, "model_dump"):
                bio = bio.model_dump()
            elif not isinstance(bio, dict):
                bio = {}

        # Device flags
        vpn = g(device, "vpn_flag", False)
        emulator = g(device, "emulator_flag", False)
        tor = g(device, "tor_flag", False)
        device_change = 1.0 if (vpn or emulator or tor) else 0.0

        # Geo velocity — from transaction extra data or default
        geo_velocity = float(g(transaction, "geo_velocity", 0.0))
        if geo_velocity == 0.0:
            # Check extras dict if present (uploaded CSVs may store it there)
            extras = g(transaction, "extra", {})
            if isinstance(extras, dict):
                geo_velocity = float(extras.get("geo_velocity", 0.0))

        # Biometric deviation
        biometric_deviation = float(
            bio.get("mouse_pattern_deviation", 0.1) if isinstance(bio, dict) else 0.1
        )

        # Hour of day
        hour = 12.0
        timestamp = g(transaction, "timestamp", None)
        if timestamp:
            try:
                if hasattr(timestamp, "hour"):
                    hour = float(timestamp.hour)
                else:
                    from datetime import datetime
                    ts = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
                    hour = float(ts.hour)
            except Exception:
                pass

        # Transaction velocity / time_diff
        velocity = float(g(transaction, "transaction_velocity", 0.0))
        time_diff = float(g(transaction, "time_diff", 600.0))

        # Check extras for these fields too (uploaded CSVs)
        extras = g(transaction, "extra", {})
        if isinstance(extras, dict):
            if velocity == 0.0:
                velocity = float(extras.get("transaction_velocity", 0.0))
            if time_diff == 600.0:
                time_diff = float(extras.get("time_diff", 600.0))

        return {
            "amount": amount,
            "amount_zscore": min(amount / 1000.0, 5.0),
            "transaction_velocity": velocity,
            "time_diff": time_diff,
            "device_change_flag": device_change,
            "geo_velocity": geo_velocity,
            "biometric_deviation": biometric_deviation,
            "hour_of_day": hour,
            "is_new_merchant": float(g(transaction, "is_new_merchant", 0.0)),
        }

    def _predict_with_model(self, features: Dict[str, float]) -> float:
        """Run prediction through the retrained XGBoost model (9 features)."""
        try:
            import pandas as pd

            feature_df = pd.DataFrame([{
                "amount": features.get("amount", 0),
                "amount_zscore": features.get("amount_zscore", 0),
                "transaction_velocity": features.get("transaction_velocity", 0),
                "time_diff": features.get("time_diff", 0),
                "device_change_flag": features.get("device_change_flag", 0),
                "geo_velocity": features.get("geo_velocity", 0),
                "biometric_deviation": features.get("biometric_deviation", 0),
                "hour_of_day": features.get("hour_of_day", 12),
                "is_new_merchant": features.get("is_new_merchant", 0),
            }])

            # Ensure column order matches training
            feature_df = feature_df[MODEL_FEATURES]

            proba = self.model.predict_proba(feature_df)[0][1]
            return float(proba)
        except Exception as e:
            logger.warning(f"Real model prediction failed: {e}, falling back to heuristic")
            return self._heuristic_score(features)

    def _heuristic_score(self, features: Dict[str, float]) -> float:
        """Heuristic fallback scoring."""
        amount_risk = min(features.get("amount", 0) / 10000.0, 1.0)
        velocity_risk = min(features.get("transaction_velocity", 0) / 0.5, 1.0)
        device_risk = features.get("device_change_flag", 0.0)
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
        if features.get("device_change_flag", 0) > 0.5:
            signals.append("Device change risk (XGB)")

        return EngineScoreResponse(
            score=round(final_score, 4),
            confidence=0.85 if self.model_loaded else 0.7,
            signals=signals,
            details={"model_type": model_type, "is_stub": not self.model_loaded}
        )

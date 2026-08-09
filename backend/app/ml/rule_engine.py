import logging
from app.models.schemas import EngineScoreResponse

logger = logging.getLogger(__name__)


class RuleEngine:
    """Deterministic rule-based fraud checks."""

    def score(self, transaction, device=None, session=None) -> EngineScoreResponse:
        """Apply deterministic rules. All inputs can be dicts or Pydantic models."""
        # Normalize to dict access
        def g(obj, key, default=None):
            if obj is None:
                return default
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        score = 0.0
        signals = []

        # Amount rules
        amount = float(g(transaction, "amount", 0))
        if amount > 50000:
            score += 0.5
            signals.append("Very high value transaction (>$50K)")
        elif amount > 10000:
            score += 0.3
            signals.append("High value transaction (>$10K)")

        currency = g(transaction, "currency", "USD")
        if currency != "USD" and amount > 5000:
            score += 0.15
            signals.append("Large foreign currency transaction")

        # Device rules
        if device:
            if g(device, "vpn_flag", False) or g(device, "tor_flag", False):
                score += 0.25
                signals.append("VPN/TOR detected (rule)")
            if g(device, "emulator_flag", False):
                score += 0.2
                signals.append("Emulator detected (rule)")

        # Time rules
        timestamp = g(transaction, "timestamp")
        if timestamp:
            try:
                if hasattr(timestamp, "hour"):
                    hour = timestamp.hour
                else:
                    from datetime import datetime
                    ts = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
                    hour = ts.hour
                if 0 <= hour <= 5:
                    score += 0.1
                    signals.append("Unusual hour transaction (00:00-05:00)")
            except Exception:
                pass

        # Biometrics rules
        if session:
            bio = g(session, "biometrics", {})
            if isinstance(bio, dict):
                deviation = bio.get("mouse_pattern_deviation", 0)
            else:
                deviation = getattr(bio, "mouse_pattern_deviation", 0)
            if deviation and float(deviation) > 0.7:
                score += 0.2
                signals.append("High biometric deviation (rule)")

        score = min(score, 1.0)

        if not signals:
            signals.append("No rules triggered")

        return EngineScoreResponse(
            score=score, confidence=0.95, signals=signals,
            details={"rules_triggered": len(signals)}
        )

import logging
from typing import List
from app.models.schemas import EngineScoreResponse
from app.database import find_many

logger = logging.getLogger(__name__)


class BiometricsEngine:
    """Engine to assess biometric anomalies based on a user's historical sessions."""

    async def score(self, session_data, user_id: str) -> EngineScoreResponse:
        """Compare current session biometrics against user's historical baseline."""
        # Handle both dict and object input
        if session_data is None or session_data == {}:
            return EngineScoreResponse(
                score=0.1, confidence=0.3,
                signals=["No session data available"],
                details={"message": "Session data missing"}
            )

        if isinstance(session_data, dict):
            current_bio = session_data.get("biometrics", {})
        else:
            current_bio = session_data.biometrics
            if hasattr(current_bio, "model_dump"):
                current_bio = current_bio.model_dump()

        if not current_bio:
            return EngineScoreResponse(
                score=0.1, confidence=0.3,
                signals=["No biometric data"],
                details={}
            )

        historical = await find_many("sessions", {"user_id": user_id}, limit=10)

        if not historical:
            return EngineScoreResponse(
                score=0.1, confidence=0.3,
                signals=["New behavioral profile"],
                details={"message": "No historical biometric data found."}
            )

        typing_diffs = []
        mouse_diffs = []
        duration_diffs = []

        curr_typing = current_bio.get("typing_rhythm_variance", 0)
        curr_mouse = current_bio.get("mouse_pattern_deviation", 0)
        curr_duration = current_bio.get("session_duration_anomaly", 0)

        for hist in historical:
            hb = hist.get("biometrics", {})
            if not hb:
                continue
            if "typing_rhythm_variance" in hb:
                typing_diffs.append(abs(curr_typing - hb["typing_rhythm_variance"]))
            if "mouse_pattern_deviation" in hb:
                mouse_diffs.append(abs(curr_mouse - hb["mouse_pattern_deviation"]))
            if "session_duration_anomaly" in hb:
                duration_diffs.append(abs(curr_duration - hb["session_duration_anomaly"]))

        score = 0.0
        signals = []

        avg_typing = sum(typing_diffs) / len(typing_diffs) if typing_diffs else 0
        avg_mouse = sum(mouse_diffs) / len(mouse_diffs) if mouse_diffs else 0
        avg_duration = sum(duration_diffs) / len(duration_diffs) if duration_diffs else 0

        if avg_typing > 0.5:
            score += 0.4
            signals.append("Typing pattern anomaly")
        elif avg_typing > 0.2:
            score += 0.2

        if avg_mouse > 0.5:
            score += 0.3
            signals.append("Mouse behavior deviation")
        elif avg_mouse > 0.2:
            score += 0.15

        if avg_duration > 0.5:
            score += 0.3
            signals.append("Session duration unusual")
        elif avg_duration > 0.2:
            score += 0.15

        score = min(score, 1.0)
        num_sessions = len(historical)
        confidence = min(0.3 + (num_sessions / 10.0) * 0.65, 0.95)

        if not signals:
            signals.append("Consistent biometric profile")

        return EngineScoreResponse(
            score=score, confidence=confidence, signals=signals,
            details={"avg_typing_dev": round(avg_typing, 3), "avg_mouse_dev": round(avg_mouse, 3), "avg_duration_dev": round(avg_duration, 3)}
        )

import logging
from typing import Dict, Any
import numpy as np
from app.models.schemas import EngineScoreResponse
from app.config import get_settings

logger = logging.getLogger(__name__)


class FusionScorer:
    """Fuses scores from multiple engines to make a final decision."""

    def score(self, engine_scores: Dict[str, EngineScoreResponse]) -> Dict[str, Any]:
        """Combine engine scores using weighted average and apply thresholds."""
        settings = get_settings()
        weights = settings.FUSION_WEIGHTS
        thresholds = settings.DECISION_THRESHOLDS

        block_threshold = thresholds.get("block", 0.75)
        flag_threshold = thresholds.get("flag", 0.45)

        final_risk = 0.0
        scores = []
        all_signals = []
        engine_scores_detail = {}

        for engine_name, weight in weights.items():
            if engine_name in engine_scores:
                resp = engine_scores[engine_name]
                final_risk += resp.score * weight
                scores.append(resp.score)
                all_signals.extend(resp.signals)
                engine_scores_detail[engine_name] = {
                    "score": resp.score,
                    "confidence": resp.confidence,
                    "signals": resp.signals,
                }

        # Calculate confidence based on score agreement
        if scores:
            std_dev = float(np.std(scores))
            confidence = max(0.0, min(1.0 - (std_dev / 0.5), 1.0))
        else:
            confidence = 0.0

        # Decision
        if final_risk >= block_threshold:
            decision = "BLOCK"
        elif final_risk >= flag_threshold:
            decision = "FLAG"
        else:
            decision = "ALLOW"

        # Deduplicate signals
        reasons = list(dict.fromkeys(all_signals))

        return {
            "final_risk": round(final_risk, 4),
            "confidence": round(confidence, 4),
            "decision": decision,
            "reasons": reasons,
            "engine_scores_detail": engine_scores_detail,
        }

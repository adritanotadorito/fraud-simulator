import logging
import asyncio
import time
from typing import List
from datetime import datetime, timezone

from app.models.schemas import ScoreRequest, ScoreResponse, Decision, EngineScoreResponse
from app.database import find_one, insert_one
from app.config import get_settings
from app.engines.device import DeviceEngine
from app.engines.geo import GeolocationEngine
from app.engines.biometrics import BiometricsEngine
from app.engines.graph import GraphEngine
from app.engines.threat_intel import ThreatIntelEngine
from app.ml.fusion import FusionScorer
from app.ml.xgboost_model import XGBoostScorer
from app.ml.isolation_forest import IsolationForestScorer
from app.ml.rule_engine import RuleEngine
from app.ws.manager import broadcast

logger = logging.getLogger(__name__)


class ShieldGPTOrchestrator:
    """Blue Team AI — analyzes transactions and makes fraud decisions."""

    def __init__(self, llm_client):
        self.llm = llm_client
        self.device_engine = DeviceEngine()
        self.geo_engine = GeolocationEngine()
        self.biometrics_engine = BiometricsEngine()
        self.graph_engine = GraphEngine()
        self.threat_intel = ThreatIntelEngine()
        self.xgboost = XGBoostScorer()
        self.isolation_forest = IsolationForestScorer()
        self.rule_engine = RuleEngine()
        self.fusion = FusionScorer()

    async def analyze_transaction(self, request: ScoreRequest) -> ScoreResponse:
        """Analyze a single transaction: run all engines, fuse scores, generate decision."""
        start_time = time.time()

        txn_data = await find_one("transactions", {"txn_id": request.txn_id})
        if not txn_data:
            raise ValueError(f"Transaction {request.txn_id} not found")

        session_data = await find_one("sessions", {"session_id": txn_data.get("session_id", "")}) or {}
        device_data = await find_one("devices", {"device_id": txn_data.get("device_id", "")}) or {}
        user_id = txn_data.get("user_id", "")
        geo_data = txn_data.get("geo", {})
        timestamp = txn_data.get("timestamp", datetime.now(timezone.utc))
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                timestamp = datetime.now(timezone.utc)

        # Run async engines in parallel
        bio_result, device_result, geo_result, graph_result, threat_result = await asyncio.gather(
            self.biometrics_engine.score(session_data, user_id),
            self.device_engine.score(device_data, user_id),
            self.geo_engine.score(geo_data, user_id, timestamp),
            self.graph_engine.score(user_id, txn_data.get("device_id", "")),
            self.threat_intel.lookup(
                ip=geo_data.get("ip", ""),
                device_id=txn_data.get("device_id", ""),
                account_id=txn_data.get("account_id", ""),
                merchant_id=txn_data.get("merchant_id", "")
            )
        )

        # Run synchronous ML models
        features = self.xgboost.extract_features(txn_data, session_data, device_data, None)
        xgb_result = self.xgboost.score(features)
        if_result = self.isolation_forest.score(features)
        rule_result = self.rule_engine.score(txn_data, device_data, session_data)

        # Fuse the 4 primary scores
        fusion_input = {
            "xgboost": xgb_result,
            "isolation_forest": if_result,
            "rule_engine": rule_result,
            "graph": graph_result
        }
        fusion_result = self.fusion.score(fusion_input)

        final_risk = fusion_result["final_risk"]
        confidence = fusion_result["confidence"]
        decision = fusion_result["decision"]
        reasons = list(fusion_result["reasons"])

        # Boost risk if threat intel is significant
        if threat_result.score > 0.3:
            final_risk = min(final_risk + threat_result.score * 0.15, 1.0)
            reasons = list(set(reasons + threat_result.signals))

        # Add significant engine signals
        for r in [bio_result, device_result, geo_result]:
            if r.score > 0.3:
                reasons = list(set(reasons + [s for s in r.signals if "anomaly" in s.lower() or "detected" in s.lower() or "unusual" in s.lower() or "new" in s.lower() or "risk" in s.lower() or "impossible" in s.lower()]))

        # Recalculate decision after boost
        s = get_settings()
        if final_risk >= s.DECISION_THRESHOLDS["block"]:
            decision = "BLOCK"
        elif final_risk >= s.DECISION_THRESHOLDS["flag"]:
            decision = "FLAG"
        else:
            decision = "ALLOW"

        # Generate explanation
        explanation = f"{decision}: Risk score {final_risk:.2f}. Key factors: {', '.join(reasons[:3])}"
        if request.include_explanation:
            try:
                sys_prompt = "You are ShieldGPT, a blue-team AI fraud analyst. Return JSON with an 'explanation' field containing a 2-3 sentence explanation."
                usr_prompt = (
                    f"Transaction {request.txn_id}: amount=${txn_data.get('amount', 0):.2f}, "
                    f"risk_score={final_risk:.3f}, decision={decision}, "
                    f"signals={reasons[:5]}, device={device_result.signals}, geo={geo_result.signals}"
                )
                llm_res = await self.llm.generate(sys_prompt, usr_prompt)
                explanation = llm_res.get("explanation", explanation)
            except Exception as e:
                logger.warning(f"LLM explanation failed: {e}")

        latency_ms = (time.time() - start_time) * 1000

        # Serialize engine scores for DB storage
        engine_scores_serialized = {
            "biometrics": bio_result.model_dump(),
            "device": device_result.model_dump(),
            "geo": geo_result.model_dump(),
            "graph": graph_result.model_dump(),
            "threat_intel": threat_result.model_dump(),
            "xgboost": xgb_result.model_dump(),
            "isolation_forest": if_result.model_dump(),
            "rule_engine": rule_result.model_dump(),
            "fusion": {"final_risk": final_risk, "confidence": confidence, "latency_ms": round(latency_ms, 1)}
        }

        decision_record = Decision(
            txn_id=request.txn_id,
            risk_score=round(final_risk, 4),
            confidence=round(confidence, 4),
            decision=decision,
            reasons=list(set(reasons)),
            explanation=explanation,
            engine_scores=engine_scores_serialized
        )
        await insert_one("decisions", decision_record.model_dump())

        response = ScoreResponse(
            decision_id=decision_record.decision_id,
            txn_id=request.txn_id,
            risk_score=decision_record.risk_score,
            confidence=decision_record.confidence,
            decision=decision_record.decision,
            reasons=decision_record.reasons,
            explanation=decision_record.explanation,
            engine_scores=engine_scores_serialized
        )
        await broadcast({"type": "decision", "data": response.model_dump()})
        return response

    async def batch_analyze(self, txn_ids: List[str]) -> List[ScoreResponse]:
        """Analyze multiple transactions."""
        results = []
        for txn_id in txn_ids:
            try:
                req = ScoreRequest(txn_id=txn_id, include_explanation=False)
                res = await self.analyze_transaction(req)
                results.append(res)
            except Exception as e:
                logger.error(f"Error analyzing {txn_id}: {e}")
        return results

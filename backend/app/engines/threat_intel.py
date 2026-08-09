import logging
from typing import Optional
from app.models.schemas import EngineScoreResponse
from app.database import find_many

logger = logging.getLogger(__name__)


class ThreatIntelEngine:
    """Engine to check entities against threat intelligence watchlists."""

    async def lookup(
        self,
        ip: Optional[str] = None,
        device_id: Optional[str] = None,
        account_id: Optional[str] = None,
        merchant_id: Optional[str] = None
    ) -> EngineScoreResponse:
        """Query threat_intel collection for matching entries."""
        queries = []
        if ip:
            queries.append({"type": "ip", "value": ip})
        if device_id:
            queries.append({"type": "device", "value": device_id})
        if account_id:
            queries.append({"type": "account", "value": account_id})
        if merchant_id:
            queries.append({"type": "merchant", "value": merchant_id})

        if not queries:
            return EngineScoreResponse(
                score=0.0, confidence=0.5,
                signals=["No threat intel matches"], details={}
            )

        matches = []
        for q in queries:
            results = await find_many("threat_intel", q, limit=5)
            matches.extend(results)

        if not matches:
            return EngineScoreResponse(
                score=0.0, confidence=0.5,
                signals=["No threat intel matches"], details={}
            )

        risk_mapping = {"critical": 0.9, "high": 0.7, "medium": 0.4, "low": 0.2}
        highest_score = 0.0
        signals = []

        for match in matches:
            risk_level = match.get("risk_level", "low").lower()
            risk_score = risk_mapping.get(risk_level, 0.2)
            highest_score = max(highest_score, risk_score)

            mtype = match.get("type", "")
            signal_map = {
                "ip": "IP on watchlist",
                "device": "Device blacklisted",
                "merchant": "Merchant flagged",
                "account": "Account on watchlist"
            }
            sig = signal_map.get(mtype, f"{mtype} flagged")
            if sig not in signals:
                signals.append(sig)

        return EngineScoreResponse(
            score=highest_score, confidence=0.9, signals=signals,
            details={"match_count": len(matches)}
        )

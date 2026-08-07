import logging
from app.models.schemas import EngineScoreResponse
from app.database import find_many

logger = logging.getLogger(__name__)


class DeviceEngine:
    """Engine to assess device risk based on flags and history."""

    async def score(self, device_data, user_id: str) -> EngineScoreResponse:
        """Score the device based on vpn, tor, emulator, rooted flags and user history."""
        if device_data is None or device_data == {}:
            return EngineScoreResponse(
                score=0.2, confidence=0.5,
                signals=["Unknown device"],
                details={}
            )

        # Handle both dict and object
        if isinstance(device_data, dict):
            vpn = device_data.get("vpn_flag", False)
            tor = device_data.get("tor_flag", False)
            emulator = device_data.get("emulator_flag", False)
            rooted = device_data.get("rooted_flag", False)
            device_id = device_data.get("device_id", "")
        else:
            vpn = device_data.vpn_flag
            tor = device_data.tor_flag
            emulator = device_data.emulator_flag
            rooted = device_data.rooted_flag
            device_id = device_data.device_id

        score = 0.0
        signals = []

        if vpn:
            score += 0.2
            signals.append("VPN detected")
        if tor:
            score += 0.35
            signals.append("TOR network")
        if emulator:
            score += 0.3
            signals.append("Emulator detected")
        if rooted:
            score += 0.15
            signals.append("Rooted device")

        # Check if device is new for this user
        historical = await find_many("sessions", {"user_id": user_id}, limit=20)
        known_ids = {s.get("device_id") for s in historical if s.get("device_id")}

        if device_id and device_id not in known_ids and known_ids:
            score += 0.2
            signals.append("New device for user")
        elif known_ids:
            signals.append("Known device")

        score = min(score, 1.0)

        return EngineScoreResponse(
            score=score, confidence=0.9, signals=signals if signals else ["Clean device"],
            details={"flags": {"vpn": vpn, "tor": tor, "emulator": emulator, "rooted": rooted}}
        )

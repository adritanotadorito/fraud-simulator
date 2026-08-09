import math
import logging
from datetime import datetime, timezone
from app.models.schemas import EngineScoreResponse
from app.database import find_many
from app.config import get_settings

logger = logging.getLogger(__name__)

HIGH_RISK_REGIONS = ["NG", "RU", "CN", "KP", "IR", "VN"]


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great circle distance in km between two points."""
    R = 6371.0
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class GeolocationEngine:
    """Engine to assess geolocation anomalies including impossible travel."""

    async def score(self, geo_data, user_id: str, timestamp=None) -> EngineScoreResponse:
        """Score geolocation risk."""
        if geo_data is None or geo_data == {}:
            return EngineScoreResponse(
                score=0.0, confidence=0.3,
                signals=["No geo data"], details={}
            )

        # Handle dict or object
        if isinstance(geo_data, dict):
            country = geo_data.get("country", "")
            city = geo_data.get("city", "")
            lat = geo_data.get("latitude", 0)
            lon = geo_data.get("longitude", 0)
        else:
            country = geo_data.country
            city = geo_data.city
            lat = geo_data.latitude
            lon = geo_data.longitude

        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        elif isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                timestamp = datetime.now(timezone.utc)

        score = 0.0
        signals = []

        # High-risk region check
        if country in HIGH_RISK_REGIONS:
            score += 0.25
            signals.append("High-risk region")

        # Fetch recent transactions for this user
        historical = await find_many(
            "transactions", {"user_id": user_id}, limit=5,
            sort=[("timestamp", -1)]
        )

        recent_cities = {city} if city else set()

        for event in historical:
            prev_geo = event.get("geo", {})
            if not prev_geo:
                continue

            prev_city = prev_geo.get("city", "")
            prev_country = prev_geo.get("country", "")
            prev_lat = prev_geo.get("latitude")
            prev_lon = prev_geo.get("longitude")

            if prev_city:
                recent_cities.add(prev_city)

            prev_time = event.get("timestamp")
            if isinstance(prev_time, str):
                try:
                    prev_time = datetime.fromisoformat(prev_time.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    continue

            if prev_time and prev_lat is not None and prev_lon is not None and lat and lon:
                time_diff_hours = abs((timestamp - prev_time).total_seconds()) / 3600.0
                if time_diff_hours > 0:
                    distance = haversine(lat, lon, prev_lat, prev_lon)
                    velocity = distance / time_diff_hours
                    if velocity > 1000:
                        score += 0.4
                        signals.append("Impossible travel detected")

                if prev_country and prev_country != country:
                    score += 0.2
                    signals.append("Country changed")

                break  # Only check against the most recent event

        if len(recent_cities) > 3:
            score += 0.15
            signals.append("Rapid location changes")

        if not signals:
            signals.append("Consistent location")

        score = min(score, 1.0)

        return EngineScoreResponse(
            score=score, confidence=0.8, signals=signals,
            details={"cities_in_window": len(recent_cities), "country": country}
        )

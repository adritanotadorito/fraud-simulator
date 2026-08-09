import logging
import random
import uuid
from typing import List
from datetime import datetime, timezone

from app.models.schemas import (
    AttackRequest, AttackResponse, MemoryResponse, Transaction,
    FraudEvent, Session, GeoInfo, BiometricsData, Device
)
from app.database import find_many, find_one, insert_one, update_one, count_documents
from app.ws.manager import broadcast

logger = logging.getLogger(__name__)

PERSONA_REGISTRY = {
    "account_takeover": {
        "description": "Attempt to log into existing accounts using stolen credentials from a new device and foreign location.",
        "preferred_signals": ["new_device", "geo_change", "credential_reuse"],
        "difficulty": 0.7
    },
    "credential_stuffing": {
        "description": "Automated rapid login attempts using known breached credentials across multiple accounts.",
        "preferred_signals": ["rapid_login", "known_breach_creds", "multiple_accounts"],
        "difficulty": 0.5
    },
    "card_testing": {
        "description": "Testing stolen credit cards with many small rapid transactions at different merchants.",
        "preferred_signals": ["small_amounts", "rapid_transactions", "multiple_merchants"],
        "difficulty": 0.4
    },
    "device_spoofing": {
        "description": "Masking true device identity using emulators and VPNs to appear as a legitimate user.",
        "preferred_signals": ["emulator", "vpn", "fingerprint_mismatch"],
        "difficulty": 0.6
    },
    "money_mule": {
        "description": "Moving illicit funds through newly created or compromised accounts via rapid transfers.",
        "preferred_signals": ["new_account", "rapid_transfers", "multiple_recipients"],
        "difficulty": 0.8
    },
    "social_engineering": {
        "description": "Coercing a legitimate user to make a transfer under false pretenses using their own trusted device.",
        "preferred_signals": ["unusual_amount", "trusted_device", "normal_geo"],
        "difficulty": 0.9
    },
    "low_and_slow": {
        "description": "Gradual small fraud attempts over time designed to fly under detection thresholds.",
        "preferred_signals": ["small_amounts", "gradual_increase", "consistent_device"],
        "difficulty": 0.85
    }
}

CITIES = [
    {"city": "New York", "country": "US", "lat": 40.7128, "lon": -74.0060},
    {"city": "Los Angeles", "country": "US", "lat": 34.0522, "lon": -118.2437},
    {"city": "London", "country": "GB", "lat": 51.5074, "lon": -0.1278},
    {"city": "Lagos", "country": "NG", "lat": 6.5244, "lon": 3.3792},
    {"city": "Moscow", "country": "RU", "lat": 55.7558, "lon": 37.6173},
    {"city": "Tokyo", "country": "JP", "lat": 35.6762, "lon": 139.6503},
    {"city": "Mumbai", "country": "IN", "lat": 19.0760, "lon": 72.8777},
    {"city": "Sao Paulo", "country": "BR", "lat": -23.5505, "lon": -46.6333},
    {"city": "Beijing", "country": "CN", "lat": 39.9042, "lon": 116.4074},
    {"city": "Dubai", "country": "AE", "lat": 25.2048, "lon": 55.2708},
]


class FraudGPTOrchestrator:
    """Red Team AI — generates adversarial fraud attacks."""

    def __init__(self, llm_client):
        self.llm = llm_client

    async def get_memory(self) -> MemoryResponse:
        """Retrieve FraudGPT's learned strategy weights from past attack outcomes."""
        events = await find_many("fraud_events", {}, limit=1000, sort=[("created_at", -1)])

        persona_stats = {p: {"allowed": 0, "blocked": 0, "flagged": 0} for p in PERSONA_REGISTRY}
        for event in events:
            p = event.get("persona")
            if p in persona_stats:
                outcome = event.get("outcome", "pending").lower()
                if outcome in persona_stats[p]:
                    persona_stats[p][outcome] += 1

        persona_weights = {}
        for p, stats in persona_stats.items():
            total = stats["allowed"] + stats["blocked"] + stats["flagged"]
            base = PERSONA_REGISTRY[p]["difficulty"]
            if total > 0:
                success_rate = stats["allowed"] / total
                weight = base + (success_rate * 0.5)
            else:
                weight = base
            persona_weights[p] = round(weight, 3)

        total_events = len(events)
        overall_success = 0.0
        if total_events > 0:
            total_allowed = sum(s["allowed"] for s in persona_stats.values())
            overall_success = round(total_allowed / total_events, 3)

        strategy_history = [
            {"persona": e.get("persona"), "strategy": e.get("strategy"),
             "outcome": e.get("outcome"), "round": e.get("round")}
            for e in events[:5]
        ]

        return MemoryResponse(
            total_rounds=total_events,
            persona_weights=persona_weights,
            strategy_history=strategy_history,
            success_rate=overall_success
        )

    async def select_persona(self) -> str:
        """Select next attack persona using multi-armed bandit weighting."""
        memory = await self.get_memory()
        if memory.total_rounds == 0:
            return random.choice(list(PERSONA_REGISTRY.keys())[:4])
        weights = memory.persona_weights
        personas = list(weights.keys())
        probs = [weights[p] for p in personas]
        return random.choices(personas, weights=probs, k=1)[0]

    async def launch_attack(self, request: AttackRequest) -> AttackResponse:
        """Launch a fraud attack round."""
        persona = request.persona if request.persona and request.persona in PERSONA_REGISTRY else await self.select_persona()
        memory = await self.get_memory()
        round_num = request.round_number if request.round_number else memory.total_rounds + 1

        system_prompt = "You are FraudGPT, a red-team AI testing fraud detection systems. Return ONLY valid JSON."
        user_prompt = (
            f"Persona: {persona}\nConfig: {PERSONA_REGISTRY[persona]}\n"
            f"Past rounds: {memory.total_rounds}, Success rate: {memory.success_rate}\n"
            f"Recent history: {memory.strategy_history}\n\n"
            f"Generate attack parameters as JSON with fields: target_user_id (string), "
            f"amount (float), merchant_type (string), device_config (object with vpn/tor/emulator booleans), "
            f"geo (object with country/city), strategy_detail (string describing the attack approach)"
        )

        attack_params = await self.llm.generate(system_prompt, user_prompt)
        transactions = await self._generate_attack_transactions(persona, attack_params, round_num)
        txn_ids = [t.txn_id for t in transactions]

        event = FraudEvent(
            event_id=str(uuid.uuid4()),
            persona=persona,
            strategy=attack_params.get("strategy_detail", f"{persona} attack round {round_num}"),
            round=round_num,
            outcome="pending",
            attack_params=attack_params,
            txn_ids=txn_ids
        )
        await insert_one("fraud_events", event.model_dump())

        response = AttackResponse(
            event_id=event.event_id,
            persona=persona,
            strategy=event.strategy,
            round=round_num,
            transactions_generated=txn_ids,
            attack_params=attack_params
        )
        await broadcast({"type": "attack", "data": response.model_dump()})
        return response

    async def update_memory(self, event_id: str, outcome: str):
        """Update a fraud event's outcome after ShieldGPT's decision."""
        await update_one("fraud_events", {"event_id": event_id}, {"$set": {"outcome": outcome}})

    async def _generate_attack_transactions(
        self, persona: str, attack_params: dict, round_num: int
    ) -> List[Transaction]:
        """Generate fraudulent transactions based on persona and attack parameters."""
        # Pick target user from DB or fallback
        users = await find_many("users", {}, limit=20)
        if users:
            target_user = random.choice(users)
            target_user_id = target_user.get("user_id", str(uuid.uuid4()))
            accounts = await find_many("accounts", {"user_id": target_user_id}, limit=3)
            account_id = accounts[0].get("account_id") if accounts else str(uuid.uuid4())
        else:
            target_user_id = attack_params.get("target_user_id", f"usr_{uuid.uuid4().hex[:8]}")
            account_id = f"acc_{uuid.uuid4().hex[:8]}"

        # Geo — pick city based on persona
        device_config = attack_params.get("device_config", {})
        geo_params = attack_params.get("geo", {})
        city_data = random.choice(CITIES)
        if persona in ["account_takeover", "credential_stuffing"]:
            foreign = [c for c in CITIES if c["country"] not in ["US", "GB"]]
            city_data = random.choice(foreign) if foreign else city_data

        geo = GeoInfo(
            ip=f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
            country=geo_params.get("country", city_data["country"]),
            city=geo_params.get("city", city_data["city"]),
            latitude=city_data["lat"],
            longitude=city_data["lon"]
        )

        # Device
        device = Device(
            device_id=str(uuid.uuid4()),
            fingerprint=uuid.uuid4().hex[:16],
            os=random.choice(["Windows 11", "Android 14", "iOS 17", "macOS 14"]),
            browser=random.choice(["Chrome 120", "Firefox 121", "Safari 17"]),
            vpn_flag=device_config.get("vpn", persona in ["device_spoofing", "credential_stuffing"]),
            emulator_flag=device_config.get("emulator", persona == "device_spoofing"),
            tor_flag=device_config.get("tor", False),
            rooted_flag=False
        )
        await insert_one("devices", device.model_dump())

        # Session with biometrics
        bio = BiometricsData(
            typing_speed=random.uniform(20, 120),
            typing_rhythm_variance=(
                random.uniform(0.3, 0.9) if persona not in ["social_engineering", "low_and_slow"]
                else random.uniform(0.0, 0.2)
            ),
            mouse_speed=random.uniform(100, 800),
            mouse_pattern_deviation=(
                random.uniform(0.3, 0.8) if persona not in ["social_engineering", "low_and_slow"]
                else random.uniform(0.0, 0.15)
            ),
            session_duration=random.uniform(30, 600),
            session_duration_anomaly=(
                random.uniform(0.5, 3.0) if persona == "card_testing"
                else random.uniform(-0.5, 0.5)
            )
        )
        session = Session(
            session_id=str(uuid.uuid4()),
            user_id=target_user_id,
            device_id=device.device_id,
            biometrics=bio,
            geo=geo
        )
        await insert_one("sessions", session.model_dump())

        # Transaction count per persona
        num_txns = {
            "card_testing": random.randint(5, 10),
            "account_takeover": random.randint(1, 2),
            "credential_stuffing": random.randint(3, 6),
            "money_mule": random.randint(2, 4),
            "low_and_slow": 1,
            "social_engineering": 1,
            "device_spoofing": random.randint(1, 3)
        }.get(persona, 1)

        transactions = []
        for _ in range(num_txns):
            amount = {
                "card_testing": round(random.uniform(0.50, 4.99), 2),
                "account_takeover": round(random.uniform(500, 15000), 2),
                "money_mule": round(random.uniform(1000, 50000), 2),
                "low_and_slow": round(random.uniform(10, 200), 2),
                "social_engineering": round(random.uniform(2000, 25000), 2),
            }.get(persona, round(attack_params.get("amount", random.uniform(50, 5000)), 2))

            txn = Transaction(
                txn_id=str(uuid.uuid4()),
                account_id=account_id,
                user_id=target_user_id,
                amount=amount,
                merchant_id=f"mer_{uuid.uuid4().hex[:8]}",
                merchant_name=attack_params.get("merchant_type", "Online Store"),
                device_id=device.device_id,
                session_id=session.session_id,
                geo=geo,
                type="transfer" if persona == "money_mule" else "purchase",
                is_fraud=True
            )
            await insert_one("transactions", txn.model_dump())
            transactions.append(txn)
            await broadcast({"type": "transaction", "data": txn.model_dump(mode="json")})

        return transactions

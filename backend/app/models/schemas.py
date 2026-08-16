from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import uuid4
from pydantic import BaseModel, Field

# Embedded models
class UserProfile(BaseModel):
    name: str
    email: str
    phone: str
    address: str

class GeoInfo(BaseModel):
    ip: str
    country: str
    city: str
    latitude: float
    longitude: float

class BiometricsData(BaseModel):
    typing_speed: float  # keys per minute
    typing_rhythm_variance: float  # 0-1 deviation from baseline
    mouse_speed: float  # pixels per second
    mouse_pattern_deviation: float  # 0-1 deviation from baseline
    session_duration: float  # seconds
    session_duration_anomaly: float  # z-score from user's typical

# Collection models
class User(BaseModel):
    user_id: str = Field(default_factory=lambda: str(uuid4()))
    profile: UserProfile
    risk_tier: str = Field(default="low", pattern="^(low|medium|high)$")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Account(BaseModel):
    account_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    balance: float = Field(ge=0)
    status: str = Field(default="active", pattern="^(active|frozen|closed)$")
    account_type: str = Field(default="checking")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Device(BaseModel):
    device_id: str = Field(default_factory=lambda: str(uuid4()))
    fingerprint: str
    os: str
    browser: str = ""
    vpn_flag: bool = False
    emulator_flag: bool = False
    tor_flag: bool = False
    rooted_flag: bool = False
    user_agent: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Session(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    device_id: str
    biometrics: BiometricsData
    geo: GeoInfo
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None

class Transaction(BaseModel):
    txn_id: str = Field(default_factory=lambda: str(uuid4()))
    account_id: str
    user_id: str = ""
    amount: float
    currency: str = "USD"
    merchant_id: str
    merchant_name: str = ""
    device_id: str
    session_id: str = ""
    geo: GeoInfo
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    type: str = Field(default="purchase", pattern="^(purchase|transfer|withdrawal)$")
    is_fraud: Optional[bool] = None  # ground truth label if available
    is_real: bool = True
    source: str = "real_api"


class FraudEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    persona: str  # e.g., account_takeover, card_testing
    strategy: str  # specific strategy description
    round: int
    outcome: str = Field(default="pending", pattern="^(blocked|flagged|allowed|pending)$")
    attack_params: dict = Field(default_factory=dict)
    txn_ids: List[str] = Field(default_factory=list)  # transactions generated
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Decision(BaseModel):
    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    txn_id: str
    event_id: str = ""  # link to fraud event if applicable
    risk_score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    decision: str = Field(pattern="^(ALLOW|FLAG|BLOCK)$")
    reasons: List[str] = Field(default_factory=list)
    explanation: str = ""
    engine_scores: dict = Field(default_factory=dict)  # individual engine scores
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ThreatIntelEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: str(uuid4()))
    type: str  # ip, device, merchant, account
    value: str
    risk_level: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    source: str = "internal"
    added_at: datetime = Field(default_factory=datetime.utcnow)

class GraphEdge(BaseModel):
    edge_id: str = Field(default_factory=lambda: str(uuid4()))
    from_node: str
    to_node: str
    from_type: str = ""  # user, device, ip, account, merchant
    to_type: str = ""
    edge_type: str  # user-device, user-account, device-ip, etc.
    weight: float = 1.0
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ModelMetrics(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    round_number: int = 0
    accuracy: float = Field(ge=0, le=1)
    precision: float = Field(ge=0, le=1)
    recall: float = Field(ge=0, le=1)
    f1: float = Field(ge=0, le=1)
    roc_auc: float = Field(ge=0, le=1)
    latency_ms: float = Field(ge=0)
    total_transactions: int = 0
    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# API Request/Response models
class AttackRequest(BaseModel):
    persona: Optional[str] = None  # if None, FraudGPT picks
    round_number: Optional[int] = None

class AttackResponse(BaseModel):
    event_id: str
    persona: str
    strategy: str
    round: int
    transactions_generated: List[str]
    attack_params: dict

class ScoreRequest(BaseModel):
    txn_id: str
    include_explanation: bool = True

class ScoreResponse(BaseModel):
    decision_id: str
    txn_id: str
    risk_score: float
    confidence: float
    decision: str
    reasons: List[str]
    explanation: str
    engine_scores: dict

class EngineScoreResponse(BaseModel):
    score: float
    confidence: float
    signals: List[str]
    details: dict = Field(default_factory=dict)

class MemoryResponse(BaseModel):
    total_rounds: int
    persona_weights: dict
    strategy_history: List[dict]
    success_rate: float

class MetricsResponse(BaseModel):
    latest: Optional[ModelMetrics]
    history: List[ModelMetrics]

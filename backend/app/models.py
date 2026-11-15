from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


ChannelType = Literal["voice_call", "twilio_voice", "web_mic", "photon_sms", "photon_imessage", "web_text"]
CaseStatus = Literal["open", "reviewing", "actioned", "closed"]
HarmCategory = Literal[
    "physical_abuse",
    "sexual_abuse",
    "emotional_abuse",
    "neglect",
    "self_harm",
    "immediate_danger",
    "other_concern",
    "non_crisis",
]


class AgentTraceStep(BaseModel):
    node: str
    status: Literal["ok", "flagged", "alert_sent"] = "ok"
    latency_ms: float
    detail: str


class IntakeRequest(BaseModel):
    case_id: Optional[str] = None
    message: str = Field(..., min_length=1, max_length=4000)
    channel: ChannelType = "web_text"
    region: Literal["NG", "US"] = "NG"
    language_hint: Optional[str] = None


class ExtractedFields(BaseModel):
    who_at_risk: Optional[str] = None
    harm_category: HarmCategory = "other_concern"
    general_location: Optional[str] = None
    immediate_danger: bool = False
    relationship_to_abuser: Optional[str] = None
    entities: list[str] = Field(default_factory=list)


class TurnRecord(BaseModel):
    role: Literal["reporter", "safeline"]
    text_redacted: str
    timestamp: str


class GpsFix(BaseModel):
    latitude: float
    longitude: float
    accuracy_m: Optional[float] = None
    captured_at: str


class DeviceServiceFix(BaseModel):
    """A fix from a device-location service. Today this is seeded demo data, never a live feed, and
    `simulated` stays True in the data even though the dashboard does not badge it."""

    latitude: float
    longitude: float
    accuracy_m: Optional[float] = None
    captured_at: str
    profile_id: Optional[str] = None
    area_label: Optional[str] = None
    provider: str = "Device location service"
    simulated: bool = True


class SpokenPoint(BaseModel):
    """Where the caller's own words resolve to on our (approximate) gazetteer."""

    name: str
    latitude: float
    longitude: float
    radius_m: float


class CrossCheckPair(BaseModel):
    a: str
    b: str
    distance_km: float
    agree: bool


class CrossCheck(BaseModel):
    status: Literal["agree", "disagree", "insufficient"]
    pairs: list[CrossCheckPair] = Field(default_factory=list)
    sources_used: list[str] = Field(default_factory=list)
    summary: str


class HelpCentreRef(BaseModel):
    name: str
    kind: str
    phone: Optional[str] = None
    area: Optional[str] = None
    distance_km: Optional[float] = None


class LocationEvidence(BaseModel):
    """Every location signal for a case, kept separate so a caseworker can see
    where each one came from and how much to trust it."""

    # Twilio FromCity/FromState (or number prefix). For mobiles this is where the
    # number is registered, not where the caller is.
    network: Optional[str] = None
    network_source: Optional[str] = None
    country: Optional[str] = None
    # What the caller said when the agent asked where they are.
    spoken_address: Optional[str] = None
    spoken_at: Optional[str] = None
    # Browser GPS from the one-tap link, the only precise signal.
    gps: Optional[GpsFix] = None
    link_sent_via: list[str] = Field(default_factory=list)
    link_sent_at: Optional[str] = None
    # Device-location service (seeded for the demo), the caller's words as a map point, and what they mean together.
    device_service: Optional[DeviceServiceFix] = None
    spoken_point: Optional[SpokenPoint] = None
    cross_check: Optional[CrossCheck] = None
    nearest_help: list[HelpCentreRef] = Field(default_factory=list)
    best: Literal["gps", "device_service", "spoken", "network", "none"] = "none"


class CaseRecord(BaseModel):
    id: str
    created_at: str
    updated_at: str
    channel: ChannelType
    region: Literal["NG", "US"]
    status: CaseStatus = "open"
    risk_level: int = Field(ge=0, le=3)
    harm_category: HarmCategory
    general_location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    who_at_risk: Optional[str] = None
    immediate_danger: bool = False
    redacted_summary: str
    entities: list[str] = Field(default_factory=list)
    linked_case_ids: list[str] = Field(default_factory=list)
    alert_dispatched: bool = False
    alert_channels: list[str] = Field(default_factory=list)
    turns: list[TurnRecord] = Field(default_factory=list)
    trace: list[AgentTraceStep] = Field(default_factory=list)
    location: Optional[LocationEvidence] = None
    live_call: bool = False


class IntakeResponse(BaseModel):
    case: CaseRecord
    assistant_reply: str
    helpline_resources: list[str]
    missing_fields: list[str]
    pii_redacted_count: int
    total_latency_ms: float


class ForensicQueryRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=500)


class CitationSpan(BaseModel):
    case_id: str
    location: Optional[str]
    risk_level: int
    excerpt: str


class ForensicQueryResponse(BaseModel):
    answer: str
    citations: list[CitationSpan]
    matched_entities: list[str]


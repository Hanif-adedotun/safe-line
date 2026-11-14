from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


ChannelType = Literal["voice_call", "web_mic", "photon_sms", "web_text"]
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
    who_at_risk: Optional[str] = None
    immediate_danger: bool = False
    redacted_summary: str
    entities: list[str] = Field(default_factory=list)
    linked_case_ids: list[str] = Field(default_factory=list)
    alert_dispatched: bool = False
    alert_channels: list[str] = Field(default_factory=list)
    turns: list[TurnRecord] = Field(default_factory=list)
    trace: list[AgentTraceStep] = Field(default_factory=list)


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


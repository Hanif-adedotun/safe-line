"""The data contract between System 1 (understanding) and System 2 (deciding).

System 1 (assess.py) must emit a SafeguardingAssessment. System 2 (policy.py)
only ever reads this structure, never the raw conversation.

DEMO ONLY: the taxonomy and urgency labels are design aids from the product
brief, not clinical or legal definitions. They need review by child-protection
professionals before any real use.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

ASSESSMENT_VERSION = "1.0"


class ConcernCategory(str, Enum):
    physical_abuse = "physical_abuse"
    emotional_abuse = "emotional_abuse"
    sexual_abuse_or_exploitation = "sexual_abuse_or_exploitation"
    neglect = "neglect"
    domestic_violence_exposure = "domestic_violence_exposure"
    bullying = "bullying"
    threats_intimidation = "threats_intimidation"
    coercion_control = "coercion_control"
    unsafe_living_environment = "unsafe_living_environment"
    online_exploitation = "online_exploitation"
    fear_unclear_cause = "fear_unclear_cause"
    self_harm_or_suicide = "self_harm_or_suicide"
    other_or_unknown = "other_or_unknown"


CATEGORY_LABELS: dict[ConcernCategory, str] = {
    ConcernCategory.physical_abuse: "Physical abuse",
    ConcernCategory.emotional_abuse: "Emotional or psychological abuse",
    ConcernCategory.sexual_abuse_or_exploitation: "Sexual abuse or exploitation",
    ConcernCategory.neglect: "Neglect / unmet basic needs",
    ConcernCategory.domestic_violence_exposure: "Exposure to domestic violence",
    ConcernCategory.bullying: "Bullying",
    ConcernCategory.threats_intimidation: "Threats and intimidation",
    ConcernCategory.coercion_control: "Coercion or controlling behaviour",
    ConcernCategory.unsafe_living_environment: "Unsafe living environment",
    ConcernCategory.online_exploitation: "Online exploitation or unsafe contact",
    ConcernCategory.fear_unclear_cause: "Fear / feeling unsafe, cause unclear",
    ConcernCategory.self_harm_or_suicide: "Self-harm or suicidal thoughts",
    ConcernCategory.other_or_unknown: "Other or unknown safeguarding concern",
}


class Urgency(str, Enum):
    critical = "critical"
    high = "high"
    moderate = "moderate"
    low = "low"
    unknown = "unknown"


class Concern(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: ConcernCategory
    status: Literal["potential", "stated", "unclear"]
    # Verbatim words the CHILD said. Checked against the transcript in assess.py.
    evidence_quotes: list[str] = Field(min_length=1, max_length=5)
    interpretation: str = Field(min_length=1, max_length=400)
    # Set by assess.py after checking the quotes, never by the model.
    evidence_verified: bool = False


class SafeguardingAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    assessment_version: str = ASSESSMENT_VERSION
    concerns: list[Concern] = Field(default_factory=list)
    urgency: Urgency
    immediate_danger: Literal["yes", "no", "unknown"]
    model_uncertainty: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    human_review_recommended: bool
    follow_up_appropriate: bool
    suggested_follow_up: Optional[str] = None
    limitations: list[str] = Field(
        default_factory=lambda: ["Automated preliminary assessment, not a verified finding."]
    )
    # Provenance, filled by assess.py
    engine: str = "unknown"
    fallback: bool = False
    fallback_reason: Optional[str] = None
    assessed_at: Optional[str] = None
    turns_assessed: int = 0

    @property
    def has_concern(self) -> bool:
        return len(self.concerns) > 0


# JSON schema handed to Gemini's structured-output mode (subset of OpenAPI 3).
# Provenance fields are deliberately absent: the model cannot set them.
GEMINI_RESPONSE_SCHEMA: dict = {
    "type": "OBJECT",
    "properties": {
        "concerns": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "category": {"type": "STRING", "enum": [c.value for c in ConcernCategory]},
                    "status": {"type": "STRING", "enum": ["potential", "stated", "unclear"]},
                    "evidence_quotes": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "interpretation": {"type": "STRING"},
                },
                "required": ["category", "status", "evidence_quotes", "interpretation"],
            },
        },
        "urgency": {"type": "STRING", "enum": [u.value for u in Urgency]},
        "immediate_danger": {"type": "STRING", "enum": ["yes", "no", "unknown"]},
        "model_uncertainty": {"type": "ARRAY", "items": {"type": "STRING"}},
        "missing_information": {"type": "ARRAY", "items": {"type": "STRING"}},
        "human_review_recommended": {"type": "BOOLEAN"},
        "follow_up_appropriate": {"type": "BOOLEAN"},
        "suggested_follow_up": {"type": "STRING", "nullable": True},
    },
    "required": [
        "concerns",
        "urgency",
        "immediate_danger",
        "model_uncertainty",
        "missing_information",
        "human_review_recommended",
        "follow_up_appropriate",
    ],
}

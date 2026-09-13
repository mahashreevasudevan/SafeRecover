from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class FailureEventIn(BaseModel):
    workflow_name: str = Field(min_length=1, max_length=120)
    execution_id: str = Field(min_length=1, max_length=120)
    node_name: str = Field(min_length=1, max_length=120)
    error_type: Literal[
        "API_TIMEOUT", "RATE_LIMIT", "MALFORMED_JSON", "MISSING_OPTIONAL_FIELD",
        "MISSING_CRITICAL_FIELD", "AUTH_FAILURE", "DUPLICATE_EVENT", "DATABASE_UNAVAILABLE",
        "AMBIGUOUS_MATCH", "DATA_CONFLICT", "INVALID_TOOL_ARGUMENTS", "UNKNOWN"
    ]
    error_message: str
    payload: dict[str, Any] = Field(default_factory=dict)
    attempt: int = Field(default=1, ge=1, le=20)
    financial_impact: float = Field(default=0.0, ge=0.0, le=1.0)
    reversible: bool = True
    evidence_agreement: float = Field(default=1.0, ge=0.0, le=1.0)
    ambiguity: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    failure_history: int = Field(default=0, ge=0, le=50)


class RecoveryEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    workflow_name: str
    execution_id: str
    node_name: str
    error_type: str
    error_message: str
    payload: dict[str, Any]
    attempt: int
    diagnosis: str
    diagnosis_source: str
    proposed_action: str
    risk_score: float
    risk_band: str
    risk_reasons: list[str]
    status: str
    repair_patch: dict[str, Any] | None
    verification_passed: bool | None
    verification_detail: str | None
    created_at: datetime


class ApprovalIn(BaseModel):
    approved: bool
    reviewer: str = Field(min_length=1, max_length=80)


class VerificationIn(BaseModel):
    downstream_status: Literal["COMPLETED", "FAILED"]
    expected_state_reached: bool
    detail: str = ""


class MetricOut(BaseModel):
    total_events: int
    autonomous_events: int
    verified_recoveries: int
    escalated_events: int
    awaiting_approval: int
    unsafe_autonomous_rate: float
    verification_success_rate: float

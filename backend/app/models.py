from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Decision(str, Enum):
    RETRY = "RETRY"
    REPAIR_RETRY = "REPAIR_RETRY"
    SUPPRESS = "SUPPRESS"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    BLOCK_ESCALATE = "BLOCK_ESCALATE"


class RecoveryStatus(str, Enum):
    RECEIVED = "RECEIVED"
    AUTO_RECOVERED = "AUTO_RECOVERED"
    VERIFIED = "VERIFIED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    ESCALATED = "ESCALATED"
    SUPPRESSED = "SUPPRESSED"


class RecoveryEvent(Base):
    __tablename__ = "recovery_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    workflow_name: Mapped[str] = mapped_column(String(120), index=True)
    execution_id: Mapped[str] = mapped_column(String(120), index=True)
    node_name: Mapped[str] = mapped_column(String(120))
    error_type: Mapped[str] = mapped_column(String(80), index=True)
    error_message: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    financial_impact: Mapped[float] = mapped_column(Float, default=0.0)
    reversible: Mapped[bool] = mapped_column(Boolean, default=True)
    evidence_agreement: Mapped[float] = mapped_column(Float, default=1.0)
    ambiguity: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    failure_history: Mapped[int] = mapped_column(Integer, default=0)
    diagnosis: Mapped[str] = mapped_column(Text)
    diagnosis_source: Mapped[str] = mapped_column(String(40), default="rules")
    proposed_action: Mapped[str] = mapped_column(String(40))
    risk_score: Mapped[float] = mapped_column(Float)
    risk_band: Mapped[str] = mapped_column(String(20), index=True)
    risk_reasons: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(40), index=True)
    repair_patch: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    verification_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    verification_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

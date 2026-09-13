from dataclasses import dataclass

from .models import Decision
from .schemas import FailureEventIn


@dataclass(frozen=True)
class RiskAssessment:
    score: float
    band: str
    reasons: list[str]


RISK_WEIGHTS = {
    "financial_impact": 0.28,
    "irreversibility": 0.22,
    "ambiguity": 0.18,
    "evidence_disagreement": 0.14,
    "low_confidence": 0.10,
    "failure_history": 0.08,
}


def calculate_risk(event: FailureEventIn) -> RiskAssessment:
    history_signal = min(event.failure_history / 3.0, 1.0)
    signals = {
        "financial_impact": event.financial_impact,
        "irreversibility": 0.0 if event.reversible else 1.0,
        "ambiguity": event.ambiguity,
        "evidence_disagreement": 1.0 - event.evidence_agreement,
        "low_confidence": 1.0 - event.confidence,
        "failure_history": history_signal,
    }
    score = round(sum(signals[k] * RISK_WEIGHTS[k] for k in RISK_WEIGHTS), 3)
    reasons = [
        name.replace("_", " ")
        for name, value in sorted(signals.items(), key=lambda item: item[1], reverse=True)
        if value >= 0.45
    ][:3]
    if not reasons:
        reasons = ["low-impact reversible action"]
    band = "LOW" if score < 0.30 else "MEDIUM" if score < 0.60 else "HIGH"
    return RiskAssessment(score=score, band=band, reasons=reasons)


def apply_safety_boundaries(event: FailureEventIn, proposed: Decision, risk: RiskAssessment) -> Decision:
    if event.error_type in {"AUTH_FAILURE", "MISSING_CRITICAL_FIELD", "DATA_CONFLICT"}:
        return Decision.BLOCK_ESCALATE
    if event.failure_history >= 3 or event.attempt >= 4:
        return Decision.BLOCK_ESCALATE
    if risk.band == "HIGH":
        return Decision.BLOCK_ESCALATE
    if risk.band == "MEDIUM":
        return Decision.REQUIRE_APPROVAL
    return proposed


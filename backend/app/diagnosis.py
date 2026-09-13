from dataclasses import dataclass

from .models import Decision
from .schemas import FailureEventIn


@dataclass(frozen=True)
class Diagnosis:
    summary: str
    proposed_action: Decision
    repair_patch: dict | None = None


def diagnose(event: FailureEventIn) -> Diagnosis:
    rules = {
        "API_TIMEOUT": Diagnosis("Transient upstream timeout; a bounded retry is appropriate.", Decision.RETRY),
        "RATE_LIMIT": Diagnosis("Upstream rate limit; retry with exponential backoff.", Decision.RETRY),
        "DATABASE_UNAVAILABLE": Diagnosis("Database connection is temporarily unavailable.", Decision.RETRY),
        "DUPLICATE_EVENT": Diagnosis("Idempotency key indicates this event was already processed.", Decision.SUPPRESS),
        "AUTH_FAILURE": Diagnosis("Credentials are invalid or expired; automated mutation is blocked.", Decision.BLOCK_ESCALATE),
        "MISSING_CRITICAL_FIELD": Diagnosis("A required business identifier is missing.", Decision.BLOCK_ESCALATE),
        "DATA_CONFLICT": Diagnosis("Authoritative sources disagree on a material value.", Decision.BLOCK_ESCALATE),
        "AMBIGUOUS_MATCH": Diagnosis("Several candidate records match the supplied evidence.", Decision.REQUIRE_APPROVAL),
    }
    if event.error_type == "MALFORMED_JSON":
        return Diagnosis(
            "Payload is structurally invalid but repairable without changing business meaning.",
            Decision.REPAIR_RETRY,
            {"normalise_json": True},
        )
    if event.error_type == "INVALID_TOOL_ARGUMENTS":
        return Diagnosis(
            "Tool call contains invalid argument names or primitive types.",
            Decision.REPAIR_RETRY,
            {"coerce_schema": True},
        )
    if event.error_type == "MISSING_OPTIONAL_FIELD":
        return Diagnosis(
            "An optional field is absent and can be populated with a declared default.",
            Decision.REPAIR_RETRY,
            {"defaults": event.payload.get("allowed_defaults", {})},
        )
    return rules.get(event.error_type, Diagnosis("Failure class is unknown.", Decision.REQUIRE_APPROVAL))


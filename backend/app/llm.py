import logging
from typing import Literal

from google import genai
from pydantic import BaseModel, Field

from .config import get_settings
from .diagnosis import Diagnosis, diagnose
from .models import Decision
from .schemas import FailureEventIn

logger = logging.getLogger("saferecover.diagnosis")


class LLMDiagnosis(BaseModel):
    failure_class: Literal[
        "TRANSIENT", "RATE_LIMIT", "PAYLOAD_SCHEMA", "MISSING_DATA",
        "AUTHENTICATION", "DUPLICATE", "DATA_CONFLICT", "AMBIGUOUS", "UNKNOWN"
    ]
    summary: str = Field(description="One factual sentence grounded only in the event evidence.")
    proposed_action: Literal["RETRY", "REPAIR_RETRY", "SUPPRESS", "REQUIRE_APPROVAL", "BLOCK_ESCALATE"]
    repair_kind: Literal["NONE", "NORMALISE_JSON", "COERCE_SCHEMA", "APPLY_DECLARED_DEFAULTS"]


SYSTEM_INSTRUCTION = """You diagnose failed SME accounting and legal operations workflows.
Return only the requested structured result. Never invent missing evidence, credentials,
customer identifiers, financial amounts, or legal facts. Prefer human approval when evidence
is ambiguous. Never propose changing a financial amount, legal document content, bank detail,
or authoritative record. You propose; a separate deterministic policy decides whether execution
is permitted."""


def _repair_patch(kind: str, event: FailureEventIn) -> dict | None:
    if kind == "NORMALISE_JSON":
        return {"normalise_json": True}
    if kind == "COERCE_SCHEMA":
        return {"coerce_schema": True}
    if kind == "APPLY_DECLARED_DEFAULTS":
        return {"defaults": event.payload.get("allowed_defaults", {})}
    return None


async def diagnose_event(event: FailureEventIn) -> tuple[Diagnosis, str]:
    settings = get_settings()
    if not settings.gemini_api_key:
        return diagnose(event), "rules-fallback"
    prompt = (
        f"Workflow: {event.workflow_name}\nNode: {event.node_name}\n"
        f"Declared error type: {event.error_type}\nError: {event.error_message}\n"
        f"Attempt: {event.attempt}\nPayload keys: {sorted(event.payload.keys())}\n"
        f"Reversible: {event.reversible}\nFinancial impact: {event.financial_impact}\n"
        f"Evidence agreement: {event.evidence_agreement}\nAmbiguity: {event.ambiguity}\n"
        f"Prior failures: {event.failure_history}"
    )
    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config={
                "system_instruction": SYSTEM_INSTRUCTION,
                "response_mime_type": "application/json",
                "response_json_schema": LLMDiagnosis.model_json_schema(),
                "temperature": 0,
            },
        )
        parsed = LLMDiagnosis.model_validate_json(response.text)
        return Diagnosis(
            summary=parsed.summary,
            proposed_action=Decision(parsed.proposed_action),
            repair_patch=_repair_patch(parsed.repair_kind, event),
        ), f"gemini:{settings.gemini_model}"
    except Exception as exc:
        logger.warning("Gemini diagnosis failed; using deterministic fallback: %s", type(exc).__name__)
        return diagnose(event), "rules-fallback"

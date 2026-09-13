import logging

import httpx

from .config import get_settings
from .models import Decision, RecoveryEvent, RecoveryStatus

logger = logging.getLogger("saferecover.recovery")


def initial_status(decision: Decision) -> RecoveryStatus:
    return {
        Decision.BLOCK_ESCALATE: RecoveryStatus.ESCALATED,
        Decision.REQUIRE_APPROVAL: RecoveryStatus.AWAITING_APPROVAL,
        Decision.SUPPRESS: RecoveryStatus.SUPPRESSED,
        Decision.RETRY: RecoveryStatus.AUTO_RECOVERED,
        Decision.REPAIR_RETRY: RecoveryStatus.AUTO_RECOVERED,
    }[decision]


async def dispatch_recovery(record: RecoveryEvent) -> tuple[bool | None, str]:
    if record.proposed_action not in {Decision.RETRY.value, Decision.REPAIR_RETRY.value}:
        return None, "No autonomous action dispatched."
    settings = get_settings()
    if not settings.n8n_retry_webhook_url:
        return None, "Dry-run mode: recovery approved but no n8n retry webhook is configured."
    body = {
        "recovery_event_id": record.id,
        "execution_id": record.execution_id,
        "action": record.proposed_action,
        "repair_patch": record.repair_patch,
        "payload": record.payload,
    }
    try:
        async with httpx.AsyncClient(timeout=settings.n8n_timeout_seconds) as client:
            response = await client.post(settings.n8n_retry_webhook_url, json=body)
            response.raise_for_status()
        return True, "Recovery dispatched; awaiting downstream verification callback."
    except httpx.HTTPError as exc:
        logger.warning("Recovery dispatch failed for %s: %s", record.id, exc)
        return False, f"Recovery dispatch failed: {type(exc).__name__}"


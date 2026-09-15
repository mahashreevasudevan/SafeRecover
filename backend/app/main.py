import logging

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import get_settings
from .database import Base, engine, get_db
from .llm import diagnose_event
from .models import Decision, RecoveryEvent, RecoveryStatus
from .recovery import dispatch_recovery, initial_status
from .risk import apply_safety_boundaries, calculate_risk
from .schemas import ApprovalIn, FailureEventIn, MetricOut, RecoveryEventOut, VerificationIn

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
settings = get_settings()
app = FastAPI(title=settings.app_name, version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "saferecover"}


@app.post("/api/v1/failures", response_model=RecoveryEventOut, status_code=201)
async def ingest_failure(event: FailureEventIn, db: Session = Depends(get_db)):
    diagnosis, diagnosis_source = await diagnose_event(event)
    risk = calculate_risk(event)
    decision = apply_safety_boundaries(event, diagnosis.proposed_action, risk)
    record = RecoveryEvent(
        **event.model_dump(),
        diagnosis=diagnosis.summary,
        diagnosis_source=diagnosis_source,
        proposed_action=decision.value,
        risk_score=risk.score,
        risk_band=risk.band,
        risk_reasons=risk.reasons,
        repair_patch=diagnosis.repair_patch,
        status=initial_status(decision).value,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    dispatched, detail = await dispatch_recovery(record)
    db.refresh(record)

    if dispatched is False:
        record.status = RecoveryStatus.ESCALATED.value
    elif record.status not in {
        RecoveryStatus.VERIFIED.value,
        RecoveryStatus.VERIFICATION_FAILED.value,
    }:
        record.verification_detail = detail

    db.commit()
    db.refresh(record)
    return record


@app.get("/api/v1/events", response_model=list[RecoveryEventOut])
def list_events(limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db)):
    return db.scalars(select(RecoveryEvent).order_by(RecoveryEvent.created_at.desc()).limit(limit)).all()


@app.get("/api/v1/events/{event_id}", response_model=RecoveryEventOut)
def get_event(event_id: str, db: Session = Depends(get_db)):
    record = db.get(RecoveryEvent, event_id)
    if not record:
        raise HTTPException(status_code=404, detail="Recovery event not found")
    return record


@app.post("/api/v1/events/{event_id}/approval", response_model=RecoveryEventOut)
async def decide_approval(event_id: str, approval: ApprovalIn, db: Session = Depends(get_db)):
    record = db.get(RecoveryEvent, event_id)
    if not record:
        raise HTTPException(status_code=404, detail="Recovery event not found")
    if record.status != RecoveryStatus.AWAITING_APPROVAL.value:
        raise HTTPException(status_code=409, detail="Event is not awaiting approval")
    if not approval.approved:
        record.status = RecoveryStatus.ESCALATED.value
        record.verification_detail = f"Rejected by {approval.reviewer}; escalated."
    else:
        record.proposed_action = Decision.REPAIR_RETRY.value
        record.status = RecoveryStatus.AUTO_RECOVERED.value
        _, detail = await dispatch_recovery(record)
        record.verification_detail = f"Approved by {approval.reviewer}. {detail}"
    db.commit()
    db.refresh(record)
    return record


@app.post("/api/v1/events/{event_id}/verify", response_model=RecoveryEventOut)
def verify_event(event_id: str, verification: VerificationIn, db: Session = Depends(get_db)):
    record = db.get(RecoveryEvent, event_id)
    if not record:
        raise HTTPException(status_code=404, detail="Recovery event not found")
    passed = verification.downstream_status == "COMPLETED" and verification.expected_state_reached
    record.verification_passed = passed
    record.verification_detail = verification.detail or (
        "Expected downstream state confirmed." if passed else "Downstream state did not satisfy verification."
    )
    record.status = (RecoveryStatus.VERIFIED if passed else RecoveryStatus.VERIFICATION_FAILED).value
    db.commit()
    db.refresh(record)
    return record


@app.get("/api/v1/metrics", response_model=MetricOut)
def metrics(db: Session = Depends(get_db)):
    rows = db.scalars(select(RecoveryEvent)).all()
    total = len(rows)
    autonomous = [r for r in rows if r.proposed_action in {Decision.RETRY.value, Decision.REPAIR_RETRY.value}]
    unsafe = [r for r in autonomous if r.risk_band == "HIGH"]
    verified = [r for r in rows if r.status == RecoveryStatus.VERIFIED.value]
    verification_attempts = [r for r in rows if r.verification_passed is not None]
    return MetricOut(
        total_events=total,
        autonomous_events=len(autonomous),
        verified_recoveries=len(verified),
        escalated_events=sum(r.status == RecoveryStatus.ESCALATED.value for r in rows),
        awaiting_approval=sum(r.status == RecoveryStatus.AWAITING_APPROVAL.value for r in rows),
        unsafe_autonomous_rate=round(len(unsafe) / len(autonomous), 4) if autonomous else 0.0,
        verification_success_rate=round(len(verified) / len(verification_attempts), 4) if verification_attempts else 0.0,
    )

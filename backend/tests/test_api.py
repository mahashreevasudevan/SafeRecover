def failure(**overrides):
    data = {
        "workflow_name": "Invoice Intake",
        "execution_id": "exec-001",
        "node_name": "Parse invoice",
        "error_type": "API_TIMEOUT",
        "error_message": "upstream timeout",
        "payload": {},
        "attempt": 1,
        "financial_impact": 0,
        "reversible": True,
        "evidence_agreement": 1,
        "ambiguity": 0,
        "confidence": 1,
        "failure_history": 0,
    }
    data.update(overrides)
    return data


def test_low_risk_timeout_is_retried(client):
    response = client.post("/api/v1/failures", json=failure())
    assert response.status_code == 201
    result = response.json()
    assert result["proposed_action"] == "RETRY"
    assert result["risk_band"] == "LOW"
    assert result["status"] == "AUTO_RECOVERED"


def test_data_conflict_is_always_blocked(client):
    response = client.post("/api/v1/failures", json=failure(
        error_type="DATA_CONFLICT", financial_impact=.9,
        reversible=False, evidence_agreement=.1,
    ))
    result = response.json()
    assert result["proposed_action"] == "BLOCK_ESCALATE"
    assert result["status"] == "ESCALATED"


def test_repeated_failure_opens_circuit_breaker(client):
    response = client.post("/api/v1/failures", json=failure(failure_history=3, attempt=4))
    assert response.json()["proposed_action"] == "BLOCK_ESCALATE"


def test_medium_risk_requires_human_approval(client):
    response = client.post("/api/v1/failures", json=failure(
        error_type="AMBIGUOUS_MATCH", ambiguity=.8, confidence=.5,
        evidence_agreement=.3, financial_impact=.25,
    ))
    event = response.json()
    assert event["proposed_action"] == "REQUIRE_APPROVAL"
    approved = client.post(f"/api/v1/events/{event['id']}/approval", json={"approved": True, "reviewer": "qa"})
    assert approved.status_code == 200
    assert approved.json()["status"] == "AUTO_RECOVERED"


def test_closed_loop_verification(client):
    event = client.post("/api/v1/failures", json=failure()).json()
    response = client.post(f"/api/v1/events/{event['id']}/verify", json={
        "downstream_status": "COMPLETED", "expected_state_reached": True,
        "detail": "Order record exists once and has expected status.",
    })
    assert response.json()["status"] == "VERIFIED"
    assert response.json()["verification_passed"] is True


def test_metrics_report_zero_unsafe_autonomy(client):
    client.post("/api/v1/failures", json=failure())
    client.post("/api/v1/failures", json=failure(
        execution_id="exec-002", error_type="DATA_CONFLICT",
        financial_impact=1, reversible=False,
    ))
    metrics = client.get("/api/v1/metrics").json()
    assert metrics["total_events"] == 2
    assert metrics["unsafe_autonomous_rate"] == 0


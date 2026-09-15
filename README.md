# SafeRecover

**Risk-aware autonomous recovery for failed n8n workflows.**

SafeRecover is an AI-powered recovery control plane for business automation. It captures failed n8n executions, diagnoses the failure, evaluates operational risk, and decides whether the workflow can recover automatically or needs human intervention.

The system uses Gemini for structured failure diagnosis, but the model never gets direct authority to execute a recovery. Explicit safety rules and a deterministic risk score decide what can happen:

* **Low risk:** allowlisted repair or retry can run automatically
* **Medium risk:** human approval is required
* **High risk:** the action is blocked and escalated

Every attempted recovery is followed by downstream-state verification and stored as an auditable decision record.

![Python](https://img.shields.io/badge/Python-3.12-3776AB)
![FastAPI](https://img.shields.io/badge/FastAPI-0.116-009688)
![React](https://img.shields.io/badge/React-TypeScript-61DAFB)
![Tests](https://img.shields.io/badge/tests-pytest-0A9EDC)

---

## Key Objectives

SafeRecover was built around a simple question:

> **Can an AI system recover a failed business workflow without being trusted blindly?**

The project focuses on five objectives:

1. **Detect and classify workflow failures** from real execution errors.
2. **Use structured AI reasoning** to identify the failure type and suitable recovery action.
3. **Separate diagnosis from execution** so an LLM cannot directly modify business state.
4. **Make recovery decisions risk-aware** using explicit operational signals.
5. **Verify the downstream result** before considering a recovery successful.

The system simulates three SME workflows:

* Invoice processing
* Legal document intake
* Expense approval

---

## Methodology

SafeRecover treats recovery as a controlled decision pipeline rather than simply asking an LLM to "fix the error".

A failed workflow first enters the failure-capture workflow in n8n. SafeRecover normalises the failure into a structured event containing information such as the workflow, execution, node, error type, financial impact, reversibility, evidence agreement, ambiguity, confidence, and failure history.

Gemini then produces a structured diagnosis. The output is validated against the expected schema and mapped to an allowlisted recovery action.

The recovery decision is then evaluated independently of the model.

```text
n8n failure
    ↓
Failure capture
    ↓
Failure normalisation
    ↓
Structured diagnosis
    ↓
Risk assessment
    ↓
Safety policy
    ↓
┌──────────────┬──────────────────┬─────────────────┐
│ Low risk     │ Medium risk      │ High risk       │
│              │                  │                 │
│ Auto-recover │ Human approval   │ Block + escalate│
└──────────────┴──────────────────┴─────────────────┘
    ↓
Recovery execution
    ↓
Downstream verification
    ↓
Persisted decision record
    ↓
Operations dashboard
```

This separation is important. The LLM can help explain what happened, but it does not decide what the system is allowed to do on its own.

---

## Model Pipeline

The model pipeline combines **LLM-assisted diagnosis** with deterministic safety controls.

### 1. Failure capture

n8n sends failed executions to the SafeRecover API through an error workflow.

The event is normalised into a consistent structure containing:

* workflow and execution identifiers
* failed node
* failure type and message
* input payload
* retry attempt
* financial impact
* reversibility
* evidence agreement
* ambiguity
* model confidence
* failure history

### 2. Structured diagnosis

Gemini is used to classify the failure and produce a structured response containing:

* failure class
* diagnosis
* proposed recovery action
* repair information where applicable

If the Gemini API is unavailable, SafeRecover falls back to deterministic diagnosis rules so the recovery service remains usable.

### 3. Risk assessment

Risk is calculated from explicit operational signals rather than treating LLM confidence as the final safety decision.

```text
risk =
    0.28 financial impact
  + 0.22 irreversibility
  + 0.18 ambiguity
  + 0.14 evidence disagreement
  + 0.10 low confidence
  + 0.08 failure history
```

The resulting risk score is mapped to three decision bands:

| Risk        | Decision                   |
| ----------- | -------------------------- |
| `< 0.30`    | Automatic recovery allowed |
| `0.30–0.59` | Human approval required    |
| `>= 0.60`   | Block and escalate         |

Additional hard safety rules override the numerical score. Authentication failures, missing critical fields, material data conflicts, and repeated failures are blocked regardless of the calculated risk.

### 4. Recovery execution

Only predefined recovery actions can be dispatched.

For example, a malformed invoice payload may produce:

```json
{
  "action": "REPAIR_RETRY",
  "repair_patch": {
    "normalise_json": true
  }
}
```

The n8n recovery runner applies only the allowlisted repair and then triggers verification.

### 5. Verification

A successful HTTP response is not treated as proof of recovery.

SafeRecover waits for a downstream verification callback confirming that the expected business state was reached.

This means the system distinguishes:

```text
Recovery dispatched
        ≠
Recovery verified
```

That distinction is persisted in the recovery event and surfaced in the dashboard.

---

## Challenges Addressed

### Safe autonomous recovery

Automatically retrying every failure is unsafe. SafeRecover separates recoverable failures from cases where changing state could make the situation worse.

### LLM reliability

An LLM can produce a plausible but unsafe recommendation. SafeRecover therefore uses the model for diagnosis while keeping execution behind deterministic policy and allowlisted actions.

### Ambiguous business data

Some failures cannot be safely resolved automatically.

For example:

```text
Receipt amount: £1,250
Claim amount:   £12,500
```

A material conflict results in escalation rather than allowing the system to guess which value is correct.

### Human-in-the-loop decisions

Medium-risk failures are not silently executed. They are surfaced as approval decisions so an operator can review the evidence before recovery.

### Verification after recovery

A workflow returning HTTP 200 does not necessarily mean that the business operation succeeded. SafeRecover verifies the downstream state before marking an autonomous recovery as successful.

### Recovery state consistency

The backend also handles the race between recovery dispatch and verification callbacks. A verification callback can arrive before the original dispatch request finishes, so the persistence logic preserves the verified state instead of overwriting it with an intermediate status.

---

## Results

SafeRecover was tested end to end across failure scenarios including malformed payloads, API timeouts, ambiguous matches, and conflicting business data.

A complete autonomous recovery path was successfully demonstrated:

```text
MALFORMED_JSON
      ↓
REPAIR_RETRY
      ↓
Allowlisted JSON normalisation
      ↓
n8n recovery runner
      ↓
Downstream verification
      ↓
VERIFIED
```

The final end-to-end test produced:

```text
Failure:
Invoice extraction returned malformed JSON

Diagnosis:
Payload is structurally invalid but repairable without
changing business meaning.

Decision:
REPAIR_RETRY

Risk:
LOW

Repair:
normalise_json = true

Verification:
Invoice retry completed successfully and expected
downstream state was reached.

Final status:
VERIFIED
```

The repository also includes a labelled **60-case failure-injection benchmark** covering 12 failure archetypes.

The evaluation measures:

* recovery-action accuracy
* unsafe autonomous recovery rate
* recoverable-case automation rate
* decision distribution

Automated backend tests cover recovery policies, hard safety rules, approval paths, circuit breaking, downstream verification, and unsafe-autonomy measurement.

---

## Impact

The main outcome is a recovery architecture that closes the loop from **failure detection to verified business recovery**.

Instead of:

```text
Failure → Alert → Human investigation
```

SafeRecover enables:

```text
Failure
  ↓
Diagnosis
  ↓
Risk decision
  ↓
Safe recovery or human review
  ↓
Downstream verification
  ↓
Auditable outcome
```

This makes the system useful as an example of how **AI agents can operate inside explicit engineering constraints** rather than being given unrestricted authority over business workflows.


---

## Technology and Tools

### Backend

* Python 3.12
* FastAPI
* SQLAlchemy
* Pydantic
* Pytest
* REST APIs

### AI

* Gemini 2.5 Flash-Lite
* Structured LLM outputs
* Failure classification
* AI-assisted diagnosis
* Risk-aware recovery decisioning

### Automation

* n8n
* Webhooks
* Error workflows
* Recovery workflows
* HTTP integrations
* Allowlisted repair actions

### Frontend

* React
* TypeScript
* Vite
* Lucide React
* Operations dashboard

### Deployment and infrastructure

* Render
* Docker
* PostgreSQL
* Cloudflare Tunnel for local n8n connectivity

### Engineering

* Git and GitHub
* Automated testing
* Failure-injection evaluation
* End-to-end integration testing
* JSON-based workflow configuration

---

## Repository Structure

```text
backend/       FastAPI API, persistence, recovery policy and tests
frontend/      React + TypeScript operations dashboard
n8n/           SME simulations, failure capture and recovery workflows
evaluation/    Labelled 60-case failure-injection benchmark
.github/       CI workflows
docs/          Deployment and project documentation
render.yaml    Cloud deployment configuration
```

---

## Run Locally

### Quick developer mode

Create a Python environment and install the backend dependencies:

```bash
python -m venv .venv
```

Activate it:

```bash
# macOS/Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r backend/requirements-dev.txt
```

Start the API:

```bash
cd backend
uvicorn app.main:app --reload
```

In a second terminal, start the dashboard:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

The dashboard can fall back to demo data when the API is unavailable and switches to live API data when the backend is reachable.

### Production-like local stack

The repository also includes a Docker Compose setup:

```bash
docker compose up --build
```

This starts the API, PostgreSQL, n8n, and the dashboard.

---

## Diagnosis Model

Set `GEMINI_API_KEY` to enable Gemini structured diagnosis.

The model produces a schema-validated diagnosis and proposed action. Its output is then passed through SafeRecover's safety policy before any recovery can execute.

The model proposal is **never executed directly**.

If the Gemini API is unavailable, deterministic fallback rules keep the recovery service operational.

---

## Connect n8n

The `n8n/` directory contains the workflow definitions required to reproduce the recovery loop.

Import the workflow files and configure:

1. The SafeRecover API URL.
2. The recovery webhook URL.
3. `SafeRecover - Failure Capture` as the n8n error workflow.
4. The recovery runner as the recovery endpoint.
5. The relevant workflows as active workflows.

The recovery runner deliberately limits repairs to allowlisted operations such as payload normalisation. It does not execute arbitrary code generated by the model.

---

## API Example

A failure can be submitted directly to the SafeRecover API:

```bash
curl -X POST http://localhost:8000/api/v1/failures \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "Invoice Intake",
    "execution_id": "exec-42",
    "node_name": "Parse invoice",
    "error_type": "MALFORMED_JSON",
    "error_message": "Unexpected token",
    "reversible": true,
    "confidence": 0.95
  }'
```

Interactive API documentation is available at:

```text
http://localhost:8000/docs
```

---

## Evaluation

Run the failure-injection benchmark with:

```bash
python evaluation/run_evaluation.py
```

Run the backend test suite with:

```bash
cd backend
pytest -q
```

The evaluation focuses on whether SafeRecover makes the **right recovery decision**, not simply whether it can produce a plausible explanation.

---

## Cloud Deployment

The repository includes `render.yaml` for the cloud deployment configuration.

See [`docs/CLOUD_DEPLOYMENT.md`](docs/CLOUD_DEPLOYMENT.md) for the deployment process, environment variables, workflow configuration, and end-to-end verification.






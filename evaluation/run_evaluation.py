import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.diagnosis import diagnose
from app.models import Decision
from app.risk import apply_safety_boundaries, calculate_risk
from app.schemas import FailureEventIn


def expand_cases(seed_cases: list[dict], repeats: int = 5) -> list[dict]:
    cases = []
    for repeat in range(repeats):
        for seed in seed_cases:
            case = dict(seed)
            case["name"] = f"{seed['name']}-{repeat + 1}"
            cases.append(case)
    return cases


def main() -> None:
    seeds = json.loads((Path(__file__).parent / "cases.json").read_text())
    cases = expand_cases(seeds)
    results = []
    for i, case in enumerate(cases):
        expected = case.pop("expected_action")
        recoverable = case.pop("recoverable")
        risky = case.pop("risky")
        name = case.pop("name")
        event = FailureEventIn(
            workflow_name="Evaluation Workflow", execution_id=f"eval-{i:03}", node_name="Injected Node",
            error_message=name, payload={}, **case,
        )
        diagnosis = diagnose(event)
        risk = calculate_risk(event)
        actual = apply_safety_boundaries(event, diagnosis.proposed_action, risk).value
        autonomous = actual in {Decision.RETRY.value, Decision.REPAIR_RETRY.value, Decision.SUPPRESS.value}
        results.append({"name": name, "expected": expected, "actual": actual, "correct": actual == expected,
                        "recoverable": recoverable, "risky": risky, "autonomous": autonomous})

    total = len(results)
    correct = sum(r["correct"] for r in results)
    risky = [r for r in results if r["risky"]]
    unsafe = [r for r in risky if r["autonomous"]]
    recoverable = [r for r in results if r["recoverable"]]
    recovered = [r for r in recoverable if r["autonomous"]]
    distribution = Counter(r["actual"] for r in results)
    report = {
        "cases": total,
        "action_accuracy": round(correct / total, 4),
        "unsafe_autonomous_recovery_rate": round(len(unsafe) / len(risky), 4),
        "recoverable_case_automation_rate": round(len(recovered) / len(recoverable), 4),
        "action_distribution": dict(distribution),
        "errors": [r for r in results if not r["correct"]],
    }
    output = Path(__file__).parent / "results.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

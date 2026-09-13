export type RecoveryEvent = {
  id: string;
  workflow_name: string;
  execution_id: string;
  node_name: string;
  error_type: string;
  error_message: string;
  payload: Record<string, unknown>;
  attempt: number;
  diagnosis: string;
  diagnosis_source: string;
  proposed_action: string;
  risk_score: number;
  risk_band: "LOW" | "MEDIUM" | "HIGH";
  risk_reasons: string[];
  status: string;
  repair_patch: Record<string, unknown> | null;
  verification_passed: boolean | null;
  verification_detail: string | null;
  created_at: string;
};

export type Metrics = {
  total_events: number;
  autonomous_events: number;
  verified_recoveries: number;
  escalated_events: number;
  awaiting_approval: number;
  unsafe_autonomous_rate: number;
  verification_success_rate: number;
};

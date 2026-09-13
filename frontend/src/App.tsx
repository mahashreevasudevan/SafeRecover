import { useEffect, useMemo, useState } from "react";
import { Activity, Check, ChevronRight, RefreshCw, ShieldCheck, ShieldX, TriangleAlert, Workflow } from "lucide-react";
import { api } from "./api";
import type { Metrics, RecoveryEvent } from "./types";

const demoEvents: RecoveryEvent[] = [
  { id: "demo-1", workflow_name: "Invoice Processing", execution_id: "exec-4821", node_name: "Parse invoice", error_type: "MALFORMED_JSON", error_message: "Unexpected token at line 1", payload: {}, attempt: 1, diagnosis: "Payload is structurally invalid but repairable without changing business meaning.", diagnosis_source: "gemini:gemini-2.5-flash-lite", proposed_action: "REPAIR_RETRY", risk_score: .08, risk_band: "LOW", risk_reasons: ["low-impact reversible action"], status: "VERIFIED", repair_patch: {normalise_json: true}, verification_passed: true, verification_detail: "Invoice record created with expected fields.", created_at: new Date(Date.now()-1000*60*7).toISOString() },
  { id: "demo-2", workflow_name: "Legal Document Intake", execution_id: "exec-4818", node_name: "Match client matter", error_type: "AMBIGUOUS_MATCH", error_message: "3 client matters matched", payload: {}, attempt: 1, diagnosis: "Several candidate matters match the supplied evidence.", diagnosis_source: "gemini:gemini-2.5-flash-lite", proposed_action: "REQUIRE_APPROVAL", risk_score: .47, risk_band: "MEDIUM", risk_reasons: ["ambiguity"], status: "AWAITING_APPROVAL", repair_patch: null, verification_passed: null, verification_detail: null, created_at: new Date(Date.now()-1000*60*19).toISOString() },
  { id: "demo-3", workflow_name: "Expense Approval", execution_id: "exec-4809", node_name: "Post approved expense", error_type: "DATA_CONFLICT", error_message: "Receipt £1,250; claim £12,500", payload: {}, attempt: 1, diagnosis: "The receipt and submitted claim disagree on a material value.", diagnosis_source: "gemini:gemini-2.5-flash-lite", proposed_action: "BLOCK_ESCALATE", risk_score: .87, risk_band: "HIGH", risk_reasons: ["financial impact", "evidence disagreement"], status: "ESCALATED", repair_patch: null, verification_passed: null, verification_detail: "Blocked before mutation.", created_at: new Date(Date.now()-1000*60*31).toISOString() },
  { id: "demo-4", workflow_name: "Invoice Processing", execution_id: "exec-4801", node_name: "Accounting API", error_type: "API_TIMEOUT", error_message: "Upstream request timed out", payload: {}, attempt: 2, diagnosis: "Transient upstream timeout; a bounded retry is appropriate.", diagnosis_source: "rules-fallback", proposed_action: "RETRY", risk_score: .11, risk_band: "LOW", risk_reasons: ["low-impact reversible action"], status: "AUTO_RECOVERED", repair_patch: null, verification_passed: null, verification_detail: "Retry dispatched.", created_at: new Date(Date.now()-1000*60*48).toISOString() },
];

const demoMetrics: Metrics = { total_events: 48, autonomous_events: 29, verified_recoveries: 25, escalated_events: 11, awaiting_approval: 8, unsafe_autonomous_rate: 0, verification_success_rate: .926 };

function pretty(value: string) { return value.replaceAll("_", " ").toLowerCase().replace(/^./, c => c.toUpperCase()); }

export default function App() {
  const [events, setEvents] = useState<RecoveryEvent[]>(demoEvents);
  const [metrics, setMetrics] = useState<Metrics>(demoMetrics);
  const [selected, setSelected] = useState<RecoveryEvent>(demoEvents[0]);
  const [mode, setMode] = useState<"live" | "demo">("demo");
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    setLoading(true);
    try {
      const [nextEvents, nextMetrics] = await Promise.all([api.events(), api.metrics()]);
      if (nextEvents.length) { setEvents(nextEvents); setSelected(nextEvents[0]); }
      setMetrics(nextMetrics); setMode("live");
    } catch { setMode("demo"); }
    finally { setLoading(false); }
  };
  useEffect(() => { refresh(); }, []);

  const approve = async (approved: boolean) => {
    if (mode === "demo") {
      const updated = {...selected, status: approved ? "AUTO_RECOVERED" : "ESCALATED"};
      setSelected(updated); setEvents(list => list.map(e => e.id === updated.id ? updated : e)); return;
    }
    const updated = await api.approve(selected.id, approved);
    setSelected(updated); setEvents(list => list.map(e => e.id === updated.id ? updated : e));
  };

  const autonomousPct = useMemo(() => metrics.total_events ? Math.round(metrics.autonomous_events / metrics.total_events * 100) : 0, [metrics]);

  return <div className="shell">
    <aside className="sidebar">
      <div className="brand"><span className="brandmark"><ShieldCheck size={21}/></span><span>SafeRecover</span></div>
      <nav><button className="nav-active"><Activity size={18}/>Operations</button><button><Workflow size={18}/>Workflows</button><button><ShieldCheck size={18}/>Policy</button></nav>
      <div className="system-card"><div className="eyebrow">CONTROL PLANE</div><strong>Guardrails active</strong><p>Only low-risk, reversible actions can run automatically.</p><div className="live-line"><span/>Policy v1.0</div></div>
      <div className="operator"><span>MV</span><div><strong>Operator</strong><small>Safety reviewer</small></div></div>
    </aside>
    <main>
      <header><div><p className="eyebrow">RECOVERY CONTROL CENTRE</p><h1>Workflow operations</h1></div><div className="header-actions"><span className={`mode ${mode}`}>{mode === "live" ? "Live API" : "Demo data"}</span><button className="icon-button" onClick={refresh} aria-label="Refresh"><RefreshCw size={17} className={loading ? "spin" : ""}/></button></div></header>
      <section className="metrics">
        <Metric label="Recovery events" value={metrics.total_events.toString()} note="Current audit window" />
        <Metric label="Autonomous" value={`${autonomousPct}%`} note={`${metrics.autonomous_events} safe actions`} accent="cyan" />
        <Metric label="Verified success" value={`${Math.round(metrics.verification_success_rate*100)}%`} note={`${metrics.verified_recoveries} downstream checks`} accent="green" />
        <Metric label="Unsafe actions" value={`${(metrics.unsafe_autonomous_rate*100).toFixed(1)}%`} note="Target: 0%" accent="red" />
      </section>
      <section className="workspace">
        <div className="event-panel">
          <div className="panel-title"><div><h2>Recovery queue</h2><p>Latest failures and decisions</p></div><span>{events.length} shown</span></div>
          <div className="table-head"><span>Workflow</span><span>Risk</span><span>Decision</span><span>Status</span><span/></div>
          <div className="event-list">{events.map(event => <button key={event.id} className={`event-row ${selected.id === event.id ? "selected" : ""}`} onClick={() => setSelected(event)}>
            <span className="workflow-name"><i className={`risk-dot ${event.risk_band.toLowerCase()}`}/><span><strong>{event.workflow_name}</strong><small>{event.node_name} · {new Date(event.created_at).toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"})}</small></span></span>
            <span><b className={`risk-pill ${event.risk_band.toLowerCase()}`}>{event.risk_band} · {event.risk_score.toFixed(2)}</b></span>
            <span className="decision">{pretty(event.proposed_action)}</span>
            <span className={`status ${event.status.toLowerCase()}`}>{pretty(event.status)}</span><ChevronRight size={16}/>
          </button>)}</div>
        </div>
        <aside className="detail-panel">
          <div className="detail-top"><div><p className="eyebrow">INCIDENT {selected.execution_id}</p><h2>{selected.workflow_name}</h2></div><span className={`risk-pill ${selected.risk_band.toLowerCase()}`}>{selected.risk_band} RISK</span></div>
          <div className="timeline"><Step done label="Failure captured" detail={`${pretty(selected.error_type)} at ${selected.node_name}`}/><Step done label="Diagnosis" detail={selected.diagnosis}/><Step done={selected.status !== "AWAITING_APPROVAL"} active={selected.status === "AWAITING_APPROVAL"} label={pretty(selected.proposed_action)} detail={`Risk ${selected.risk_score.toFixed(2)} · ${selected.risk_reasons.join(", ")}`}/><Step done={selected.verification_passed === true} label="Downstream verification" detail={selected.verification_detail ?? "Pending recovery decision"}/></div>
          {selected.status === "AWAITING_APPROVAL" && <div className="approval"><p><TriangleAlert size={17}/>Human decision required</p><div><button className="reject" onClick={() => approve(false)}><ShieldX size={16}/>Block</button><button className="approve" onClick={() => approve(true)}><Check size={16}/>Approve recovery</button></div></div>}
          <div className="evidence"><h3>Decision evidence</h3><dl><div><dt>Failure</dt><dd>{selected.error_message}</dd></div><div><dt>Execution</dt><dd>{selected.execution_id} · attempt {selected.attempt}</dd></div><div><dt>Repair</dt><dd>{selected.repair_patch ? JSON.stringify(selected.repair_patch) : "No payload mutation"}</dd></div></dl></div>
        </aside>
      </section>
    </main>
  </div>;
}

function Metric({label,value,note,accent=""}:{label:string,value:string,note:string,accent?:string}) { return <article className={`metric ${accent}`}><p>{label}</p><strong>{value}</strong><small>{note}</small></article> }
function Step({label,detail,done=false,active=false}:{label:string,detail:string,done?:boolean,active?:boolean}) { return <div className={`step ${done ? "done" : ""} ${active ? "active" : ""}`}><span>{done ? <Check size={14}/> : ""}</span><div><strong>{label}</strong><p>{detail}</p></div></div> }

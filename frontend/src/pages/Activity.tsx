import { useState } from "react";
import type { FormEvent } from "react";
import { Activity, RefreshCw, Search, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { api, unwrapList } from "../api/jobs";
import { useJobs } from "../hooks/useJobs";
import type { WorkflowEvent } from "../api/types";
import ActivityTimeline from "../components/ActivityTimeline";

export default function ActivityPage() {
  const { jobs } = useJobs();
  const [jobId, setJobId] = useState("");
  const [events, setEvents] = useState<WorkflowEvent[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function loadEvents(idToLoad: string) {
    if (!idToLoad.trim()) return;
    setBusy(true);
    setError("");
    try {
      const data = await api.events(idToLoad.trim());
      setEvents(unwrapList(data, "events"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load events.");
    } finally {
      setBusy(false);
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    void loadEvents(jobId);
  }

  return (
    <div className="page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">EVENT STREAM</div>
          <h1>Agent activity</h1>
          <p>Inspect backend-recorded workflow transitions, patch hashes, and lifecycle state changes.</p>
        </div>
      </div>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <div className="eyebrow">JOB EVENT QUERY</div>
            <h2>
              <Activity size={18} /> Workflow timeline
            </h2>
          </div>
        </div>

        <div style={{ padding: "20px" }}>
          {jobs.length > 0 && (
            <div style={{ marginBottom: "16px" }}>
              <div style={{ fontSize: "11px", color: "#99958c", marginBottom: "8px" }}>
                Quick select from recent jobs:
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                {jobs.slice(0, 5).map((j) => {
                  const jId = j.id || j.job_id || "";
                  return (
                    <button
                      key={jId}
                      className="button button-secondary"
                      style={{ padding: "6px 12px", fontSize: "11px" }}
                      onClick={() => {
                        setJobId(jId);
                        void loadEvents(jId);
                      }}
                    >
                      {j.finding?.id || jId} <small style={{ color: "#888" }}>({j.status})</small>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          <form className="evidence-form" onSubmit={handleSubmit}>
            <label htmlFor="activity-job" style={{ display: "block", fontSize: "11px", color: "#99958c", marginBottom: "6px" }}>
              Job ID
            </label>
            <div className="evidence-input-row">
              <input
                id="activity-job"
                value={jobId}
                onChange={(e) => setJobId(e.target.value)}
                placeholder="Enter a backend job ID..."
                required
              />
              <button className="button button-primary" disabled={busy || !jobId.trim()} type="submit">
                {busy ? <RefreshCw size={15} className="spin" /> : <Search size={15} />} Load events
              </button>
            </div>
          </form>

          {error && (
            <div className="error-banner" style={{ marginTop: "16px" }}>
              {error}
            </div>
          )}

          {events.length > 0 && (
            <div style={{ marginTop: "24px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
                <h3 style={{ margin: 0, fontSize: "16px", color: "#fff" }}>Recorded Events ({events.length})</h3>
                <Link to={`/jobs/${encodeURIComponent(jobId)}`} className="text-link">
                  Open in Investigation <ArrowRight size={13} />
                </Link>
              </div>
              <ActivityTimeline events={events} />
            </div>
          )}

          {!busy && !error && !events.length && (
            <div className="empty-state" style={{ marginTop: "16px" }}>
              Enter a job ID or select a recent job above to load actual workflow events from <code>GET /api/jobs/{`{job_id}`}/events</code>.
            </div>
          )}
        </div>
      </section>

      <section className="panel event-types">
        <div style={{ padding: "20px" }}>
          <div className="eyebrow">WORKFLOW LIFECYCLE STATES</div>
          <h2 style={{ fontSize: "20px", margin: "6px 0 10px" }}>Supported backend states</h2>
          <p style={{ margin: 0, fontSize: "12px", color: "#b5b2ab", lineHeight: 1.6 }}>
            FINDING_RECEIVED · PLANNING · AWAITING_APPROVAL · VERIFYING · VERIFICATION_FAILED · VERIFIED · POLICY_REJECTED · USER_REJECTED · RETRY_EXHAUSTED · EXECUTION_ERROR
          </p>
        </div>
      </section>
    </div>
  );
}
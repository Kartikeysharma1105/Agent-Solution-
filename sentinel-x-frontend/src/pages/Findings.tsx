import { useState } from "react";
import { Plus, RefreshCw, Search, X, AlertTriangle, CheckCircle2, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../api/jobs";
import { useJobs } from "../hooks/useJobs";
import FindingsTable from "../components/FindingsTable";
import type { Finding, FindingRequest, FindingSeverity } from "../api/types";

export default function Findings() {
  const { jobs, loading, error, refresh } = useJobs();
  const [showCreate, setShowCreate] = useState(false);
  const [activeTab, setActiveTab] = useState<"demo" | "custom">("demo");
  const [creating, setCreating] = useState(false);
  const [message, setMessage] = useState("");
  const [createdJobId, setCreatedJobId] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  // Custom finding form state
  const [customTargetApp, setCustomTargetApp] = useState("bola-demo-v1");
  const [customFindingId, setCustomFindingId] = useState("BOLA-001");
  const [customType, setCustomType] = useState("BROKEN_OBJECT_LEVEL_AUTHORIZATION");
  const [customSeverity, setCustomSeverity] = useState<FindingSeverity>("HIGH");
  const [customFilePath, setCustomFilePath] = useState("app/access.py");
  const [customDescription, setCustomDescription] = useState("A user can access another user's private document via unrestricted parameter manipulation.");

  async function submitFinding(payload: FindingRequest) {
    setCreating(true);
    setMessage("");
    setCreatedJobId(null);

    try {
      const res = await api.createFinding(payload);
      const jobId = res.job_id;
      setCreatedJobId(jobId);
      setMessage(`Job created successfully: ${jobId} (Status: ${res.status}). Planning will proceed asynchronously.`);
      await refresh(false);
    } catch (e: unknown) {
      const err = e as { message?: string };
      setMessage(err.message || "Finding submission failed.");
    } finally {
      setCreating(false);
    }
  }

  function handleDemoSubmit() {
    const finding: Finding = {
      id: "BOLA-001",
      type: "BROKEN_OBJECT_LEVEL_AUTHORIZATION",
      severity: "HIGH",
      file_path: "app/access.py",
      description: "A user can access another user's private document.",
    };
    void submitFinding({ target_app_id: "bola-demo-v1", finding });
  }

  function handleCustomSubmit(e: React.FormEvent) {
    e.preventDefault();
    const finding: Finding = {
      id: customFindingId.trim(),
      type: customType.trim(),
      severity: customSeverity,
      file_path: customFilePath.trim(),
      description: customDescription.trim(),
    };
    void submitFinding({ target_app_id: customTargetApp.trim(), finding });
  }

  const filtered = jobs.filter((j) => {
    const searchTarget = `${j.finding?.id || j.finding_id || ""} ${j.finding?.type || ""} ${j.finding?.file_path || ""} ${j.id || j.job_id || ""}`.toLowerCase();
    return searchTarget.includes(filter.toLowerCase());
  });

  return (
    <div className="page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">DETECTION INTAKE</div>
          <h1>Security findings</h1>
          <p>Review incoming vulnerabilities and track autonomous remediation jobs.</p>
        </div>
        <button
          className="button button-primary"
          onClick={() => {
            setShowCreate(!showCreate);
            setMessage("");
            setCreatedJobId(null);
          }}
        >
          <Plus size={16} /> Submit security finding
        </button>
      </div>

      {showCreate && (
        <section className="panel create-panel">
          <div className="panel-heading">
            <div>
              <div className="eyebrow">SUBMIT FINDING</div>
              <h3>Intake new vulnerability</h3>
            </div>
            <button className="icon-button" onClick={() => setShowCreate(false)} aria-label="Close">
              <X size={16} />
            </button>
          </div>

          <div style={{ padding: "0 22px 14px", display: "flex", gap: "10px", borderBottom: "1px solid #333" }}>
            <button
              className={`button ${activeTab === "demo" ? "button-primary" : "button-secondary"}`}
              style={{ padding: "8px 14px", fontSize: "11px" }}
              onClick={() => setActiveTab("demo")}
            >
              Standard BOLA-001 Finding
            </button>
            <button
              className={`button ${activeTab === "custom" ? "button-primary" : "button-secondary"}`}
              style={{ padding: "8px 14px", fontSize: "11px" }}
              onClick={() => setActiveTab("custom")}
            >
              Custom Finding
            </button>
          </div>

          {activeTab === "demo" ? (
            <div>
              <p style={{ margin: "16px 22px 0" }}>
                Submits the standard BOLA-001 vulnerability to <code>POST /api/findings</code>. The backend verifies target authorization and initiates autonomous remediation planning.
              </p>
              <div className="demo-payload">
                <span>Target App ID</span>
                <code>bola-demo-v1</code>
                <span>Finding ID</span>
                <code>BOLA-001</code>
                <span>Type</span>
                <code>BROKEN_OBJECT_LEVEL_AUTHORIZATION</code>
                <span>File Path</span>
                <code>app/access.py</code>
                <span>Severity</span>
                <code className="danger-text">HIGH</code>
                <span>Description</span>
                <span>A user can access another user's private document.</span>
              </div>
              <button
                className="button button-primary"
                disabled={creating}
                onClick={handleDemoSubmit}
              >
                {creating ? <RefreshCw size={15} className="spin" /> : <Plus size={15} />}
                Submit finding to backend
              </button>
            </div>
          ) : (
            <form onSubmit={handleCustomSubmit} style={{ padding: "16px 22px" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px", marginBottom: "14px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "11px", color: "#99958c", marginBottom: "5px" }}>
                    Target App ID
                  </label>
                  <input
                    value={customTargetApp}
                    onChange={(e) => setCustomTargetApp(e.target.value)}
                    style={{ width: "100%", padding: "10px", background: "#151515", border: "1px solid #444", borderRadius: "8px", color: "#fff", fontSize: "12px" }}
                    required
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "11px", color: "#99958c", marginBottom: "5px" }}>
                    Finding ID
                  </label>
                  <input
                    value={customFindingId}
                    onChange={(e) => setCustomFindingId(e.target.value)}
                    style={{ width: "100%", padding: "10px", background: "#151515", border: "1px solid #444", borderRadius: "8px", color: "#fff", fontSize: "12px" }}
                    required
                  />
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "14px", marginBottom: "14px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "11px", color: "#99958c", marginBottom: "5px" }}>
                    Vulnerability Type
                  </label>
                  <input
                    value={customType}
                    onChange={(e) => setCustomType(e.target.value)}
                    style={{ width: "100%", padding: "10px", background: "#151515", border: "1px solid #444", borderRadius: "8px", color: "#fff", fontSize: "12px" }}
                    required
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "11px", color: "#99958c", marginBottom: "5px" }}>
                    Severity
                  </label>
                  <select
                    value={customSeverity}
                    onChange={(e) => setCustomSeverity(e.target.value as FindingSeverity)}
                    style={{ width: "100%", padding: "10px", background: "#151515", border: "1px solid #444", borderRadius: "8px", color: "#fff", fontSize: "12px" }}
                  >
                    <option value="LOW">LOW</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="HIGH">HIGH</option>
                    <option value="CRITICAL">CRITICAL</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "11px", color: "#99958c", marginBottom: "5px" }}>
                    File Path
                  </label>
                  <input
                    value={customFilePath}
                    onChange={(e) => setCustomFilePath(e.target.value)}
                    style={{ width: "100%", padding: "10px", background: "#151515", border: "1px solid #444", borderRadius: "8px", color: "#fff", fontSize: "12px" }}
                    required
                  />
                </div>
              </div>

              <div style={{ marginBottom: "16px" }}>
                <label style={{ display: "block", fontSize: "11px", color: "#99958c", marginBottom: "5px" }}>
                  Description
                </label>
                <textarea
                  value={customDescription}
                  onChange={(e) => setCustomDescription(e.target.value)}
                  rows={2}
                  style={{ width: "100%", padding: "10px", background: "#151515", border: "1px solid #444", borderRadius: "8px", color: "#fff", fontSize: "12px" }}
                  required
                />
              </div>

              <button type="submit" className="button button-primary" disabled={creating}>
                {creating ? <RefreshCw size={15} className="spin" /> : <Plus size={15} />}
                Submit finding to backend
              </button>
            </form>
          )}

          {message && (
            <div style={{ margin: "0 22px 18px" }}>
              <div className="notice" style={{ margin: 0 }}>
                {createdJobId ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
                <span>{message}</span>
                {createdJobId && (
                  <Link
                    to={`/jobs/${encodeURIComponent(createdJobId)}`}
                    className="button button-secondary"
                    style={{ marginLeft: "auto", padding: "6px 12px", fontSize: "11px" }}
                  >
                    Open Job <ArrowRight size={13} />
                  </Link>
                )}
              </div>
            </div>
          )}
        </section>
      )}

      {error && <div className="error-banner">{error}</div>}

      <section className="panel table-panel">
        <div className="panel-heading">
          <div>
            <div className="eyebrow">BACKEND RECORDS</div>
            <h2>
              Findings & jobs <span className="subtle-count">{filtered.length}</span>
            </h2>
          </div>
          <div className="table-tools">
            <div className="input-search">
              <Search size={15} />
              <input
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder="Filter findings…"
              />
            </div>
            <button
              className="icon-button"
              onClick={() => void refresh(true)}
              aria-label="Refresh"
              disabled={loading}
            >
              <RefreshCw size={15} className={loading ? "spin" : ""} />
            </button>
          </div>
        </div>

        {loading ? (
          <div className="loading-state">
            <RefreshCw size={17} className="spin" /> Loading findings from backend…
          </div>
        ) : (
          <FindingsTable jobs={filtered} />
        )}
      </section>
    </div>
  );
}
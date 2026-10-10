import { Link } from "react-router-dom";
import { ShieldCheck, ArrowUpRight, FlaskConical, RefreshCw, CheckCircle2, XCircle } from "lucide-react";
import { useJobs } from "../hooks/useJobs";
import StatusBadge from "../components/StatusBadge";

export default function VerificationPage() {
  const { jobs, loading, error, refresh } = useJobs();

  const verifyingJobs = jobs.filter((j) => j.status === "VERIFYING");
  const completedJobs = jobs.filter((j) =>
    ["VERIFIED", "VERIFICATION_FAILED", "EXECUTION_ERROR"].includes(String(j.status))
  );

  return (
    <div className="page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">DEVELOPER 3 ADVERSARIAL ENGINE</div>
          <h1>Verification console</h1>
          <p>
            Execute and monitor isolated sandbox tests against operator-approved patches.
          </p>
        </div>
        <button
          className="button button-secondary"
          onClick={() => void refresh(true)}
          disabled={loading}
        >
          <RefreshCw size={14} className={loading ? "spin" : ""} /> Refresh jobs
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="dashboard-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <div className="eyebrow">READY FOR VERIFICATION</div>
              <h2>Approved jobs ({verifyingJobs.length})</h2>
            </div>
            <FlaskConical size={18} className="text-cyan" />
          </div>

          <div style={{ padding: "20px" }}>
            {loading ? (
              <div className="loading-state">
                <RefreshCw size={16} className="spin" /> Loading jobs...
              </div>
            ) : !verifyingJobs.length ? (
              <div className="empty-state">
                No jobs currently awaiting verification execution. Approve a proposed patch from the Investigation page to transition it to the VERIFYING state.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {verifyingJobs.map((job) => {
                  const jId = job.id || job.job_id || "";
                  return (
                    <div
                      key={jId}
                      style={{
                        background: "#151515",
                        border: "1px solid #3d3d3d",
                        borderRadius: "12px",
                        padding: "16px",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <div>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                          <span style={{ color: "#16b8ef", fontFamily: "monospace", fontSize: "12px" }}>
                            {job.finding?.id || jId}
                          </span>
                          <StatusBadge status={job.status} />
                        </div>
                        <div style={{ fontSize: "13px", fontWeight: 700, color: "#fff" }}>
                          {job.finding?.type ? job.finding.type.replaceAll("_", " ") : "BOLA vulnerability"}
                        </div>
                        <div style={{ fontSize: "11px", color: "#888", marginTop: "2px" }}>
                          {job.finding?.file_path || "app/access.py"} · Attempt {job.attempt ?? 0}
                        </div>
                      </div>

                      <Link
                        to={`/jobs/${encodeURIComponent(jId)}`}
                        className="button button-primary"
                        style={{ padding: "8px 14px", fontSize: "11px" }}
                      >
                        Execute in Sandbox <ArrowUpRight size={13} />
                      </Link>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <div>
              <div className="eyebrow">VERIFIED HISTORY</div>
              <h2>Completed runs ({completedJobs.length})</h2>
            </div>
            <ShieldCheck size={18} className="text-cyan" />
          </div>

          <div style={{ padding: "20px" }}>
            {loading ? (
              <div className="loading-state">
                <RefreshCw size={16} className="spin" /> Loading history...
              </div>
            ) : !completedJobs.length ? (
              <div className="empty-state">
                Completed verification runs will appear here with cryptographic attestations and test suite summaries.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {completedJobs.slice(0, 6).map((job) => {
                  const jId = job.id || job.job_id || "";
                  const isPass = job.status === "VERIFIED";
                  return (
                    <div
                      key={jId}
                      style={{
                        background: "#151515",
                        border: "1px solid #333",
                        borderRadius: "10px",
                        padding: "12px 16px",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        {isPass ? (
                          <CheckCircle2 size={18} style={{ color: "#c9ef72", flexShrink: 0 }} />
                        ) : (
                          <XCircle size={18} style={{ color: "#ff8ca2", flexShrink: 0 }} />
                        )}
                        <div>
                          <div style={{ fontSize: "12px", fontWeight: 700, color: "#fff" }}>
                            {job.finding?.id || jId}
                          </div>
                          <div style={{ fontSize: "10px", color: "#888" }}>
                            {job.finding?.file_path || "app/access.py"}
                          </div>
                        </div>
                      </div>

                      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        <StatusBadge status={job.status} />
                        <Link
                          to={`/jobs/${encodeURIComponent(jId)}`}
                          className="table-action"
                          aria-label={`Open ${jId}`}
                        >
                          <ArrowUpRight size={14} />
                        </Link>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </section>
      </div>

      <section className="panel" style={{ marginTop: "24px" }}>
        <div className="panel-heading">
          <div>
            <div className="eyebrow">SANDBOX ARCHITECTURE</div>
            <h2>Verification Security Guarantees</h2>
          </div>
        </div>
        <div style={{ padding: "20px", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "16px" }}>
          <div style={{ background: "#171717", padding: "16px", borderRadius: "12px", border: "1px solid #333" }}>
            <div style={{ color: "#16b8ef", fontWeight: 800, fontSize: "12px", marginBottom: "6px" }}>
              01 · AIR-GAPPED DOCKER SANDBOX
            </div>
            <p style={{ margin: 0, fontSize: "12px", color: "#ccc", lineHeight: 1.5 }}>
              Verification executes inside an ephemeral Docker container with network isolation (<code>network_disabled=True</code>), read-only protected test suites, and strict process limits.
            </p>
          </div>

          <div style={{ background: "#171717", padding: "16px", borderRadius: "12px", border: "1px solid #333" }}>
            <div style={{ color: "#16b8ef", fontWeight: 800, fontSize: "12px", marginBottom: "6px" }}>
              02 · PROTECTED TEST SUITE INTEGRITY
            </div>
            <p style={{ margin: 0, fontSize: "12px", color: "#ccc", lineHeight: 1.5 }}>
              Protected tests are injected into the sandbox container directly from trusted verification storage and cannot be modified or bypassed by the proposed patch.
            </p>
          </div>

          <div style={{ background: "#171717", padding: "16px", borderRadius: "12px", border: "1px solid #333" }}>
            <div style={{ color: "#16b8ef", fontWeight: 800, fontSize: "12px", marginBottom: "6px" }}>
              03 · CRYPTOGRAPHIC ATTESTATION
            </div>
            <p style={{ margin: 0, fontSize: "12px", color: "#ccc", lineHeight: 1.5 }}>
              Every completed run produces a SHA-256 evidence attestation binding run ID, patch hash, source revision, and test outcomes into an unforgeable audit record.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}

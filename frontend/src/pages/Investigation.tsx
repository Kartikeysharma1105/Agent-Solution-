import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  RefreshCw,
  BrainCircuit,
  FileCode2,
  History,
  ShieldCheck,
  ScrollText,
  AlertTriangle,
  KeyRound,
  CheckCircle2,
} from "lucide-react";
import { useJobDetails } from "../hooks/useJobDetails";
import StatusBadge from "../components/StatusBadge";
import PatchDiffViewer from "../components/PatchDiffViewer";
import ApprovalPanel from "../components/ApprovalPanel";
import ActivityTimeline from "../components/ActivityTimeline";
import VerificationPanel from "../components/VerificationPanel";
import { api } from "../api/jobs";
import { getOperatorToken, setOperatorToken } from "../api/client";

export default function Investigation() {
  const { jobId } = useParams();
  const {
    job,
    patch,
    events,
    verificationResult,
    loading,
    error,
    refresh,
    setVerificationResult,
  } = useJobDetails(jobId);

  const [verifyBusy, setVerifyBusy] = useState(false);
  const [verifyError, setVerifyError] = useState("");
  const [verifySuccess, setVerifySuccess] = useState("");
  const [showTokenPrompt, setShowTokenPrompt] = useState(false);
  const [tokenInput, setTokenInput] = useState(getOperatorToken());

  const currentJobId = job?.id || job?.job_id || jobId || "";
  const canVerify = job?.status === "VERIFYING";
  const isPlanning = job?.status === "PLANNING" || job?.status === "FINDING_RECEIVED";

  async function handleVerify() {
    if (!currentJobId || verifyBusy || !canVerify) return;
    setVerifyBusy(true);
    setVerifyError("");
    setVerifySuccess("");

    try {
      const res = await api.verify(currentJobId);
      setVerificationResult(res);
      setVerifySuccess(`Verification executed: ${res.status} (${res.tests_passed ?? 0}/${res.tests_total ?? 0} passed in isolated container).`);
      await refresh(false);
    } catch (e: unknown) {
      const err = e as { message?: string; status?: number; code?: string };
      if (err.status === 401 || err.code === "OPERATOR_AUTH_REQUIRED") {
        setVerifyError("Operator authentication required to launch verification sandbox.");
        setShowTokenPrompt(true);
      } else {
        setVerifyError(err.message || "Verification request failed.");
      }
    } finally {
      setVerifyBusy(false);
    }
  }

  function handleSaveToken(e: React.FormEvent) {
    e.preventDefault();
    setOperatorToken(tokenInput.trim());
    setShowTokenPrompt(false);
    setVerifyError("");
  }

  if (!jobId) {
    return (
      <div className="page">
        <div className="error-state">
          <h2>Select a job to investigate</h2>
          <p>Open a job from the Findings queue or Overview dashboard.</p>
          <Link to="/findings" className="button button-primary">
            Browse findings
          </Link>
        </div>
      </div>
    );
  }

  if (loading && !job) {
    return (
      <div className="page">
        <div className="loading-state">
          <RefreshCw size={18} className="spin" /> Loading job, patch, and event history from backend…
        </div>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="page">
        <div className="error-state">
          <h2>Unable to load investigation</h2>
          <p>{error || "The backend returned no job for this identifier."}</p>
          <p>Check backend availability or verify the job identifier.</p>
          <div style={{ display: "flex", gap: "10px", marginTop: "14px" }}>
            <button className="button button-secondary" onClick={() => void refresh(true)}>
              Retry
            </button>
            <Link to="/findings" className="button button-primary">
              Back to findings
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const finding = job.finding;
  const rootCauseText = patch?.root_cause || (job.root_cause as string) || (job.analysis as string);

  return (
    <div className="page">
      <div className="page-heading">
        <div>
          <Link to="/findings" className="back-link">
            <ArrowLeft size={14} /> Findings
          </Link>
          <div className="eyebrow">INVESTIGATION / {currentJobId}</div>
          <h1>{finding?.id || job.finding_id || currentJobId}</h1>
          <p>
            {finding?.description ||
              job.summary ||
              "Autonomous remediation workflow managed by SENTINEL-X."}
          </p>
        </div>
        <div className="heading-actions">
          <StatusBadge status={job.status} />
          <button className="button button-secondary" onClick={() => void refresh(true)}>
            <RefreshCw size={14} className={loading ? "spin" : ""} /> Refresh
          </button>
          <Link to={`/evidence?jobId=${encodeURIComponent(currentJobId)}`} className="button button-secondary">
            <ScrollText size={14} /> View evidence
          </Link>
        </div>
      </div>

      <div className="investigation-summary">
        <div>
          <span>Vulnerability</span>
          <strong>{finding?.type ? finding.type.replaceAll("_", " ") : "Not provided"}</strong>
        </div>
        <div>
          <span>Severity</span>
          <strong className={`severity ${String(finding?.severity || "").toLowerCase()}`}>
            {finding?.severity || "—"}
          </strong>
        </div>
        <div>
          <span>Affected file</span>
          <strong>
            <FileCode2 size={14} />
            {finding?.file_path || "—"}
          </strong>
        </div>
        <div>
          <span>Patch Attempt</span>
          <strong>{patch?.attempt ?? job.attempt ?? 0}</strong>
        </div>
      </div>

      {isPlanning && (
        <div className="notice" style={{ marginTop: "18px", marginBottom: "18px", background: "#102a33", borderColor: "#1d6074", color: "#72dcff" }}>
          <RefreshCw size={16} className="spin" />
          <div>
            <strong>Autonomous Remediation Planning in Progress</strong>
            <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#c1e7f5" }}>
              The planner is generating a minimal, secure patch proposal. This page will update automatically once the patch is ready for operator review.
            </p>
          </div>
        </div>
      )}

      <div className="investigation-grid">
        <div className="investigation-main">
          <section className="panel">
            <div className="panel-heading">
              <div>
                <div className="eyebrow">ACTIVE PATCH</div>
                <h2>
                  <FileCode2 size={18} /> Proposed code changes
                </h2>
              </div>
              <span className="version-pill">
                Attempt {patch?.attempt ?? job.attempt ?? 0}
              </span>
            </div>

            <PatchDiffViewer patch={patch} />

            <div className="patch-explanation">
              <BrainCircuit size={17} />
              <div>
                <strong>Patch explanation</strong>
                <p>
                  {patch?.explanation ||
                    (isPlanning
                      ? "The autonomous planner is currently generating a patch explanation."
                      : "No patch explanation was returned in the backend response.")}
                </p>
              </div>
            </div>
          </section>

          <section className="panel">
            <div className="panel-heading">
              <div>
                <div className="eyebrow">ADVERSARIAL VERIFICATION</div>
                <h2>
                  <ShieldCheck size={18} /> Test evidence
                </h2>
              </div>
            </div>

            <VerificationPanel result={verificationResult} />

            {verifyError && (
              <div className="error-banner" style={{ margin: "16px 20px 0" }}>
                <AlertTriangle size={15} />
                <span>{verifyError}</span>
              </div>
            )}

            {verifySuccess && (
              <div className="notice" style={{ margin: "16px 20px 0" }}>
                <CheckCircle2 size={15} />
                <span>{verifySuccess}</span>
              </div>
            )}

            {showTokenPrompt && (
              <form
                onSubmit={handleSaveToken}
                style={{
                  margin: "16px 20px 0",
                  padding: "14px",
                  background: "#171717",
                  border: "1px solid #ffe45e",
                  borderRadius: "12px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#ffe45e", marginBottom: "8px", fontSize: "12px", fontWeight: 700 }}>
                  <KeyRound size={16} /> Operator Authentication Required
                </div>
                <input
                  type="password"
                  value={tokenInput}
                  onChange={(e) => setTokenInput(e.target.value)}
                  placeholder="Enter SENTINEL_OPERATOR_TOKEN..."
                  style={{ width: "100%", padding: "10px", background: "#0c0c0c", border: "1px solid #444", borderRadius: "8px", color: "#fff", fontSize: "12px", marginBottom: "10px" }}
                  required
                />
                <button type="submit" className="button button-primary" style={{ padding: "8px 14px", fontSize: "11px" }}>
                  Save and Retry
                </button>
              </form>
            )}

            <div className="verify-action" style={{ padding: "16px 20px" }}>
              <button
                className="button button-primary"
                disabled={verifyBusy || !canVerify}
                onClick={() => void handleVerify()}
              >
                {verifyBusy ? (
                  <RefreshCw size={15} className="spin" />
                ) : (
                  <ShieldCheck size={15} />
                )}
                Request verification
              </button>
              <span style={{ fontSize: "11px", color: "#99958c" }}>
                {canVerify
                  ? "Patch approved. Verification executes Developer 3 engine in isolated container."
                  : "Verification is enabled only when patch is in VERIFYING state."}
              </span>
            </div>
          </section>
        </div>

        <div className="investigation-side">
          <ApprovalPanel
            job={job}
            patch={patch}
            onUpdated={() => void refresh(false)}
          />

          <section className="panel">
            <div className="panel-heading">
              <div>
                <div className="eyebrow">ROOT CAUSE</div>
                <h3>
                  <BrainCircuit size={16} /> Analysis
                </h3>
              </div>
            </div>
            <p className="analysis-copy" style={{ padding: "16px 20px" }}>
              {rootCauseText ||
                (isPlanning
                  ? "Root-cause analysis is being prepared by the planner."
                  : "Root-cause analysis has not been supplied in the job response.")}
            </p>
          </section>

          <section className="panel">
            <div className="panel-heading">
              <div>
                <div className="eyebrow">AUDIT TRAIL</div>
                <h3>
                  <History size={16} /> Revision history
                </h3>
              </div>
            </div>
            <ActivityTimeline events={events} />
          </section>
        </div>
      </div>
    </div>
  );
}
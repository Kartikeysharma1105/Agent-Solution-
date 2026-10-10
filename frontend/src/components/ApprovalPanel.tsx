import { useState } from "react";
import { Check, X, ShieldCheck, AlertTriangle, LoaderCircle, KeyRound } from "lucide-react";
import { api } from "../api/jobs";
import { getOperatorToken, setOperatorToken } from "../api/client";
import type { Job, Patch } from "../api/types";
import StatusBadge from "./StatusBadge";

export default function ApprovalPanel({
  job,
  patch,
  onUpdated,
}: {
  job: Job | null;
  patch: Patch | null;
  onUpdated: () => void;
}) {
  const [busy, setBusy] = useState<"APPROVE" | "REJECT" | null>(null);
  const [message, setMessage] = useState("");
  const [isError, setIsError] = useState(false);
  const [confirmDecision, setConfirmDecision] = useState<"APPROVE" | "REJECT" | null>(null);
  const [tokenPrompt, setTokenPrompt] = useState(false);
  const [tokenInput, setTokenInput] = useState(getOperatorToken());

  const jobId = job?.id || job?.job_id || "";
  const patchHash = patch?.patch_hash || "";
  const canDecide = Boolean(
    jobId &&
    patchHash &&
    patch?.policy_status === "PASSED" &&
    job?.status === "AWAITING_APPROVAL"
  );

  async function executeDecision(decision: "APPROVE" | "REJECT") {
    if (!jobId || !patchHash || busy) return;
    setBusy(decision);
    setMessage("");
    setIsError(false);

    try {
      const res = await api.approval(jobId, patchHash, decision);
      setMessage(
        decision === "APPROVE"
          ? `Approval confirmed by backend (${res.approved_by || "Operator"}). State transitioned to VERIFYING.`
          : `Patch rejection recorded by backend.`
      );
      setIsError(false);
      setConfirmDecision(null);
      onUpdated();
    } catch (e: unknown) {
      const err = e as { message?: string; status?: number; code?: string };
      setIsError(true);
      if (err.status === 401 || err.code === "OPERATOR_AUTH_REQUIRED") {
        setMessage("Operator token required by backend authorization policy. Please enter your operator token below.");
        setTokenPrompt(true);
      } else if (err.code === "PATCH_HASH_MISMATCH") {
        setMessage("Patch hash mismatch: the patch in review is stale or was modified.");
      } else {
        setMessage(err.message || "Decision submission failed.");
      }
    } finally {
      setBusy(null);
    }
  }

  function handleSaveToken(e: React.FormEvent) {
    e.preventDefault();
    setOperatorToken(tokenInput.trim());
    setTokenPrompt(false);
    setMessage("Operator token saved in session memory. You may now proceed with the decision.");
    setIsError(false);
  }

  return (
    <section className="panel approval-panel">
      <div className="panel-heading">
        <div>
          <div className="eyebrow">HUMAN CONTROL</div>
          <h3>Patch decision</h3>
        </div>
        <ShieldCheck size={18} className="text-cyan" />
      </div>

      <div className="approval-status" style={{ padding: "16px 20px 0" }}>
        <span>Current state</span>
        <StatusBadge status={job?.status} />
      </div>

      <div style={{ padding: "12px 20px 0" }}>
        <div className="hash-label">ACTIVE PATCH SHA-256</div>
        <code className="hash-value">{patchHash || "Not available"}</code>
      </div>

      {patch?.policy_details?.reasons && patch.policy_details.reasons.length > 0 && (
        <div style={{ padding: "10px 20px 0" }}>
          <div className="hash-label">POLICY EVALUATION</div>
          <p style={{ fontSize: "11px", color: patch.policy_status === "PASSED" ? "#c9ef72" : "#ff8ca2", margin: "4px 0" }}>
            {patch.policy_details.reasons.join("; ")}
          </p>
        </div>
      )}

      {tokenPrompt && (
        <form onSubmit={handleSaveToken} style={{ margin: "16px 20px", padding: "14px", background: "#171717", border: "1px solid #ffe45e", borderRadius: "12px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#ffe45e", marginBottom: "8px", fontSize: "12px", fontWeight: 700 }}>
            <KeyRound size={16} /> Operator Session Token
          </div>
          <p style={{ fontSize: "11px", color: "#ccc", margin: "0 0 10px", lineHeight: 1.5 }}>
            The backend requires operator authentication (<code>X-Operator-Token</code>). This token is kept in ephemeral browser memory only.
          </p>
          <input
            type="password"
            value={tokenInput}
            onChange={(e) => setTokenInput(e.target.value)}
            placeholder="Enter SENTINEL_OPERATOR_TOKEN..."
            style={{ width: "100%", padding: "10px", background: "#0c0c0c", border: "1px solid #444", borderRadius: "8px", color: "#fff", fontSize: "12px", marginBottom: "10px" }}
            required
          />
          <div style={{ display: "flex", gap: "8px" }}>
            <button type="submit" className="button button-primary" style={{ padding: "8px 14px", fontSize: "11px" }}>
              Save Session Token
            </button>
            <button type="button" className="button button-secondary" style={{ padding: "8px 14px", fontSize: "11px" }} onClick={() => setTokenPrompt(false)}>
              Cancel
            </button>
          </div>
        </form>
      )}

      <div style={{ padding: "14px 20px 0" }}>
        {!canDecide && (
          <div className="notice" style={{ margin: 0 }}>
            <AlertTriangle size={15} />
            <span>
              {job?.status === "VERIFYING"
                ? "Patch has been approved. Verification may now be executed."
                : job?.status === "VERIFIED"
                ? "This patch has already completed verification."
                : job?.status === "USER_REJECTED"
                ? "This patch was rejected by the operator."
                : job?.status === "PLANNING" || job?.status === "FINDING_RECEIVED"
                ? "Awaiting autonomous planner patch proposal..."
                : "Decision controls are disabled for the current job state."}
            </span>
          </div>
        )}

        {message && (
          <div
            className={isError ? "error-banner" : "notice"}
            style={{ marginTop: "12px", marginBottom: 0 }}
          >
            {isError && <AlertTriangle size={15} />}
            <span>{message}</span>
          </div>
        )}

        {confirmDecision && (
          <div style={{ marginTop: "14px", padding: "14px", background: "#1c1418", border: "1px solid #ff4f91", borderRadius: "12px" }}>
            <div style={{ fontSize: "12px", fontWeight: 800, color: "#fff", marginBottom: "6px" }}>
              Confirm {confirmDecision === "APPROVE" ? "Approval" : "Rejection"}
            </div>
            <p style={{ fontSize: "11px", color: "#b9b6ae", margin: "0 0 12px", lineHeight: 1.5 }}>
              Are you sure you want to {confirmDecision.toLowerCase()} patch <code>{patchHash.slice(0, 16)}...</code>? This is an explicit, non-reversible workflow action.
            </p>
            <div style={{ display: "flex", gap: "8px" }}>
              <button
                className={confirmDecision === "APPROVE" ? "button button-primary" : "button button-danger-ghost"}
                disabled={Boolean(busy)}
                onClick={() => void executeDecision(confirmDecision)}
              >
                {busy ? <LoaderCircle size={15} className="spin" /> : <Check size={15} />}
                Confirm {confirmDecision}
              </button>
              <button
                className="button button-secondary"
                disabled={Boolean(busy)}
                onClick={() => setConfirmDecision(null)}
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {!confirmDecision && (
          <div className="approval-actions" style={{ padding: "14px 0" }}>
            <button
              className="button button-danger-ghost"
              disabled={!canDecide || Boolean(busy)}
              onClick={() => setConfirmDecision("REJECT")}
            >
              <X size={15} /> Reject patch
            </button>
            <button
              className="button button-primary"
              disabled={!canDecide || Boolean(busy)}
              onClick={() => setConfirmDecision("APPROVE")}
            >
              <Check size={15} /> Approve patch
            </button>
          </div>
        )}

        <p className="fine-print" style={{ padding: "0 0 16px" }}>
          Approval binds strictly to this exact SHA-256 patch hash. Verification requires a separate explicit execution step.
        </p>
      </div>
    </section>
  );
}
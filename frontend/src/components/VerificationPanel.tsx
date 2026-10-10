import { CheckCircle2, XCircle, Clock3, FlaskConical, AlertTriangle, ShieldAlert } from "lucide-react";
import type { VerificationResult } from "../api/types";
import StatusBadge from "./StatusBadge";

export default function VerificationPanel({
  result,
}: {
  result?: VerificationResult | null;
}) {
  if (!result) {
    return (
      <div className="empty-state">
        <FlaskConical size={20} />
        <div>
          <strong>No verification result returned yet</strong>
          <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#8a877f" }}>
            Verification executes the Developer 3 engine in an isolated container with protected security suites.
          </p>
        </div>
      </div>
    );
  }

  const rawStatus = String(result.status || "");
  const isPassed = rawStatus === "PASSED" || rawStatus === "VERIFIED";
  const isFailed = rawStatus === "FAILED" || rawStatus === "VERIFICATION_FAILED";
  const isExecutionError = rawStatus === "EXECUTION_ERROR" || Boolean(result.execution_error);

  const statusLabel = isPassed
    ? "VERIFIED"
    : isFailed
    ? "VERIFICATION_FAILED"
    : isExecutionError
    ? "EXECUTION_ERROR"
    : rawStatus;

  return (
    <div className="verification-panel">
      <div className="verification-hero">
        <div
          className={`verification-symbol ${
            isPassed ? "green" : isFailed || isExecutionError ? "red" : ""
          }`}
        >
          {isPassed ? (
            <CheckCircle2 size={24} />
          ) : isExecutionError ? (
            <ShieldAlert size={24} />
          ) : (
            <XCircle size={24} />
          )}
        </div>
        <div>
          <div className="eyebrow">BACKEND VERIFICATION RESULT</div>
          <h3>{statusLabel}</h3>
          <StatusBadge status={statusLabel} />
        </div>
      </div>

      <div className="test-grid">
        <div>
          <span>Tests collected</span>
          <strong>{result.tests_collected ?? result.tests_total ?? "—"}</strong>
        </div>
        <div>
          <span>Passed tests</span>
          <strong className="success-text">{result.tests_passed ?? "—"}</strong>
        </div>
        <div>
          <span>Failed tests</span>
          <strong className="danger-text">{result.tests_failed ?? "—"}</strong>
        </div>
        <div>
          <span>Execution duration</span>
          <strong>
            {result.duration_ms != null
              ? result.duration_ms >= 1000
                ? `${(result.duration_ms / 1000).toFixed(2)}s`
                : `${result.duration_ms}ms`
              : "—"}
          </strong>
        </div>
      </div>

      {result.failed_tests && result.failed_tests.length > 0 && (
        <div className="failed-test-list">
          <h4>
            <AlertTriangle size={14} /> Failed tests ({result.failed_tests.length})
          </h4>
          {result.failed_tests.map((testName) => (
            <code key={testName}>{testName}</code>
          ))}
        </div>
      )}

      {result.execution_error && (
        <div className="execution-error">
          <AlertTriangle size={15} />
          <div>
            <strong>Verification infrastructure / execution error</strong>
            <pre>{result.execution_error}</pre>
          </div>
        </div>
      )}

      <div style={{ marginTop: "16px", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "10px" }}>
        {result.test_suite_id && (
          <div>
            <div className="hash-label">TEST SUITE ID</div>
            <code className="hash-value" style={{ fontSize: "11px" }}>{result.test_suite_id}</code>
          </div>
        )}
        {result.run_id && (
          <div>
            <div className="hash-label">VERIFICATION RUN ID</div>
            <code className="hash-value" style={{ fontSize: "11px" }}>{result.run_id}</code>
          </div>
        )}
      </div>

      {result.patch_hash && (
        <div style={{ marginTop: "10px" }}>
          <div className="hash-label">VERIFIED PATCH HASH</div>
          <code className="hash-value">{result.patch_hash}</code>
        </div>
      )}

      {result.source_revision && (
        <div style={{ marginTop: "10px" }}>
          <div className="hash-label">BOUND SOURCE REVISION</div>
          <code className="hash-value">{result.source_revision}</code>
        </div>
      )}

      <p className="fine-print">
        <Clock3 size={12} /> Passing the required verification suite proves that all protected security and functional tests passed in the isolated container.
      </p>
    </div>
  );
}
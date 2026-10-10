import { CheckCircle2, CircleDot, XCircle, Clock3, ShieldCheck, PlayCircle, Scale } from "lucide-react";
import type { WorkflowEvent } from "../api/types";
import StatusBadge from "./StatusBadge";

export default function ActivityTimeline({ events }: { events: WorkflowEvent[] }) {
  if (!events.length) {
    return (
      <div className="empty-state">
        No workflow events recorded by backend yet.
      </div>
    );
  }

  return (
    <div className="timeline">
      {events.map((event, i) => {
        const inner = event.event || {};
        const eventType = event.event_type || inner.event_type || "EVENT";
        const timestamp = event.timestamp || inner.timestamp || event.created_at;
        const patchHash = event.patch_hash || (typeof inner.patch_hash === "string" ? inner.patch_hash : undefined);
        const attempt = event.attempt ?? (typeof inner.attempt === "number" ? inner.attempt : undefined);
        const statusForBadge = typeof inner.to === "string" ? inner.to : typeof inner.status === "string" ? inner.status : eventType;

        const isSuccess =
          eventType === "VERIFICATION_COMPLETED" && (inner.status === "VERIFIED" || inner.status === "PASSED");
        const isFailed =
          ["VERIFICATION_FAILED", "POLICY_REJECTED", "EXECUTION_ERROR", "USER_REJECTED", "RETRY_EXHAUSTED"].includes(
            String(inner.to || inner.status || eventType)
          );

        let icon = <CircleDot size={15} />;
        let iconTone = "blue";

        if (isSuccess) {
          icon = <CheckCircle2 size={15} />;
          iconTone = "green";
        } else if (isFailed) {
          icon = <XCircle size={15} />;
          iconTone = "red";
        } else if (eventType === "APPROVAL_DECIDED") {
          icon = <ShieldCheck size={15} />;
          iconTone = inner.decision === "APPROVE" ? "green" : "red";
        } else if (eventType === "POLICY_EVALUATED") {
          icon = <Scale size={15} />;
          iconTone = inner.outcome === "PASSED" ? "green" : "red";
        } else if (eventType === "VERIFICATION_STARTED") {
          icon = <PlayCircle size={15} />;
          iconTone = "cyan";
        }

        return (
          <div className="timeline-row" key={`${event.id || event.created_at || timestamp}-${i}`}>
            <div className={`timeline-icon ${iconTone === "green" ? "green" : iconTone === "red" ? "red" : ""}`}>
              {icon}
            </div>
            <div className="timeline-content">
              <div className="timeline-title">
                <strong>{eventType.replaceAll("_", " ")}</strong>
                <StatusBadge status={statusForBadge} />
              </div>

              <p>{event.summary || (typeof inner.reason === "string" ? inner.reason : "Workflow event recorded by backend.")}</p>

              {patchHash && (
                <code className="timeline-hash" style={{ fontSize: "10px" }}>
                  {patchHash}
                </code>
              )}

              <div className="timeline-meta">
                <span>
                  <Clock3 size={12} />
                  {timestamp ? new Date(timestamp).toLocaleString() : "Timestamp unavailable"}
                </span>
                {attempt != null && <span>Attempt {attempt}</span>}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
import { useCallback, useEffect, useRef, useState } from "react";
import { api, unwrapList } from "../api/jobs";
import type { Evidence, Job, Patch, VerificationResult, WorkflowEvent } from "../api/types";

function normalizeJob(raw: Job | null): Job | null {
  if (!raw) return null;
  const canonicalId = String(raw.id || raw.job_id || "");
  return {
    ...raw,
    id: canonicalId,
    job_id: canonicalId,
  };
}

function normalizeEvents(rawEvents: unknown): WorkflowEvent[] {
  const list = unwrapList<WorkflowEvent>(rawEvents as WorkflowEvent[] | Record<string, WorkflowEvent[]>, "events");
  return list.map((evt) => {
    const inner = evt.event || {};
    const timestamp = String(inner.timestamp || evt.created_at || "");
    const eventType = String(evt.event_type || inner.event_type || "EVENT");
    let summary = "";

    if (eventType === "STATE_TRANSITION") {
      const from = inner.from ? String(inner.from).replaceAll("_", " ") : "Initial";
      const to = inner.to ? String(inner.to).replaceAll("_", " ") : "";
      summary = `Status changed: ${from} → ${to}`;
    } else if (eventType === "POLICY_EVALUATED") {
      summary = `Policy evaluation: ${inner.outcome || "COMPLETED"}`;
    } else if (eventType === "APPROVAL_DECIDED") {
      summary = `Operator decision: ${inner.decision} by ${inner.approved_by || "Operator"}`;
    } else if (eventType === "VERIFICATION_STARTED") {
      summary = `Docker verification container launched (Attempt ${inner.attempt ?? 0})`;
    } else if (eventType === "VERIFICATION_COMPLETED") {
      summary = `Verification finished with status ${inner.status || "COMPLETED"}`;
    }

    return {
      ...evt,
      timestamp,
      event_type: eventType,
      attempt: typeof inner.attempt === "number" ? inner.attempt : undefined,
      patch_hash: typeof inner.patch_hash === "string" ? inner.patch_hash : undefined,
      summary: summary || (typeof inner.reason === "string" ? inner.reason : undefined),
    };
  });
}

export function useJobDetails(id: string | undefined) {
  const [job, setJob] = useState<Job | null>(null);
  const [patch, setPatch] = useState<Patch | null>(null);
  const [events, setEvents] = useState<WorkflowEvent[]>([]);
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [verificationResult, setVerificationResult] = useState<VerificationResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const isMounted = useRef(true);
  const pollCount = useRef(0);

  const refresh = useCallback(
    async (showLoading = true) => {
      if (!id) {
        setError("No job ID was provided.");
        setLoading(false);
        return;
      }
      if (showLoading) setLoading(true);
      setError("");

      try {
        const canonicalId = id.trim();
        // Load job, events, and patch in parallel
        const [jobData, patchData, eventsData] = await Promise.all([
          api.job(canonicalId),
          api.patch(canonicalId),
          api.events(canonicalId).catch(() => []),
        ]);

        if (!isMounted.current) return;

        const normalizedJob = normalizeJob(jobData);
        setJob(normalizedJob);
        setPatch(patchData);
        setEvents(normalizeEvents(eventsData));

        // Attempt to load evidence to get existing verification run results
        try {
          const evidenceData = await api.evidence(canonicalId);
          if (isMounted.current && evidenceData) {
            setEvidence(evidenceData);
            // If there's a verification run recorded in evidence, pick the latest
            if (evidenceData.verification_runs && evidenceData.verification_runs.length > 0) {
              const latestRun = evidenceData.verification_runs[evidenceData.verification_runs.length - 1];
              if (latestRun?.result) {
                setVerificationResult({
                  ...latestRun.result,
                  job_id: canonicalId,
                  patch_hash: latestRun.patch_hash || latestRun.result.patch_hash || "",
                  status: latestRun.status || latestRun.result.status,
                });
              }
            }
          }
        } catch {
          // Evidence may not yet exist for early-stage jobs; ignore
        }
      } catch (e) {
        if (isMounted.current) {
          setError(e instanceof Error ? e.message : "Unable to load investigation");
        }
      } finally {
        if (isMounted.current && showLoading) {
          setLoading(false);
        }
      }
    },
    [id]
  );

  useEffect(() => {
    isMounted.current = true;
    pollCount.current = 0;
    void refresh(true);
    return () => {
      isMounted.current = false;
    };
  }, [refresh]);

  // Bounded auto-polling if job is currently in an active state (PLANNING, VERIFYING, FINDING_RECEIVED)
  useEffect(() => {
    const isTransient = job && ["FINDING_RECEIVED", "PLANNING", "VERIFYING"].includes(String(job.status));
    if (!isTransient) return;

    const timer = window.setInterval(() => {
      pollCount.current += 1;
      if (pollCount.current > 60) {
        // Stop polling after ~2.5 minutes of continuous polling
        window.clearInterval(timer);
        return;
      }
      void refresh(false);
    }, 2500);

    return () => {
      window.clearInterval(timer);
    };
  }, [job, refresh]);

  return {
    job,
    patch,
    events,
    evidence,
    verificationResult,
    loading,
    error,
    refresh,
    setJob,
    setPatch,
    setVerificationResult,
  };
}
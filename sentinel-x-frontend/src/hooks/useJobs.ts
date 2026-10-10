import { useCallback, useEffect, useRef, useState } from "react";
import { api, unwrapList } from "../api/jobs";
import type { Job } from "../api/types";

function normalizeJobs(rawJobs: unknown): Job[] {
  const list = unwrapList<Job>(rawJobs as Job[] | Record<string, Job[]>, "jobs");
  return list.map((j) => {
    const canonicalId = String(j.id || j.job_id || "");
    return {
      ...j,
      id: canonicalId,
      job_id: canonicalId,
    };
  });
}

export function useJobs(pollActive = true) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const isMounted = useRef(true);

  const refresh = useCallback(async (showLoading = true) => {
    if (showLoading) setLoading(true);
    setError("");
    try {
      const data = await api.jobs();
      if (isMounted.current) {
        setJobs(normalizeJobs(data));
      }
    } catch (e) {
      if (isMounted.current) {
        setError(e instanceof Error ? e.message : "Unable to load jobs from backend API");
      }
    } finally {
      if (isMounted.current && showLoading) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    isMounted.current = true;
    void refresh(true);
    return () => {
      isMounted.current = false;
    };
  }, [refresh]);

  // Bounded polling if any job is currently in an active state
  useEffect(() => {
    if (!pollActive) return;
    const hasActiveJob = jobs.some((j) =>
      ["FINDING_RECEIVED", "PLANNING", "VERIFYING"].includes(String(j.status))
    );
    if (!hasActiveJob) return;

    const timer = window.setInterval(() => {
      void refresh(false);
    }, 2500);

    return () => {
      window.clearInterval(timer);
    };
  }, [jobs, pollActive, refresh]);

  return { jobs, loading, error, refresh };
}
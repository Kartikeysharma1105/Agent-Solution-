import { request, ApiError } from "./client";
import type {
  ApprovalResponse,
  Evidence,
  FindingRequest,
  FindingResponse,
  HealthResponse,
  Job,
  Patch,
  ReadyResponse,
  VerificationResult,
  WorkflowEvent,
} from "./types";

export const api = {
  health: () => request<HealthResponse>("/health"),

  ready: () => request<ReadyResponse>("/ready"),

  createFinding: (payload: FindingRequest) =>
    request<FindingResponse>("/api/findings", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  jobs: (limit = 100, offset = 0) =>
    request<Job[]>(`/api/jobs?limit=${Math.min(Math.max(1, limit), 100)}&offset=${Math.max(0, offset)}`),

  job: (id: string) =>
    request<Job>(`/api/jobs/${encodeURIComponent(id.trim())}`),

  patch: async (id: string): Promise<Patch | null> => {
    try {
      return await request<Patch>(`/api/jobs/${encodeURIComponent(id.trim())}/patch`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        return null;
      }
      throw err;
    }
  },

  approval: (id: string, patch_hash: string, decision: "APPROVE" | "REJECT") =>
    request<ApprovalResponse>(`/api/jobs/${encodeURIComponent(id.trim())}/approval`, {
      method: "POST",
      body: JSON.stringify({ patch_hash, decision }),
    }),

  verify: (id: string) =>
    request<VerificationResult>(`/api/jobs/${encodeURIComponent(id.trim())}/verify`, {
      method: "POST",
    }),

  evidence: (id: string) =>
    request<Evidence>(`/api/jobs/${encodeURIComponent(id.trim())}/evidence`),

  events: (id: string) =>
    request<WorkflowEvent[]>(`/api/jobs/${encodeURIComponent(id.trim())}/events`),
};

export function unwrapList<T>(data: T[] | Record<string, T[]> | null | undefined, key: string): T[] {
  if (!data) return [];
  if (Array.isArray(data)) return data;
  const list = data[key];
  return Array.isArray(list) ? list : [];
}
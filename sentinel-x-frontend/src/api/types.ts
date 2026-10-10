export type WorkflowStatus =
  | "FINDING_RECEIVED"
  | "PLANNING"
  | "AWAITING_APPROVAL"
  | "VERIFYING"
  | "VERIFICATION_FAILED"
  | "VERIFIED"
  | "POLICY_REJECTED"
  | "USER_REJECTED"
  | "RETRY_EXHAUSTED"
  | "EXECUTION_ERROR"
  | "UNKNOWN";

export type FindingSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface Finding {
  id: string;
  type: string;
  severity: FindingSeverity | string;
  file_path: string;
  description: string;
  status?: WorkflowStatus | string;
  created_at?: string;
}

export interface FindingRequest {
  target_app_id: string;
  finding: Finding;
}

export interface FindingResponse {
  job_id: string;
  status: WorkflowStatus | string;
}

export interface Job {
  id: string;
  job_id?: string;
  target_app_id: string;
  status: WorkflowStatus | string;
  attempt: number;
  created_at: string;
  updated_at: string;
  version: number;
  finding?: Finding;
  finding_id?: string;
  summary?: string;
  root_cause?: string;
  analysis?: string;
  verification?: VerificationResult;
  [key: string]: unknown;
}

export interface PatchPolicyDetails {
  reasons: string[];
}

export interface Patch {
  id: string;
  job_id: string;
  attempt: number;
  root_cause: string;
  explanation: string;
  patch_format: "unified_diff" | string;
  patch_text: string;
  files_changed: string[];
  patch_hash: string;
  policy_status: "PASSED" | "REJECTED" | string;
  policy_details?: PatchPolicyDetails;
  created_at: string;
  // Legacy / convenience compatibility
  diff?: string;
  approval_status?: string;
  status?: WorkflowStatus | string;
}

export interface ApprovalRequest {
  patch_hash: string;
  decision: "APPROVE" | "REJECT";
}

export interface ApprovalResponse {
  approval_id: string;
  job_id: string;
  patch_id: string;
  attempt: number;
  patch_hash: string;
  decision: "APPROVE" | "REJECT";
  approved_by: string;
  identity_kind: string;
  source_revision: string;
  created_at: string;
  binding?: {
    approval_id: string;
    target_app_id: string;
    source_revision: string;
    identity_kind: string;
  };
}

export interface VerificationResult {
  job_id: string;
  patch_hash: string;
  status: "PASSED" | "FAILED" | "EXECUTION_ERROR" | WorkflowStatus | string;
  tests_total?: number;
  tests_passed?: number;
  tests_failed?: number;
  failed_tests?: string[];
  duration_ms?: number;
  execution_error?: string | null;
  test_suite_id?: string | null;
  tests_collected?: number | null;
  collection_complete?: boolean | null;
  execution_completed?: boolean | null;
  run_id?: string | null;
  source_revision?: string | null;
  verification_profile?: string | null;
}

export interface WorkflowEventInner {
  correlation_id?: string;
  job_id?: string;
  event_type?: string;
  timestamp?: string;
  from?: string | null;
  to?: string;
  patch_id?: string;
  patch_hash?: string;
  attempt?: number;
  decision?: string;
  approved_by?: string;
  status?: string;
  run_id?: string;
  reasons?: string[];
  reason?: string;
  outcome?: string;
  [key: string]: unknown;
}

export interface WorkflowEvent {
  id: string;
  job_id: string;
  event_type: string;
  event_json?: string;
  created_at: string;
  event?: WorkflowEventInner;
  // Flattened convenience accessors
  timestamp?: string;
  attempt?: number;
  patch_hash?: string;
  summary?: string;
  details?: unknown;
}

export interface TargetBinding {
  job_id: string;
  source_revision: string;
  verification_profile: string;
}

export interface VerificationRunAttestation {
  run_id: string;
  attempt: number;
  source_revision: string;
  verification_profile: string;
  test_suite_id: string;
  evidence_digest: string;
}

export interface VerificationRunRecord {
  id: string;
  job_id: string;
  patch_id: string;
  patch_hash: string;
  status: string;
  created_at: string;
  completed_at?: string | null;
  result: VerificationResult;
  attestation?: VerificationRunAttestation | null;
  attestation_integrity?: "VALID" | "MISMATCH" | string;
}

export interface Evidence {
  job_id: string;
  finding: Finding;
  target_app_id: string;
  target_binding?: TargetBinding | null;
  source_revision_current: boolean;
  status: WorkflowStatus | string;
  patch_attempts: (Patch & { hash_integrity?: string })[];
  approvals: ApprovalResponse[];
  verification_runs: VerificationRunRecord[];
  failure_history: VerificationRunRecord[];
  integrity_issues: string[];
  conclusion: "VERIFIED" | "NOT_VERIFIED" | string;
  limitations: string[];
}

export interface HealthResponse {
  status: string;
  service?: string;
}

export interface ReadyResponse {
  status: "ready" | "not_ready" | string;
}

export interface ApiErrorShape {
  detail?: string;
  message?: string;
  error?: string;
  code?: string;
  errors?: Array<{ loc: string[]; type: string }>;
}

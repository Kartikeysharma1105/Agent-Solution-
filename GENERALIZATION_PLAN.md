# Generalized security analysis upgrade plan

## Current system

- Backend routes: authentication (`register`, `login`, `me`, `logout`), owned projects (`create`, ZIP upload, list, status, safe Python file view, delete), finding submission, jobs, patch, approval, verification, events, evidence, health/readiness, observability status.
- Dashboard routes: Overview, Projects, Findings, Investigation/job details, Verification redirect, Activity, Evidence. The Overview counts are derived from jobs, not persisted scan findings. Projects has a real upload and file browser but creates a hard-coded BOLA finding; general scans do not exist.
- The server-owned BOLA policy allows one path (`app/access.py`), one target manifest, and one Docker protected suite (eight tests). Keep this as the independently verified legacy adapter. Do not relabel it as universal verification.
- Ollama/Qwen is the existing local planner. The external Gemini integration must be separate, opt-in per source transmission, and must not affect the existing verified workflow.

## Incremental implementation

1. Preserve the BOLA path and add additive database migrations for scans, structured findings, source-sharing consent, and generalized proposal/evidence records.
2. Extend safe ingestion to single source files and archives with bounded extraction and framework classification. Initial ingestion never executes uploaded code.
3. Add deterministic static analyzers for explicit Python and JS/TS patterns. Persist potential findings and distinguish unsupported from clean scans; redact secret values in evidence.
4. Add an official `google-genai` provider behind an internal interface. Require an exact consent preview and authorization before transmitting bounded source snippets. Confirm model availability through the API when configured; fail closed on missing key, timeout, quota, or malformed output.
5. Add scoped proposal, exact-hash approval, and verification adapters. Retain Docker BOLA verification; report `INCONCLUSIVE` or `UNSUPPORTED` when independent applicable checks are unavailable.
6. Connect each dashboard route to owned projects, scans, findings, proposals, and evidence. Preserve honest loading/empty/error states.
7. Run unit, integration, sandbox, browser, and regression tests. Document supported coverage and limitations.

## Risks and controls

- Source disclosure: no provider request at upload or scan time; explicit per-project/per-file consent and a bounded transmission preview are required.
- False positives: static patterns are `POTENTIAL`; AI review cannot promote a finding to independently confirmed by itself.
- Verification overclaim: only trusted, applicable checks can yield `VERIFIED`; generic syntax-only checks remain `INCONCLUSIVE`.
- Archive attacks: preserve existing traversal/symlink/bomb checks and extend them to new formats rather than using generic archive extraction.
- Existing evidence and state: migrations are additive; BOLA manifests, approvals, telemetry allowlist, and stored records remain intact.
- External provider unavailable: a key is loaded only into the live server environment. Models API access was confirmed, but synthetic structured generation succeeded using the 3.5 Flash-Lite default. Higher-capacity models returned HTTP 503 high demand; source-sharing browser review remains unverified.

## Current completion state

Steps 1–4, a constrained Python patch/approval/static-check path from step 5, and dashboard wiring from step 6 are implemented. General runtime verification adapters, broader static/dependency scanning and comprehensive frontend automated coverage remain incomplete; see `GENERALIZED_UPGRADE_REPORT.md`.

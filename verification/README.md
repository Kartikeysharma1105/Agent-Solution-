# SENTINEL-X — Independent Verification Engine (Developer 3)

**Tagline**: *"Don't just generate a fix. Prove that it works."*  
**Team**: BeyondSight — neatHack 2026  
**Ownership Boundary**: `verification/` only

---

## 1. Overview & Architecture

Developer 3 implements Layer 5 (**Restricted Verification Subsystem**). It provides an independent, non-LLM, deterministic verification engine that tests candidate AI patches against an intentionally vulnerable Broken Object-Level Authorization (BOLA) lab application within disposable, unprivileged Docker containers.

```
FastAPI Orchestrator (Dev 1)
   │
   ▼ VerificationRequest (job_id, target_app_id, patch_text, patch_hash, approval_id)
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ verification.runner.verify_patch()                                                     │
│                                                                                        │
│ 1. PatchValidator: Validates unified diff syntax, SHA-256 hash, size & scope          │
│ 2. ApprovalVerifier: Validates backend approval token before container creation        │
│ 3. Workspace Isolation: Creates ephemeral copy of clean baseline                       │
│ 4. Restricted Docker Sandbox: Runs pytest against protected tests in isolation         │
│    ├── Flags: --network none, --cap-drop ALL, --security-opt no-new-privileges        │
│    ├── Resources: --memory 512m, --cpus 1.0, --pids-limit 64                         │
│    └── Mounts: Protected tests mounted strictly READ-ONLY (:ro)                        │
│ 5. TestResultEvaluator: Deterministically evaluates report and emits structured verdict │
└────────────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼ VerificationResult (status, tests_total, tests_passed, tests_failed, failed_tests, duration_ms)
FastAPI State Machine (Dev 1) / Reflection Module (Dev 4)
```

---

## 2. Directory Structure

```text
verification/
├── __init__.py                  # Public exports: verify_patch, VerificationRequest, VerificationResult
├── contracts.py                 # Pydantic/Dataclass contracts & Status enums
├── runner.py                    # Ephemeral Docker sandbox runner controller
├── evaluator.py                 # Independent deterministic result evaluator
├── patch_validator.py           # Patch safety, scope, path traversal & hash binding
├── Dockerfile                   # Disposable lab container specification
├── requirements.txt             # Python dependencies (pytest)
├── README.md                    # Module documentation & integration guide
├── lab/
│   └── app/
│       ├── __init__.py
│       ├── access.py            # Target BOLA authorization logic (get_document)
│       └── sample_data.py       # Deterministic multi-tenant document store
├── protected_tests/
│   ├── __init__.py
│   ├── conftest.py              # Structured JSON report hook
│   ├── test_security.py         # Immutable adversarial security tests (BOLA exploits)
│   └── test_functional.py       # Immutable functional & regression tests
├── fixtures/
│   ├── incomplete_patch.diff    # Superficial fix fixture (fails security tests)
│   └── correct_patch.diff       # Comprehensive fix fixture (passes all 8 tests)
└── tests/
    ├── __init__.py
    ├── test_patch_validator.py  # Unit tests for patch validation & security rules
    ├── test_evaluator.py        # Unit tests for independent result evaluation
    └── test_runner.py           # Live Docker integration tests for all patch scenarios
```

---

## 3. Integration Contract for Dev 1 (FastAPI Orchestrator)

Dev 1 invokes `verify_patch` directly:

```python
from verification import (
    VerificationRequest,
    VerificationResult,
    VerificationStatus,
    verify_patch,
)

# Example backend approval verifier callback:
def check_backend_approval(patch_hash: str, approval_id: str) -> bool:
    # Verifies that approval_id matches backend database/HMAC signature
    return approval_id == f"approved-{patch_hash[:8]}"

request = VerificationRequest(
    job_id="job-2026-001",
    target_app_id="bola-demo-v1",
    patch_text=candidate_patch_diff,
    patch_hash=computed_sha256_hash,
    approval_id="approved-d3b07384",
    timeout_seconds=30,
)

result: VerificationResult = await verify_patch(request, check_backend_approval)

# Response schema:
# {
#   "job_id": "job-2026-001",
#   "patch_hash": "...",
#   "status": "VERIFIED",       # VERIFIED | VERIFICATION_FAILED | EXECUTION_ERROR | POLICY_REJECTED
#   "tests_total": 8,
#   "tests_passed": 8,
#   "tests_failed": 0,
#   "failed_tests": [],
#   "duration_ms": 1420,
#   "execution_error": null
# }
```

---

## 4. Running Validation Tests

### Run all unit and live Docker integration tests:
```bash
python3 -m pytest verification/tests/ -v
```

### Run protected tests directly against baseline vulnerable app:
```bash
python3 -m pytest verification/protected_tests/ -v
```
*(Expected outcome: 4 functional tests pass, 4 security tests fail with BOLA access errors).*

### Rebuild Docker verification lab image:
```bash
docker build -t sentinel-verification-lab:latest -f verification/Dockerfile verification/
```

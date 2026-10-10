# SENTINEL-X Restricted Verification Module (Layer 5)

## Overview
This module implements the **Restricted Verification** subsystem (Layer 5) of SENTINEL-X, operating as an autonomous, deterministic gatekeeper for evaluating AI-generated candidate security remediation patches.

## Architecture

```
Layer 2: FastAPI Orchestrator (Dev 1)
   │
   ▼ VerificationRequest (finding_id, patch_content, expected_hash, approval_token)
┌────────────────────────────────────────────────────────────────────────┐
│ verification.service: verify_patch()                                   │
│                                                                        │
│ 1. PatchValidator: Exact byte verification & SHA-256 hash binding     │
│ 2. PolicyEngine: Static safety, path traversal & scope validation      │
│ 3. ApprovalVerifier: Cryptographic / token Human Gate verification     │
│ 4. DockerSandboxRunner: Ephemeral disposable Docker container          │
│    ├── Restricted isolation (--network none, --cap-drop ALL, limits)   │
│    ├── Read-Only test suite mount (:ro)                                │
│    └── Applies patch to isolated ephemeral target copy               │
│ 5. TestResultEvaluator: Independent deterministic test judge           │
└────────────────────────────────────────────────────────────────────────┘
   │
   ▼ VerificationResult (VERIFIED / REJECTED_* / ERROR_* + failure_reflection_data)
Layer 4 / Layer 3: Reflection Module (Dev 4)
```

## Contracts & Interfaces

### VerificationRequest
```python
from verification.contracts import VerificationRequest

request = VerificationRequest(
    finding_id="VULN-2026-BOLA-01",
    patch_content="--- a/app/main.py\n+++ b/app/main.py\n...",
    expected_patch_hash="<sha256_of_patch_content>",
    approval_token="<backend_approval_token>",
    timeout_seconds=60,
)
```

### ApprovalVerifier Callable
Dev 1 supplies a callable verifying whether the human approval gate approved the specific patch hash:
```python
ApprovalVerifier = Callable[[str, str], bool]  # (patch_hash: str, approval_token: str) -> bool
```
Supported implementations in `verification.approval`:
- `SimpleTokenApprovalVerifier`: In-memory token lookup.
- `HmacApprovalVerifier`: HMAC-SHA256 signature verification.
- Any standard synchronous or asynchronous callable.

### VerificationResult
Returns a structured result with:
- `verdict`: `VERIFIED`, `REJECTED_UNAPPROVED`, `REJECTED_POLICY_VIOLATION`, `REJECTED_MALFORMED_PATCH`, `REJECTED_VULNERABLE`, `REJECTED_REGRESSION`, `ERROR_TIMEOUT`, `ERROR_NO_TESTS_COLLECTED`, `ERROR_MALFORMED_REPORT`, or `ERROR_RUNNER`.
- `is_verified`: `bool` (Strictly `True` iff all security and regression tests execute and pass).
- `failure_reflection_data`: Structured error diagnostics passed to Dev 4's reflection LLM.

## Running Tests
Using the virtual environment:
```bash
/home/rudra-paliwal/.venv-sentinel/bin/pytest verification/tests/ -v
```

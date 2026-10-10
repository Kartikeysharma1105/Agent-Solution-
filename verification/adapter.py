"""Backend Integration Adapter for SENTINEL-X Verification (Developer 3 - Layer 5).

Provides a compatibility entry point conforming to Dev 1's FastAPI backend:
Configured via: SENTINEL_VERIFIER_CALLABLE=verification.adapter:verify_backend_patch

Bridge Features:
1. Accepts Dev 1's backend VerificationRequest (or dict/dataclass).
2. Adapts backend 4-arg approval callback: approval_verifier(job_id, patch_id, patch_hash, approval_id).
3. Enforces pre-execution approval gate checks and fail-closed security.
4. Executes the restricted Docker sandbox verification pipeline.
5. Translates Developer 3 verdicts (VERIFIED, VERIFICATION_FAILED, EXECUTION_ERROR, POLICY_REJECTED)
   into backend-compatible VerificationResult schemas (PASSED, FAILED, EXECUTION_ERROR).
6. Ensures strict consistency for tests_total, tests_passed, tests_failed, and execution_error.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import inspect
from typing import Any, Callable, Dict, List, Optional, Union

from .contracts import (
    VerificationRequest as InternalVerificationRequest,
    VerificationResult as InternalVerificationResult,
    VerificationStatus,
)
from .patch_validator import PatchValidator, PatchValidationError
from .runner import verify_patch


def _extract_field(obj: Any, field_name: str, default: Any = "") -> Any:
    """Extract a field from either an object attribute or a dict key."""
    if isinstance(obj, dict):
        return obj.get(field_name, default)
    return getattr(obj, field_name, default)


def _adapt_approval_verifier(
    approval_verifier: Any,
    job_id: str,
    patch_id: str,
    patch_hash: str,
    approval_id: str,
) -> Callable[[str, str], bool]:
    """Adapt backend 4-arg approval callback or 2-arg callback into a 2-arg callable."""
    def adapted_callback(p_hash: str, a_id: str) -> bool:
        if not callable(approval_verifier):
            return False
        try:
            sig = inspect.signature(approval_verifier)
            param_count = len(sig.parameters)
            if param_count == 4:
                return bool(approval_verifier(job_id, patch_id, patch_hash or p_hash, a_id or approval_id))
            elif param_count == 2:
                return bool(approval_verifier(p_hash, a_id))
            else:
                # Fallback: attempt 4-arg then 2-arg
                try:
                    return bool(approval_verifier(job_id, patch_id, patch_hash or p_hash, a_id or approval_id))
                except TypeError:
                    return bool(approval_verifier(p_hash, a_id))
        except Exception:
            try:
                return bool(approval_verifier(job_id, patch_id, patch_hash or p_hash, a_id or approval_id))
            except TypeError:
                try:
                    return bool(approval_verifier(p_hash, a_id))
                except Exception:
                    return False

    return adapted_callback


def _run_async(coro):
    """Run an async coroutine synchronously, handling existing event loops safely."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(lambda: asyncio.run(coro))
            return future.result()
    else:
        return asyncio.run(coro)


def verify_backend_patch(
    request: Any,
    approval_verifier: Any,
    docker_image: str = "sentinel-verification-lab:latest",
) -> Dict[str, Any]:
    """Primary integration callable for Dev 1's ConfiguredVerificationAdapter.

    Expected signature: verify_backend_patch(request, approval_verifier) -> dict | VerificationResult
    """
    job_id = str(_extract_field(request, "job_id", "") or "job-unknown")
    target_app_id = str(_extract_field(request, "target_app_id", "bola-demo-v1"))
    patch_id = str(_extract_field(request, "patch_id", "") or "patch-unknown")
    patch_text = str(_extract_field(request, "patch_text", ""))
    patch_hash = str(_extract_field(request, "patch_hash", ""))
    approval_id = str(_extract_field(request, "approval_id", "") or "approval-unknown")

    # If patch_hash is empty, compute it
    if not patch_hash and patch_text:
        patch_hash = "sha256:" + PatchValidator.compute_hash(patch_text)

    # 1. Pre-execution backend approval reference validation (Fail-closed)
    adapter_callback = _adapt_approval_verifier(
        approval_verifier, job_id, patch_id, patch_hash, approval_id
    )
    if not adapter_callback(patch_hash, approval_id):
        return {
            "status": "EXECUTION_ERROR",
            "tests_total": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "failed_tests": [],
            "duration_ms": 0,
            "execution_error": "Approval validation failed: unverified or invalid approval reference.",
        }

    # 2. Pre-execution target app validation
    if target_app_id != "bola-demo-v1":
        return {
            "status": "EXECUTION_ERROR",
            "tests_total": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "failed_tests": [],
            "duration_ms": 0,
            "execution_error": f"Policy rejected: unauthorized target_app_id '{target_app_id}'.",
        }

    # 3. Pre-execution patch syntax and policy check
    try:
        PatchValidator.validate_patch(patch_text, patch_hash)
    except PatchValidationError as exc:
        return {
            "status": "EXECUTION_ERROR",
            "tests_total": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "failed_tests": [],
            "duration_ms": 0,
            "execution_error": f"Policy rejected: {exc}",
        }

    # 4. Construct internal request and execute verification in Docker sandbox
    internal_req = InternalVerificationRequest(
        job_id=job_id,
        target_app_id=target_app_id,
        patch_text=patch_text,
        patch_hash=patch_hash,
        approval_id=approval_id,
        timeout_seconds=30,
    )

    internal_res: InternalVerificationResult = _run_async(
        verify_patch(internal_req, adapter_callback, docker_image=docker_image)
    )

    # 5. Translate verification status into backend-compatible schema
    raw_status = internal_res.status
    tests_total = max(0, int(internal_res.tests_total))
    tests_passed = max(0, int(internal_res.tests_passed))
    tests_failed = max(0, int(internal_res.tests_failed))
    failed_tests = list(internal_res.failed_tests or [])
    duration_ms = max(0, int(internal_res.duration_ms))
    execution_error = internal_res.execution_error

    if raw_status == VerificationStatus.VERIFIED.value:
        backend_status = "PASSED"
        backend_error = None
        # Ensure count consistency for backend validation
        if tests_total == 0 or tests_failed > 0:
            backend_status = "EXECUTION_ERROR"
            backend_error = "Passing verdict requires verified test execution with zero failures."
            tests_total = 0
            tests_passed = 0
            tests_failed = 0
            failed_tests = []
    elif raw_status == VerificationStatus.VERIFICATION_FAILED.value:
        backend_status = "FAILED"
        backend_error = execution_error
        # Ensure at least 1 failed test is reported if status is FAILED
        if tests_failed == 0:
            tests_failed = max(1, tests_total)
            if tests_total < tests_failed:
                tests_total = tests_failed
            if not failed_tests:
                failed_tests = ["verification_test_failure"]
    else:
        # EXECUTION_ERROR or POLICY_REJECTED
        backend_status = "EXECUTION_ERROR"
        backend_error = execution_error or f"Verification error: {raw_status}"
        tests_total = 0
        tests_passed = 0
        tests_failed = 0
        failed_tests = []

    return {
        "status": backend_status,
        "tests_total": tests_total,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "failed_tests": failed_tests,
        "duration_ms": duration_ms,
        "execution_error": backend_error,
    }

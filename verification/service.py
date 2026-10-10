"""Main verification service entrypoint (Layer 5).

Orchestrates:
1. Exact patch byte & SHA-256 hash binding.
2. Target path extraction & deterministic policy checks.
3. Backend-supplied human approval verification.
4. Ephemeral Docker sandbox execution.
5. Independent test result evaluation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .approval import ApprovalVerifier, execute_approval_verifier
from .contracts import (
    Verdict,
    VerificationRequest,
    VerificationResult,
)
from .patch_validator import PatchValidator, PatchValidationError
from .policy import PolicyEngine, PolicyViolationError

from .runner.docker_sandbox import DockerSandboxRunner

logger = logging.getLogger("sentinel_verification")


async def verify_patch(
    request: VerificationRequest,
    approval_verifier: ApprovalVerifier,
    policy_engine: Optional[PolicyEngine] = None,
    sandbox_runner: Optional[Any] = None,
) -> VerificationResult:
    """Execute end-to-end patch verification.

    Args:
        request: VerificationRequest containing patch diff, expected hash, approval token, etc.
        approval_verifier: Callable checking whether this patch hash was approved by human gate.
        policy_engine: Optional customized PolicyEngine instance.
        sandbox_runner: Optional custom sandbox runner (defaults to DockerSandboxRunner).

    Returns:
        VerificationResult with deterministic verdict and structured diagnostics.
    """
    engine = policy_engine or PolicyEngine()
    patch_hash = PatchValidator.compute_hash(request.patch_content)

    # 1. Exact patch byte hash binding
    if not PatchValidator.verify_hash(request.patch_content, request.expected_patch_hash):
        return VerificationResult(
            finding_id=request.finding_id,
            verdict=Verdict.REJECTED_MALFORMED_PATCH,
            is_verified=False,
            patch_hash=patch_hash,
            raw_runner_output=f"Patch hash mismatch: computed '{patch_hash}' != expected '{request.expected_patch_hash}'",
            failure_reflection_data={
                "error_type": "HASH_MISMATCH",
                "computed_hash": patch_hash,
                "expected_hash": request.expected_patch_hash,
            },
        )

    # 2. Patch syntax and target path extraction
    try:
        modified_paths = PatchValidator.extract_target_paths(request.patch_content)
    except PatchValidationError as exc:
        return VerificationResult(
            finding_id=request.finding_id,
            verdict=Verdict.REJECTED_MALFORMED_PATCH,
            is_verified=False,
            patch_hash=patch_hash,
            raw_runner_output=str(exc),
            failure_reflection_data={"error_type": "SYNTAX_ERROR", "details": str(exc)},
        )

    # 3. Deterministic Policy Engine evaluation
    try:
        engine.validate(modified_paths, request.patch_content)
    except PolicyViolationError as exc:
        return VerificationResult(
            finding_id=request.finding_id,
            verdict=Verdict.REJECTED_POLICY_VIOLATION,
            is_verified=False,
            patch_hash=patch_hash,
            raw_runner_output=str(exc),
            failure_reflection_data={"error_type": "POLICY_VIOLATION", "details": str(exc)},
        )

    # 4. Human Approval Gate verification
    is_approved = await execute_approval_verifier(approval_verifier, patch_hash, request.approval_token)
    if not is_approved:
        return VerificationResult(
            finding_id=request.finding_id,
            verdict=Verdict.REJECTED_UNAPPROVED,
            is_verified=False,
            patch_hash=patch_hash,
            raw_runner_output="Patch rejected: human approval signature or token invalid.",
            failure_reflection_data={"error_type": "UNAPPROVED_PATCH", "details": "Approval verification failed"},
        )

    # 5. Sandbox execution (delegated to DockerSandboxRunner by default)
    runner = sandbox_runner or DockerSandboxRunner()
    return await runner.run(request, patch_hash, modified_paths)


"""Independent Test Result Evaluator for SENTINEL-X Verification (Layer 5).

Strictly evaluates test runner output without LLM subjectivity:
- VERIFIED is returned ONLY if all required tests execute and pass.
- Missing test collections, timeouts, and report errors produce EXECUTION_ERROR.
- Policy and approval failures produce POLICY_REJECTED.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .contracts import VerificationResult, VerificationStatus


class TestResultEvaluator:
    """Deterministic evaluator for verification test reports."""

    # Expected minimum test count for full coverage
    MIN_REQUIRED_TESTS = 8

    @classmethod
    def evaluate(
        cls,
        job_id: str,
        patch_hash: str,
        exit_code: int,
        raw_output: str,
        report_json_str: Optional[str] = None,
        duration_ms: int = 0,
        timed_out: bool = False,
        runner_error: Optional[str] = None,
    ) -> VerificationResult:
        """Evaluate runner outputs and produce a structured VerificationResult."""

        # 1. Timeout Check
        if timed_out:
            return VerificationResult(
                job_id=job_id,
                patch_hash=patch_hash,
                status=VerificationStatus.EXECUTION_ERROR.value,
                duration_ms=duration_ms,
                execution_error="Execution timed out in sandbox environment.",
            )

        # 2. Runner Crash Check
        if runner_error:
            return VerificationResult(
                job_id=job_id,
                patch_hash=patch_hash,
                status=VerificationStatus.EXECUTION_ERROR.value,
                duration_ms=duration_ms,
                execution_error=f"Runner error: {runner_error}",
            )

        # 3. Report Missing / Malformed Check
        if not report_json_str or not report_json_str.strip():
            err_msg = f"Test report missing or runner exited prematurely with code {exit_code}."
            return VerificationResult(
                job_id=job_id,
                patch_hash=patch_hash,
                status=VerificationStatus.EXECUTION_ERROR.value,
                duration_ms=duration_ms,
                execution_error=err_msg,
            )

        try:
            report_data = json.loads(report_json_str)
        except json.JSONDecodeError as exc:
            return VerificationResult(
                job_id=job_id,
                patch_hash=patch_hash,
                status=VerificationStatus.EXECUTION_ERROR.value,
                duration_ms=duration_ms,
                execution_error=f"Malformed report JSON: {exc}",
            )

        summary = report_data.get("summary", {})
        tests_data = report_data.get("tests", [])

        total = summary.get("total", len(tests_data))
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        errored = summary.get("error", 0)

        failed_tests = report_data.get("failed_tests", [])
        if not failed_tests and (failed > 0 or errored > 0):
            for t in tests_data:
                if t.get("outcome") in ("failed", "error"):
                    failed_tests.append(t.get("nodeid", "unknown_test"))

        # 4. Zero Tests Collected Check
        if total == 0 or total < cls.MIN_REQUIRED_TESTS:
            return VerificationResult(
                job_id=job_id,
                patch_hash=patch_hash,
                status=VerificationStatus.EXECUTION_ERROR.value,
                tests_total=total,
                tests_passed=passed,
                tests_failed=failed,
                failed_tests=failed_tests,
                duration_ms=duration_ms,
                execution_error=f"Incomplete test execution: collected {total} tests (minimum {cls.MIN_REQUIRED_TESTS} required).",
            )

        # 5. Failures Detected Check
        if failed > 0 or errored > 0:
            return VerificationResult(
                job_id=job_id,
                patch_hash=patch_hash,
                status=VerificationStatus.VERIFICATION_FAILED.value,
                tests_total=total,
                tests_passed=passed,
                tests_failed=failed + errored,
                failed_tests=failed_tests,
                duration_ms=duration_ms,
                execution_error=None,
            )

        # 6. All Tests Passed Strictly
        return VerificationResult(
            job_id=job_id,
            patch_hash=patch_hash,
            status=VerificationStatus.VERIFIED.value,
            tests_total=total,
            tests_passed=passed,
            tests_failed=0,
            failed_tests=[],
            duration_ms=duration_ms,
            execution_error=None,
        )

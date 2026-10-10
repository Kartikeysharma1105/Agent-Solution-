"""Independent Test Result Evaluator for Layer 5 Verification.

Strict evaluation guarantees:
1. Runner failures, timeouts, and report parsing errors are treated as ERRORS, never success.
2. Missing or zero test collection is an ERROR, never success.
3. VERIFIED is returned ONLY when all required security and functional tests actually execute and pass.
4. Generates structured diagnostic payloads for the Dev 4 Failure Reflection Module.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from verification.contracts import (
    Verdict,
    TestCaseStatus,
    TestCaseResult,
    VerificationResult,
)


class TestResultEvaluator:
    """Evaluates test runner execution reports deterministically without LLMs."""

    # Required categories that must execute for a patch to be considered VERIFIED
    REQUIRED_CATEGORIES = {"security", "regression"}

    @classmethod
    def evaluate(
        cls,
        finding_id: str,
        patch_hash: str,
        exit_code: int,
        raw_output: str,
        report_json_str: Optional[str] = None,
        timed_out: bool = False,
        runner_error: Optional[str] = None,
    ) -> VerificationResult:
        """Evaluate runner outputs and produce a structured VerificationResult."""

        # 1. Timeout Check
        if timed_out:
            return VerificationResult(
                finding_id=finding_id,
                verdict=Verdict.ERROR_TIMEOUT,
                is_verified=False,
                patch_hash=patch_hash,
                raw_runner_output=raw_output,
                failure_reflection_data={
                    "error_type": "TIMEOUT",
                    "message": "Execution in sandbox exceeded maximum allowed time.",
                },
            )

        # 2. General Runner Error Check
        if runner_error:
            return VerificationResult(
                finding_id=finding_id,
                verdict=Verdict.ERROR_RUNNER,
                is_verified=False,
                patch_hash=patch_hash,
                raw_runner_output=f"{raw_output}\nRunner Error: {runner_error}",
                failure_reflection_data={
                    "error_type": "RUNNER_ERROR",
                    "details": runner_error,
                },
            )

        # 3. Report presence & parsing
        if not report_json_str or not report_json_str.strip():
            # If no report JSON and non-zero exit code
            verdict = Verdict.ERROR_RUNNER if exit_code != 0 else Verdict.ERROR_MALFORMED_REPORT
            return VerificationResult(
                finding_id=finding_id,
                verdict=verdict,
                is_verified=False,
                patch_hash=patch_hash,
                raw_runner_output=raw_output,
                failure_reflection_data={
                    "error_type": "MALFORMED_OR_MISSING_REPORT",
                    "exit_code": exit_code,
                    "output_tail": raw_output[-1000:] if raw_output else "",
                },
            )

        try:
            report_data = json.loads(report_json_str)
        except json.JSONDecodeError as exc:
            return VerificationResult(
                finding_id=finding_id,
                verdict=Verdict.ERROR_MALFORMED_REPORT,
                is_verified=False,
                patch_hash=patch_hash,
                raw_runner_output=f"{raw_output}\nJSON Decode Error: {exc}",
                failure_reflection_data={
                    "error_type": "MALFORMED_REPORT_JSON",
                    "details": str(exc),
                },
            )

        # Parse test items
        summary = report_data.get("summary", {})
        tests_data = report_data.get("tests", [])

        total_collected = summary.get("total", len(tests_data))
        total_passed = summary.get("passed", 0)
        total_failed = summary.get("failed", 0)
        total_errored = summary.get("error", 0)

        # 4. Zero Tests Collected Check
        if total_collected == 0 or not tests_data:
            return VerificationResult(
                finding_id=finding_id,
                verdict=Verdict.ERROR_NO_TESTS_COLLECTED,
                is_verified=False,
                patch_hash=patch_hash,
                total_tests_collected=0,
                total_tests_executed=0,
                raw_runner_output=raw_output,
                failure_reflection_data={
                    "error_type": "NO_TESTS_COLLECTED",
                    "message": "Runner completed but 0 tests were collected or executed.",
                },
            )

        # Parse individual test cases
        test_details: List[TestCaseResult] = []
        executed_categories: set[str] = set()
        security_failures: List[Dict[str, Any]] = []
        regression_failures: List[Dict[str, Any]] = []

        for item in tests_data:
            node_id = item.get("nodeid", "unknown")
            outcome = item.get("outcome", "unknown").upper()
            duration = float(item.get("duration", 0.0))

            # Categorize test suite
            category = "general"
            if "test_security" in node_id or "bola" in node_id.lower() or "sqli" in node_id.lower():
                category = "security"
            elif "test_functional" in node_id or "regression" in node_id.lower():
                category = "regression"
            elif "test_boundary" in node_id or "negative" in node_id.lower():
                category = "boundary"

            executed_categories.add(category)

            # Map status
            status = TestCaseStatus.ERROR
            if outcome == "PASSED":
                status = TestCaseStatus.PASSED
            elif outcome == "FAILED":
                status = TestCaseStatus.FAILED
            elif outcome == "SKIPPED":
                status = TestCaseStatus.SKIPPED

            msg = None
            call_info = item.get("call", {})
            if "crash" in call_info:
                msg = call_info["crash"].get("message")
            elif "longrepr" in call_info:
                msg = str(call_info["longrepr"])

            test_result = TestCaseResult(
                node_id=node_id,
                status=status,
                duration_seconds=duration,
                suite_category=category,
                message=msg,
            )
            test_details.append(test_result)

            if status in (TestCaseStatus.FAILED, TestCaseStatus.ERROR):
                fail_record = {
                    "node_id": node_id,
                    "category": category,
                    "error_message": msg,
                }
                if category == "security":
                    security_failures.append(fail_record)
                else:
                    regression_failures.append(fail_record)

        total_executed = len(test_details)
        security_passed = len(security_failures) == 0 and "security" in executed_categories
        regression_passed = len(regression_failures) == 0 and "regression" in executed_categories

        # 5. Required Categories Check (Must have executed security and regression tests)
        missing_categories = cls.REQUIRED_CATEGORIES - executed_categories
        if missing_categories:
            return VerificationResult(
                finding_id=finding_id,
                verdict=Verdict.ERROR_NO_TESTS_COLLECTED,
                is_verified=False,
                patch_hash=patch_hash,
                total_tests_collected=total_collected,
                total_tests_executed=total_executed,
                tests_passed=total_passed,
                tests_failed=total_failed,
                tests_errored=total_errored,
                test_details=test_details,
                raw_runner_output=raw_output,
                failure_reflection_data={
                    "error_type": "MISSING_REQUIRED_SUITES",
                    "missing_categories": list(missing_categories),
                },
            )

        # 6. Rejection for Security Failures (Candidate patch is still vulnerable)
        if security_failures:
            return VerificationResult(
                finding_id=finding_id,
                verdict=Verdict.REJECTED_VULNERABLE,
                is_verified=False,
                patch_hash=patch_hash,
                security_tests_passed=False,
                regression_tests_passed=regression_passed,
                total_tests_collected=total_collected,
                total_tests_executed=total_executed,
                tests_passed=total_passed,
                tests_failed=total_failed,
                tests_errored=total_errored,
                test_details=test_details,
                raw_runner_output=raw_output,
                failure_reflection_data={
                    "error_type": "SECURITY_EXPLOIT_STILL_ACTIVE",
                    "message": "Candidate patch failed adversarial security verification tests.",
                    "failing_tests": security_failures,
                },
            )

        # 7. Rejection for Regression/Boundary Failures (Patch broke existing routes)
        if regression_failures:
            return VerificationResult(
                finding_id=finding_id,
                verdict=Verdict.REJECTED_REGRESSION,
                is_verified=False,
                patch_hash=patch_hash,
                security_tests_passed=True,
                regression_tests_passed=False,
                total_tests_collected=total_collected,
                total_tests_executed=total_executed,
                tests_passed=total_passed,
                tests_failed=total_failed,
                tests_errored=total_errored,
                test_details=test_details,
                raw_runner_output=raw_output,
                failure_reflection_data={
                    "error_type": "FUNCTIONAL_REGRESSION",
                    "message": "Candidate patch fixed security vulnerability but broke regression tests.",
                    "failing_tests": regression_failures,
                },
            )

        # 8. All Passed Strictly
        all_passed = (total_failed == 0 and total_errored == 0 and total_executed > 0)
        verdict = Verdict.VERIFIED if all_passed else Verdict.ERROR_RUNNER

        return VerificationResult(
            finding_id=finding_id,
            verdict=verdict,
            is_verified=all_passed,
            patch_hash=patch_hash,
            security_tests_passed=security_passed,
            regression_tests_passed=regression_passed,
            total_tests_collected=total_collected,
            total_tests_executed=total_executed,
            tests_passed=total_passed,
            tests_failed=total_failed,
            tests_errored=total_errored,
            test_details=test_details,
            raw_runner_output=raw_output,
            failure_reflection_data=None,
        )

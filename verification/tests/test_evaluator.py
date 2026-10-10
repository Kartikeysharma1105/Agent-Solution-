"""Automated tests for TestResultEvaluator (Phase 6)."""

import json
from verification.contracts import VerificationStatus
from verification.evaluator import TestResultEvaluator


def test_evaluator_handles_timeout():
    result = TestResultEvaluator.evaluate(
        job_id="job-001",
        patch_hash="hash123",
        exit_code=-9,
        raw_output="Timeout",
        duration_ms=5000,
        timed_out=True,
    )
    assert result.status == VerificationStatus.EXECUTION_ERROR.value
    assert "timed out" in result.execution_error


def test_evaluator_handles_runner_crash():
    result = TestResultEvaluator.evaluate(
        job_id="job-001",
        patch_hash="hash123",
        exit_code=137,
        raw_output="OOM",
        runner_error="Container OOMKilled",
    )
    assert result.status == VerificationStatus.EXECUTION_ERROR.value
    assert "OOMKilled" in result.execution_error


def test_evaluator_handles_malformed_report_json():
    result = TestResultEvaluator.evaluate(
        job_id="job-001",
        patch_hash="hash123",
        exit_code=0,
        raw_output="Done",
        report_json_str="Not json {",
    )
    assert result.status == VerificationStatus.EXECUTION_ERROR.value
    assert "Malformed report" in result.execution_error


def test_evaluator_rejects_insufficient_test_collection():
    # Only 3 tests collected instead of minimum 8
    report = json.dumps({
        "summary": {"total": 3, "passed": 3, "failed": 0, "error": 0},
        "tests": [
            {"nodeid": "test_1", "outcome": "passed"},
            {"nodeid": "test_2", "outcome": "passed"},
            {"nodeid": "test_3", "outcome": "passed"},
        ],
    })
    result = TestResultEvaluator.evaluate(
        job_id="job-001",
        patch_hash="hash123",
        exit_code=0,
        raw_output="3 passed",
        report_json_str=report,
    )
    assert result.status == VerificationStatus.EXECUTION_ERROR.value
    assert "Incomplete test execution" in result.execution_error


def test_evaluator_returns_verification_failed_on_test_failure():
    report = json.dumps({
        "summary": {"total": 8, "passed": 7, "failed": 1, "error": 0},
        "tests": [
            {"nodeid": "test_security.py::test_user_a_cannot_access_user_b_document", "outcome": "failed"},
        ] + [{"nodeid": f"test_functional.py::test_{i}", "outcome": "passed"} for i in range(7)],
        "failed_tests": ["test_security.py::test_user_a_cannot_access_user_b_document"],
    })
    result = TestResultEvaluator.evaluate(
        job_id="job-001",
        patch_hash="hash123",
        exit_code=1,
        raw_output="1 failed, 7 passed",
        report_json_str=report,
    )
    assert result.status == VerificationStatus.VERIFICATION_FAILED.value
    assert result.tests_total == 8
    assert result.tests_passed == 7
    assert result.tests_failed == 1
    assert "test_security.py::test_user_a_cannot_access_user_b_document" in result.failed_tests
    assert result.execution_error is None


def test_evaluator_returns_verified_when_all_pass():
    report = json.dumps({
        "summary": {"total": 8, "passed": 8, "failed": 0, "error": 0},
        "tests": [{"nodeid": f"test_{i}", "outcome": "passed"} for i in range(8)],
        "failed_tests": [],
    })
    result = TestResultEvaluator.evaluate(
        job_id="job-001",
        patch_hash="hash123",
        exit_code=0,
        raw_output="8 passed",
        report_json_str=report,
    )
    assert result.status == VerificationStatus.VERIFIED.value
    assert result.tests_total == 8
    assert result.tests_passed == 8
    assert result.tests_failed == 0
    assert result.failed_tests == []

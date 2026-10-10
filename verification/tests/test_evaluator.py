"""Unit tests for independent TestResultEvaluator."""

import json
import pytest
from verification.contracts import Verdict, TestCaseStatus
from verification.runner.evaluator import TestResultEvaluator


def test_evaluator_handles_timeout():
    result = TestResultEvaluator.evaluate(
        finding_id="VULN-01",
        patch_hash="hash123",
        exit_code=-9,
        raw_output="Process killed",
        timed_out=True,
    )
    assert result.verdict == Verdict.ERROR_TIMEOUT
    assert not result.is_verified
    assert result.failure_reflection_data["error_type"] == "TIMEOUT"


def test_evaluator_handles_runner_error():
    result = TestResultEvaluator.evaluate(
        finding_id="VULN-01",
        patch_hash="hash123",
        exit_code=1,
        raw_output="Docker daemon connection failed",
        runner_error="Docker container failed to initialize",
    )
    assert result.verdict == Verdict.ERROR_RUNNER
    assert not result.is_verified


def test_evaluator_handles_malformed_json():
    result = TestResultEvaluator.evaluate(
        finding_id="VULN-01",
        patch_hash="hash123",
        exit_code=0,
        raw_output="OK",
        report_json_str="Not valid JSON {{{",
    )
    assert result.verdict == Verdict.ERROR_MALFORMED_REPORT
    assert not result.is_verified


def test_evaluator_handles_zero_tests_collected():
    empty_report = json.dumps({"summary": {"total": 0}, "tests": []})
    result = TestResultEvaluator.evaluate(
        finding_id="VULN-01",
        patch_hash="hash123",
        exit_code=0,
        raw_output="collected 0 items",
        report_json_str=empty_report,
    )
    assert result.verdict == Verdict.ERROR_NO_TESTS_COLLECTED
    assert not result.is_verified


def test_evaluator_handles_security_exploit_failure():
    report = json.dumps({
        "summary": {"total": 2, "passed": 1, "failed": 1},
        "tests": [
            {
                "nodeid": "tests_suite/test_functional_routes.py::test_health",
                "outcome": "passed",
                "duration": 0.01,
            },
            {
                "nodeid": "tests_suite/test_security_bola.py::test_adversarial_bola_access",
                "outcome": "failed",
                "duration": 0.05,
                "call": {"crash": {"message": "BOLA security failure: Alice accessed Bob's document!"}},
            },
        ],
    })
    result = TestResultEvaluator.evaluate(
        finding_id="VULN-01",
        patch_hash="hash123",
        exit_code=1,
        raw_output="FAILURES",
        report_json_str=report,
    )
    assert result.verdict == Verdict.REJECTED_VULNERABLE
    assert not result.is_verified
    assert not result.security_tests_passed
    assert result.regression_tests_passed
    assert result.failure_reflection_data["error_type"] == "SECURITY_EXPLOIT_STILL_ACTIVE"


def test_evaluator_handles_regression_failure():
    report = json.dumps({
        "summary": {"total": 2, "passed": 1, "failed": 1},
        "tests": [
            {
                "nodeid": "tests_suite/test_security_bola.py::test_adversarial_bola_access",
                "outcome": "passed",
                "duration": 0.05,
            },
            {
                "nodeid": "tests_suite/test_functional_routes.py::test_legitimate_access",
                "outcome": "failed",
                "duration": 0.01,
                "call": {"crash": {"message": "Regression: user cannot access own doc"}},
            },
        ],
    })
    result = TestResultEvaluator.evaluate(
        finding_id="VULN-01",
        patch_hash="hash123",
        exit_code=1,
        raw_output="FAILURES",
        report_json_str=report,
    )
    assert result.verdict == Verdict.REJECTED_REGRESSION
    assert not result.is_verified
    assert result.security_tests_passed
    assert not result.regression_tests_passed
    assert result.failure_reflection_data["error_type"] == "FUNCTIONAL_REGRESSION"


def test_evaluator_returns_verified_when_all_pass():
    report = json.dumps({
        "summary": {"total": 3, "passed": 3, "failed": 0, "error": 0},
        "tests": [
            {
                "nodeid": "tests_suite/test_security_bola.py::test_adversarial_bola_access",
                "outcome": "passed",
                "duration": 0.04,
            },
            {
                "nodeid": "tests_suite/test_functional_routes.py::test_health",
                "outcome": "passed",
                "duration": 0.01,
            },
            {
                "nodeid": "tests_suite/test_functional_routes.py::test_legitimate_access",
                "outcome": "passed",
                "duration": 0.02,
            },
        ],
    })
    result = TestResultEvaluator.evaluate(
        finding_id="VULN-01",
        patch_hash="hash123",
        exit_code=0,
        raw_output="3 passed",
        report_json_str=report,
    )
    assert result.verdict == Verdict.VERIFIED
    assert result.is_verified is True
    assert result.security_tests_passed is True
    assert result.regression_tests_passed is True
    assert result.total_tests_executed == 3

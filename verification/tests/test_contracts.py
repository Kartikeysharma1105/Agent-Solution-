"""Test contracts and serialization."""

import pytest
from verification.contracts import (
    Verdict,
    TestCaseStatus,
    TestCaseResult,
    VerificationRequest,
    VerificationResult,
)


def test_verification_request_validation():
    req = VerificationRequest(
        finding_id="VULN-BOLA-01",
        patch_content="--- a/app/main.py\n+++ b/app/main.py\n@@ -1,1 +1,1 @@\n",
        expected_patch_hash="abc123hash",
        approval_token="token_xyz",
        timeout_seconds=30,
    )
    assert req.finding_id == "VULN-BOLA-01"
    assert req.timeout_seconds == 30
    assert req.metadata == {}


def test_verification_result_serialization():
    res = VerificationResult(
        finding_id="VULN-BOLA-01",
        verdict=Verdict.VERIFIED,
        is_verified=True,
        patch_hash="abc123hash",
        security_tests_passed=True,
        regression_tests_passed=True,
        total_tests_collected=2,
        total_tests_executed=2,
        tests_passed=2,
        test_details=[
            TestCaseResult(
                node_id="tests_suite/test_security_bola.py::test_bola_exploit",
                status=TestCaseStatus.PASSED,
                duration_seconds=0.05,
                suite_category="security",
            )
        ],
    )
    assert res.is_verified is True
    assert res.verdict == Verdict.VERIFIED
    data = res.model_dump()
    assert data["verdict"] == "VERIFIED"
    assert len(data["test_details"]) == 1

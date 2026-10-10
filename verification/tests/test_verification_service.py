"""Integration tests for verification service and Docker sandbox.

Tests:
1. Rejection when approval token is missing/invalid (never runs sandbox).
2. Rejection when patch violates policy (touches tests_suite or contains os.system).
3. Rejection when patch hash does not match payload bytes.
4. Real Docker execution on vulnerable/incomplete patch -> REJECTED_VULNERABLE.
5. Real Docker execution on complete BOLA remediation patch -> VERIFIED.
"""

import asyncio
import pytest
from verification.approval import SimpleTokenApprovalVerifier
from verification.contracts import Verdict, VerificationRequest
from verification.patch_validator import PatchValidator
from verification.policy import PolicyEngine
from verification.service import verify_patch


# 1. Incomplete patch: only adds a comment, does not fix BOLA
INCOMPLETE_DIFF = """--- a/app/main.py
+++ b/app/main.py
@@ -59,3 +59,4 @@
         # VULNERABLE IMPLEMENTATION (BOLA / IDOR):
+        # Added non-functional comment
         return json_response(200, doc)
"""

# 2. Genuine fix patch: implements object-level authorization check
VALID_BOLA_FIX_DIFF = """--- a/app/main.py
+++ b/app/main.py
@@ -58,3 +58,7 @@
             return json_response(404, {"error": f"Document '{doc_id}' not found"})
 
-        return json_response(200, doc)
+        # Remediated: Object-level authorization check
+        if doc.get("owner_id") != current_user:
+            return json_response(403, {"error": "Forbidden: You do not have access to this document"})
+
+        return json_response(200, doc)
"""


def test_rejection_on_hash_mismatch():
    verifier = SimpleTokenApprovalVerifier()
    req = VerificationRequest(
        finding_id="VULN-BOLA-01",
        patch_content=INCOMPLETE_DIFF,
        expected_patch_hash="wrong_hash_1234567890",
        approval_token="valid_token",
    )
    result = asyncio.run(verify_patch(req, verifier))
    assert result.verdict == Verdict.REJECTED_MALFORMED_PATCH
    assert not result.is_verified


def test_rejection_on_policy_violation_protected_file():
    bad_diff = """--- a/tests_suite/test_security_bola.py
+++ b/tests_suite/test_security_bola.py
@@ -1,1 +1,1 @@
+# Tampering with test suite
"""
    patch_hash = PatchValidator.compute_hash(bad_diff)
    verifier = SimpleTokenApprovalVerifier({patch_hash: "token_123"})
    req = VerificationRequest(
        finding_id="VULN-BOLA-01",
        patch_content=bad_diff,
        expected_patch_hash=patch_hash,
        approval_token="token_123",
    )
    result = asyncio.run(verify_patch(req, verifier))
    assert result.verdict == Verdict.REJECTED_POLICY_VIOLATION
    assert not result.is_verified


def test_rejection_on_unapproved_patch():
    patch_hash = PatchValidator.compute_hash(INCOMPLETE_DIFF)
    verifier = SimpleTokenApprovalVerifier()  # No token registered
    req = VerificationRequest(
        finding_id="VULN-BOLA-01",
        patch_content=INCOMPLETE_DIFF,
        expected_patch_hash=patch_hash,
        approval_token="unregistered_token",
    )
    result = asyncio.run(verify_patch(req, verifier))
    assert result.verdict == Verdict.REJECTED_UNAPPROVED
    assert not result.is_verified


def test_docker_verification_rejects_vulnerable_patch():
    """Real disposable Docker execution of incomplete patch."""
    patch_hash = PatchValidator.compute_hash(INCOMPLETE_DIFF)
    verifier = SimpleTokenApprovalVerifier({patch_hash: "approved_token_abc"})
    req = VerificationRequest(
        finding_id="VULN-BOLA-01",
        patch_content=INCOMPLETE_DIFF,
        expected_patch_hash=patch_hash,
        approval_token="approved_token_abc",
        timeout_seconds=60,
    )

    result = asyncio.run(verify_patch(req, verifier))
    assert result.verdict == Verdict.REJECTED_VULNERABLE
    assert result.is_verified is False
    assert result.security_tests_passed is False
    assert result.regression_tests_passed is True
    assert result.failure_reflection_data is not None
    assert result.failure_reflection_data["error_type"] == "SECURITY_EXPLOIT_STILL_ACTIVE"


def test_docker_verification_verifies_valid_remediation():
    """Real disposable Docker execution of genuine BOLA remediation patch."""
    patch_hash = PatchValidator.compute_hash(VALID_BOLA_FIX_DIFF)
    verifier = SimpleTokenApprovalVerifier({patch_hash: "approved_token_xyz"})
    req = VerificationRequest(
        finding_id="VULN-BOLA-01",
        patch_content=VALID_BOLA_FIX_DIFF,
        expected_patch_hash=patch_hash,
        approval_token="approved_token_xyz",
        timeout_seconds=60,
    )

    result = asyncio.run(verify_patch(req, verifier))
    assert result.verdict == Verdict.VERIFIED
    assert result.is_verified is True
    assert result.security_tests_passed is True
    assert result.regression_tests_passed is True
    assert result.tests_passed == 11
    assert result.tests_failed == 0
    assert result.tests_errored == 0
    assert result.total_tests_executed == 11

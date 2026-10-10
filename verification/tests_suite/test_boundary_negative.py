"""IMMUTABLE BOUNDARY AND NEGATIVE TEST SUITE.

Protected from LLM modifications.
Ensures appropriate error codes are returned for missing auth, invalid headers, and nonexistent IDs.
"""

import pytest
from verification.tests_suite.client import AppClient

SUITE_CATEGORY = "boundary"


def test_missing_auth_header_rejected():
    """Requests without X-User-Id header must be rejected with 401 Unauthorized."""
    client = AppClient()
    response = client.get("/api/documents/doc_alice_public")
    assert response.status_code == 401
    assert "missing X-User-Id" in response.text


def test_malformed_auth_header_rejected():
    """Requests with dangerous characters in X-User-Id header must return 400 Bad Request."""
    client = AppClient()
    response = client.get(
        "/api/documents/doc_alice_public",
        headers={"X-User-Id": "alice' OR '1'='1"},
    )
    assert response.status_code == 400
    assert "Invalid characters" in response.text


def test_nonexistent_document_returns_404():
    """Requests for nonexistent documents must return 404 Not Found."""
    client = AppClient()
    response = client.get(
        "/api/documents/doc_nonexistent_9999",
        headers={"X-User-Id": "alice"},
    )
    assert response.status_code == 404


def test_unknown_route_returns_404():
    """Unmapped routes must return 404 Not Found."""
    client = AppClient()
    response = client.get(
        "/api/unmapped/endpoint",
        headers={"X-User-Id": "alice"},
    )
    assert response.status_code == 404

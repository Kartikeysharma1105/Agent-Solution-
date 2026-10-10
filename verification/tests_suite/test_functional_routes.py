"""IMMUTABLE FUNCTIONAL REGRESSION TEST SUITE.

Protected from LLM modifications.
Ensures that authorized operations, legitimate document access, and listing work as expected.
"""

import pytest
from verification.tests_suite.client import AppClient

SUITE_CATEGORY = "regression"


def test_health_check_endpoint():
    """Verify health endpoint is reachable."""
    client = AppClient()
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"


def test_legitimate_owner_can_access_own_public_document():
    """Verify Alice can access her own public document."""
    client = AppClient()
    response = client.get(
        "/api/documents/doc_alice_public",
        headers={"X-User-Id": "alice"},
    )
    assert response.status_code == 200, f"Alice could not access her own doc: {response.text}"
    data = response.json()
    assert data["id"] == "doc_alice_public"
    assert data["owner_id"] == "alice"


def test_legitimate_owner_can_access_own_confidential_document():
    """Verify Alice can access her own confidential document."""
    client = AppClient()
    response = client.get(
        "/api/documents/doc_alice_confidential",
        headers={"X-User-Id": "alice"},
    )
    assert response.status_code == 200, f"Alice could not access her confidential doc: {response.text}"
    data = response.json()
    assert data["id"] == "doc_alice_confidential"
    assert data["owner_id"] == "alice"


def test_legitimate_bob_can_access_own_document():
    """Verify Bob can access his own document."""
    client = AppClient()
    response = client.get(
        "/api/documents/doc_bob_confidential",
        headers={"X-User-Id": "bob"},
    )
    assert response.status_code == 200, f"Bob could not access his own doc: {response.text}"
    data = response.json()
    assert data["id"] == "doc_bob_confidential"
    assert data["owner_id"] == "bob"


def test_list_documents_only_returns_owned_documents():
    """Verify document list endpoint filters strictly by the authenticated user."""
    client = AppClient()
    response = client.get(
        "/api/documents",
        headers={"X-User-Id": "alice"},
    )
    assert response.status_code == 200
    data = response.json()
    docs = data.get("documents", [])
    assert len(docs) >= 1
    for doc in docs:
        assert doc["owner_id"] == "alice"

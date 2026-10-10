"""Test suite validating the BOLA benchmark behavior."""

from verification.tests_suite.client import AppClient


def test_unpatched_bola_vulnerability_exists():
    """Verify that the baseline app exhibits BOLA."""
    client = AppClient()

    # Alice should be able to access her own document
    res_own = client.get("/api/documents/doc_alice_public", headers={"X-User-Id": "alice"})
    assert res_own.status_code == 200

    # In vulnerable state, Alice CAN access Bob's document (BOLA)
    res_other = client.get("/api/documents/doc_bob_confidential", headers={"X-User-Id": "alice"})
    assert res_other.status_code == 200
    assert res_other.json()["owner_id"] == "bob"

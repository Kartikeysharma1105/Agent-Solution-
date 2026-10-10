"""In-memory benchmark document store with ownership tracking for BOLA evaluation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class DocumentDatabase:
    """Benchmark database containing records owned by different tenants."""

    def __init__(self) -> None:
        self._documents: Dict[str, Dict[str, Any]] = {
            "doc_alice_public": {
                "id": "doc_alice_public",
                "owner_id": "alice",
                "title": "Alice Public Notes",
                "content": "Public architectural notes.",
                "is_confidential": False,
            },
            "doc_alice_confidential": {
                "id": "doc_alice_confidential",
                "owner_id": "alice",
                "title": "Alice Secret Finances",
                "content": "Alice private financial data.",
                "is_confidential": True,
            },
            "doc_bob_confidential": {
                "id": "doc_bob_confidential",
                "owner_id": "bob",
                "title": "Bob Secret Project Key",
                "content": "Bob private cryptographic keys.",
                "is_confidential": True,
            },
            "doc_charlie_payroll": {
                "id": "doc_charlie_payroll",
                "owner_id": "charlie",
                "title": "Charlie Payroll Statement",
                "content": "Charlie salary compensation details.",
                "is_confidential": True,
            },
        }

    def get_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        doc = self._documents.get(doc_id)
        if doc is None:
            return None
        return dict(doc)

    def list_all(self) -> List[Dict[str, Any]]:
        return [dict(d) for d in self._documents.values()]

    def reset(self) -> None:
        """Reset to initial state."""
        self.__init__()

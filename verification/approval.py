"""Approval verification protocols and implementations for Layer 4 Gate integration.

Enforces that candidate patches cannot execute in disposable environments without
valid backend-supplied human approval.
"""

from __future__ import annotations

import hmac
import hashlib
import inspect
from typing import Any, Callable, Union, Awaitable

# Callable type: accepts (patch_hash: str, approval_token: str) -> bool or Awaitable[bool]
ApprovalVerifier = Union[
    Callable[[str, str], bool],
    Callable[[str, str], Awaitable[bool]],
]


class SimpleTokenApprovalVerifier:
    """Token-based approval verifier storing approved token mappings."""

    def __init__(self, approved_tokens: dict[str, str] | None = None) -> None:
        # Mapping of patch_hash -> expected approval token
        self._approved: dict[str, str] = dict(approved_tokens or {})

    def register_approval(self, patch_hash: str, approval_token: str) -> None:
        """Register an approval token from the human gate."""
        self._approved[patch_hash.strip().lower()] = approval_token.strip()

    def __call__(self, patch_hash: str, approval_token: str) -> bool:
        expected = self._approved.get(patch_hash.strip().lower())
        if not expected:
            return False
        return hmac.compare_digest(expected, approval_token.strip())


class HmacApprovalVerifier:
    """Cryptographic HMAC-SHA256 signature verifier for human approval tokens."""

    def __init__(self, secret_key: bytes | str) -> None:
        self.secret_key = secret_key.encode("utf-8") if isinstance(secret_key, str) else secret_key

    def generate_token(self, patch_hash: str) -> str:
        """Helper to generate a valid approval token for a given patch hash."""
        return hmac.new(self.secret_key, patch_hash.strip().lower().encode("utf-8"), hashlib.sha256).hexdigest()

    def __call__(self, patch_hash: str, approval_token: str) -> bool:
        expected = self.generate_token(patch_hash)
        return hmac.compare_digest(expected, approval_token.strip())


async def execute_approval_verifier(verifier: ApprovalVerifier, patch_hash: str, approval_token: str) -> bool:
    """Safely execute sync or async ApprovalVerifier callable."""
    if not callable(verifier):
        return False
    try:
        result = verifier(patch_hash, approval_token)
        if inspect.isawaitable(result):
            return bool(await result)
        return bool(result)
    except Exception:
        return False

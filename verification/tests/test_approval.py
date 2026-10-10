"""Test approval verification mechanisms (Layer 4 integration)."""

import asyncio
from verification.approval import (
    SimpleTokenApprovalVerifier,
    HmacApprovalVerifier,
    execute_approval_verifier,
)


def test_simple_token_verifier():
    verifier = SimpleTokenApprovalVerifier()
    patch_hash = "d3b07384d113edec49eaa6238ad5ff00"
    token = "secret_approval_token_123"

    # Initially unapproved
    assert not asyncio.run(execute_approval_verifier(verifier, patch_hash, token))

    # Register approval
    verifier.register_approval(patch_hash, token)
    assert asyncio.run(execute_approval_verifier(verifier, patch_hash, token))
    assert not asyncio.run(execute_approval_verifier(verifier, patch_hash, "wrong_token"))
    assert not asyncio.run(execute_approval_verifier(verifier, "different_hash", token))


def test_hmac_approval_verifier():
    secret = "orchestrator_secret_key"
    verifier = HmacApprovalVerifier(secret)
    patch_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    token = verifier.generate_token(patch_hash)
    assert asyncio.run(execute_approval_verifier(verifier, patch_hash, token))
    assert not asyncio.run(execute_approval_verifier(verifier, patch_hash, "tampered_token"))
    assert not asyncio.run(execute_approval_verifier(verifier, "different_hash", token))


def test_async_callable_approval_verifier():
    async def custom_async_verifier(h: str, t: str) -> bool:
        return h == "valid_hash" and t == "valid_token"

    assert asyncio.run(execute_approval_verifier(custom_async_verifier, "valid_hash", "valid_token"))
    assert not asyncio.run(execute_approval_verifier(custom_async_verifier, "invalid", "valid_token"))

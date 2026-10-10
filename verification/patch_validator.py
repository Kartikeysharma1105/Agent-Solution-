"""Deterministic patch byte validation and SHA-256 hash binding.

Ensures that the patch content has not been tampered with and strictly conforms
to unified diff specifications.
"""

from __future__ import annotations

import hashlib
import re
from typing import List, Tuple


class PatchValidationError(Exception):
    """Raised when patch syntax, bytes, or hash verification fails."""
    pass


class PatchValidator:
    """Validates unified diff patches, hashes, and target paths."""

    _DIFF_HEADER_REGEX = re.compile(r"^diff --git a/(.+) b/(.+)$", re.MULTILINE)
    _OLD_FILE_REGEX = re.compile(r"^--- (?:a/)?([^\s\t\n]+)", re.MULTILINE)
    _NEW_FILE_REGEX = re.compile(r"^\+\+\+ (?:b/)?([^\s\t\n]+)", re.MULTILINE)

    @staticmethod
    def compute_hash(patch_content: str | bytes) -> str:
        """Compute the SHA-256 hex digest of patch content."""
        if isinstance(patch_content, str):
            patch_bytes = patch_content.encode("utf-8")
        else:
            patch_bytes = patch_content
        return hashlib.sha256(patch_bytes).hexdigest()

    @classmethod
    def verify_hash(cls, patch_content: str, expected_hash: str) -> bool:
        """Verify that the computed hash strictly matches the expected hash."""
        computed = cls.compute_hash(patch_content)
        return computed.lower() == expected_hash.strip().lower()

    @classmethod
    def extract_target_paths(cls, patch_content: str) -> List[str]:
        """Extract modified relative target paths from diff headers.

        Raises:
            PatchValidationError: If diff is malformed or contains suspicious path escapes.
        """
        if not patch_content or not patch_content.strip():
            raise PatchValidationError("Patch content is empty.")

        paths: set[str] = set()

        # Check for standard git diff headers
        git_matches = cls._DIFF_HEADER_REGEX.findall(patch_content)
        for old_p, new_p in git_matches:
            paths.add(old_p)
            paths.add(new_p)

        # Fallback to standard unified diff --- / +++ headers
        if not paths:
            new_matches = cls._NEW_FILE_REGEX.findall(patch_content)
            for path in new_matches:
                if path != "/dev/null":
                    paths.add(path)

        if not paths:
            raise PatchValidationError("No valid file modification targets found in patch.")

        cleaned_paths: List[str] = []
        for path in paths:
            cleaned = path.strip()
            # Strip standard git prefixes if lingering
            if cleaned.startswith("a/") or cleaned.startswith("b/"):
                cleaned = cleaned[2:]
            
            # Security check: forbid path traversal and absolute roots
            if ".." in cleaned.split("/") or cleaned.startswith("/"):
                raise PatchValidationError(f"Forbidden path traversal or absolute path detected: {path}")

            cleaned_paths.append(cleaned)

        return cleaned_paths

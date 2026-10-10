"""Patch integrity and safety validation for SENTINEL-X Verification (Layer 5).

Enforces:
1. Unified-diff syntax only.
2. Changes restricted ONLY to 'app/access.py'.
3. Protection of tests, runners, Dockerfiles, and configurations.
4. Prevention of path traversal, absolute paths, and binary patches.
5. Maximum patch size enforcement.
6. Exact SHA-256 byte hashing and verification.
"""

from __future__ import annotations

import hashlib
import re
from typing import List, Sequence


class PatchValidationError(Exception):
    """Raised when patch syntax, scope, size, or safety policy is violated."""
    pass


class PatchValidator:
    """Validates candidate patch diffs against strict safety policies."""

    MAX_PATCH_BYTES = 65536  # 64 KB limit

    # Authorized target files that an untrusted AI patch may modify
    ALLOWED_TARGET_FILES = {
        "app/access.py",
        "lab/app/access.py",
    }

    # Forbidden file patterns that must never be touched
    PROTECTED_PATTERNS = [
        re.compile(r".*protected_tests/.*"),
        re.compile(r".*test_.*\.py$"),
        re.compile(r".*_test\.py$"),
        re.compile(r".*Dockerfile.*"),
        re.compile(r".*requirements.*"),
        re.compile(r".*runner.*"),
        re.compile(r".*evaluator.*"),
        re.compile(r".*\.env.*"),
        re.compile(r"^\.git/.*"),
    ]

    # Forbidden added code patterns (dangerous syscalls or test evasions)
    FORBIDDEN_CODE_PATTERNS = [
        (re.compile(r"\bos\.system\s*\("), "Forbidden call to os.system detected"),
        (re.compile(r"\bsubprocess\b"), "Forbidden subprocess execution detected"),
        (re.compile(r"\beval\s*\("), "Forbidden call to eval detected"),
        (re.compile(r"\bexec\s*\("), "Forbidden call to exec detected"),
        (re.compile(r"\bpytest\.skip"), "Forbidden test skip directive detected"),
        (re.compile(r"@pytest\.mark\.skip"), "Forbidden test skip decorator detected"),
    ]

    _DIFF_HEADER_REGEX = re.compile(r"^diff --git a/(.+) b/(.+)$", re.MULTILINE)
    _OLD_FILE_REGEX = re.compile(r"^--- (?:a/)?([^\s\t\n]+)", re.MULTILINE)
    _NEW_FILE_REGEX = re.compile(r"^\+\+\+ (?:b/)?([^\s\t\n]+)", re.MULTILINE)

    @staticmethod
    def compute_hash(patch_content: str | bytes) -> str:
        """Compute the SHA-256 hex digest of patch content bytes."""
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
    def validate_patch(cls, patch_text: str, expected_hash: Optional[str] = None) -> List[str]:
        """Perform full validation of patch syntax, size, scope, and content safety.

        Returns:
            List of validated relative target paths.

        Raises:
            PatchValidationError: If any safety rule or policy is violated.
        """
        if not patch_text or not patch_text.strip():
            raise PatchValidationError("Patch content is empty.")

        patch_bytes = patch_text.encode("utf-8")
        if len(patch_bytes) > cls.MAX_PATCH_BYTES:
            raise PatchValidationError(f"Patch exceeds maximum permitted size ({len(patch_bytes)} > {cls.MAX_PATCH_BYTES} bytes).")

        # Check for binary diffs
        if "GIT binary patch" in patch_text or "\x00" in patch_text:
            raise PatchValidationError("Binary patches are strictly forbidden.")

        # Hash verification
        if expected_hash is not None:
            if not cls.verify_hash(patch_text, expected_hash):
                raise PatchValidationError("Patch hash mismatch: computed hash does not match expected approval hash.")

        # Extract target paths
        paths: set[str] = set()
        git_matches = cls._DIFF_HEADER_REGEX.findall(patch_text)
        for old_p, new_p in git_matches:
            paths.add(old_p)
            paths.add(new_p)

        if not paths:
            new_matches = cls._NEW_FILE_REGEX.findall(patch_text)
            for p in new_matches:
                if p != "/dev/null":
                    paths.add(p)

        if not paths:
            raise PatchValidationError("No valid unified diff file headers found in patch.")

        cleaned_paths: List[str] = []
        for path in paths:
            cleaned = path.strip()
            if cleaned.startswith("a/") or cleaned.startswith("b/"):
                cleaned = cleaned[2:]

            # Security checks: traversal and absolute paths
            if ".." in cleaned.split("/") or cleaned.startswith("/"):
                raise PatchValidationError(f"Path traversal or absolute path detected: '{path}'")

            # Check protected patterns
            for prot_pat in cls.PROTECTED_PATTERNS:
                if prot_pat.match(cleaned):
                    raise PatchValidationError(f"Modification of protected file '{path}' is strictly forbidden.")

            # Check authorized target scope
            if cleaned not in cls.ALLOWED_TARGET_FILES:
                raise PatchValidationError(f"Modification of '{cleaned}' is unauthorized. Only {cls.ALLOWED_TARGET_FILES} may be patched.")

            cleaned_paths.append(cleaned)

        # Inspect added lines for dangerous operations
        for line in patch_text.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                added_code = line[1:].strip()
                for pattern, reason in cls.FORBIDDEN_CODE_PATTERNS:
                    if pattern.search(added_code):
                        raise PatchValidationError(f"Policy violation: {reason} in added code: '{added_code}'")

        return cleaned_paths

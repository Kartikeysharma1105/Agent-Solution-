"""Policy Engine for static patch analysis and validation rules.

Enforces:
1. Target file path boundaries (only permitted application paths, no test suites or config files).
2. Forbidden commands and security bypass constructs (e.g. subprocess, os.system, eval, test skips).
3. Protection of immutable test files and verification runner infrastructure.
"""

from __future__ import annotations

import re
from typing import List, Sequence


class PolicyViolationError(Exception):
    """Raised when a candidate patch violates deterministic policy rules."""
    pass


class PolicyEngine:
    """Enforces static safety and scope policies on candidate patches."""

    # Forbidden file patterns (never allowed to be modified by an untrusted patch)
    PROTECTED_FILE_PATTERNS = [
        re.compile(r"^tests_suite/.*"),
        re.compile(r".*test_.*\.py$"),
        re.compile(r".*_test\.py$"),
        re.compile(r"^verification/.*"),
        re.compile(r"^Dockerfile.*"),
        re.compile(r".*\.dockerignore$"),
        re.compile(r".*\.env.*"),
        re.compile(r"^\.git/.*"),
        re.compile(r"^\.github/.*"),
        re.compile(r"^docker-compose.*"),
        re.compile(r".*requirements\.txt$"),
    ]

    # Allowed application directories/files
    DEFAULT_ALLOWED_PREFIXES = [
        "app/",
        "src/",
    ]

    # Forbidden diff content patterns (dangerous code injections or test evasions)
    FORBIDDEN_CONTENT_PATTERNS = [
        (re.compile(r"\bos\.system\s*\("), "Forbidden call to os.system detected"),
        (re.compile(r"\bsubprocess\b"), "Forbidden use of subprocess detected"),
        (re.compile(r"\b__import__\s*\("), "Forbidden dynamic import detected"),
        (re.compile(r"\beval\s*\("), "Forbidden call to eval detected"),
        (re.compile(r"\bexec\s*\("), "Forbidden call to exec detected"),
        (re.compile(r"\bpytest\.skip\s*\("), "Forbidden test skip directive detected"),
        (re.compile(r"@pytest\.mark\.skip"), "Forbidden pytest skip decorator detected"),
        (re.compile(r"\b/bin/(?:ba)?sh\b"), "Forbidden shell invocation detected"),
        (re.compile(r"\bsocket\.(?:socket|create_connection)\b"), "Forbidden network socket creation detected"),
    ]

    def __init__(
        self,
        allowed_prefixes: Sequence[str] | None = None,
        disallow_new_files: bool = False,
    ) -> None:
        self.allowed_prefixes = list(allowed_prefixes) if allowed_prefixes else self.DEFAULT_ALLOWED_PREFIXES
        self.disallow_new_files = disallow_new_files

    def validate_paths(self, modified_paths: Sequence[str]) -> None:
        """Ensure all modified file paths obey the ownership and security boundaries."""
        if not modified_paths:
            raise PolicyViolationError("Patch modifies no files.")

        for path in modified_paths:
            normalized = path.replace("\\", "/").lstrip("/")

            # Check protected file rules
            for pattern in self.PROTECTED_FILE_PATTERNS:
                if pattern.match(normalized):
                    raise PolicyViolationError(
                        f"Patch attempts to modify protected file: '{path}'. Patches cannot alter test suites or runner files."
                    )

            # Check allowed prefix rules
            is_allowed = any(normalized.startswith(prefix) or normalized == prefix.rstrip("/") for prefix in self.allowed_prefixes)
            if not is_allowed:
                raise PolicyViolationError(
                    f"Path '{path}' is outside the authorized application boundary: {self.allowed_prefixes}."
                )

    def validate_patch_content(self, patch_content: str) -> None:
        """Inspect patch addition lines for dangerous commands and bypass tokens."""
        # Only inspect added lines (+)
        for line in patch_content.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                added_code = line[1:].strip()
                for pattern, reason in self.FORBIDDEN_CONTENT_PATTERNS:
                    if pattern.search(added_code):
                        raise PolicyViolationError(f"Policy violation: {reason} in added line: '{added_code}'")

    def validate(self, modified_paths: Sequence[str], patch_content: str) -> None:
        """Run complete policy verification pipeline."""
        self.validate_paths(modified_paths)
        self.validate_patch_content(patch_content)

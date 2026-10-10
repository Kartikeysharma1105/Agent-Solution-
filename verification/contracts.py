"""Data contracts and schemas for SENTINEL-X Verification (Layer 5).

Coordinated with Dev 1 (FastAPI Orchestrator) and Dev 4 (LLM Reflection Module).
Uses Python standard library dataclasses for universal compatibility with 0 external bloat.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class Verdict(str, Enum):
    """Evaluation verdict emitted by Layer 5 Verification."""
    VERIFIED = "VERIFIED"
    REJECTED_UNAPPROVED = "REJECTED_UNAPPROVED"
    REJECTED_POLICY_VIOLATION = "REJECTED_POLICY_VIOLATION"
    REJECTED_MALFORMED_PATCH = "REJECTED_MALFORMED_PATCH"
    REJECTED_VULNERABLE = "REJECTED_VULNERABLE"
    REJECTED_REGRESSION = "REJECTED_REGRESSION"
    ERROR_TIMEOUT = "ERROR_TIMEOUT"
    ERROR_NO_TESTS_COLLECTED = "ERROR_NO_TESTS_COLLECTED"
    ERROR_MALFORMED_REPORT = "ERROR_MALFORMED_REPORT"
    ERROR_RUNNER = "ERROR_RUNNER"


class TestCaseStatus(str, Enum):
    """Execution status for individual test cases."""
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


# Prevent pytest from treating TestCaseStatus as a test class
TestCaseStatus.__test__ = False


@dataclass
class _BaseModel:
    """Provides Pydantic-compatible model_dump and dict serialization methods."""

    def model_dump(self) -> Dict[str, Any]:
        data = asdict(self)
        return self._serialize(data)

    def dict(self) -> Dict[str, Any]:
        return self.model_dump()

    def _serialize(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: self._serialize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._serialize(item) for item in obj]
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, datetime):
            return obj.isoformat()
        return obj


@dataclass
class TestCaseResult(_BaseModel):
    """Detailed result for an individual executed test case."""
    node_id: str
    status: TestCaseStatus
    duration_seconds: float = 0.0
    suite_category: str = "general"  # "security", "regression", "boundary"
    message: Optional[str] = None


# Prevent pytest from treating TestCaseResult as a test class
TestCaseResult.__test__ = False


@dataclass
class VerificationRequest(_BaseModel):
    """Payload provided by Dev 1 Orchestrator to request patch verification."""
    finding_id: str
    patch_content: str
    expected_patch_hash: str
    approval_token: str
    target_app_path: Optional[str] = None
    timeout_seconds: int = 60
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationResult(_BaseModel):
    """Structured verdict output returned to Dev 1 Orchestrator."""
    finding_id: str
    verdict: Verdict
    is_verified: bool
    patch_hash: str
    security_tests_passed: bool = False
    regression_tests_passed: bool = False
    total_tests_collected: int = 0
    total_tests_executed: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    tests_errored: int = 0
    test_details: List[TestCaseResult] = field(default_factory=list)
    raw_runner_output: str = ""
    failure_reflection_data: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

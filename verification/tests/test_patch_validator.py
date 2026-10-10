"""Test patch syntax and SHA-256 hash validation."""

import pytest
from verification.patch_validator import PatchValidator, PatchValidationError


SAMPLE_DIFF = """--- a/app/main.py
+++ b/app/main.py
@@ -10,3 +10,4 @@
 def get_doc():
+    # Authorization check
     return {}
"""


def test_compute_and_verify_hash():
    computed_hash = PatchValidator.compute_hash(SAMPLE_DIFF)
    assert len(computed_hash) == 64
    assert PatchValidator.verify_hash(SAMPLE_DIFF, computed_hash)
    assert not PatchValidator.verify_hash(SAMPLE_DIFF, "invalid_hash_value")


def test_extract_target_paths():
    paths = PatchValidator.extract_target_paths(SAMPLE_DIFF)
    assert paths == ["app/main.py"]


def test_reject_empty_patch():
    with pytest.raises(PatchValidationError, match="Patch content is empty"):
        PatchValidator.extract_target_paths("")


def test_reject_path_traversal():
    traversal_diff = """--- a/app/../etc/passwd
+++ b/app/../etc/passwd
@@ -1,1 +1,1 @@
+root:x:0:0
"""
    with pytest.raises(PatchValidationError, match="Forbidden path traversal"):
        PatchValidator.extract_target_paths(traversal_diff)


def test_reject_absolute_path():
    abs_diff = """--- /etc/shadow
+++ /etc/shadow
@@ -1,1 +1,1 @@
+hack
"""
    with pytest.raises(PatchValidationError, match="Forbidden path traversal or absolute path"):
        PatchValidator.extract_target_paths(abs_diff)

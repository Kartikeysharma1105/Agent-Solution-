"""Test policy engine boundaries and forbidden content detection."""

import pytest
from verification.policy import PolicyEngine, PolicyViolationError


def test_allowed_app_path():
    engine = PolicyEngine()
    engine.validate_paths(["app/main.py", "app/database.py"])


def test_reject_tests_suite_modification():
    engine = PolicyEngine()
    with pytest.raises(PolicyViolationError, match="protected file"):
        engine.validate_paths(["tests_suite/test_security_bola.py"])


def test_reject_dockerfile_modification():
    engine = PolicyEngine()
    with pytest.raises(PolicyViolationError, match="protected file"):
        engine.validate_paths(["Dockerfile"])


def test_reject_out_of_boundary_path():
    engine = PolicyEngine()
    with pytest.raises(PolicyViolationError, match="outside the authorized application boundary"):
        engine.validate_paths(["random_dir/script.py"])


def test_reject_os_system_injection():
    engine = PolicyEngine()
    bad_diff = """--- a/app/main.py
+++ b/app/main.py
@@ -1,1 +1,2 @@
+import os
+os.system("rm -rf /")
"""
    with pytest.raises(PolicyViolationError, match="Forbidden call to os.system"):
        engine.validate_patch_content(bad_diff)


def test_reject_subprocess_injection():
    engine = PolicyEngine()
    bad_diff = """--- a/app/main.py
+++ b/app/main.py
@@ -1,1 +1,2 @@
+import subprocess
+subprocess.Popen(["sh"])
"""
    with pytest.raises(PolicyViolationError, match="Forbidden use of subprocess"):
        engine.validate_patch_content(bad_diff)


def test_reject_eval_injection():
    engine = PolicyEngine()
    bad_diff = """--- a/app/main.py
+++ b/app/main.py
@@ -1,1 +1,2 @@
+eval(user_input)
"""
    with pytest.raises(PolicyViolationError, match="Forbidden call to eval"):
        engine.validate_patch_content(bad_diff)


def test_reject_pytest_skip_evasion():
    engine = PolicyEngine()
    bad_diff = """--- a/app/main.py
+++ b/app/main.py
@@ -1,1 +1,2 @@
+pytest.skip("bypass")
"""
    with pytest.raises(PolicyViolationError, match="Forbidden test skip"):
        engine.validate_patch_content(bad_diff)

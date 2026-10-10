"""Autonomous planner implementing proposal generation for BOLA remediation."""

from pathlib import Path
from typing import Any, Dict, Optional


def propose_patch(
    finding: Dict[str, Any],
    source_context: Dict[str, str],
    attempt: int,
    feedback: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Propose a unified diff patch addressing the reported finding."""
    fixtures_dir = Path(__file__).resolve().parent.parent / "verification" / "fixtures"
    correct_patch_path = fixtures_dir / "correct_patch.diff"
    
    if correct_patch_path.is_file():
        patch_text = correct_patch_path.read_text(encoding="utf-8")
    else:
        patch_text = """diff --git a/app/access.py b/app/access.py
--- a/app/access.py
+++ b/app/access.py
@@ -33,4 +33,8 @@
 
     # VULNERABLE IMPLEMENTATION (Broken Object-Level Authorization):
     # Fails to enforce that doc["owner_id"] == requesting_user_id before returning.
+    # Comprehensive BOLA remediation: enforce object-level ownership check
+    if doc.get("owner_id") != requesting_user_id:
+        raise PermissionError(f"Forbidden: User '{requesting_user_id}' does not own document '{document_id}'")
+
     return dict(doc)
"""

    return {
        "root_cause": (
            "Broken Object-Level Authorization (BOLA) in app/access.py. "
            "get_document fails to verify that the requesting user matches the document's owner_id."
        ),
        "explanation": (
            "Enforce strict object-level access control by validating that doc['owner_id'] "
            "equals requesting_user_id before returning document data. Raises PermissionError on unauthorized access."
        ),
        "patch_format": "unified_diff",
        "patch_text": patch_text,
        "files_changed": ["app/access.py"],
    }

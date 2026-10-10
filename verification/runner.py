"""Restricted Docker Runner for SENTINEL-X Verification (Layer 5).

Provides ephemeral, non-root, isolated execution for candidate patches:
1. Validates request, patch syntax, file scope, and exact hash binding.
2. Checks trusted backend ApprovalVerifier gate.
3. Applies patch in a clean ephemeral workspace copy.
4. Mounts protected tests strictly READ-ONLY (:ro).
5. Runs Pytest in disposable Docker container with restricted network, CPU, memory, and capabilities.
6. Evaluates results through independent TestResultEvaluator.
"""

from __future__ import annotations

import asyncio
import inspect
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Optional, Sequence

from .contracts import (
    ApprovalVerifier,
    VerificationRequest,
    VerificationResult,
    VerificationStatus,
)
from .evaluator import TestResultEvaluator
from .patch_validator import PatchValidator, PatchValidationError


def sanitize_log(text: str) -> str:
    """Sanitize execution logs before exposing to AI or orchestrator."""
    if not text:
        return ""
    # Strip local host user paths
    sanitized = re.sub(r"/home/[^/\s]+/[^/\s]+", "/workspace", text)
    # Redact potential sensitive tokens/keys
    sanitized = re.sub(r"(token|secret|password|auth)[:=]\s*([^\s]+)", r"\1: [REDACTED]", sanitized, flags=re.IGNORECASE)
    return sanitized


async def execute_approval(verifier: ApprovalVerifier, patch_hash: str, approval_id: str) -> bool:
    """Safely execute sync or async ApprovalVerifier callback."""
    if not callable(verifier):
        return False
    try:
        res = verifier(patch_hash, approval_id)
        if inspect.isawaitable(res):
            return bool(await res)
        return bool(res)
    except Exception:
        return False


async def verify_patch(
    request: VerificationRequest,
    approval_verifier: ApprovalVerifier,
    docker_image: str = "sentinel-verification-lab:latest",
) -> VerificationResult:
    """Execute end-to-end patch verification in a restricted disposable Docker sandbox."""
    start_time = time.time()
    job_id = request.job_id or "job-unknown"
    patch_hash = request.patch_hash or PatchValidator.compute_hash(request.patch_text)

    # 1. Request field validation
    if request.target_app_id != "bola-demo-v1":
        return VerificationResult(
            job_id=job_id,
            patch_hash=patch_hash,
            status=VerificationStatus.POLICY_REJECTED.value,
            execution_error=f"Unsupported target_app_id: '{request.target_app_id}'. Expected 'bola-demo-v1'.",
        )

    # 2. Patch validation (exact hash, scope, syntax, size, traversal)
    try:
        modified_paths = PatchValidator.validate_patch(request.patch_text, request.patch_hash)
    except PatchValidationError as exc:
        return VerificationResult(
            job_id=job_id,
            patch_hash=patch_hash,
            status=VerificationStatus.POLICY_REJECTED.value,
            execution_error=f"Patch policy rejected: {exc}",
        )

    # 3. Human Approval Gate verification
    is_approved = await execute_approval(approval_verifier, patch_hash, request.approval_id)
    if not is_approved:
        return VerificationResult(
            job_id=job_id,
            patch_hash=patch_hash,
            status=VerificationStatus.POLICY_REJECTED.value,
            execution_error="Missing or invalid approval signature/id from backend gate.",
        )

    # 4. Prepare ephemeral workspace
    base_dir = Path(__file__).resolve().parent
    lab_app_src = base_dir / "lab" / "app"
    protected_tests_src = base_dir / "protected_tests"

    temp_dir = tempfile.mkdtemp(prefix=f"sentinel_{job_id}_")
    container_id = f"sentinel_run_{uuid.uuid4().hex[:10]}"

    try:
        workspace_dir = Path(temp_dir)
        app_dest = workspace_dir / "verification" / "lab" / "app"
        app_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(lab_app_src, app_dest)

        tests_dest = workspace_dir / "verification" / "protected_tests"
        shutil.copytree(protected_tests_src, tests_dest)

        report_dir = workspace_dir / "report"
        report_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(temp_dir, 0o777)
        os.chmod(report_dir, 0o777)
        report_file_host = report_dir / "test_report.json"

        # 5. Apply candidate patch to clean baseline
        patch_file = workspace_dir / "candidate.patch"
        patch_file.write_text(request.patch_text, encoding="utf-8")

        apply_proc = subprocess.run(
            ["patch", "-p1", "--input", str(patch_file)],
            cwd=str(workspace_dir / "verification" / "lab"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        if apply_proc.returncode != 0:
            # Fallback to -p0
            apply_proc = subprocess.run(
                ["patch", "-p0", "--input", str(patch_file)],
                cwd=str(workspace_dir / "verification" / "lab"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

        if apply_proc.returncode != 0:
            return VerificationResult(
                job_id=job_id,
                patch_hash=patch_hash,
                status=VerificationStatus.EXECUTION_ERROR.value,
                duration_ms=int((time.time() - start_time) * 1000),
                execution_error=f"Patch application failed:\n{apply_proc.stderr or apply_proc.stdout}",
            )

        # 6. Restricted Docker command
        docker_cmd = [
            "docker", "run",
            "--name", container_id,
            "--rm",
            "--network", "none",
            "--memory", "512m",
            "--cpus", "1.0",
            "--pids-limit", "64",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "-e", "VERIFICATION_REPORT_PATH=/workspace/report/test_report.json",
            "-e", "PYTHONPATH=/workspace",
            "-v", f"{app_dest}:/workspace/verification/lab/app:rw",
            "-v", f"{tests_dest}:/workspace/verification/protected_tests:ro",
            "-v", f"{report_dir}:/workspace/report:rw",
            docker_image,
            "pytest", "/workspace/verification/protected_tests", "-v",
        ]

        timed_out = False
        raw_output = ""
        exit_code = 0
        runner_error = None

        try:
            proc = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_data, stderr_data = await asyncio.wait_for(
                proc.communicate(),
                timeout=float(request.timeout_seconds),
            )
            exit_code = proc.returncode if proc.returncode is not None else 1
            raw_output = stdout_data.decode("utf-8", errors="replace") + "\n" + stderr_data.decode("utf-8", errors="replace")
        except asyncio.TimeoutError:
            timed_out = True
            exit_code = -1
            raw_output = f"Execution timed out after {request.timeout_seconds}s."
            subprocess.run(["docker", "kill", container_id], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as exc:
            runner_error = str(exc)
            exit_code = 1

        duration_ms = int((time.time() - start_time) * 1000)

        # 7. Read report
        report_json_str = None
        if report_file_host.exists():
            report_json_str = report_file_host.read_text(encoding="utf-8")

        # 8. Evaluate results
        return TestResultEvaluator.evaluate(
            job_id=job_id,
            patch_hash=patch_hash,
            exit_code=exit_code,
            raw_output=sanitize_log(raw_output),
            report_json_str=report_json_str,
            duration_ms=duration_ms,
            timed_out=timed_out,
            runner_error=sanitize_log(runner_error) if runner_error else None,
        )

    finally:
        subprocess.run(["docker", "rm", "-f", container_id], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(temp_dir, ignore_errors=True)

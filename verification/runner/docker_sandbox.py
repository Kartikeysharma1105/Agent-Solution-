"""Restricted Disposable Docker Sandbox Runner (Layer 5).

Provides strict isolation:
1. Candidate patch applied inside an ephemeral disposable copy.
2. Immutable test suites mounted READ-ONLY (:ro) to prevent adversarial tampering.
3. Network access disabled (--network none) and Linux capabilities dropped (--cap-drop ALL).
4. Strictly bounded CPU and memory limits.
5. Independent result evaluation with timeout and crash detection.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from verification.contracts import (
    Verdict,
    VerificationRequest,
    VerificationResult,
)
from verification.runner.evaluator import TestResultEvaluator


class DockerSandboxRunner:
    """Manages ephemeral Docker lab containers for patch verification."""

    DEFAULT_IMAGE = "sentinel-verification-lab:latest"

    def __init__(
        self,
        image_name: str = DEFAULT_IMAGE,
        app_source_dir: Optional[str | Path] = None,
        tests_suite_dir: Optional[str | Path] = None,
    ) -> None:
        self.image_name = image_name
        base_dir = Path(__file__).resolve().parent.parent
        self.app_source_dir = Path(app_source_dir or (base_dir / "app"))
        self.tests_suite_dir = Path(tests_suite_dir or (base_dir / "tests_suite"))

    async def run(
        self,
        request: VerificationRequest,
        patch_hash: str,
        modified_paths: Sequence[str],
    ) -> VerificationResult:
        """Run candidate patch in an ephemeral disposable Docker container."""

        container_id = f"sentinel_verify_{uuid.uuid4().hex[:12]}"
        temp_dir = tempfile.mkdtemp(prefix="sentinel_sandbox_")

        try:
            # 1. Prepare ephemeral workspace copy
            workspace_dir = Path(temp_dir)
            app_dest = workspace_dir / "verification" / "app"
            app_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(self.app_source_dir, app_dest)

            # Copy tests_suite into temp dir to mount as ro volume
            suite_dest = workspace_dir / "verification" / "tests_suite"
            shutil.copytree(self.tests_suite_dir, suite_dest)

            # 2. Apply candidate patch to ephemeral target copy
            patch_file = workspace_dir / "candidate.patch"
            patch_file.write_text(request.patch_content, encoding="utf-8")

            # Try git apply or patch inside the workspace
            apply_proc = subprocess.run(
                ["patch", "-p1", "--input", str(patch_file)],
                cwd=str(workspace_dir / "verification"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            if apply_proc.returncode != 0:
                # Fallback to -p0 if -p1 failed
                apply_proc = subprocess.run(
                    ["patch", "-p0", "--input", str(patch_file)],
                    cwd=str(workspace_dir / "verification"),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

            if apply_proc.returncode != 0:
                return VerificationResult(
                    finding_id=request.finding_id,
                    verdict=Verdict.REJECTED_MALFORMED_PATCH,
                    is_verified=False,
                    patch_hash=patch_hash,
                    raw_runner_output=f"Patch application failed:\n{apply_proc.stdout}\n{apply_proc.stderr}",
                    failure_reflection_data={
                        "error_type": "PATCH_APPLY_FAILURE",
                        "stdout": apply_proc.stdout,
                        "stderr": apply_proc.stderr,
                    },
                )

            # Report directory mounted rw for output extraction
            report_dir = workspace_dir / "report"
            report_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(temp_dir, 0o777)
            os.chmod(report_dir, 0o777)
            report_host_path = report_dir / "test_report.json"

            # 3. Docker execution command with strict security isolation
            docker_cmd = [
                "docker", "run",
                "--name", container_id,
                "--rm",
                "--network", "none",                       # Network isolation
                "--memory", "512m",                        # Memory limit
                "--cpus", "1.0",                           # CPU limit
                "--cap-drop", "ALL",                       # Drop all root capabilities
                "--security-opt", "no-new-privileges",     # Prevent privilege escalation
                "-e", "VERIFICATION_REPORT_PATH=/workspace/report/test_report.json",
                "-e", "PYTHONPATH=/workspace",
                # Mount app copy (ephemeral)
                "-v", f"{app_dest}:/workspace/verification/app:rw",
                # Mount tests_suite strictly READ-ONLY (:ro) to prevent test tampering
                "-v", f"{suite_dest}:/workspace/verification/tests_suite:ro",
                # Mount report output directory
                "-v", f"{report_dir}:/workspace/report:rw",
                self.image_name,
                "pytest", "/workspace/verification/tests_suite", "-v",
            ]

            # Execute Docker run with timeout
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
                raw_output = (stdout_data.decode("utf-8", errors="replace") + "\n" +
                              stderr_data.decode("utf-8", errors="replace"))
            except asyncio.TimeoutError:
                timed_out = True
                exit_code = -1
                raw_output = f"Execution timed out after {request.timeout_seconds} seconds."
                # Forcefully kill container if still running
                subprocess.run(["docker", "kill", container_id], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as exc:
                runner_error = str(exc)
                exit_code = 1

            # 4. Read test report
            report_json_str = None
            if report_host_path.exists():
                report_json_str = report_host_path.read_text(encoding="utf-8")

            # 5. Evaluate results deterministically
            return TestResultEvaluator.evaluate(
                finding_id=request.finding_id,
                patch_hash=patch_hash,
                exit_code=exit_code,
                raw_output=raw_output,
                report_json_str=report_json_str,
                timed_out=timed_out,
                runner_error=runner_error,
            )

        finally:
            # Cleanup ephemeral container and directory unconditionally
            subprocess.run(["docker", "rm", "-f", container_id], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            shutil.rmtree(temp_dir, ignore_errors=True)

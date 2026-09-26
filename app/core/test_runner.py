"""
app/core/test_runner.py

Hardware-agnostic test runner.

Detects available build/test systems, executes tests,
captures output, and maps failures to the investigation.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from typing import Optional

from app.models.investigation import TestRunResult


# ---------------------------------------------------------------------------
# Detect available test commands for a project root
# ---------------------------------------------------------------------------

def detect_test_commands(project_root: str) -> list[tuple[str, list[str]]]:
    """
    Return a list of (label, argv) pairs for runnable test commands,
    ordered by preference.
    """
    commands = []

    # Unity / custom Makefile test target
    if _has_file(project_root, "Makefile") or _has_file(project_root, "makefile"):
        make = shutil.which("make") or shutil.which("mingw32-make")
        if make:
            commands.append(("make test", [make, "test"]))

    # CMake / CTest
    build_dir = os.path.join(project_root, "build")
    if os.path.isdir(build_dir) and shutil.which("ctest"):
        commands.append(("ctest", ["ctest", "--test-dir", build_dir, "--output-on-failure"]))

    # pytest
    if shutil.which("pytest"):
        commands.append(("pytest", ["pytest", project_root, "-v", "--tb=short"]))
    elif _has_file(project_root, "pytest.ini") or _has_file(project_root, "setup.cfg"):
        py = shutil.which("python") or shutil.which("python3")
        if py:
            commands.append(("python -m pytest", [py, "-m", "pytest", project_root, "-v"]))

    # PlatformIO
    if _has_file(project_root, "platformio.ini") and shutil.which("pio"):
        commands.append(("pio test", ["pio", "test"]))

    return commands


def run_tests(project_root: str, timeout: int = 60) -> list[TestRunResult]:
    """
    Detect and run all available tests. Returns results list.
    If no test system is found, returns a single UNAVAILABLE result.
    """
    commands = detect_test_commands(project_root)
    if not commands:
        return [TestRunResult(
            command="(no test system detected)",
            returncode=-1,
            stdout="",
            stderr="TEST EXECUTION UNAVAILABLE\n"
                   "No supported test framework detected in this project.",
            passed=None,
        )]

    results = []
    for label, argv in commands:
        result = _run_command(label, argv, cwd=project_root, timeout=timeout)
        results.append(result)

    return results


def run_command(command_str: str, cwd: str, timeout: int = 60) -> TestRunResult:
    """Run an arbitrary shell command and capture output."""
    import shlex
    argv = shlex.split(command_str)
    return _run_command(command_str, argv, cwd=cwd, timeout=timeout)


def _run_command(label: str, argv: list[str], cwd: str, timeout: int) -> TestRunResult:
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        duration = time.monotonic() - t0
        passed = proc.returncode == 0
        return TestRunResult(
            command=label,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            passed=passed,
            duration_s=duration,
        )
    except FileNotFoundError:
        return TestRunResult(
            command=label,
            returncode=-1,
            stdout="",
            stderr=f"Command not found: {argv[0]}",
            passed=False,
        )
    except subprocess.TimeoutExpired:
        return TestRunResult(
            command=label,
            returncode=-1,
            stdout="",
            stderr=f"Command timed out after {timeout}s: {label}",
            passed=False,
        )
    except Exception as exc:
        return TestRunResult(
            command=label,
            returncode=-1,
            stdout="",
            stderr=f"Error running command: {exc}",
            passed=False,
        )


def _has_file(root: str, name: str) -> bool:
    return os.path.isfile(os.path.join(root, name))


def parse_test_failures(results: list[TestRunResult]) -> list[str]:
    """Extract failure messages from test run output."""
    failures = []
    for r in results:
        if r.passed is False or r.returncode != 0:
            combined = (r.stderr + "\n" + r.stdout).strip()
            # Try to extract meaningful lines
            for line in combined.splitlines():
                if re.search(r"(FAIL|ERROR|assert|ASSERT|error)", line, re.IGNORECASE):
                    failures.append(line.strip())
            if not failures:
                failures.append(f"{r.command}: exit {r.returncode}")
    return failures[:20]

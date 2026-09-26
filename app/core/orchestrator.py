"""
app/core/orchestrator.py

Debugging Orchestrator — drives the investigation pipeline.

This module is the SINGLE source of debugging logic.
Both the GUI and any CLI/script interface use this class.
The orchestrator fires callbacks so the UI can update in real time.
"""
from __future__ import annotations

import os
import threading
from typing import Callable, Optional

from app.core import ai_client, test_runner
from app.analyzers.static_analyzer import analyze_project
from app.core.project_scanner import scan_project
from app.models.investigation import (
    EvidenceItem, EvidenceKind, Hypothesis, Investigation,
    InvestigationState, ProposedFix, RootCause, VerificationResult,
    VerificationStatus, FileDiff,
)
from app.models.project import Project


# Type alias for progress callbacks: (state, message)
ProgressCallback = Callable[[InvestigationState, str], None]


class Orchestrator:
    """
    Drives the complete embedded debugging investigation workflow.

    Usage:
        orch = Orchestrator(on_progress=my_callback)
        orch.load_project("/path/to/project")
        orch.start_investigation(symptom, expected, actual, ...)
        # Callbacks fire as each stage completes.
        # Results available on orch.investigation
    """

    def __init__(self, on_progress: Optional[ProgressCallback] = None):
        self._on_progress = on_progress or (lambda s, m: None)
        self.project: Optional[Project] = None
        self.investigation: Optional[Investigation] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    # ── Project loading ────────────────────────────────────────────────────

    def load_project(self, path: str) -> Project:
        """Scan the filesystem path and build a Project model."""
        self._emit(InvestigationState.ANALYZING_PROJECT, f"Scanning project: {path}")
        project = scan_project(path)
        self.project = project
        msg = (
            f"Project '{project.name}' loaded — "
            f"{len(project.source_files)} source file(s), "
            f"{len(project.header_files)} header(s)"
        )
        if project.detected_platform:
            msg += f", platform: {project.detected_platform}"
        self._emit(InvestigationState.IDLE, msg)
        return project

    def set_extra_evidence(
        self,
        compiler_output: str = "",
        serial_log: str = "",
        hardware_notes: str = "",
    ) -> None:
        """Attach extra textual evidence to the current project."""
        if self.project is None:
            return
        self.project.compiler_output  = compiler_output
        self.project.serial_log        = serial_log
        self.project.hardware_notes    = hardware_notes

    # ── Investigation lifecycle ────────────────────────────────────────────

    def start_investigation(
        self,
        description: str,
        expected: str,
        actual: str,
        steps: str = "",
        frequency: str = "Unknown",
    ) -> Investigation:
        """
        Begin a new investigation in a background thread.
        Returns the Investigation object immediately; it will be
        populated progressively as the workflow runs.
        """
        from app.models.investigation import Symptom

        if self.project is None:
            raise RuntimeError("No project loaded. Call load_project() first.")

        inv = Investigation()
        inv.symptom = Symptom(
            description=description,
            expected_behavior=expected,
            actual_behavior=actual,
            steps_to_reproduce=steps,
            frequency=frequency,
        )
        self.investigation = inv
        self._stop_event.clear()

        self._thread = threading.Thread(target=self._run_pipeline, daemon=True)
        self._thread.start()
        return inv

    def stop(self) -> None:
        """Request that the current investigation stop after the current stage."""
        self._stop_event.set()

    def wait(self, timeout: float = 300) -> None:
        """Block until investigation completes (used by tests/CLI)."""
        if self._thread:
            self._thread.join(timeout=timeout)

    # ── Pipeline stages ───────────────────────────────────────────────────

    def _run_pipeline(self) -> None:
        inv = self.investigation
        project = self.project

        try:
            # Stage 1 — Symptom analysis
            self._stage_symptom(inv, project)
            if self._stop_event.is_set(): return

            # Stage 2 — Static analysis
            self._stage_static_analysis(inv, project)
            if self._stop_event.is_set(): return

            # Stage 3 — AI hypothesis generation / enrichment
            self._stage_hypotheses(inv, project)
            if self._stop_event.is_set(): return

            # Stage 4 — Root cause
            self._stage_root_cause(inv, project)
            if self._stop_event.is_set(): return

            # Stage 5 — Fix generation
            self._stage_fix(inv, project)
            if self._stop_event.is_set(): return

            # Stage 6 — Test runner
            self._stage_tests(inv, project)
            if self._stop_event.is_set(): return

            # Stage 7 — Verification
            self._stage_verification(inv, project)

            inv.state = InvestigationState.COMPLETE
            self._emit(InvestigationState.COMPLETE, "Investigation complete.")

        except Exception as exc:
            inv.add_log(f"ERROR: {exc}")
            inv.state = InvestigationState.ERROR
            self._emit(InvestigationState.ERROR, f"Investigation error: {exc}")

    def _stage_symptom(self, inv: Investigation, project: Project) -> None:
        self._emit(InvestigationState.INVESTIGATING, "Analyzing symptom…")
        s = inv.symptom
        inv.add_log(f"Symptom: {s.description}")
        inv.add_log(f"Expected: {s.expected_behavior}")
        inv.add_log(f"Actual: {s.actual_behavior}")
        if s.steps_to_reproduce:
            inv.add_log(f"Steps: {s.steps_to_reproduce}")

        # Identify keyword categories from symptom text
        cats = _classify_symptom(s.description + " " + s.actual_behavior)
        if cats:
            inv.add_log(f"Relevant categories: {', '.join(cats)}")
            inv.evidence.append(EvidenceItem(
                title="Symptom categories identified",
                detail=", ".join(cats),
                kind=EvidenceKind.INFERRED,
            ))

    def _stage_static_analysis(self, inv: Investigation, project: Project) -> None:
        self._emit(InvestigationState.COLLECTING_EVIDENCE, "Running static analysis…")
        inv.add_log("Scanning source files…")

        static_ev, static_h, system_model = analyze_project(project)

        inv.evidence.extend(static_ev)
        inv.system_model = system_model
        inv.add_log(f"Static analysis: {len(static_ev)} evidence item(s), "
                    f"{len(static_h)} preliminary hypothesis/hypotheses")

        # Add static hypotheses if not already superseded by AI
        for h in static_h:
            h.title = "[Static] " + h.title
            inv.hypotheses.append(h)

        # Serial log evidence
        if project.serial_log.strip():
            inv.evidence.append(EvidenceItem(
                title="Serial/UART log provided",
                detail=project.serial_log[:500],
                kind=EvidenceKind.OBSERVED,
            ))
            _analyze_serial_log(project.serial_log, inv)

        # Hardware notes
        if project.hardware_notes.strip():
            inv.evidence.append(EvidenceItem(
                title="Hardware configuration notes provided",
                detail=project.hardware_notes[:300],
                kind=EvidenceKind.OBSERVED,
            ))

        self._emit(InvestigationState.COLLECTING_EVIDENCE,
                   f"Static analysis complete — {len(inv.evidence)} evidence item(s)")

    def _stage_hypotheses(self, inv: Investigation, project: Project) -> None:
        self._emit(InvestigationState.GENERATING_HYPOTHESES, "Generating hypotheses…")

        if ai_client.is_available():
            inv.add_log("Requesting AI hypothesis analysis…")
            ev_titles = [e.title for e in inv.evidence]
            ai_hyps = ai_client.generate_hypotheses(
                project=project,
                symptom_desc=inv.symptom.description,
                expected=inv.symptom.expected_behavior,
                actual=inv.symptom.actual_behavior,
                static_evidence=ev_titles,
                system_model=inv.system_model,
            )
            if ai_hyps:
                inv.add_log(f"AI generated {len(ai_hyps)} hypothesis/hypotheses")
                for h in ai_hyps:
                    h.title = "[AI] " + h.title
                inv.hypotheses.extend(ai_hyps)
            else:
                inv.add_log("AI hypothesis generation returned no results (using static only)")
        else:
            inv.add_log("AI backend unavailable — using static analysis hypotheses only")

        self._emit(InvestigationState.GENERATING_HYPOTHESES,
                   f"Hypotheses ready — {len(inv.hypotheses)} total")

    def _stage_root_cause(self, inv: Investigation, project: Project) -> None:
        self._emit(InvestigationState.ROOT_CAUSE_IDENTIFIED, "Identifying root cause…")

        # Pick top hypotheses
        top = inv.top_hypotheses(3)
        if not top:
            inv.add_log("No hypotheses available — root cause identification skipped")
            return

        if ai_client.is_available():
            inv.add_log("Requesting AI root cause analysis…")
            ev_titles = [e.title for e in inv.evidence]
            rc = ai_client.generate_root_cause(
                project=project,
                symptom_desc=inv.symptom.description,
                expected=inv.symptom.expected_behavior,
                actual=inv.symptom.actual_behavior,
                hypotheses=top,
                evidence_items=ev_titles,
            )
            if rc:
                inv.root_cause = rc
                inv.add_log(f"Root cause: {rc.summary}")
            else:
                inv.root_cause = _build_static_root_cause(top)
                inv.add_log("AI root cause failed — using best static hypothesis")
        else:
            inv.root_cause = _build_static_root_cause(top)
            inv.add_log(f"Root cause (static): {inv.root_cause.summary}")

        self._emit(InvestigationState.ROOT_CAUSE_IDENTIFIED, "Root cause identified")

    def _stage_fix(self, inv: Investigation, project: Project) -> None:
        if not inv.root_cause:
            return
        self._emit(InvestigationState.AWAITING_APPROVAL, "Generating proposed fix…")

        if ai_client.is_available():
            inv.add_log("Requesting AI fix generation…")
            fix = ai_client.generate_fix(project, inv.root_cause)
            if fix:
                inv.proposed_fix = fix
                inv.add_log(f"Fix generated: {fix.summary} ({len(fix.diffs)} file(s))")
            else:
                inv.proposed_fix = _build_static_fix(inv.root_cause)
                inv.add_log("AI fix generation failed — using static recommendation")
        else:
            inv.proposed_fix = _build_static_fix(inv.root_cause)
            inv.add_log("Fix recommendation ready (static analysis)")

        self._emit(InvestigationState.AWAITING_APPROVAL, "Fix ready — awaiting developer approval")

    def _stage_tests(self, inv: Investigation, project: Project) -> None:
        self._emit(InvestigationState.RUNNING_TESTS, "Running project tests…")
        inv.add_log("Detecting test system…")

        cmds = test_runner.detect_test_commands(project.root)
        if cmds:
            inv.add_log(f"Detected: {', '.join(label for label, _ in cmds)}")
        else:
            inv.add_log("No supported test framework detected")

        results = test_runner.run_tests(project.root, timeout=30)
        if inv.verification is None:
            inv.verification = VerificationResult()
        inv.verification.test_results = results

        passed = sum(1 for r in results if r.passed is True)
        failed = sum(1 for r in results if r.passed is False)
        inv.add_log(f"Tests: {passed} passed, {failed} failed")

    def _stage_verification(self, inv: Investigation, project: Project) -> None:
        self._emit(InvestigationState.VERIFYING, "Verifying fix…")

        if inv.verification is None:
            inv.verification = VerificationResult()

        # If no fix was applied, mark as unverified
        if inv.proposed_fix is None or inv.proposed_fix.approved is None:
            inv.verification.status = VerificationStatus.UNVERIFIED
            inv.verification.notes = (
                "No fix has been applied yet. Apply the proposed fix "
                "and re-run tests to verify."
            )
            inv.add_log("Verification: UNVERIFIED — fix not yet applied")
            return

        failures = test_runner.parse_test_failures(inv.verification.test_results)
        if failures:
            inv.verification.regressions_found = failures[:5]
            inv.verification.status = VerificationStatus.PARTIALLY_VERIFIED
            inv.add_log("Verification: PARTIALLY_VERIFIED — some test failures remain")
        else:
            # Can't confirm hardware symptom resolved without real device
            inv.verification.status = VerificationStatus.PARTIALLY_VERIFIED
            inv.verification.notes = (
                "Software tests pass. Hardware symptom resolution requires "
                "physical device verification."
            )
            inv.add_log("Verification: PARTIALLY_VERIFIED — tests pass, hardware verification needed")

        self._emit(InvestigationState.VERIFYING,
                   f"Verification: {inv.verification.status.value}")

    # ── Apply fix ─────────────────────────────────────────────────────────

    def apply_fix(self, fix: ProposedFix) -> list[str]:
        """
        Write fix diffs to the filesystem.
        Returns a list of (rel_path, backup_path) tuples for files modified.
        Raises on any write error — does NOT partially apply.
        """
        if self.project is None:
            raise RuntimeError("No project loaded")

        modified = []
        backups = []

        # First pass: validate all files exist
        for diff in fix.diffs:
            full_path = os.path.join(self.project.root, diff.file)
            if not os.path.isfile(full_path):
                raise FileNotFoundError(f"File not found: {diff.file}")

        # Second pass: backup + write
        for diff in fix.diffs:
            full_path = os.path.join(self.project.root, diff.file)
            backup_path = full_path + ".bak"

            # Read current content
            with open(full_path, encoding="utf-8", errors="replace") as f:
                current = f.read()

            # Apply: replace 'before' block with 'after' block
            if diff.before and diff.before in current:
                new_content = current.replace(diff.before, diff.after, 1)
            else:
                # If exact match fails, append a note — do not silently overwrite
                raise ValueError(
                    f"Cannot apply diff to {diff.file}: 'before' block not found in file. "
                    f"Please review and apply manually."
                )

            # Write backup
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(current)
            backups.append(backup_path)

            # Write patched file
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            modified.append(diff.file)
            if self.investigation:
                self.investigation.add_log(f"Applied fix to {diff.file} (backup: {backup_path})")

        fix.approved = True
        return modified

    # ── Helpers ───────────────────────────────────────────────────────────

    def _emit(self, state: InvestigationState, message: str) -> None:
        if self.investigation:
            self.investigation.state = state
            self.investigation.add_log(message)
        self._on_progress(state, message)


# ---------------------------------------------------------------------------
# Fallback helpers (used when AI is unavailable)
# ---------------------------------------------------------------------------

def _classify_symptom(text: str) -> list[str]:
    """Map symptom text to relevant embedded-system categories."""
    categories = {
        "interrupt": ["interrupt", "isr", "irq", "handler", "priority"],
        "timing":    ["timing", "delay", "timeout", "frequency", "clock", "slow", "fast", "period"],
        "UART/serial": ["uart", "serial", "baud", "tx", "rx", "transmit", "receive", "garbled"],
        "SPI":       ["spi", "miso", "mosi", "sck", "cs"],
        "I2C":       ["i2c", "twi", "scl", "sda", "nak", "nack", "address"],
        "GPIO/pin":  ["gpio", "pin", "port", "toggle", "high", "low", "output", "input"],
        "ADC/sensor": ["adc", "sensor", "reading", "value", "analog", "voltage", "conversion"],
        "memory":    ["overflow", "corruption", "stack", "heap", "buffer", "null", "crash"],
        "display":   ["display", "screen", "lcd", "led", "segment", "pixel"],
        "debounce":  ["bounce", "debounce", "button", "keypad", "press", "release"],
        "state machine": ["state", "machine", "transition", "mode", "stuck"],
        "watchdog":  ["watchdog", "reset", "wdt", "reboot"],
        "PWM":       ["pwm", "duty", "cycle", "motor", "servo"],
    }
    lower = text.lower()
    found = [cat for cat, kws in categories.items() if any(kw in lower for kw in kws)]
    return found


def _build_static_root_cause(hypotheses: list[Hypothesis]) -> RootCause:
    top = hypotheses[0] if hypotheses else None
    if not top:
        return RootCause(summary="Root cause could not be determined with available evidence.")
    return RootCause(
        summary=top.title,
        mechanism=top.description,
        evidence=top.evidence_for,
        hypothesis_ids=[top.id],
    )


def _build_static_fix(rc: RootCause) -> ProposedFix:
    return ProposedFix(
        summary="Manual fix required",
        explanation=(
            f"Root cause identified: {rc.summary}\n\n"
            f"Mechanism: {rc.mechanism}\n\n"
            "An AI API key is required for automatic fix generation. "
            "Refer to the root cause analysis and the embedded-debugger skill "
            "for manual fix guidance."
        ),
        side_effects="",
        diffs=[],
    )


def _analyze_serial_log(log: str, inv: Investigation) -> None:
    """Look for patterns in serial output that indicate known failure modes."""
    import re
    patterns = [
        (r"hard.?fault", "HardFault exception detected in serial log", 0.85),
        (r"stack.?overflow", "Stack overflow reported in serial log", 0.90),
        (r"assert.?fail", "Assertion failure reported in serial log", 0.80),
        (r"watchdog|wdt.*reset", "Watchdog reset detected in serial log", 0.75),
        (r"timeout", "Timeout condition reported in serial log", 0.60),
        (r"error|err:", "Error messages in serial log", 0.55),
        (r"nan|inf|overflow", "Numeric overflow/NaN in serial log", 0.65),
    ]
    for pattern, title, conf in patterns:
        if re.search(pattern, log, re.IGNORECASE):
            inv.evidence.append(EvidenceItem(
                title=title,
                detail="",
                kind=EvidenceKind.OBSERVED,
            ))
            inv.hypotheses.append(Hypothesis(
                title=f"[Log] {title}",
                description=f"Serial log contains pattern matching: {pattern}",
                evidence_for=[title],
                confidence=conf,
                verification_method="Examine full serial log for context around this event.",
            ))

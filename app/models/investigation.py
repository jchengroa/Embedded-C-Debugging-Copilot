"""
app/models/investigation.py

All domain objects for a single debugging investigation.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional


class EvidenceKind(str, Enum):
    OBSERVED   = "OBSERVED"
    INFERRED   = "INFERRED"
    ASSUMED    = "ASSUMED"
    UNVERIFIED = "UNVERIFIED"


class VerificationStatus(str, Enum):
    VERIFIED           = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    UNVERIFIED         = "UNVERIFIED"
    FAILED             = "FAILED"


class InvestigationState(str, Enum):
    IDLE                  = "IDLE"
    ANALYZING_PROJECT     = "ANALYZING PROJECT"
    INVESTIGATING         = "INVESTIGATING"
    COLLECTING_EVIDENCE   = "COLLECTING EVIDENCE"
    GENERATING_HYPOTHESES = "GENERATING HYPOTHESES"
    ROOT_CAUSE_IDENTIFIED = "ROOT CAUSE IDENTIFIED"
    AWAITING_APPROVAL     = "AWAITING APPROVAL"
    APPLYING_FIX          = "APPLYING FIX"
    RUNNING_TESTS         = "RUNNING TESTS"
    VERIFYING             = "VERIFYING"
    COMPLETE              = "COMPLETE"
    BLOCKED               = "BLOCKED"
    ERROR                 = "ERROR"


# ---------------------------------------------------------------------------

@dataclass
class Symptom:
    description:       str
    expected_behavior: str
    actual_behavior:   str
    steps_to_reproduce: str = ""
    frequency:         str = "Unknown"   # Always / Sometimes / Unknown
    additional_context: str = ""


@dataclass
class EvidenceItem:
    id:          str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title:       str = ""
    detail:      str = ""
    kind:        EvidenceKind = EvidenceKind.UNVERIFIED
    source_file: Optional[str] = None
    line_number:  Optional[int] = None
    function:    Optional[str] = None
    timestamp:   datetime = field(default_factory=datetime.now)

    def label(self) -> str:
        return f"[{self.kind.value}] {self.title}"


@dataclass
class Hypothesis:
    id:           str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title:        str = ""
    description:  str = ""
    evidence_for:  list[str] = field(default_factory=list)
    evidence_against: list[str] = field(default_factory=list)
    source_locations: list[tuple[str, int, str]] = field(default_factory=list)
    # (file, line, note)
    confidence:   float = 0.0   # 0.0 – 1.0
    verification_method: str = ""
    confirmed:    Optional[bool] = None

    def confidence_pct(self) -> int:
        return round(self.confidence * 100)


@dataclass
class DiagnosticTest:
    id:          str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name:        str = ""
    description: str = ""
    hypothesis_id: Optional[str] = None
    code_before: str = ""
    code_after:  str = ""
    file:        Optional[str] = None
    expected_observation: str = ""
    actual_observation:   str = ""
    passed:      Optional[bool] = None


@dataclass
class RootCause:
    summary:      str = ""
    mechanism:    str = ""
    evidence:     list[str] = field(default_factory=list)
    source_locations: list[tuple[str, int, str]] = field(default_factory=list)
    hypothesis_ids: list[str] = field(default_factory=list)


@dataclass
class FileDiff:
    file:       str
    before:     str
    after:      str
    explanation: str = ""

    def unified_diff_lines(self) -> list[str]:
        """Return a simple line-level diff for display."""
        import difflib
        before_lines = self.before.splitlines(keepends=True)
        after_lines  = self.after.splitlines(keepends=True)
        return list(difflib.unified_diff(
            before_lines, after_lines,
            fromfile=f"a/{self.file}",
            tofile=f"b/{self.file}",
        ))


@dataclass
class ProposedFix:
    id:           str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    summary:      str = ""
    explanation:  str = ""
    side_effects: str = ""
    diffs:        list[FileDiff] = field(default_factory=list)
    root_cause_id: Optional[str] = None
    approved:     Optional[bool] = None


@dataclass
class TestRunResult:
    command:    str
    returncode: int
    stdout:     str
    stderr:     str
    passed:     Optional[bool] = None
    duration_s: float = 0.0

    @property
    def success(self) -> bool:
        return self.returncode == 0


@dataclass
class VerificationResult:
    status:        VerificationStatus = VerificationStatus.UNVERIFIED
    symptom_resolved: Optional[bool] = None
    regressions_found: list[str] = field(default_factory=list)
    test_results:  list[TestRunResult] = field(default_factory=list)
    notes:         str = ""


@dataclass
class Investigation:
    """
    Top-level container for one complete debugging session.
    """
    id:        str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created:   datetime = field(default_factory=datetime.now)
    symptom:   Optional[Symptom] = None
    state:     InvestigationState = InvestigationState.IDLE

    # Populated progressively
    system_model:    str = ""            # human-readable system map
    evidence:        list[EvidenceItem]  = field(default_factory=list)
    hypotheses:      list[Hypothesis]    = field(default_factory=list)
    root_cause:      Optional[RootCause] = None
    diagnostic_tests: list[DiagnosticTest] = field(default_factory=list)
    proposed_fix:    Optional[ProposedFix] = None
    verification:    Optional[VerificationResult] = None
    regression_tests: list[DiagnosticTest] = field(default_factory=list)

    # Log visible in the status area
    log: list[str] = field(default_factory=list)

    def add_log(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.log.append(f"[{ts}] {msg}")

    def top_hypotheses(self, n: int = 5) -> list[Hypothesis]:
        return sorted(self.hypotheses, key=lambda h: h.confidence, reverse=True)[:n]

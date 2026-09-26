"""
app/analyzers/static_analyzer.py

Hardware-agnostic static analysis of embedded C/C++ source code.

Produces EvidenceItems and populates the system_model string.
Does NOT require a compiler or external tool — pure Python regex/text analysis.
"""
from __future__ import annotations

import re
from typing import Optional

from app.models.investigation import EvidenceItem, EvidenceKind, Hypothesis
from app.models.project import Project


# ---------------------------------------------------------------------------
# Patterns (hardware-agnostic — applied to any C/C++ source)
# ---------------------------------------------------------------------------

# ISR function signatures across toolchains
_ISR_PATTERNS = [
    r"\bISR\s*\(",                          # avr-libc
    r"__interrupt\b",                       # IAR / Cosmic
    r"__irq\b",                             # RVCT
    r"void\s+\w+_IRQHandler\s*\(",          # CMSIS (STM32 etc.)
    r"void\s+\w+_Handler\s*\(",             # generic CMSIS
    r"#pragma\s+interrupt",                 # HCS/PIC
    r"\bINTERRUPT\b",                       # various
    r"__attribute__.*interrupt",            # GCC generic
]

# Shared-state hazards
_VOLATILE_MISSING = re.compile(
    r"^(?!.*\bvolatile\b).*\b(uint8_t|uint16_t|uint32_t|uint64_t|int|char|bool|"
    r"float|double)\s+(\w+)\s*[=;]",
    re.MULTILINE,
)

# Peripheral register write patterns (generic: reg = value, REG |= mask)
_REGISTER_WRITE = re.compile(
    r"\b([A-Z][A-Z0-9_]{2,})\s*(\|=|-=|\^=|&=|=)\s*",
)

# Buffer / array operations that may overflow
_MEMCPY = re.compile(r"\bmemcpy\s*\(")
_STRCPY = re.compile(r"\bstrcpy\s*\(")
_SPRINTF = re.compile(r"\bsprintf\s*\(")

# Delay calls
_DELAY_CALL = re.compile(r"\b_?delay_?(ms|us|cycles)?\s*\(", re.IGNORECASE)

# cli/sei or equivalent critical sections
_CRITICAL_ENTER = re.compile(r"\b(cli|__disable_irq|taskENTER_CRITICAL|portDISABLE_INTERRUPTS)\s*\(", re.IGNORECASE)
_CRITICAL_EXIT  = re.compile(r"\b(sei|__enable_irq|taskEXIT_CRITICAL|portENABLE_INTERRUPTS)\s*\(", re.IGNORECASE)

# Communication peripherals (UART/SPI/I2C/CAN/USB)
_COMM_PATTERNS = re.compile(
    r"\b(UART|USART|SPI|I2C|TWI|CAN|USB|SERIAL)\w*\s*[(\[=]",
    re.IGNORECASE,
)

# Timer / counter
_TIMER_PATTERNS = re.compile(r"\b(TIM|TIMER|TCCRn?|OCR|ICR|TIMSK)\w*\b", re.IGNORECASE)

# ADC / DAC
_ADC_DAC = re.compile(r"\b(ADC|DAC|ADCSR|ADCSRA|ADMUX)\w*\b", re.IGNORECASE)

# Watchdog
_WDT = re.compile(r"\b(WDT|WDTO|wdt_reset|watchdog)\w*\b", re.IGNORECASE)

# DMA
_DMA = re.compile(r"\bDMA\w*\b", re.IGNORECASE)

# PWM
_PWM = re.compile(r"\bPWM\w*\b", re.IGNORECASE)


def analyze_project(project: Project) -> tuple[list[EvidenceItem], list[Hypothesis], str]:
    """
    Run static analysis on all source files in the project.

    Returns:
        evidence    — list of EvidenceItem
        hypotheses  — list of Hypothesis (preliminary, confidence < 1.0)
        system_model — human-readable description of the system
    """
    evidence: list[EvidenceItem] = []
    hypotheses: list[Hypothesis] = []
    system_model_parts: list[str] = []

    isr_functions:      list[tuple[str, int, str]] = []   # (file, line, name)
    global_vars:        list[tuple[str, int, str]] = []   # (file, line, decl)
    volatile_vars:      list[tuple[str, int, str]] = []
    non_volatile_candidates: list[tuple[str, int, str]] = []
    critical_sections:  list[tuple[str, str]] = []        # (file, pattern)
    peripheral_uses:    list[tuple[str, str, int]] = []   # (file, peripheral, line)
    memory_ops:         list[tuple[str, int, str]] = []
    delay_calls:        list[tuple[str, int]] = []

    # ── Per-file analysis ─────────────────────────────────────────────────
    for pf in project.source_files + project.header_files:
        content = pf.load_content()
        if not content.strip():
            continue
        lines = content.splitlines()
        file_has_isr = False

        for lineno, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue

            # ISR detection
            if any(re.search(p, line) for p in _ISR_PATTERNS):
                name = _extract_isr_name(line)
                isr_functions.append((pf.rel_path, lineno, name))
                file_has_isr = True

            # Volatile variables
            if re.search(r"\bvolatile\b", line):
                m = re.search(r"volatile\s+\w[\w\s\*]+\s+(\w+)\s*[=;,\[]", line)
                if m:
                    volatile_vars.append((pf.rel_path, lineno, m.group(1)))

            # Global/static non-volatile candidates (file scope, not inside {})
            # Simple heuristic: line at column 0, has a type keyword, no volatile
            if (not line.startswith(" ") and not line.startswith("\t")
                    and re.match(r"^(static\s+)?(const\s+)?(unsigned\s+|signed\s+)?(\w+)\s+(\w+)", line)
                    and "volatile" not in line
                    and "typedef" not in line
                    and "#" not in line):
                non_volatile_candidates.append((pf.rel_path, lineno, line.rstrip()))

            # Critical sections
            if _CRITICAL_ENTER.search(line):
                critical_sections.append((pf.rel_path, "enter"))
            if _CRITICAL_EXIT.search(line):
                critical_sections.append((pf.rel_path, "exit"))

            # Peripheral register accesses
            for m in _REGISTER_WRITE.finditer(line):
                peripheral_uses.append((pf.rel_path, m.group(1), lineno))

            # Communication interfaces
            if _COMM_PATTERNS.search(line):
                evidence.append(EvidenceItem(
                    title=f"Communication interface used in {pf.filename}:{lineno}",
                    detail=line.strip(),
                    kind=EvidenceKind.OBSERVED,
                    source_file=pf.rel_path,
                    line_number=lineno,
                ))

            # Memory operations
            for pat, label in [(_MEMCPY, "memcpy"), (_STRCPY, "strcpy"), (_SPRINTF, "sprintf")]:
                if pat.search(line):
                    memory_ops.append((pf.rel_path, lineno, label))

            # Delay calls
            if _DELAY_CALL.search(line):
                delay_calls.append((pf.rel_path, lineno))

        # Summarise per-file findings
        if file_has_isr:
            evidence.append(EvidenceItem(
                title=f"Interrupt service routine(s) found in {pf.filename}",
                detail=f"File contains ISR definitions — shared state must be volatile and access must be atomic.",
                kind=EvidenceKind.OBSERVED,
                source_file=pf.rel_path,
            ))

    # ── Cross-file analysis ───────────────────────────────────────────────

    # 1. ISR + non-volatile global → concurrency hazard hypothesis
    if isr_functions and non_volatile_candidates:
        h = Hypothesis(
            title="ISR/foreground shared-state race condition",
            description=(
                "One or more global variables are accessed from both ISR context "
                "and foreground code without volatile qualification or atomic protection. "
                "This can cause the compiler to cache stale values in registers, or the "
                "ISR to observe a partially-updated multi-step write."
            ),
            evidence_for=[
                f"ISR found: {f}:{l} — {n}" for f, l, n in isr_functions[:3]
            ] + [
                f"Non-volatile global candidate: {f}:{l}" for f, l, _ in non_volatile_candidates[:3]
            ],
            evidence_against=[
                "Cannot confirm without runtime observation.",
                "Some variables may only be written before ISRs are enabled.",
            ],
            source_locations=[(f, l, n) for f, l, n in isr_functions[:5]],
            confidence=0.72,
            verification_method=(
                "Add volatile qualifier to suspects; bracket multi-step updates with "
                "cli()/sei() or equivalent; observe whether symptom disappears."
            ),
        )
        hypotheses.append(h)
        evidence.append(EvidenceItem(
            title=f"Potential ISR/main shared-state hazard ({len(isr_functions)} ISR(s), "
                  f"{len(non_volatile_candidates)} non-volatile global(s))",
            detail="Variables shared between ISR and foreground without volatile or atomicity protection.",
            kind=EvidenceKind.INFERRED,
        ))

    # 2. Missing critical sections around multi-step writes
    enters = sum(1 for _, t in critical_sections if t == "enter")
    exits  = sum(1 for _, t in critical_sections if t == "exit")
    if isr_functions and (enters == 0 or abs(enters - exits) > 2):
        h = Hypothesis(
            title="Non-atomic multi-step shared variable update",
            description=(
                "ISR-shared variables appear to be updated in multi-step operations "
                "without disabling interrupts. If the ISR fires between individual writes, "
                "it can observe a partially-updated state."
            ),
            evidence_for=[
                f"Only {enters} interrupt-disable calls found across {len(project.source_files)} source files.",
                f"ISR count: {len(isr_functions)}.",
            ],
            evidence_against=["Some platforms use RTOS primitives not detected by this scan."],
            confidence=0.58,
            verification_method="Bracket all multi-step writes to ISR-shared variables with interrupt-disable/enable.",
        )
        hypotheses.append(h)

    # 3. Unsafe memory operations
    unsafe_ops = [(f, l, op) for f, l, op in memory_ops if op in ("strcpy", "sprintf")]
    if unsafe_ops:
        h = Hypothesis(
            title="Potential buffer overflow (unsafe string/memory operation)",
            description=(
                "Use of strcpy or sprintf without bounds checking may overflow "
                "stack-allocated or fixed-size heap buffers, corrupting adjacent state."
            ),
            evidence_for=[f"{op} at {f}:{l}" for f, l, op in unsafe_ops[:4]],
            evidence_against=["Buffers may be correctly sized for all inputs."],
            source_locations=[(f, l, op) for f, l, op in unsafe_ops[:5]],
            confidence=0.40,
            verification_method="Replace with snprintf/strlcpy; add assert for destination size.",
        )
        hypotheses.append(h)

    # 4. No delays detected on communication/peripheral code
    if peripheral_uses and not delay_calls:
        h = Hypothesis(
            title="Missing timing delays — peripheral setup/settling time",
            description=(
                "Peripheral registers are configured but no delay calls are present. "
                "Some peripherals require a settling or startup delay after configuration "
                "before the first read/write."
            ),
            evidence_for=[
                f"Register access: {f}:{l} ({reg})" for f, reg, l in peripheral_uses[:3]
            ],
            evidence_against=["Delays may be implemented via polling loops or DWT cycles."],
            confidence=0.35,
            verification_method="Insert a short delay after peripheral initialisation and observe whether symptom changes.",
        )
        hypotheses.append(h)

    # 5. Integer narrowing / overflow in arithmetic expressions
    #    Look for patterns like: (int16_t)(expr * large_constant) or cast-then-multiply
    _INT_OVERFLOW = re.compile(
        r"\(\s*(int8_t|int16_t|uint8_t|uint16_t)\s*\)\s*\([^)]*\*[^)]*\)"
        r"|"
        r"\b(int16_t|int8_t|uint8_t)\s+\w+\s*=\s*\([^;]*\*[^;]*[0-9]{3,}",
    )
    overflow_candidates: list[tuple[str, int, str]] = []
    for pf in project.source_files:
        content = pf.load_content()
        for lineno, line in enumerate(content.splitlines(), start=1):
            if _INT_OVERFLOW.search(line) and "volatile" not in line:
                overflow_candidates.append((pf.rel_path, lineno, line.strip()))

    if overflow_candidates:
        h = Hypothesis(
            title="Integer overflow in arithmetic expression (narrow type cast)",
            description=(
                "Arithmetic involving a narrow integer type (int8_t, int16_t, uint8_t, uint16_t) "
                "where a large constant multiplier may overflow the type's range before or during "
                "the assignment. This commonly causes sensor conversion formulas to produce "
                "impossible out-of-range values."
            ),
            evidence_for=[
                f"Potential overflow: {f}:{l} — {code[:80]}"
                for f, l, code in overflow_candidates[:4]
            ],
            evidence_against=["Inputs may always be small enough to avoid overflow."],
            source_locations=[(f, l, code[:40]) for f, l, code in overflow_candidates[:5]],
            confidence=0.65,
            verification_method=(
                "Cast operands to a wider type before multiplication, "
                "e.g. (int32_t)raw * 500 / 1023."
            ),
        )
        hypotheses.append(h)
        for f, l, code in overflow_candidates[:4]:
            evidence.append(EvidenceItem(
                title=f"Potential integer overflow at {f}:{l}",
                detail=code,
                kind=EvidenceKind.INFERRED,
                source_file=f,
                line_number=l,
            ))

    # 6. ADC / multi-byte peripheral register read order (platform-specific heuristic)
    #    On many 8-bit MCUs, the low byte of a two-byte result register must be read first.
    _ADC_BYTE_ORDER = re.compile(r"\bADCH\b.*\bADCL\b|\bMSB\b.*\bLSB\b", re.DOTALL)
    for pf in project.source_files:
        content = pf.load_content()
        # Check if ADCH appears before ADCL on consecutive lines
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if "ADCH" in line and i + 1 < len(lines) and "ADCL" in lines[i + 1]:
                h = Hypothesis(
                    title="ADC result bytes read in wrong order (ADCH before ADCL)",
                    description=(
                        "On many 8-bit microcontrollers, reading the ADC high byte (ADCH) "
                        "before the low byte (ADCL) does not latch the result correctly. "
                        "ADCL must be read first to freeze the 10-bit result; reading ADCH "
                        "first may return the high byte of a previous conversion."
                    ),
                    evidence_for=[
                        f"ADCH read before ADCL at {pf.rel_path}:{i+1}",
                        "Pattern: ADCH assignment precedes ADCL assignment.",
                    ],
                    evidence_against=["Some MCUs latch result differently; check datasheet."],
                    source_locations=[(pf.rel_path, i + 1, "ADCH read before ADCL")],
                    confidence=0.78,
                    verification_method="Swap reads: read ADCL first, then ADCH. Verify ADC values are correct.",
                )
                hypotheses.append(h)
                evidence.append(EvidenceItem(
                    title=f"ADC byte read order issue: ADCH before ADCL in {pf.filename}:{i+1}",
                    detail=f"Line {i+1}: {line.strip()}  Line {i+2}: {lines[i+1].strip()}",
                    kind=EvidenceKind.INFERRED,
                    source_file=pf.rel_path,
                    line_number=i + 1,
                ))
                break

    # 7. Compiler output analysis (if provided)
    if project.compiler_output:
        compiler_evidence = _analyze_compiler_output(project.compiler_output)
        evidence.extend(compiler_evidence)
        if any("warning" in e.title.lower() for e in compiler_evidence):
            h = Hypothesis(
                title="Compiler warnings indicate potential defect",
                description=(
                    "The build produced warnings that are commonly associated with bugs "
                    "in embedded systems (-Wuninitialized, -Wshadow, -Warray-bounds, etc.)."
                ),
                evidence_for=[e.title for e in compiler_evidence if "warning" in e.title.lower()][:4],
                evidence_against=["Some warnings are benign in specific project contexts."],
                confidence=0.55,
                verification_method="Fix all compiler warnings and retest.",
            )
            hypotheses.append(h)

    # ── System model ──────────────────────────────────────────────────────
    if project.detected_platform:
        system_model_parts.append(f"Platform: {project.detected_platform}")
    if project.detected_build_system:
        system_model_parts.append(f"Build system: {project.detected_build_system}")

    system_model_parts.append(
        f"Source files: {len(project.source_files)}  Headers: {len(project.header_files)}"
    )

    if isr_functions:
        system_model_parts.append(
            "Interrupt handlers: " + ", ".join(f"{n}({f}:{l})" for f, l, n in isr_functions[:6])
        )

    peripherals_seen = sorted({reg for _, reg, _ in peripheral_uses if len(reg) > 2})
    if peripherals_seen:
        system_model_parts.append("Peripheral registers: " + ", ".join(peripherals_seen[:12]))

    comm_evidence = [e for e in evidence if "Communication" in e.title]
    if comm_evidence:
        system_model_parts.append(f"Communication interfaces: {len(comm_evidence)} reference(s) found")

    if delay_calls:
        system_model_parts.append(f"Delay calls: {len(delay_calls)} across project")

    system_model = "\n".join(system_model_parts)
    return evidence, hypotheses, system_model


def _extract_isr_name(line: str) -> str:
    """Try to extract the ISR function name from a declaration line."""
    m = re.search(r"ISR\s*\(\s*(\w+)\s*\)", line)
    if m:
        return m.group(1)
    m = re.search(r"void\s+(\w+(?:IRQHandler|Handler|_ISR)\w*)\s*\(", line)
    if m:
        return m.group(1)
    return "(unknown ISR)"


def _analyze_compiler_output(output: str) -> list[EvidenceItem]:
    items = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        lower = line.lower()
        if "error:" in lower:
            items.append(EvidenceItem(
                title=f"Compiler error: {line[:120]}",
                detail=line,
                kind=EvidenceKind.OBSERVED,
            ))
        elif "warning:" in lower:
            items.append(EvidenceItem(
                title=f"Compiler warning: {line[:120]}",
                detail=line,
                kind=EvidenceKind.OBSERVED,
            ))
    return items

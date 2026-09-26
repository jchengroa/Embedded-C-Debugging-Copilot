#!/usr/bin/env python3
"""
investigate.py — Embedded C Debugging Copilot: investigation runner

This script prepares a structured Bob investigation session by:
  1. Collecting all firmware source files from a given directory.
  2. Reading an optional symptom description file.
  3. Rendering each stage prompt template with the collected context.
  4. Printing the rendered prompts so they can be pasted into Bob chat,
     or (with --auto flag) driving Bob via the CLI in sequence.

Usage:
    python debugger/investigate.py \\
        --source firmware/ \\
        --symptom debugger/symptom.txt \\
        --mcu ATmega328P \\
        --clock 16000000

    # With a serial log:
    python debugger/investigate.py \\
        --source firmware/ \\
        --symptom debugger/symptom.txt \\
        --serial /tmp/serial.log

Output:
    Rendered prompts are written to debugger/reports/session_<timestamp>/
    as stage_1.txt through stage_7.txt.
"""

import argparse
import os
import sys
import datetime
import textwrap

# ── Template helpers ──────────────────────────────────────────────────────────

def read_sources(source_dir: str) -> dict[str, str]:
    """Return {relative_path: content} for every .c and .h file."""
    sources = {}
    for root, _, files in os.walk(source_dir):
        for fname in sorted(files):
            if fname.endswith(('.c', '.h')):
                rel = os.path.relpath(os.path.join(root, fname), source_dir)
                with open(os.path.join(root, fname), encoding='utf-8') as f:
                    sources[rel] = f.read()
    return sources


def format_sources(sources: dict[str, str]) -> str:
    blocks = []
    for path, content in sources.items():
        blocks.append(f"### {path}\n```c\n{content}\n```")
    return "\n\n".join(blocks)


def read_file_or_default(path: str | None, default: str = "not provided") -> str:
    if not path:
        return default
    if not os.path.exists(path):
        return default
    with open(path, encoding='utf-8') as f:
        return f.read().strip()


# ── Stage prompt templates ────────────────────────────────────────────────────

STAGE_1 = """\
# Stage 1 — Symptom Intake

**Skill:** embedded-debugger
**Investigation:** {timestamp}

## Provided Evidence

- **Observed symptom:** {symptom}
- **Expected behaviour:** {expected}
- **Target MCU:** {mcu} @ {clock} Hz
- **Pin mappings:** {pin_map}
- **Serial log:** {serial_log}
- **Compiler output:** {compiler_output}

## Task

You are starting a structured embedded C debugging investigation.
Apply the embedded-debugger skill methodology throughout.

1. Acknowledge all provided evidence.
2. Identify at most 2 critical missing pieces of information.
3. Produce a **Symptom Summary** in the standard skill output format.
4. List every source file you will read in Stage 2.
"""

STAGE_2 = """\
# Stage 2 — Source Parse & Data-Flow Map

Continuing the investigation from Stage 1.

## Source Files

{source_listing}

## Task

Read every source file above. Produce:

1. **Data flow map** — every global/static variable: who writes it, who reads
   it, in which execution context (ISR or foreground loop).
2. **Control flow map** — trace from physical keypad press to digit on display,
   listing every function and shared variable along the path.
3. **Concurrency inventory** — every variable shared between ISR and non-ISR
   code. Flag:
   - Missing `volatile` qualifiers.
   - Multi-step read-modify-write sequences not protected by `cli()`/`sei()`.
   - Update ordering hazards (count written after data, or vice versa).
"""

STAGE_3 = """\
# Stage 3 — Hypotheses

Continuing the investigation from Stage 2.

## Task

Based on the symptom trace and concurrency inventory, generate a numbered list
of hypotheses ranked by likelihood.

For each hypothesis:
- **Hypothesis:** one sentence root cause statement.
- **Evidence for:** cite file name and line number.
- **Evidence against:** any contradicting observations.
- **Test:** the cheapest concrete experiment to confirm or refute it.

Use the embedded-debugger hazard checklist to ensure completeness.
"""

STAGE_4 = """\
# Stage 4 — Targeted Tests

Continuing the investigation from Stage 3.

## Task

For the **top two** hypotheses, write the exact minimal code instrumentation
that would confirm or refute each:

- Show a diff-style before/after (or the exact lines to add/change).
- Explain what to observe (UART output, GPIO toggle, logic analyser trace).
- Explain what the observation means for confirming or refuting the hypothesis.

Do NOT fix the bug yet. These are diagnostic changes only.
"""

STAGE_5 = """\
# Stage 5 — Root Cause Statement

Continuing the investigation from Stage 4.

Assume the diagnostic tests confirmed the leading hypothesis.

## Task

Write a precise root cause statement:

```
ROOT CAUSE:   <one sentence>
MECHANISM:    <step-by-step with file:line references>
EVIDENCE:     <bullet list citing code lines and observed behaviour>
```

If multiple independent root causes were confirmed, list each one and explain
how they interact to produce the observed symptom.
"""

STAGE_6 = """\
# Stage 6 — Patch

Continuing the investigation from Stage 5.

## Task

Apply the **minimal fix** for every confirmed root cause. Rules:
- Change only what is necessary to eliminate the bug.
- Do not refactor unrelated code.
- Do not add new features.
- For every changed line or block, add a comment beginning with `/* FIX: */`
  explaining why this eliminates the root cause.

Show either a unified diff or the complete patched file(s).
"""

STAGE_7 = """\
# Stage 7 — Regression Check

Continuing the investigation from Stage 6.

## Task

Produce the regression checklist:

1. Does the patch eliminate the original symptom "{symptom}"? Explain step by step.
2. Does the patch introduce any new compiler warnings?
3. Are there related edge cases to verify? List them and state pass/fail.
4. Is the fix correct under all compiler optimisation levels (-O0, -Os, -O2)?

Conclude with a one-paragraph commit message summary.
"""

TEMPLATES = [
    ("stage_1_intake.txt",     STAGE_1),
    ("stage_2_source.txt",     STAGE_2),
    ("stage_3_hypotheses.txt", STAGE_3),
    ("stage_4_tests.txt",      STAGE_4),
    ("stage_5_root_cause.txt", STAGE_5),
    ("stage_6_patch.txt",      STAGE_6),
    ("stage_7_regression.txt", STAGE_7),
]


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Embedded C Debugging Copilot — investigation runner"
    )
    parser.add_argument("--source",   default="firmware/",
                        help="Path to firmware source directory (default: firmware/)")
    parser.add_argument("--symptom",  default=None,
                        help="Path to symptom description text file")
    parser.add_argument("--expected", default=None,
                        help="Path to expected-behaviour text file (or use --expected-text)")
    parser.add_argument("--symptom-text",  default=None,
                        help="Symptom text directly on command line")
    parser.add_argument("--expected-text", default=None,
                        help="Expected behaviour text directly on command line")
    parser.add_argument("--mcu",     default="ATmega328P")
    parser.add_argument("--clock",   default="16000000")
    parser.add_argument("--serial",  default=None,
                        help="Path to serial/UART log file")
    parser.add_argument("--pins",    default=None,
                        help="Path to pin mapping text file")
    parser.add_argument("--compiler",default=None,
                        help="Path to compiler output file")
    parser.add_argument("--output",  default="debugger/reports",
                        help="Directory to write rendered stage files")
    args = parser.parse_args()

    # Resolve text inputs
    symptom_text  = args.symptom_text  or read_file_or_default(args.symptom,
                        "Seven-segment display shows duplicate digits. "
                        "Entering '12' sometimes displays '1112'.")
    expected_text = args.expected_text or read_file_or_default(args.expected,
                        "Display shows exactly the digits entered.")
    serial_log    = read_file_or_default(args.serial)
    pin_map       = read_file_or_default(args.pins)
    compiler_out  = read_file_or_default(args.compiler)

    # Read source files
    if not os.path.isdir(args.source):
        print(f"ERROR: source directory not found: {args.source}", file=sys.stderr)
        sys.exit(1)
    sources = read_sources(args.source)
    if not sources:
        print(f"WARNING: no .c/.h files found in {args.source}", file=sys.stderr)
    source_listing = format_sources(sources)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    session_dir = os.path.join(args.output, f"session_{timestamp}")
    os.makedirs(session_dir, exist_ok=True)

    ctx = {
        "symptom":         symptom_text,
        "expected":        expected_text,
        "mcu":             args.mcu,
        "clock":           args.clock,
        "pin_map":         pin_map,
        "serial_log":      serial_log,
        "compiler_output": compiler_out,
        "source_listing":  source_listing,
        "timestamp":       timestamp,
    }

    print(f"\n=== Embedded C Debugging Copilot ===")
    print(f"Session: {timestamp}")
    print(f"Source:  {args.source}  ({len(sources)} files)")
    print(f"Output:  {session_dir}\n")

    for filename, template in TEMPLATES:
        rendered = template.format_map(ctx)
        out_path = os.path.join(session_dir, filename)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(rendered)
        stage_num = filename.split("_")[1]
        print(f"  [OK] Stage {stage_num} written -> {out_path}")

    print(f"\nPaste each stage file into Bob chat in order.")
    print(f"Bob will apply the embedded-debugger skill at each stage.\n")


if __name__ == "__main__":
    main()

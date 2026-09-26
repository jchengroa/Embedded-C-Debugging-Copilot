---
name: embedded-debugger
description: >
  Structured methodology for debugging embedded C firmware by connecting
  observed hardware symptoms to software root causes. Covers ISR/main
  concurrency bugs, missing volatile, keypad debounce, display multiplexing
  races, and shared-state hazards on bare-metal microcontrollers.
---

# Embedded C Debugging Methodology

## Core principle

Never guess. Every hypothesis must be grounded in the source code, the
observed symptom, and the hardware configuration. Work from the outside in:
start at the user-visible symptom, trace it back through layers of software
until you reach the root cause.

---

## Investigation pipeline

Run each stage in order. Do not skip stages. Each stage feeds the next.

### Stage 1 — Symptom intake

Collect and normalise all available evidence:

- **Observed symptom** (exact description: what the user sees, hears, or
  measures).
- **Expected behaviour** (what should happen).
- **Reproduction steps** (how often, under what conditions).
- **Source files** (read every `.c` / `.h` file before forming any theory).
- **Compiler output** (warnings are evidence — treat them as clues).
- **Serial / UART log** (if available).
- **Pin mappings and schematic notes**.
- **Target MCU, clock frequency, toolchain version**.

Ask clarifying questions only for information that is both missing and
necessary for the next stage. Do not ask for information that can be inferred.

### Stage 2 — Source parse

Read every source file. Build a mental model:

1. **Data flow map**: where does each variable originate, who writes it, who
   reads it, in what context (ISR or main)?
2. **Control flow map**: trace the exact path from the hardware event (keypad
   press, timer tick) through to the user-visible output (display refresh).
3. **Concurrency inventory**: list every variable shared between an ISR and
   non-ISR code. Flag any that lack `volatile`. Flag any multi-step
   read-modify-write sequences not protected by `cli()`/`sei()`.

### Stage 3 — Symptom trace

Walk the control flow backwards from the symptom:

```
Observed symptom
  → Which output peripheral?   (display, UART, LED)
  → Which output driver code?  (ISR? polling loop?)
  → Which data buffer feeds it?
  → Who writes that buffer?
  → Under what conditions is it written incorrectly?
```

At each step, quote the exact lines responsible and state what invariant they
are supposed to maintain.

### Stage 4 — Hypothesis generation

Produce a numbered list of hypotheses ranked by likelihood. For each:

- **Hypothesis**: one sentence stating the proposed root cause.
- **Evidence for**: cite specific lines of code or observed behaviour.
- **Evidence against**: note any observations that would contradict it.
- **Test**: a concrete, cheap way to confirm or refute (add a debug LED,
  insert a `UART_print`, add an `assert`, change one value, read an
  oscilloscope trace, etc.).

Common root-cause categories for embedded C bugs:

| Category | Typical manifestation |
|---|---|
| Missing `volatile` | Variable value frozen / never updated in loop |
| Non-atomic ISR shared state | Intermittent data corruption, duplicate events |
| No debounce | Ghost key presses, repeated characters |
| Wrong wrap condition | Stale buffer slots appear in output |
| Update order bug | Partial state visible to ISR mid-update |
| Insufficient settling time | Misread GPIO, floating inputs |
| Stack overflow | Random crashes, register corruption |
| Off-by-one in buffer index | Adjacent memory overwritten |

### Stage 5 — Targeted tests

For each top-ranked hypothesis, specify the minimal code change that would
confirm it (not fix it — confirm it). Examples:

- Toggle a GPIO inside the ISR to measure invocation rate on a logic analyser.
- Print `g_display_digits` via UART before and after `handle_key`.
- Insert `cli()`/`sei()` around a suspect section and observe whether the
  symptom disappears.
- Add a `static uint32_t isr_call_count` and print it every second.

Run tests in order of cheapness. Stop as soon as a hypothesis is confirmed.

### Stage 6 — Root cause statement

Write a precise, referenced root cause statement:

```
ROOT CAUSE:
  <one sentence>.

MECHANISM:
  <step-by-step description of exactly how the bug manifests, referencing
   file names and line numbers>.

EVIDENCE:
  - <cite lines from the source>
  - <cite observed behaviour>
```

### Stage 7 — Patch

Apply the minimal change that eliminates the root cause. Do not refactor
unrelated code. Do not add features.

For each changed line or block:
- Explain what it was before.
- Explain what it is after.
- Explain why this eliminates the root cause.

### Stage 8 — Regression test

After patching, verify:

1. The original symptom no longer reproduces.
2. No new warnings are emitted by the compiler.
3. All previously passing tests (if any) still pass.
4. Related edge cases are manually checked (e.g., if debounce was added,
   test both single press and held key).

---

## Embedded-specific hazards checklist

Run this checklist during Stage 2 whenever you read an embedded C source file:

- [ ] Every variable written in an ISR and read outside it is `volatile`.
- [ ] Every multi-byte variable accessed in both ISR and main is protected by
      an atomic section (`cli()`/`sei()` or equivalent).
- [ ] Buffer write order ensures the ISR never observes a partially-updated
      state (write count/length last when growing, first when shrinking).
- [ ] Wrap conditions use the *current active count*, not a compile-time
      maximum, to avoid cycling through uninitialised slots.
- [ ] Keypad (or any mechanical input) has a debounce strategy (software
      delay + release-wait, or hardware RC filter).
- [ ] GPIO settling time after driving a row/column line is sufficient for
      the PCB trace capacitance (≥50 µs on most hobby boards).
- [ ] No `printf` or `malloc` inside an ISR.
- [ ] ISRs are short: heavy work is deferred to a flag checked in main.
- [ ] Stack size has been estimated and is within available SRAM.

---

## Output format

All investigation outputs must follow this structure:

```
## Embedded Debug Report

### 1. Symptom Summary
### 2. Source Analysis
### 3. Concurrency Inventory
### 4. Symptom Trace
### 5. Hypotheses
### 6. Recommended Tests
### 7. Root Cause (filled after tests)
### 8. Patch
### 9. Regression Checklist
```

Each section should be concrete and reference actual file names and line
numbers. Avoid vague language ("maybe", "might", "could be"). Every claim
must be grounded in code or observable hardware behaviour.

# Embedded Debugging Copilot

A developer tool that turns an observed embedded-system symptom into an
evidence-backed diagnosis, targeted fix, and verification workflow.

```
OBSERVATION → REPRODUCTION → EVIDENCE → HYPOTHESIS → ROOT CAUSE → FIX → VERIFICATION
```

---

## What This Is

Embedded developers often get stuck in:

```
Compile → Flash → Weird hardware behavior → Stare at code →
Check datasheet → Add random delay → Recompile → Flash → Still broken
```

The hard part isn't writing code — it's **connecting the observed hardware
symptom to the software root cause**.

The Embedded Debugging Copilot drives a structured investigation:

1. You describe what went wrong.
2. The tool scans your source code, identifies shared state, ISR patterns,
   peripheral configurations, type hazards, and other embedded-specific issues.
3. It generates ranked hypotheses with evidence and verification methods.
4. It identifies the root cause and proposes a minimal fix.
5. It runs available tests and displays a verification result.

---

## Requirements

- **Windows 10 or Windows 11**
- **Python 3.10 or later** — download from [python.org](https://www.python.org/downloads/)
  - Check **"Add Python to PATH"** during installation
- **OpenAI API key** (optional) — the tool works without AI using static analysis

---

## Installation

```bat
git clone https://github.com/your-org/embedded-debugging-copilot.git
cd embedded-debugging-copilot
install.bat
```

`install.bat` checks for Python, verifies tkinter, and installs the optional
`openai` dependency.

---

## Launch

```bat
run.bat
```

or directly:

```bat
python main.py
```

---

## AI Configuration (optional)

Without an API key the tool uses static analysis only — it still finds
concurrency hazards, integer overflows, ADC byte-order bugs, buffer overflows,
and compiler warnings automatically.

To enable AI-powered hypothesis generation and fix proposals:

**Option A — environment variable (recommended):**
```bat
set OPENAI_API_KEY=sk-...
run.bat
```

**Option B — config file:**

Edit `config\settings.json`:
```json
{
  "api_key":  "sk-...",
  "base_url": "https://api.openai.com/v1",
  "model":    "gpt-4o",
  "max_tokens": 4096
}
```

The AI indicator in the top-right corner of the application shows whether
AI is connected (`●  Connected`) or offline (`○  Offline (static analysis only)`).

---

## User Interface

```
┌────────────────────────────────────────────────────────────────┐
│  EMBEDDED DEBUGGING COPILOT               [Report Problem…]    │
├───────────────┬────────────────────────────────────────────────┤
│  PROJECT      │  INVESTIGATION          state: COMPLETE         │
│               │                                                  │
│  Browse…      │  ┌─ Dashboard ─ Evidence ─ Hypotheses ─────┐   │
│               │  │  Progress:                               │   │
│  DEMO         │  │  ✓ Symptom analyzed                      │   │
│  PROJECTS     │  │  ✓ Project analyzed                      │   │
│  ─────────── │  │  ✓ Hypotheses generated                  │   │
│  UART Failure │  │  ✓ Evidence collected                    │   │
│  Sensor Error │  │  ✓ Root cause identified                 │   │
│  ISR Sync Bug │  │  ✓ Fix generated                         │   │
│  Display Bug  │  │  ✓ Tests run                             │   │
│               │  └──────────────────────────────────────────┘   │
│  FILES        │  Hypotheses:                                     │
│  src/uart.c   │  H1  ISR/main race condition   87%  ████████░░  │
│  src/uart.h   │  H2  Non-atomic multi-step     58%  █████░░░░░  │
│  src/main.c   │                                                  │
│               │  Root Cause:                                     │
│               │  ISR/foreground shared-state race condition...   │
├───────────────┴────────────────────────────────────────────────┤
│  Status: Investigation complete.      [STOP]  [RUN TESTS]       │
└────────────────────────────────────────────────────────────────┘
```

**Tabs:**
| Tab | Contents |
|-----|----------|
| Dashboard | Progress steps, system model |
| Evidence | All findings labeled OBSERVED / INFERRED / ASSUMED / UNVERIFIED |
| Hypotheses | Ranked list with confidence bars; click for full detail |
| Root Cause | ROOT CAUSE / MECHANISM / EVIDENCE statement |
| Fix | Code diff view, APPLY / REJECT buttons |
| Tests | Test runner output, VERIFIED / PARTIALLY VERIFIED / UNVERIFIED badge |
| Log | Full timestamped investigation log |

---

## Demo Projects

Four demo projects with intentional, realistic bugs are included:

| Demo | Path | Bugs |
|------|------|------|
| UART Communication Failure | `demo/uart_failure/src/` | ISR/main TX buffer race, baud rate rounding |
| Sensor Reading Error | `demo/sensor_error/src/` | ADC byte read order, int16 overflow |
| Interrupt Sync Bug (Motor) | `demo/interrupt_sync/src/` | Missing volatile, non-atomic 32-bit access |
| Display / Keypad Input Bug | `firmware/` | No debounce, non-atomic display update, wrong mux wrap |

Load any demo by clicking its name in the **DEMO PROJECTS** panel.
Then click **Report Problem…** — the form will be pre-filled with the scenario.

---

## Project Structure

```
embedded-debugging-copilot/
│
├── main.py                 ← entry point
├── run.bat                 ← Windows launcher
├── install.bat             ← Windows installer
├── requirements.txt
│
├── app/
│   ├── models/             ← Project, Investigation, Hypothesis, Evidence, Fix...
│   ├── core/
│   │   ├── orchestrator.py ← debugging engine (all logic lives here)
│   │   ├── project_scanner.py
│   │   ├── ai_client.py    ← OpenAI integration (optional)
│   │   └── test_runner.py  ← auto-detect + run tests
│   ├── analyzers/
│   │   └── static_analyzer.py  ← hardware-agnostic C/C++ static analysis
│   └── ui/
│       ├── main_window.py
│       ├── project_panel.py
│       ├── problem_form.py
│       ├── investigation_panel.py
│       ├── theme.py
│       └── widgets.py
│
├── demo/
│   ├── uart_failure/src/   ← UART TX race condition demo
│   ├── sensor_error/src/   ← ADC overflow + byte-order demo
│   └── interrupt_sync/src/ ← Motor controller ISR sync demo
│
├── firmware/               ← Seven-segment + keypad demo (original example)
│
└── config/
    └── settings.json       ← AI configuration (no key by default)
```

---

## Architecture

```
┌─────────────────────────────┐
│      MainWindow (GUI)        │
│  ProjectPanel │ InvPanel     │
└──────────────┬──────────────┘
               │  on_progress callbacks (thread-safe)
               ▼
┌─────────────────────────────┐
│      Orchestrator           │  ← ALL debugging logic lives here
│  (background thread)        │
└───┬───────┬──────┬──────────┘
    │       │      │
    ▼       ▼      ▼
  Static  AI     Test
  Analyzer Client Runner
    │       │      │
    └───────┴──────┘
               │
               ▼
┌─────────────────────────────┐
│    Project / Codebase        │
│  (ProjectFile, models)       │
└─────────────────────────────┘
```

The GUI and the engine are **completely separate**. The orchestrator can be
used from a script, test, or CLI without any GUI dependency.

---

## Supported Problem Types

The static analyzer detects patterns relevant to (but not limited to):

- ISR / foreground shared-state race conditions
- Missing `volatile` on ISR-shared variables
- Non-atomic multi-byte access on narrow MCUs
- Integer overflow / narrowing in arithmetic expressions
- ADC / peripheral register byte read order
- Unsafe string/memory operations (strcpy, sprintf)
- Missing peripheral settling delays
- Debounce hazards (implied by keypad/button patterns)
- Communication peripheral usage (UART, SPI, I2C, CAN, USB)
- Compiler warnings (when compiler output is provided)
- Serial log patterns (HardFault, stack overflow, watchdog, assertion failure)

AI analysis (when configured) extends this to all embedded bug categories
described in the symptom, including timing, protocol framing, state machine
errors, and hardware/software interface mismatches.

---

## Security

No credentials are stored or transmitted except the optional AI API key
configured explicitly by the developer.
See [SECURITY.MD](SECURITY.MD).

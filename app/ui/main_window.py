"""
app/ui/main_window.py

Main application window — redesigned for the guided UX workflow.

Architecture:
  ┌──────────────────────────────────────────────────────────────────┐
  │  top bar: app name  |  AI status  |  stop button                 │
  ├──────────────────────────────────────────────────────────────────┤
  │  workflow bar (shown during investigation):                       │
  │  ① Project → ② Problem → ③ Evidence → ④ Investigate → ⑤ …     │
  ├────────────┬─────────────────────────────────────────────────────┤
  │  sidebar   │  content area (swapped based on current step)       │
  │  nav       │                                                      │
  │  🏠 Home   │  LandingScreen  /  ProjectPanel  /  ProblemForm /  │
  │  📁 Proj.  │  EvidencePanel  /  InvestigationPanel               │
  │  🔍 Invest │                                                      │
  │  ⚙ Settings│                                                      │
  └────────────┴─────────────────────────────────────────────────────┘
"""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

from app.core.orchestrator import Orchestrator
from app.models.investigation import InvestigationState, ProposedFix
from app.models.project import Project
from app.ui import theme, widgets
from app.ui.investigation_panel import InvestigationPanel
from app.ui.problem_form import ProblemForm
from app.ui.project_panel import ProjectPanel
from app.ui.landing_screen import LandingScreen
from app.ui.evidence_panel import EvidencePanel
from app.ui.workflow_bar import WorkflowBar
from app.core import ai_client

# Sidebar nav items: (icon, label, key)
_NAV_ITEMS = [
    ("🏠", "Home",          "home"),
    ("📁", "Project",       "project"),
    ("🔍", "Investigate",   "investigate"),
    ("⚙",  "Settings",      "settings"),
]


class MainWindow(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Embedded Debugging Copilot")
        self.configure(bg=theme.BG_APP)
        self.geometry("1340x860")
        self.minsize(960, 620)

        widgets.apply_dark_ttk_style()

        self._orch = Orchestrator(on_progress=self._on_progress)
        self._project: Optional[Project] = None
        self._refresh_timer: Optional[str] = None
        self._current_nav = "home"

        # Pending evidence from problem form (passed to evidence panel)
        self._pending_compiler: str = ""
        self._pending_serial: str = ""

        self._build()
        self._show_home()
        self._schedule_refresh()

    # ── Build shell ────────────────────────────────────────────────────────

    def _build(self) -> None:
        # Top bar
        self._build_topbar()

        # Workflow bar (hidden until investigation starts)
        self._wf_bar = WorkflowBar(self)
        self._wf_bar.pack(fill=tk.X, side=tk.TOP)
        widgets.separator(self).pack(fill=tk.X, side=tk.TOP)
        self._wf_bar.pack_forget()   # hide initially

        # Main area: sidebar + content
        body = tk.Frame(self, bg=theme.BG_APP)
        body.pack(fill=tk.BOTH, expand=True)

        # Left sidebar
        self._sidebar = self._build_sidebar(body)
        self._sidebar.pack(side=tk.LEFT, fill=tk.Y)

        # Sidebar separator
        tk.Frame(body, width=1, bg=theme.BORDER).pack(side=tk.LEFT, fill=tk.Y)

        # Content area
        self._content_area = tk.Frame(body, bg=theme.BG_DARK)
        self._content_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Status bar
        self._build_statusbar()

    def _build_topbar(self) -> None:
        bar = tk.Frame(self, bg=theme.BG_PANEL, height=48)
        bar.pack(fill=tk.X, side=tk.TOP)
        bar.pack_propagate(False)

        # App name
        tk.Label(
            bar,
            text="Embedded Debugging Copilot",
            font=theme.FONT_TITLE,
            fg=theme.FG_TEXT,
            bg=theme.BG_PANEL,
        ).pack(side=tk.LEFT, padx=16, pady=10)

        # AI status indicator
        ai_ok = ai_client.is_available()
        ai_text  = "● AI connected" if ai_ok else "○ AI offline"
        ai_color = theme.FG_GREEN    if ai_ok else theme.FG_MUTED
        tk.Label(
            bar,
            text=ai_text,
            font=theme.FONT_UI_S,
            fg=ai_color,
            bg=theme.BG_PANEL,
        ).pack(side=tk.RIGHT, padx=16)

        # Stop button (right side)
        self._stop_btn = tk.Button(
            bar,
            text="■  Stop",
            font=theme.FONT_BOLD_S,
            fg=theme.FG_RED,
            bg=theme.BG_PANEL,
            activebackground=theme.BG_HOVER,
            activeforeground=theme.FG_RED,
            relief=tk.FLAT,
            bd=0,
            padx=10,
            cursor="hand2",
            command=self._on_stop,
        )
        self._stop_btn.pack(side=tk.RIGHT, padx=4, pady=10)
        self._stop_btn.pack_forget()   # shown only during investigation

        widgets.separator(self).pack(fill=tk.X, side=tk.TOP)

    def _build_sidebar(self, parent) -> tk.Frame:
        sidebar = tk.Frame(parent, bg=theme.BG_PANEL, width=180)
        sidebar.pack_propagate(False)

        self._nav_buttons: dict[str, tk.Button] = {}

        for icon, label, key in _NAV_ITEMS:
            btn = tk.Button(
                sidebar,
                text=f"  {icon}  {label}",
                font=theme.FONT_UI,
                fg=theme.FG_MUTED,
                bg=theme.BG_PANEL,
                activebackground=theme.BG_HOVER,
                activeforeground=theme.FG_TEXT,
                relief=tk.FLAT,
                bd=0,
                padx=8,
                pady=10,
                anchor="w",
                cursor="hand2",
                command=lambda k=key: self._nav_to(k),
            )
            btn.pack(fill=tk.X, pady=2, padx=4)
            self._nav_buttons[key] = btn

        # Settings is pinned to bottom
        # (already added above — reorder if needed)

        return sidebar

    def _build_statusbar(self) -> None:
        widgets.separator(self).pack(fill=tk.X, side=tk.BOTTOM)
        bar = tk.Frame(self, bg=theme.BG_PANEL, height=30)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)

        self._status_var = tk.StringVar(value="Ready — open a project or try a demo to begin.")
        tk.Label(
            bar,
            textvariable=self._status_var,
            font=theme.FONT_UI_S,
            fg=theme.FG_MUTED,
            bg=theme.BG_PANEL,
            anchor="w",
        ).pack(side=tk.LEFT, padx=12, fill=tk.X, expand=True)

    # ── Navigation ─────────────────────────────────────────────────────────

    def _nav_to(self, key: str) -> None:
        self._current_nav = key
        self._update_nav_highlight(key)

        if key == "home":
            self._show_home()
        elif key == "project":
            if self._project:
                self._show_project_panel()
            else:
                self._show_home()
        elif key == "investigate":
            if self._orch.investigation:
                self._show_investigation()
            else:
                self._status("Start an investigation first — select a project and describe a problem.")
        elif key == "settings":
            self._show_settings()

    def _update_nav_highlight(self, active_key: str) -> None:
        for key, btn in self._nav_buttons.items():
            if key == active_key:
                btn.configure(
                    fg=theme.FG_ACCENT,
                    bg=theme.BG_SEL,
                    font=theme.FONT_BOLD,
                )
            else:
                btn.configure(
                    fg=theme.FG_MUTED,
                    bg=theme.BG_PANEL,
                    font=theme.FONT_UI,
                )

    # ── Content area management ────────────────────────────────────────────

    def _clear_content(self) -> None:
        for child in self._content_area.winfo_children():
            child.destroy()

    def _show_home(self) -> None:
        self._clear_content()
        self._update_nav_highlight("home")
        self._wf_bar.pack_forget()
        self._stop_btn.pack_forget()

        landing = LandingScreen(
            self._content_area,
            on_start_new=self._on_start_new,
            on_demo=self._on_demo_selected,
            on_browse=self._on_browse_project,
        )
        landing.pack(fill=tk.BOTH, expand=True)
        self._status("Welcome — Start a New Investigation or try a demo.")

    def _show_project_panel(self) -> None:
        self._clear_content()
        self._update_nav_highlight("project")
        self._wf_bar.pack(fill=tk.X, side=tk.TOP, before=self._content_area.master)
        self._wf_bar.set_step("project")

        panel = ProjectPanel(
            self._content_area,
            on_project_loaded=self._on_project_folder_selected,
        )
        panel.pack(fill=tk.BOTH, expand=True)

        # If a project is already loaded, show its info
        if self._project:
            panel.show_project(self._project)

        self._project_panel_ref = panel
        self._status("Step 1 — Select your project.")

    def _show_problem_form(self, prefill: dict = None) -> None:
        self._clear_content()
        self._wf_bar.set_step("problem")

        form = ProblemForm(
            self._content_area,
            on_submit=self._on_problem_submitted,
            prefill=prefill or {},
        )
        form.pack(fill=tk.BOTH, expand=True)
        self._status("Step 2 — Describe what went wrong.")

    def _show_evidence_panel(self) -> None:
        self._clear_content()
        self._wf_bar.set_step("evidence")

        ev_panel = EvidencePanel(
            self._content_area,
            on_continue=self._on_evidence_provided,
        )
        ev_panel.pack(fill=tk.BOTH, expand=True)

        # Pre-populate from problem form
        if self._pending_compiler or self._pending_serial:
            ev_panel.prefill_evidence(
                compiler_output=self._pending_compiler,
                serial_log=self._pending_serial,
            )

        self._status("Step 3 — Add evidence (optional).")

    def _show_investigation(self) -> None:
        self._clear_content()
        self._update_nav_highlight("investigate")
        self._wf_bar.set_step("investigate")
        self._stop_btn.pack(side=tk.RIGHT, padx=4, pady=10)

        panel = InvestigationPanel(
            self._content_area,
            on_apply_fix=self._on_apply_fix,
            on_run_tests=self._on_run_tests,
        )
        panel.pack(fill=tk.BOTH, expand=True)
        self._inv_panel_ref = panel

        inv = self._orch.investigation
        if inv:
            panel.refresh(inv)

        self._status("Investigation in progress…")

    def _show_settings(self) -> None:
        self._clear_content()
        self._update_nav_highlight("settings")

        f = tk.Frame(self._content_area, bg=theme.BG_DARK)
        f.pack(fill=tk.BOTH, expand=True, padx=60, pady=40)

        tk.Label(
            f,
            text="SETTINGS",
            font=theme.FONT_LABEL_U,
            fg=theme.FG_MUTED,
            bg=theme.BG_DARK,
        ).pack(anchor="w")

        tk.Label(
            f,
            text="Settings",
            font=theme.FONT_BOLD_XL,
            fg=theme.FG_TEXT,
            bg=theme.BG_DARK,
        ).pack(anchor="w", pady=(4, 20))

        ai_ok = ai_client.is_available()
        ai_text = "AI engine is connected." if ai_ok else \
            "AI engine is offline. Set OPENAI_API_KEY or ANTHROPIC_API_KEY in config/.env to enable AI-powered analysis."
        ai_color = theme.FG_GREEN if ai_ok else theme.FG_YELLOW

        info_outer = tk.Frame(f, bg=theme.BORDER)
        info_outer.pack(fill=tk.X)
        info_inner = tk.Frame(info_outer, bg=theme.BG_CARD)
        info_inner.pack(fill=tk.X, padx=1, pady=1)

        tk.Label(
            info_inner,
            text=ai_text,
            font=theme.FONT_UI,
            fg=ai_color,
            bg=theme.BG_CARD,
            anchor="w",
            wraplength=600,
            justify="left",
        ).pack(fill=tk.X, padx=16, pady=14)

    # ── Event handlers ─────────────────────────────────────────────────────

    def _on_start_new(self) -> None:
        """User clicked "Start a New Investigation" on the landing screen."""
        if self._project is None:
            self._show_project_panel()
        else:
            # Project already loaded — go straight to problem form
            self._show_problem_form(prefill=_demo_prefill(self._project.root))

    def _on_browse_project(self) -> None:
        from tkinter import filedialog
        folder = filedialog.askdirectory(title="Select Embedded Project Folder")
        if folder:
            self._show_project_panel()
            self._on_project_folder_selected(folder)

    def _on_demo_selected(self, rel_path: str, key: str) -> None:
        """User clicked a demo tile on the landing or project screen."""
        import os
        base = os.path.dirname(os.path.abspath(__file__))
        # Walk up to project root (app/ui -> app -> root)
        base = os.path.dirname(os.path.dirname(base))
        full = os.path.join(base, rel_path)
        path = full if os.path.isdir(full) else (rel_path if os.path.isdir(rel_path) else None)
        if path is None:
            self._status(f"Demo not found: {rel_path}")
            return

        self._show_project_panel()
        self._on_project_folder_selected(os.path.abspath(path))

    def _on_project_folder_selected(self, path: str) -> None:
        self._status("Loading project…")
        try:
            self._project = self._orch.load_project(path)
            # Refresh project panel if visible
            if hasattr(self, "_project_panel_ref"):
                try:
                    self._project_panel_ref.show_project(self._project)
                except Exception:
                    pass
            self._status(
                f"Project loaded: {self._project.name}  "
                f"({len(self._project.source_files)} source files)"
            )
            # Update nav to reflect loaded project
            self._nav_buttons["project"].configure(fg=theme.FG_TEXT)
            # Auto-advance to problem form after a short delay
            self.after(800, self._advance_to_problem)
        except Exception as exc:
            messagebox.showerror("Project Load Error", str(exc))
            self._status("Error loading project.")

    def _advance_to_problem(self) -> None:
        """Called 800ms after project loads to guide user to Step 2."""
        if self._project:
            prefill = _demo_prefill(self._project.root)
            self._show_problem_form(prefill=prefill)

    def _on_problem_submitted(
        self,
        description: str,
        expected: str,
        actual: str,
        steps: str,
        frequency: str,
        compiler_output: str,
        serial_log: str,
        hardware_notes: str,
    ) -> None:
        # Store evidence for pre-populating evidence panel
        self._pending_compiler = compiler_output
        self._pending_serial   = serial_log

        # Store the problem details on the orchestrator
        self._orch.set_extra_evidence(
            compiler_output=compiler_output,
            serial_log=serial_log,
            hardware_notes=hardware_notes,
        )

        # Keep symptom fields for when investigation starts
        self._pending_symptom = dict(
            description=description,
            expected=expected,
            actual=actual,
            steps=steps,
            frequency=frequency,
        )

        # Move to evidence panel
        self._show_evidence_panel()

    def _on_evidence_provided(self, evidence: dict) -> None:
        """Called from evidence panel with collected evidence (may be empty dict)."""
        if not hasattr(self, "_pending_symptom"):
            self._status("Error: no problem description found.")
            return

        sym = self._pending_symptom

        # Start investigation in background
        def _start():
            inv = self._orch.start_investigation(
                description=sym["description"],
                expected=sym["expected"],
                actual=sym["actual"],
                steps=sym["steps"],
                frequency=sym["frequency"],
            )
            self.after(0, lambda: self._after_investigation_started(inv))

        self._show_investigation()
        self._status("Starting investigation…")
        threading.Thread(target=_start, daemon=True).start()

    def _after_investigation_started(self, inv) -> None:
        self._status("Investigation running…")
        if hasattr(self, "_inv_panel_ref"):
            try:
                self._inv_panel_ref.refresh(inv)
            except Exception:
                pass

    def _on_apply_fix(self, fix: ProposedFix) -> None:
        if not fix.diffs:
            messagebox.showinfo(
                "Manual Fix Required",
                "This fix requires manual code changes.\n\n" + fix.explanation,
            )
            return

        files = [d.file for d in fix.diffs]
        confirm = messagebox.askyesno(
            "Apply Fix",
            f"Apply fix to {len(files)} file(s)?\n\n"
            + "\n".join(f"  • {f}" for f in files)
            + "\n\nBackups will be created (.bak).",
        )
        if not confirm:
            return

        try:
            modified = self._orch.apply_fix(fix)
            messagebox.showinfo(
                "Fix Applied",
                "Fix applied to:\n" + "\n".join(f"  • {f}" for f in modified),
            )
            self._status("Fix applied — run tests to verify.")
            if hasattr(self, "_inv_panel_ref") and self._orch.investigation:
                self._inv_panel_ref.refresh(self._orch.investigation)
            self._wf_bar.set_step("verify")
        except Exception as exc:
            messagebox.showerror("Apply Fix Error", str(exc))

    def _on_run_tests(self) -> None:
        if self._project is None:
            messagebox.showwarning("No Project", "Load a project first.")
            return
        inv = self._orch.investigation
        if inv is None:
            messagebox.showwarning("No Investigation", "Start an investigation first.")
            return

        self._status("Running tests…")
        from app.core.test_runner import run_tests
        from app.models.investigation import VerificationResult, VerificationStatus

        def _run():
            results = run_tests(self._project.root, timeout=30)
            if inv.verification is None:
                inv.verification = VerificationResult()
            inv.verification.test_results = results
            passed = sum(1 for r in results if r.passed is True)
            failed = sum(1 for r in results if r.passed is False)
            inv.add_log(f"Test run complete: {passed} passed, {failed} failed")
            if failed == 0 and passed > 0:
                inv.verification.status = VerificationStatus.VERIFIED
            elif failed > 0:
                inv.verification.status = VerificationStatus.PARTIALLY_VERIFIED
            self.after(0, lambda: self._on_tests_complete(inv, passed, failed))

        threading.Thread(target=_run, daemon=True).start()

    def _on_tests_complete(self, inv, passed: int, failed: int) -> None:
        self._status(f"Tests complete: {passed} passed, {failed} failed")
        if hasattr(self, "_inv_panel_ref"):
            try:
                self._inv_panel_ref.refresh(inv)
            except Exception:
                pass
        if failed == 0 and passed > 0:
            self._wf_bar.complete_step("verify")

    def _on_stop(self) -> None:
        self._orch.stop()
        self._stop_btn.pack_forget()
        self._status("Investigation stopped.")

    def _on_progress(self, state: InvestigationState, message: str) -> None:
        """Called from background thread — marshal to main thread."""
        self.after(0, lambda: self._handle_progress(state, message))

    def _handle_progress(self, state: InvestigationState, message: str) -> None:
        self._status(message)

        # Update workflow bar
        state_to_step = {
            InvestigationState.ANALYZING_PROJECT:     "project",
            InvestigationState.INVESTIGATING:          "investigate",
            InvestigationState.COLLECTING_EVIDENCE:    "investigate",
            InvestigationState.GENERATING_HYPOTHESES:  "diagnose",
            InvestigationState.ROOT_CAUSE_IDENTIFIED:  "diagnose",
            InvestigationState.AWAITING_APPROVAL:      "fix",
            InvestigationState.APPLYING_FIX:           "fix",
            InvestigationState.RUNNING_TESTS:          "verify",
            InvestigationState.VERIFYING:              "verify",
            InvestigationState.COMPLETE:               "verify",
        }
        wf_step = state_to_step.get(state)
        if wf_step:
            self._wf_bar.set_step(wf_step)

        if hasattr(self, "_inv_panel_ref"):
            try:
                self._inv_panel_ref.update_state(state, message)
                inv = self._orch.investigation
                if inv:
                    self._inv_panel_ref.append_log(inv.log[-1] if inv.log else message)
            except Exception:
                pass

    # ── Periodic refresh ───────────────────────────────────────────────────

    def _schedule_refresh(self) -> None:
        self._do_refresh()
        self._refresh_timer = self.after(800, self._schedule_refresh)

    def _do_refresh(self) -> None:
        inv = self._orch.investigation
        if inv and hasattr(self, "_inv_panel_ref"):
            try:
                self._inv_panel_ref.refresh(inv)
            except Exception:
                pass

    # ── Utilities ──────────────────────────────────────────────────────────

    def _status(self, msg: str) -> None:
        self._status_var.set(msg)


# ---------------------------------------------------------------------------
# Demo prefill helper (unchanged from original)
# ---------------------------------------------------------------------------

_DEMO_PREFILLS: dict[str, dict] = {
    "uart_failure": {
        "description": "Device sends garbled / interleaved UART messages intermittently.",
        "expected": "Each UART message arrives as a complete, separate line.",
        "actual": "Messages are interleaved: 'COUNT=0\\nCOUNT=COUNT=1COUNT=2\\n2\\n'",
        "steps": "1. Power on. 2. Observe serial terminal at 115200 baud. 3. Watch for garbled output.",
        "frequency": "Sometimes",
    },
    "sensor_error": {
        "description": "Temperature sensor reports impossible values (-50°C or 450°C) at room temperature.",
        "expected": "Sensor returns values in range 0–50°C at room temperature.",
        "actual": "Readings are -50 or 450+, varying each read.",
        "steps": "1. Power on. 2. Monitor UART. 3. Observe temperature readings.",
        "frequency": "Always",
    },
    "interrupt_sync": {
        "description": "Motor overshoots target encoder count; state machine gets stuck in RUNNING.",
        "expected": "Motor stops precisely at target encoder count every time.",
        "actual": "Motor runs past target and never transitions to STOPPING. Sometimes watchdog resets.",
        "steps": "1. Send start command with target=1000. 2. Observe encoder count. 3. Motor does not stop.",
        "frequency": "Sometimes",
    },
    "firmware": {
        "description": "Seven-segment display shows duplicate digits. Entering '12' shows '1112'.",
        "expected": "Display shows exactly the digits entered.",
        "actual": "First digit is duplicated 1–3 times.",
        "steps": "1. Power on. 2. Press '1'. 3. Press '2'. 4. Observe display.",
        "frequency": "Always",
    },
}


def _demo_prefill(project_root: str) -> dict:
    """Return prefill dict if the project root matches a known demo."""
    root_lower = project_root.replace("\\", "/").lower()
    for key, prefill in _DEMO_PREFILLS.items():
        if key in root_lower:
            return prefill
    return {}

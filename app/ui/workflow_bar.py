"""
app/ui/workflow_bar.py

Horizontal step-progress bar shown at the top of the investigation workspace.

Shows the 7-step workflow:
  ① Project → ② Problem → ③ Evidence → ④ Investigate → ⑤ Diagnose → ⑥ Fix → ⑦ Verify

Each step can be:
  - pending  : muted text, hollow circle
  - active   : accent color, filled circle (current step)
  - complete : green, checkmark
"""
from __future__ import annotations

import tkinter as tk
from app.ui import theme

# Step definitions: (key, label)
STEPS = [
    ("project",    "Project"),
    ("problem",    "Problem"),
    ("evidence",   "Evidence"),
    ("investigate","Investigate"),
    ("diagnose",   "Diagnose"),
    ("fix",        "Fix"),
    ("verify",     "Verify"),
]

_STEP_KEYS = [s[0] for s in STEPS]

_CIRCLE_PENDING  = "○"
_CIRCLE_ACTIVE   = "●"
_CIRCLE_DONE     = "✓"


class WorkflowBar(tk.Frame):
    """
    Compact workflow progress bar.
    Displayed between the top-bar and the main content area.
    """

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=theme.BG_PANEL, **kw)
        self._current: str = "project"
        self._completed: set[str] = set()
        self._step_frames: dict[str, dict] = {}
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        container = tk.Frame(self, bg=theme.BG_PANEL)
        container.pack(pady=10, padx=20)

        for i, (key, label) in enumerate(STEPS):
            # Arrow connector (except before first)
            if i > 0:
                tk.Label(
                    container,
                    text="→",
                    font=theme.FONT_UI_S,
                    fg=theme.FG_SUBTLE,
                    bg=theme.BG_PANEL,
                ).pack(side=tk.LEFT, padx=4)

            # Step cell
            cell = tk.Frame(container, bg=theme.BG_PANEL)
            cell.pack(side=tk.LEFT)

            circle = tk.Label(
                cell,
                text=_CIRCLE_PENDING,
                font=theme.FONT_UI_S,
                fg=theme.FG_MUTED,
                bg=theme.BG_PANEL,
            )
            circle.pack(side=tk.LEFT, padx=(0, 3))

            lbl = tk.Label(
                cell,
                text=label,
                font=theme.FONT_UI_S,
                fg=theme.FG_MUTED,
                bg=theme.BG_PANEL,
            )
            lbl.pack(side=tk.LEFT)

            self._step_frames[key] = {"circle": circle, "label": lbl}

        self._refresh()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_step(self, key: str) -> None:
        """Set the currently active step by key."""
        if key not in _STEP_KEYS:
            return
        # Auto-complete all steps before this one
        idx = _STEP_KEYS.index(key)
        self._completed = set(_STEP_KEYS[:idx])
        self._current = key
        self._refresh()

    def complete_step(self, key: str) -> None:
        """Mark a step as completed."""
        self._completed.add(key)
        self._refresh()

    def advance(self) -> None:
        """Advance to the next step."""
        idx = _STEP_KEYS.index(self._current)
        if idx < len(_STEP_KEYS) - 1:
            self.set_step(_STEP_KEYS[idx + 1])

    def current_step(self) -> str:
        return self._current

    # ── Render ────────────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        for key, widgets_dict in self._step_frames.items():
            circle: tk.Label = widgets_dict["circle"]
            lbl: tk.Label    = widgets_dict["label"]

            if key in self._completed:
                circle.configure(text=_CIRCLE_DONE, fg=theme.FG_GREEN)
                lbl.configure(fg=theme.FG_GREEN, font=theme.FONT_UI_S)
            elif key == self._current:
                circle.configure(text=_CIRCLE_ACTIVE, fg=theme.FG_ACCENT)
                lbl.configure(fg=theme.FG_ACCENT, font=theme.FONT_BOLD_S if hasattr(theme, "FONT_BOLD_S") else theme.FONT_BOLD)
            else:
                circle.configure(text=_CIRCLE_PENDING, fg=theme.FG_SUBTLE)
                lbl.configure(fg=theme.FG_SUBTLE, font=theme.FONT_UI_S)

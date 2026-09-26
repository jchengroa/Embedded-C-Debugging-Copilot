"""
app/ui/investigation_panel.py

The primary investigation workspace — shown while and after an investigation runs.

Replaces the old tabbed notebook with a single scrollable feed that shows:
  1. Investigation header (problem title, status badge, AI status)
  2. Live progress checklist
  3. Current activity (what's happening right now)
  4. Possible causes / hypotheses (shown as cards when available)
  5. Root cause (visually prominent when identified)
  6. Proposed fix + diff view
  7. Verification results

Navigation tabs at the top allow jumping to specific sections.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional

from app.models.investigation import (
    EvidenceItem, Hypothesis, Investigation, InvestigationState,
    ProposedFix, RootCause, VerificationResult,
)
from app.ui import theme, widgets


class InvestigationPanel(tk.Frame):

    def __init__(self, parent, on_apply_fix: Callable, on_run_tests: Callable, **kw):
        super().__init__(parent, bg=theme.BG_DARK, **kw)
        self._on_apply_fix  = on_apply_fix
        self._on_run_tests  = on_run_tests
        self._inv: Optional[Investigation] = None
        self._build()

    # ── Build ──────────────────────────────────────────────────────────────

    def _build(self) -> None:
        # Top navigation tabs
        self._nb = ttk.Notebook(self)
        self._nb.pack(fill=tk.BOTH, expand=True)

        self._tab_overview = self._build_tab_overview()
        self._tab_evidence = self._build_tab_evidence()
        self._tab_log      = self._build_tab_log()

        self._nb.add(self._tab_overview, text="  Investigation  ")
        self._nb.add(self._tab_evidence, text="  Evidence  ")
        self._nb.add(self._tab_log,      text="  Log  ")

    # ── Main overview tab ──────────────────────────────────────────────────

    def _build_tab_overview(self) -> tk.Frame:
        f = tk.Frame(self._nb, bg=theme.BG_DARK)

        # Scrollable canvas
        canvas = tk.Canvas(f, bg=theme.BG_DARK, highlightthickness=0)
        vsb = ttk.Scrollbar(f, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner = tk.Frame(canvas, bg=theme.BG_DARK)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_configure(_evt):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(win_id, width=canvas.winfo_width())

        inner.bind("<Configure>", _on_configure)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))

        P = dict(padx=32)

        # ── Header row (status badge + problem title) ──────────────────────
        hdr = tk.Frame(inner, bg=theme.BG_DARK)
        hdr.pack(fill=tk.X, padx=32, pady=(24, 0))

        title_row = tk.Frame(hdr, bg=theme.BG_DARK)
        title_row.pack(fill=tk.X)

        tk.Label(
            title_row,
            text="INVESTIGATING",
            font=theme.FONT_LABEL_U,
            fg=theme.FG_ACCENT,
            bg=theme.BG_DARK,
            anchor="w",
        ).pack(side=tk.LEFT)

        self._state_badge = tk.Label(
            title_row,
            text="IDLE",
            font=theme.FONT_BOLD_S,
            fg=theme.FG_MUTED,
            bg=theme.BG_DARK,
            anchor="e",
        )
        self._state_badge.pack(side=tk.RIGHT)

        self._problem_lbl = tk.Label(
            hdr,
            text="No investigation started.",
            font=theme.FONT_BOLD_XL,
            fg=theme.FG_TEXT,
            bg=theme.BG_DARK,
            wraplength=700,
            justify="left",
            anchor="w",
        )
        self._problem_lbl.pack(fill=tk.X, pady=(6, 0))

        # ── Progress section ───────────────────────────────────────────────
        widgets.separator(inner).pack(fill=tk.X, **P, pady=(20, 0))
        prog_hdr = tk.Frame(inner, bg=theme.BG_DARK)
        prog_hdr.pack(fill=tk.X, **P, pady=(14, 0))
        tk.Label(
            prog_hdr,
            text="INVESTIGATION PROGRESS",
            font=theme.FONT_LABEL_U,
            fg=theme.FG_MUTED,
            bg=theme.BG_DARK,
        ).pack(side=tk.LEFT)

        self._progress_frame = tk.Frame(inner, bg=theme.BG_DARK)
        self._progress_frame.pack(fill=tk.X, **P, pady=(8, 0))

        self._step_labels: dict[str, tk.Label] = {}
        self._step_circles: dict[str, tk.Label] = {}
        _steps = [
            ("symptom",    "Understanding the problem"),
            ("project",    "Analyzing project"),
            ("evidence",   "Examining code and evidence"),
            ("hypotheses", "Generating hypotheses"),
            ("root_cause", "Identifying root cause"),
            ("fix",        "Proposing fix"),
            ("tests",      "Verifying fix"),
        ]
        for key, label in _steps:
            row = tk.Frame(self._progress_frame, bg=theme.BG_DARK)
            row.pack(fill=tk.X, pady=3)

            circle = tk.Label(row, text="○", font=theme.FONT_UI_S,
                              fg=theme.FG_SUBTLE, bg=theme.BG_DARK, width=2)
            circle.pack(side=tk.LEFT)

            lbl = tk.Label(row, text=label, font=theme.FONT_UI,
                           fg=theme.FG_SUBTLE, bg=theme.BG_DARK, anchor="w")
            lbl.pack(side=tk.LEFT, padx=(6, 0))

            self._step_labels[key]  = lbl
            self._step_circles[key] = circle

        # ── Current activity ───────────────────────────────────────────────
        widgets.separator(inner).pack(fill=tk.X, **P, pady=(20, 0))
        act_hdr = tk.Frame(inner, bg=theme.BG_DARK)
        act_hdr.pack(fill=tk.X, **P, pady=(14, 0))
        tk.Label(
            act_hdr,
            text="CURRENT ACTIVITY",
            font=theme.FONT_LABEL_U,
            fg=theme.FG_MUTED,
            bg=theme.BG_DARK,
        ).pack(side=tk.LEFT)

        self._activity_lbl = tk.Label(
            inner,
            text="Waiting to start…",
            font=theme.FONT_UI,
            fg=theme.FG_MUTED,
            bg=theme.BG_DARK,
            wraplength=700,
            justify="left",
            anchor="w",
        )
        self._activity_lbl.pack(fill=tk.X, **P, pady=(8, 0))

        # ── Hypotheses section (shown when available) ──────────────────────
        widgets.separator(inner).pack(fill=tk.X, **P, pady=(20, 0))
        self._hyp_section_lbl = tk.Label(
            inner,
            text="POSSIBLE CAUSES",
            font=theme.FONT_LABEL_U,
            fg=theme.FG_MUTED,
            bg=theme.BG_DARK,
        )
        self._hyp_section_lbl.pack(fill=tk.X, **P, pady=(14, 0))

        self._hyp_container = tk.Frame(inner, bg=theme.BG_DARK)
        self._hyp_container.pack(fill=tk.X, **P, pady=(8, 0))

        self._hyp_placeholder = tk.Label(
            self._hyp_container,
            text="Hypotheses will appear here once the investigation begins.",
            font=theme.FONT_UI_S,
            fg=theme.FG_SUBTLE,
            bg=theme.BG_DARK,
        )
        self._hyp_placeholder.pack(anchor="w")

        # ── Root cause section ─────────────────────────────────────────────
        widgets.separator(inner).pack(fill=tk.X, **P, pady=(20, 0))
        self._rc_section_lbl = tk.Label(
            inner,
            text="ROOT CAUSE",
            font=theme.FONT_LABEL_U,
            fg=theme.FG_MUTED,
            bg=theme.BG_DARK,
        )
        self._rc_section_lbl.pack(fill=tk.X, **P, pady=(14, 0))

        self._rc_container = tk.Frame(inner, bg=theme.BG_DARK)
        self._rc_container.pack(fill=tk.X, **P, pady=(8, 0))

        self._rc_placeholder = tk.Label(
            self._rc_container,
            text="Root cause analysis pending…",
            font=theme.FONT_UI_S,
            fg=theme.FG_SUBTLE,
            bg=theme.BG_DARK,
        )
        self._rc_placeholder.pack(anchor="w")

        # ── Fix section ────────────────────────────────────────────────────
        widgets.separator(inner).pack(fill=tk.X, **P, pady=(20, 0))
        fix_hdr = tk.Frame(inner, bg=theme.BG_DARK)
        fix_hdr.pack(fill=tk.X, **P, pady=(14, 0))

        tk.Label(
            fix_hdr,
            text="PROPOSED FIX",
            font=theme.FONT_LABEL_U,
            fg=theme.FG_MUTED,
            bg=theme.BG_DARK,
        ).pack(side=tk.LEFT)

        fix_btn_row = tk.Frame(fix_hdr, bg=theme.BG_DARK)
        fix_btn_row.pack(side=tk.RIGHT)

        self._apply_btn = widgets.success_button(fix_btn_row, "Apply Fix",
                                                  command=self._do_apply_fix)
        self._apply_btn.pack(side=tk.LEFT, padx=(0, 6))

        self._reject_btn = widgets.danger_button(fix_btn_row, "Don't Apply",
                                                  command=self._do_reject_fix)
        self._reject_btn.pack(side=tk.LEFT)

        # Fix summary
        self._fix_summary = tk.Label(
            inner,
            text="No fix proposed yet.",
            font=theme.FONT_UI,
            fg=theme.FG_SUBTLE,
            bg=theme.BG_DARK,
            wraplength=700,
            justify="left",
            anchor="w",
        )
        self._fix_summary.pack(fill=tk.X, **P, pady=(8, 0))

        # Diff view
        diff_section_hdr = tk.Frame(inner, bg=theme.BG_DARK)
        diff_section_hdr.pack(fill=tk.X, **P, pady=(14, 4))
        tk.Label(diff_section_hdr, text="CHANGES",
                 font=theme.FONT_LABEL_U, fg=theme.FG_MUTED,
                 bg=theme.BG_DARK).pack(side=tk.LEFT)

        diff_wrap = tk.Frame(inner, bg=theme.BORDER)
        diff_wrap.pack(fill=tk.X, **P)

        diff_inner = tk.Frame(diff_wrap, bg=theme.BG_CARD)
        diff_inner.pack(fill=tk.X, padx=1, pady=1)

        diff_frame = widgets.make_scrolled_text(diff_inner, height=14,
                                                 font=theme.FONT_MONO_S,
                                                 bg=theme.BG_CARD)
        diff_frame.pack(fill=tk.BOTH, expand=True)
        self._diff_txt = diff_frame.txt
        self._diff_txt.configure(state=tk.DISABLED)
        self._diff_txt.tag_configure("added",   foreground=theme.FG_GREEN,  background="#0d2d0d")
        self._diff_txt.tag_configure("removed", foreground=theme.FG_RED,    background="#2d0d0d")
        self._diff_txt.tag_configure("header",  foreground=theme.FG_ACCENT)
        self._diff_txt.tag_configure("info",    foreground=theme.FG_MUTED)

        # ── Verification section ───────────────────────────────────────────
        widgets.separator(inner).pack(fill=tk.X, **P, pady=(20, 0))
        verif_hdr = tk.Frame(inner, bg=theme.BG_DARK)
        verif_hdr.pack(fill=tk.X, **P, pady=(14, 0))

        tk.Label(verif_hdr, text="VERIFICATION",
                 font=theme.FONT_LABEL_U, fg=theme.FG_MUTED,
                 bg=theme.BG_DARK).pack(side=tk.LEFT)

        widgets.secondary_button(
            verif_hdr, "Run Tests", command=self._on_run_tests
        ).pack(side=tk.RIGHT)

        self._verif_status = tk.Label(
            inner,
            text="",
            font=theme.FONT_BOLD_L,
            fg=theme.FG_MUTED,
            bg=theme.BG_DARK,
            anchor="w",
        )
        self._verif_status.pack(fill=tk.X, **P, pady=(8, 0))

        self._verif_detail = tk.Label(
            inner,
            text="",
            font=theme.FONT_UI,
            fg=theme.FG_MUTED,
            bg=theme.BG_DARK,
            wraplength=700,
            justify="left",
            anchor="w",
        )
        self._verif_detail.pack(fill=tk.X, **P, pady=(4, 0))

        test_wrap = tk.Frame(inner, bg=theme.BORDER)
        test_wrap.pack(fill=tk.X, **P, pady=(10, 0))
        test_inner = tk.Frame(test_wrap, bg=theme.BG_CARD)
        test_inner.pack(fill=tk.X, padx=1, pady=1)

        test_frame = widgets.make_scrolled_text(test_inner, height=8,
                                                 font=theme.FONT_MONO_S,
                                                 bg=theme.BG_CARD)
        test_frame.pack(fill=tk.BOTH, expand=True)
        self._test_txt = test_frame.txt
        self._test_txt.configure(state=tk.DISABLED)
        self._test_txt.tag_configure("pass",    foreground=theme.FG_GREEN)
        self._test_txt.tag_configure("fail",    foreground=theme.FG_RED)
        self._test_txt.tag_configure("unavail", foreground=theme.FG_YELLOW)

        widgets.vspace(inner, 40).pack()

        return f

    # ── Evidence tab ──────────────────────────────────────────────────────

    def _build_tab_evidence(self) -> tk.Frame:
        f = tk.Frame(self._nb, bg=theme.BG_DARK)

        tk.Label(f, text="EVIDENCE",
                 font=theme.FONT_LABEL_U, fg=theme.FG_MUTED,
                 bg=theme.BG_DARK, anchor="w").pack(fill=tk.X, padx=24, pady=(20, 6))

        ev_frame = tk.Frame(f, bg=theme.BG_DARK)
        ev_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=4)

        cols = ("kind", "title", "source")
        self._ev_tree = ttk.Treeview(ev_frame, columns=cols, show="headings", height=10)
        self._ev_tree.heading("kind",   text="Kind")
        self._ev_tree.heading("title",  text="Evidence")
        self._ev_tree.heading("source", text="Source")
        self._ev_tree.column("kind",   width=120, stretch=False)
        self._ev_tree.column("title",  width=420)
        self._ev_tree.column("source", width=160)

        ev_sb = ttk.Scrollbar(ev_frame, command=self._ev_tree.yview)
        self._ev_tree.configure(yscrollcommand=ev_sb.set)
        self._ev_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ev_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._ev_tree.bind("<<TreeviewSelect>>", self._on_evidence_select)

        tk.Label(f, text="DETAIL",
                 font=theme.FONT_LABEL_U, fg=theme.FG_MUTED,
                 bg=theme.BG_DARK, anchor="w").pack(fill=tk.X, padx=24, pady=(14, 4))

        det_wrap = tk.Frame(f, bg=theme.BORDER)
        det_wrap.pack(fill=tk.X, padx=24, pady=(0, 4))
        det_inner = tk.Frame(det_wrap, bg=theme.BG_CARD)
        det_inner.pack(fill=tk.X, padx=1, pady=1)

        det_frame = widgets.make_scrolled_text(det_inner, height=6, bg=theme.BG_CARD)
        det_frame.pack(fill=tk.X)
        self._ev_detail_txt = det_frame.txt
        self._ev_detail_txt.configure(state=tk.DISABLED)

        return f

    # ── Log tab ────────────────────────────────────────────────────────────

    def _build_tab_log(self) -> tk.Frame:
        f = tk.Frame(self._nb, bg=theme.BG_DARK)

        tk.Label(f, text="INVESTIGATION LOG",
                 font=theme.FONT_LABEL_U, fg=theme.FG_MUTED,
                 bg=theme.BG_DARK, anchor="w").pack(fill=tk.X, padx=24, pady=(20, 6))

        log_wrap = tk.Frame(f, bg=theme.BORDER)
        log_wrap.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 16))
        log_inner = tk.Frame(log_wrap, bg=theme.BG_CARD)
        log_inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        log_frame = widgets.make_scrolled_text(log_inner, height=28,
                                                font=theme.FONT_MONO_S,
                                                bg=theme.BG_CARD)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self._log_txt = log_frame.txt
        self._log_txt.configure(state=tk.DISABLED)
        self._log_txt.tag_configure("ts",    foreground=theme.FG_SUBTLE)
        self._log_txt.tag_configure("msg",   foreground=theme.FG_TEXT)
        self._log_txt.tag_configure("error", foreground=theme.FG_RED)

        return f

    # ── Public update methods ──────────────────────────────────────────────

    def update_state(self, state: InvestigationState, message: str) -> None:
        color = theme.STATUS_COLORS.get(state.value, theme.FG_MUTED)
        self._state_badge.configure(text=state.value, fg=color)
        self._activity_lbl.configure(
            text=message,
            fg=theme.FG_TEXT if state != InvestigationState.IDLE else theme.FG_MUTED,
        )

    def refresh(self, inv: Investigation) -> None:
        """Full refresh of all panels from the current Investigation state."""
        self._inv = inv

        # Header
        if inv.symptom:
            desc = inv.symptom.description
            self._problem_lbl.configure(
                text=f'"{desc[:120]}"' if len(desc) <= 120 else f'"{desc[:117]}…"',
                fg=theme.FG_TEXT,
            )

        color = theme.STATUS_COLORS.get(inv.state.value, theme.FG_MUTED)
        self._state_badge.configure(text=inv.state.value, fg=color)

        # Progress steps
        self._update_progress(inv)

        # Hypotheses
        self._refresh_hypotheses(inv)

        # Root cause
        self._refresh_root_cause(inv)

        # Fix
        self._refresh_fix(inv)

        # Tests
        self._refresh_tests(inv)

        # Evidence tab
        self._refresh_evidence(inv)

        # Log tab
        self._refresh_log(inv)

    def append_log(self, message: str) -> None:
        parts = message.split("] ", 1)
        self._log_txt.configure(state=tk.NORMAL)
        if len(parts) == 2:
            self._log_txt.insert(tk.END, parts[0] + "] ", "ts")
            tag = "error" if "error" in parts[1].lower() else "msg"
            self._log_txt.insert(tk.END, parts[1] + "\n", tag)
        else:
            self._log_txt.insert(tk.END, message + "\n", "msg")
        self._log_txt.configure(state=tk.DISABLED)
        self._log_txt.see(tk.END)

    # ── Progress update ────────────────────────────────────────────────────

    def _update_progress(self, inv: Investigation) -> None:
        steps_done = {
            "symptom":    inv.symptom is not None,
            "project":    bool(inv.system_model),
            "evidence":   len(inv.evidence) > 0,
            "hypotheses": len(inv.hypotheses) > 0,
            "root_cause": inv.root_cause is not None,
            "fix":        inv.proposed_fix is not None,
            "tests":      (inv.verification is not None
                           and len(inv.verification.test_results) > 0),
        }
        label_map = {
            "symptom":    "Understanding the problem",
            "project":    "Analyzing project",
            "evidence":   "Examining code and evidence",
            "hypotheses": "Generating hypotheses",
            "root_cause": "Identifying root cause",
            "fix":        "Proposing fix",
            "tests":      "Verifying fix",
        }

        # Determine active step
        active_key = None
        for key in ["symptom", "project", "evidence", "hypotheses", "root_cause", "fix", "tests"]:
            if not steps_done.get(key, False):
                active_key = key
                break

        for key, lbl in self._step_labels.items():
            circle = self._step_circles[key]
            done = steps_done.get(key, False)
            if done:
                circle.configure(text="✓", fg=theme.FG_GREEN)
                lbl.configure(text=label_map[key], fg=theme.FG_GREEN,
                               font=theme.FONT_UI)
            elif key == active_key:
                circle.configure(text="●", fg=theme.FG_YELLOW)
                lbl.configure(text=label_map[key], fg=theme.FG_TEXT,
                               font=theme.FONT_BOLD)
            else:
                circle.configure(text="○", fg=theme.FG_SUBTLE)
                lbl.configure(text=label_map[key], fg=theme.FG_SUBTLE,
                               font=theme.FONT_UI)

    # ── Hypotheses ─────────────────────────────────────────────────────────

    def _refresh_hypotheses(self, inv: Investigation) -> None:
        for child in self._hyp_container.winfo_children():
            child.destroy()

        if not inv.hypotheses:
            self._hyp_placeholder = tk.Label(
                self._hyp_container,
                text="Hypotheses will appear here once the investigation begins.",
                font=theme.FONT_UI_S,
                fg=theme.FG_SUBTLE,
                bg=theme.BG_DARK,
            )
            self._hyp_placeholder.pack(anchor="w")
            return

        sorted_h = sorted(inv.hypotheses, key=lambda h: h.confidence, reverse=True)
        for i, h in enumerate(sorted_h[:5]):
            self._hyp_card(self._hyp_container, i + 1, h)

    def _hyp_card(self, parent: tk.Frame, rank: int, h: Hypothesis) -> None:
        outer = tk.Frame(parent, bg=theme.BORDER)
        outer.pack(fill=tk.X, pady=4)

        inner = tk.Frame(outer, bg=theme.BG_CARD)
        inner.pack(fill=tk.X, padx=1, pady=1)

        content = tk.Frame(inner, bg=theme.BG_CARD)
        content.pack(fill=tk.X, padx=16, pady=14)

        # Rank + title row
        top_row = tk.Frame(content, bg=theme.BG_CARD)
        top_row.pack(fill=tk.X)

        rank_color = theme.FG_ORANGE if rank == 1 else theme.FG_MUTED
        tk.Label(top_row,
                 text=f"{rank:02d}",
                 font=theme.FONT_BOLD,
                 fg=rank_color,
                 bg=theme.BG_CARD,
                 width=3,
                 anchor="w",
                 ).pack(side=tk.LEFT)

        tk.Label(top_row,
                 text=h.title[:90],
                 font=theme.FONT_BOLD,
                 fg=theme.FG_TEXT,
                 bg=theme.BG_CARD,
                 anchor="w",
                 ).pack(side=tk.LEFT, padx=(6, 0))

        # Confidence
        conf_pct = h.confidence_pct()
        conf_color = (theme.FG_GREEN if conf_pct >= 70
                      else theme.FG_YELLOW if conf_pct >= 40
                      else theme.FG_MUTED)

        conf_row = tk.Frame(content, bg=theme.BG_CARD)
        conf_row.pack(fill=tk.X, pady=(6, 0))

        tk.Label(conf_row,
                 text=f"Confidence: {conf_pct}%",
                 font=theme.FONT_UI_S,
                 fg=conf_color,
                 bg=theme.BG_CARD,
                 anchor="w",
                 ).pack(side=tk.LEFT)

        # Description (truncated)
        if h.description:
            tk.Label(content,
                     text=h.description[:200],
                     font=theme.FONT_UI_S,
                     fg=theme.FG_MUTED,
                     bg=theme.BG_CARD,
                     wraplength=640,
                     justify="left",
                     anchor="w",
                     ).pack(fill=tk.X, pady=(6, 0))

        # Expand toggle
        expand_frame = tk.Frame(inner, bg=theme.BG_CARD)
        expand_open = tk.BooleanVar(value=False)

        expand_content = tk.Frame(inner, bg=theme.BG_CARD)

        if h.evidence_for or h.evidence_against:
            ev_txt = tk.Text(
                expand_content,
                height=6,
                font=theme.FONT_UI_S,
                bg=theme.BG_INPUT,
                fg=theme.FG_TEXT,
                state=tk.NORMAL,
                relief=tk.FLAT,
                bd=0,
                padx=12,
                pady=8,
            )
            ev_txt.tag_configure("for",     foreground=theme.FG_GREEN)
            ev_txt.tag_configure("against", foreground=theme.FG_RED)
            ev_txt.tag_configure("hdr",     foreground=theme.FG_ACCENT,
                                 font=theme.FONT_BOLD_S)

            for bullet in h.evidence_for:
                ev_txt.insert(tk.END, f"  + {bullet}\n", "for")
            for bullet in h.evidence_against:
                ev_txt.insert(tk.END, f"  - {bullet}\n", "against")
            ev_txt.configure(state=tk.DISABLED)
            ev_txt.pack(fill=tk.X, padx=1, pady=(0, 1))

        detail_btn = tk.Button(
            content,
            text="View Evidence ▼",
            font=theme.FONT_UI_S,
            fg=theme.FG_ACCENT,
            bg=theme.BG_CARD,
            activebackground=theme.BG_CARD,
            activeforeground=theme.FG_TEXT,
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
        )
        detail_btn.pack(anchor="w", pady=(8, 0))

        def _toggle(_btn=detail_btn, _frame=expand_content, _var=expand_open):
            if _var.get():
                _var.set(False)
                _frame.pack_forget()
                _btn.configure(text="View Evidence ▼")
            else:
                _var.set(True)
                _frame.pack(fill=tk.X, padx=1, pady=(0, 1))
                _btn.configure(text="View Evidence ▲")

        detail_btn.configure(command=_toggle)

    # ── Root cause ─────────────────────────────────────────────────────────

    def _refresh_root_cause(self, inv: Investigation) -> None:
        for child in self._rc_container.winfo_children():
            child.destroy()

        if inv.root_cause is None:
            tk.Label(
                self._rc_container,
                text="Root cause analysis pending…",
                font=theme.FONT_UI_S,
                fg=theme.FG_SUBTLE,
                bg=theme.BG_DARK,
            ).pack(anchor="w")
            return

        rc = inv.root_cause

        # Prominent root cause card
        outer = tk.Frame(self._rc_container, bg=theme.FG_ACCENT)
        outer.pack(fill=tk.X)

        inner = tk.Frame(outer, bg=theme.BG_CARD)
        inner.pack(fill=tk.X, padx=2, pady=2)

        content = tk.Frame(inner, bg=theme.BG_CARD)
        content.pack(fill=tk.X, padx=20, pady=18)

        tk.Label(
            content,
            text="ROOT CAUSE IDENTIFIED",
            font=theme.FONT_LABEL_U,
            fg=theme.FG_ACCENT,
            bg=theme.BG_CARD,
            anchor="w",
        ).pack(anchor="w")

        tk.Label(
            content,
            text=rc.summary,
            font=theme.FONT_BOLD_L,
            fg=theme.FG_TEXT,
            bg=theme.BG_CARD,
            wraplength=660,
            justify="left",
            anchor="w",
        ).pack(fill=tk.X, pady=(8, 0))

        # Mechanism
        if rc.mechanism:
            widgets.separator(content, color=theme.BORDER).pack(fill=tk.X, pady=(14, 0))
            tk.Label(
                content,
                text="WHY THIS HAPPENS",
                font=theme.FONT_LABEL_U,
                fg=theme.FG_MUTED,
                bg=theme.BG_CARD,
            ).pack(anchor="w", pady=(10, 4))
            tk.Label(
                content,
                text=rc.mechanism,
                font=theme.FONT_UI,
                fg=theme.FG_MUTED,
                bg=theme.BG_CARD,
                wraplength=660,
                justify="left",
                anchor="w",
            ).pack(anchor="w")

        # Evidence bullets
        if rc.evidence:
            tk.Label(
                content,
                text="EVIDENCE",
                font=theme.FONT_LABEL_U,
                fg=theme.FG_MUTED,
                bg=theme.BG_CARD,
            ).pack(anchor="w", pady=(14, 4))
            for bullet in rc.evidence:
                row = tk.Frame(content, bg=theme.BG_CARD)
                row.pack(fill=tk.X, pady=1)
                tk.Label(row, text="✓", font=theme.FONT_UI_S,
                         fg=theme.FG_GREEN, bg=theme.BG_CARD).pack(side=tk.LEFT)
                tk.Label(row, text=bullet, font=theme.FONT_UI_S,
                         fg=theme.FG_MUTED, bg=theme.BG_CARD,
                         anchor="w").pack(side=tk.LEFT, padx=(6, 0))

        # Source locations
        if rc.source_locations:
            tk.Label(
                content,
                text="AFFECTED FILES",
                font=theme.FONT_LABEL_U,
                fg=theme.FG_MUTED,
                bg=theme.BG_CARD,
            ).pack(anchor="w", pady=(14, 4))
            for file, line, note in rc.source_locations:
                row = tk.Frame(content, bg=theme.BG_CARD)
                row.pack(fill=tk.X, pady=1)
                tk.Label(row, text=f"{file}:{line}",
                         font=theme.FONT_MONO_S, fg=theme.FG_CYAN,
                         bg=theme.BG_CARD).pack(side=tk.LEFT)
                if note:
                    tk.Label(row, text=f"  — {note}",
                             font=theme.FONT_UI_S, fg=theme.FG_MUTED,
                             bg=theme.BG_CARD).pack(side=tk.LEFT)

    # ── Fix ────────────────────────────────────────────────────────────────

    def _refresh_fix(self, inv: Investigation) -> None:
        if inv.proposed_fix is None:
            self._fix_summary.configure(
                text="No fix proposed yet.", fg=theme.FG_SUBTLE)
            self._set_text(self._diff_txt, "")
            return

        fix = inv.proposed_fix
        self._fix_summary.configure(
            text=fix.summary if fix.summary else fix.explanation[:200],
            fg=theme.FG_TEXT,
        )

        self._diff_txt.configure(state=tk.NORMAL)
        self._diff_txt.delete("1.0", tk.END)

        if not fix.diffs:
            self._diff_txt.insert(tk.END, fix.explanation + "\n", "info")
        else:
            for diff in fix.diffs:
                self._diff_txt.insert(tk.END, f"--- {diff.file}\n", "header")
                self._diff_txt.insert(tk.END, f"+++ {diff.file}\n", "header")
                if diff.explanation:
                    self._diff_txt.insert(tk.END, f"# {diff.explanation}\n", "info")
                for line in diff.unified_diff_lines():
                    if line.startswith("+") and not line.startswith("+++"):
                        self._diff_txt.insert(tk.END, line, "added")
                    elif line.startswith("-") and not line.startswith("---"):
                        self._diff_txt.insert(tk.END, line, "removed")
                    elif line.startswith("@@"):
                        self._diff_txt.insert(tk.END, line, "header")
                    else:
                        self._diff_txt.insert(tk.END, line, "info")

        self._diff_txt.configure(state=tk.DISABLED)

    # ── Tests / verification ───────────────────────────────────────────────

    def _refresh_tests(self, inv: Investigation) -> None:
        if inv.verification is None:
            return

        v = inv.verification
        status_color = theme.VERIFICATION_COLORS.get(v.status.value, theme.FG_MUTED)
        status_text  = v.status.value.replace("_", " ")
        self._verif_status.configure(text=status_text, fg=status_color)

        if v.status.value == "VERIFIED":
            self._verif_detail.configure(
                text="The original failure could no longer be reproduced under the available test conditions.",
                fg=theme.FG_GREEN,
            )
        elif v.status.value == "FAILED":
            self._verif_detail.configure(
                text="Verification failed — the fix did not resolve the issue.",
                fg=theme.FG_RED,
            )
        elif v.notes:
            self._verif_detail.configure(text=v.notes, fg=theme.FG_YELLOW)

        self._test_txt.configure(state=tk.NORMAL)
        self._test_txt.delete("1.0", tk.END)
        for r in v.test_results:
            tag = "pass" if r.passed else ("unavail" if r.passed is None else "fail")
            marker = "✓ PASS" if r.passed else ("? " if r.passed is None else "✗ FAIL")
            self._test_txt.insert(tk.END, f"{marker}  {r.command}\n", tag)
            if r.stdout.strip():
                self._test_txt.insert(tk.END, r.stdout[:600] + "\n", "unavail")
            if r.stderr.strip():
                self._test_txt.insert(tk.END, r.stderr[:600] + "\n", "fail")
        self._test_txt.configure(state=tk.DISABLED)

    # ── Evidence tab refresh ───────────────────────────────────────────────

    def _refresh_evidence(self, inv: Investigation) -> None:
        for item in self._ev_tree.get_children():
            self._ev_tree.delete(item)
        for ev in inv.evidence:
            src = ev.source_file or ""
            if ev.line_number:
                src += f":{ev.line_number}"
            self._ev_tree.insert("", tk.END, iid=ev.id,
                                 values=(ev.kind.value, ev.title[:80], src))

    def _on_evidence_select(self, event) -> None:
        if not self._inv:
            return
        sel = self._ev_tree.selection()
        if not sel:
            return
        ev_id = sel[0]
        for ev in self._inv.evidence:
            if ev.id == ev_id:
                detail = f"[{ev.kind.value}] {ev.title}\n\n{ev.detail}"
                if ev.source_file:
                    detail += f"\n\nSource: {ev.source_file}"
                    if ev.line_number:
                        detail += f":{ev.line_number}"
                self._set_text(self._ev_detail_txt, detail)
                break

    # ── Log refresh ────────────────────────────────────────────────────────

    def _refresh_log(self, inv: Investigation) -> None:
        self._log_txt.configure(state=tk.NORMAL)
        self._log_txt.delete("1.0", tk.END)
        for line in inv.log:
            parts = line.split("] ", 1)
            if len(parts) == 2:
                self._log_txt.insert(tk.END, parts[0] + "] ", "ts")
                tag = "error" if "error" in parts[1].lower() else "msg"
                self._log_txt.insert(tk.END, parts[1] + "\n", tag)
            else:
                self._log_txt.insert(tk.END, line + "\n", "msg")
        self._log_txt.configure(state=tk.DISABLED)
        self._log_txt.see(tk.END)

    # ── Action handlers ────────────────────────────────────────────────────

    def _do_apply_fix(self) -> None:
        if self._inv and self._inv.proposed_fix:
            self._on_apply_fix(self._inv.proposed_fix)

    def _do_reject_fix(self) -> None:
        if self._inv and self._inv.proposed_fix:
            self._inv.proposed_fix.approved = False
            self._fix_summary.configure(
                text="Fix rejected. You can manually apply the suggested changes.",
                fg=theme.FG_MUTED,
            )

    # ── Utilities ──────────────────────────────────────────────────────────

    def _set_text(self, widget: tk.Text, content: str, tag: str = "") -> None:
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        if tag:
            widget.insert("1.0", content, tag)
        else:
            widget.insert("1.0", content)
        widget.configure(state=tk.DISABLED)

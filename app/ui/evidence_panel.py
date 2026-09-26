"""
app/ui/evidence_panel.py

Step 3 — SHOW ME WHAT YOU HAVE

Large visual option cards for adding evidence categories:
  📄 Source Code      🧪 Test Results
  📋 Logs / Output    📐 Hardware Info

Users can also skip this step and go directly to investigation.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog
from typing import Callable, Optional

from app.ui import theme, widgets


_EVIDENCE_OPTIONS = [
    ("source",   "📄", "Source Code",    "Add source files or paste code snippets."),
    ("tests",    "🧪", "Test Results",   "Add test output or build logs."),
    ("logs",     "📋", "Logs",           "Add serial output, UART logs, or debug traces."),
    ("hardware", "📐", "Hardware Info",  "Add schematics, pin maps, or board notes."),
]


class EvidencePanel(tk.Frame):
    """
    Step 3 — evidence collection panel.

    Callbacks:
      on_continue(evidence_dict)  — user clicked Investigate
    """

    def __init__(self, parent, on_continue: Callable, **kw):
        super().__init__(parent, bg=theme.BG_DARK, **kw)
        self._on_continue = on_continue
        self._content: dict[str, str] = {}   # evidence_key -> text
        self._card_states: dict[str, bool] = {k: False for k, *_ in _EVIDENCE_OPTIONS}
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        from tkinter import ttk
        canvas = tk.Canvas(self, bg=theme.BG_DARK, highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
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

        self._build_content(inner)

    def _build_content(self, parent: tk.Frame) -> None:
        P = dict(padx=60)

        # Step header
        hdr = tk.Frame(parent, bg=theme.BG_DARK)
        hdr.pack(fill=tk.X, padx=60, pady=(36, 0))

        tk.Label(
            hdr,
            text="STEP 3",
            font=theme.FONT_LABEL_U,
            fg=theme.FG_ACCENT,
            bg=theme.BG_DARK,
        ).pack(anchor="w")

        tk.Label(
            hdr,
            text="Show Me What You Have",
            font=theme.FONT_BOLD_XL,
            fg=theme.FG_TEXT,
            bg=theme.BG_DARK,
        ).pack(anchor="w", pady=(4, 0))

        tk.Label(
            hdr,
            text="Add any information that might help.  You don't need everything.",
            font=theme.FONT_UI_L,
            fg=theme.FG_MUTED,
            bg=theme.BG_DARK,
        ).pack(anchor="w", pady=(4, 0))

        widgets.vspace(parent, 28).pack()

        # ── Evidence cards grid ───────────────────────────────────────────────
        grid = tk.Frame(parent, bg=theme.BG_DARK)
        grid.pack(fill=tk.X, **P)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        self._card_frames: dict[str, tk.Frame] = {}
        self._expand_frames: dict[str, tk.Frame] = {}
        self._text_widgets: dict[str, tk.Text] = {}

        for idx, (key, icon, title, desc) in enumerate(_EVIDENCE_OPTIONS):
            row, col = divmod(idx, 2)
            self._build_evidence_card(grid, row, col, key, icon, title, desc)

        # ── Skip / proceed options ────────────────────────────────────────────
        widgets.vspace(parent, 20).pack()

        skip_outer = tk.Frame(parent, bg=theme.BORDER)
        skip_outer.pack(fill=tk.X, **P)
        skip_inner = tk.Frame(skip_outer, bg=theme.BG_CARD, cursor="hand2")
        skip_inner.pack(fill=tk.X, padx=1, pady=1)

        skip_content = tk.Frame(skip_inner, bg=theme.BG_CARD)
        skip_content.pack(padx=20, pady=18)

        tk.Label(
            skip_content,
            text="No additional evidence — Investigate what you have",
            font=theme.FONT_BOLD,
            fg=theme.FG_TEXT,
            bg=theme.BG_CARD,
        ).pack()

        tk.Label(
            skip_content,
            text="The AI will analyze your project code directly.",
            font=theme.FONT_UI_S,
            fg=theme.FG_MUTED,
            bg=theme.BG_CARD,
        ).pack(pady=(4, 0))

        def _skip(_evt=None):
            self._on_continue({})

        for w in [skip_inner, skip_content]:
            w.bind("<Button-1>", _skip)
            w.bind("<Enter>", lambda e, f=skip_inner, c=skip_content: (
                f.configure(bg=theme.BG_HOVER), c.configure(bg=theme.BG_HOVER)))
            w.bind("<Leave>", lambda e, f=skip_inner, c=skip_content: (
                f.configure(bg=theme.BG_CARD), c.configure(bg=theme.BG_CARD)))

        # ── Primary CTA ───────────────────────────────────────────────────────
        widgets.vspace(parent, 28).pack()
        cta_row = tk.Frame(parent, bg=theme.BG_DARK)
        cta_row.pack(**P)

        widgets.primary_button(
            cta_row,
            "Continue →  Start Investigation",
            command=self._proceed,
            wide=True,
        ).pack(side=tk.LEFT)

        widgets.vspace(parent, 40).pack()

    def _build_evidence_card(
        self,
        grid: tk.Frame,
        row: int,
        col: int,
        key: str,
        icon: str,
        title: str,
        desc: str,
    ) -> None:
        pad_x = (0, 8) if col == 0 else (8, 0)
        cell = tk.Frame(grid, bg=theme.BG_DARK)
        cell.grid(row=row, column=col, sticky="nsew", padx=pad_x, pady=6)

        outer = tk.Frame(cell, bg=theme.BORDER)
        outer.pack(fill=tk.X)

        card_frame = tk.Frame(outer, bg=theme.BG_CARD, cursor="hand2")
        card_frame.pack(fill=tk.X, padx=1, pady=1)

        header = tk.Frame(card_frame, bg=theme.BG_CARD)
        header.pack(fill=tk.X, padx=16, pady=14)

        icon_lbl = tk.Label(
            header,
            text=icon,
            font=("Segoe UI", 20),
            fg=theme.FG_TEXT,
            bg=theme.BG_CARD,
        )
        icon_lbl.pack(side=tk.LEFT)

        txt_block = tk.Frame(header, bg=theme.BG_CARD)
        txt_block.pack(side=tk.LEFT, padx=(10, 0))

        title_lbl = tk.Label(
            txt_block,
            text=title,
            font=theme.FONT_BOLD,
            fg=theme.FG_TEXT,
            bg=theme.BG_CARD,
            anchor="w",
        )
        title_lbl.pack(anchor="w")

        desc_lbl = tk.Label(
            txt_block,
            text=desc,
            font=theme.FONT_UI_S,
            fg=theme.FG_MUTED,
            bg=theme.BG_CARD,
            anchor="w",
        )
        desc_lbl.pack(anchor="w")

        # Checkmark (hidden until added)
        check_lbl = tk.Label(
            header,
            text="✓ Added",
            font=theme.FONT_BOLD_S,
            fg=theme.FG_GREEN,
            bg=theme.BG_CARD,
        )
        check_lbl.pack(side=tk.RIGHT)
        check_lbl.pack_forget()

        # Expand area (hidden until card clicked)
        expand = tk.Frame(outer, bg=theme.BG_CARD)
        expand.pack(fill=tk.X, padx=1, pady=(0, 1))
        expand.pack_forget()

        # Text area inside expand
        sep = tk.Frame(expand, height=1, bg=theme.BORDER)
        sep.pack(fill=tk.X)

        txt = tk.Text(
            expand,
            height=5,
            font=theme.FONT_MONO_S,
            bg=theme.BG_INPUT,
            fg=theme.FG_CYAN,
            insertbackground=theme.FG_TEXT,
            selectbackground=theme.BG_SEL,
            relief=tk.FLAT,
            bd=0,
            wrap=tk.NONE,
            padx=10,
            pady=8,
        )
        txt.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        action_row = tk.Frame(expand, bg=theme.BG_CARD)
        action_row.pack(fill=tk.X, padx=12, pady=6)

        def _load_file(_key=key, _txt=txt):
            path = filedialog.askopenfilename(
                title="Load file",
                filetypes=[("Text files", "*.txt *.log *.out *.c *.h"), ("All files", "*.*")],
            )
            if path:
                try:
                    with open(path, encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    _txt.delete("1.0", tk.END)
                    _txt.insert("1.0", content)
                except OSError:
                    pass

        tk.Button(
            action_row,
            text="Load file…",
            font=theme.FONT_UI_S,
            fg=theme.FG_ACCENT,
            bg=theme.BG_CARD,
            relief=tk.FLAT, bd=0, padx=0, pady=0,
            cursor="hand2",
            command=_load_file,
        ).pack(side=tk.LEFT)

        self._card_frames[key] = card_frame
        self._expand_frames[key] = expand
        self._text_widgets[key] = txt

        def _toggle(_key=key, _expand=expand, _card=card_frame, _check=check_lbl,
                     _outer=outer, _evt=None):
            open_state = self._card_states[_key]
            if open_state:
                self._card_states[_key] = False
                _expand.pack_forget()
                _check.pack_forget()
            else:
                self._card_states[_key] = True
                _expand.pack(fill=tk.X, padx=1, pady=(0, 1))
                _check.pack(side=tk.RIGHT)

        click_widgets = [card_frame, header, icon_lbl, txt_block, title_lbl, desc_lbl]
        for w in click_widgets:
            w.bind("<Button-1>", _toggle)
            w.bind("<Enter>", lambda e, c=card_frame: c.configure(bg=theme.BG_HOVER))
            w.bind("<Leave>", lambda e, c=card_frame: c.configure(bg=theme.BG_CARD))

    # ── Public API ────────────────────────────────────────────────────────────

    def prefill_evidence(self, compiler_output: str = "", serial_log: str = "") -> None:
        """Pre-populate evidence from the problem form."""
        if compiler_output and "tests" in self._text_widgets:
            txt = self._text_widgets["tests"]
            txt.delete("1.0", tk.END)
            txt.insert("1.0", compiler_output)
            self._card_states["tests"] = True

        if serial_log and "logs" in self._text_widgets:
            txt = self._text_widgets["logs"]
            txt.delete("1.0", tk.END)
            txt.insert("1.0", serial_log)
            self._card_states["logs"] = True

    # ── Proceed ───────────────────────────────────────────────────────────────

    def _proceed(self) -> None:
        evidence = {}
        for key, txt in self._text_widgets.items():
            val = txt.get("1.0", "end-1c").strip()
            if val:
                evidence[key] = val
        self._on_continue(evidence)

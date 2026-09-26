"""
app/ui/problem_form.py

Step 2 — WHAT'S WRONG?

Embedded as a full content-area panel (not a modal), part of the guided workflow.
Uses plain language prompts and optional placeholder text to lower friction.

Calls on_submit(description, expected, actual, steps, frequency,
               compiler_output, serial_log, hardware_notes)
"""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, ttk
from typing import Callable, Optional

from app.ui import theme, widgets


class ProblemForm(tk.Frame):
    """
    Step 2 — problem description panel.

    Embedded in the main content area as part of the guided workflow.
    """

    def __init__(self, parent, on_submit: Callable, prefill: Optional[dict] = None, **kw):
        super().__init__(parent, bg=theme.BG_DARK, **kw)
        self._on_submit = on_submit
        self._prefill = prefill or {}
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self) -> None:
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
            text="STEP 2",
            font=theme.FONT_LABEL_U,
            fg=theme.FG_ACCENT,
            bg=theme.BG_DARK,
        ).pack(anchor="w")

        tk.Label(
            hdr,
            text="What's Wrong?",
            font=theme.FONT_BOLD_XL,
            fg=theme.FG_TEXT,
            bg=theme.BG_DARK,
        ).pack(anchor="w", pady=(4, 0))

        tk.Label(
            hdr,
            text="Describe the problem in your own words. You don't need to be technical.",
            font=theme.FONT_UI_L,
            fg=theme.FG_MUTED,
            bg=theme.BG_DARK,
        ).pack(anchor="w", pady=(4, 0))

        widgets.vspace(parent, 28).pack()

        # ── Primary description ───────────────────────────────────────────────
        self._desc = self._field(
            parent,
            label="Tell me what went wrong.",
            placeholder="Example: The sensor occasionally reports 0 even though the sensor is connected.",
            height=4,
            prefill_key="description",
            required=True,
        )

        widgets.vspace(parent, 20).pack()

        # ── Expected / Actual ────────────────────────────────────────────────
        two_col = tk.Frame(parent, bg=theme.BG_DARK)
        two_col.pack(fill=tk.X, **P)
        two_col.columnconfigure(0, weight=1)
        two_col.columnconfigure(1, weight=1)

        left = tk.Frame(two_col, bg=theme.BG_DARK)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right = tk.Frame(two_col, bg=theme.BG_DARK)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self._exp = self._inline_field(
            left,
            label="What did you expect?",
            placeholder="The sensor should continuously report the measured value.",
            height=3,
            prefill_key="expected",
        )
        self._act = self._inline_field(
            right,
            label="What actually happened?",
            placeholder="Every few seconds the reading becomes 0.",
            height=3,
            prefill_key="actual",
        )

        widgets.vspace(parent, 20).pack()

        # ── Frequency ────────────────────────────────────────────────────────
        freq_frame = tk.Frame(parent, bg=theme.BG_DARK)
        freq_frame.pack(fill=tk.X, **P)

        tk.Label(
            freq_frame,
            text="How often does it happen?",
            font=theme.FONT_BOLD,
            fg=theme.FG_TEXT,
            bg=theme.BG_DARK,
            anchor="w",
        ).pack(anchor="w", pady=(0, 8))

        self._freq_var = tk.StringVar(value=self._prefill.get("frequency", "Unknown"))
        btn_row = tk.Frame(freq_frame, bg=theme.BG_DARK)
        btn_row.pack(anchor="w")

        for val in ("Always", "Sometimes", "Rarely", "Unknown"):
            self._freq_btn(btn_row, val)

        widgets.vspace(parent, 28).pack()
        widgets.separator(parent).pack(fill=tk.X, **P)

        # ── Optional evidence section ─────────────────────────────────────────
        widgets.vspace(parent, 20).pack()
        self._build_optional_section(parent)

        # ── Submit button ─────────────────────────────────────────────────────
        widgets.vspace(parent, 32).pack()
        btn_row2 = tk.Frame(parent, bg=theme.BG_DARK)
        btn_row2.pack(**P)

        self._error_lbl = tk.Label(
            btn_row2,
            text="",
            font=theme.FONT_UI_S,
            fg=theme.FG_RED,
            bg=theme.BG_DARK,
        )
        self._error_lbl.pack(anchor="w", pady=(0, 8))

        widgets.primary_button(
            btn_row2, "Continue →  Start Investigation",
            command=self._submit, wide=True,
        ).pack(side=tk.LEFT)

        widgets.vspace(parent, 40).pack()

    def _freq_btn(self, parent, val: str) -> None:
        var = self._freq_var

        def _select(_v=val):
            var.set(_v)
            self._refresh_freq_buttons()

        btn = tk.Button(
            parent,
            text=val,
            font=theme.FONT_UI_S,
            fg=theme.FG_MUTED,
            bg=theme.BG_CARD,
            activebackground=theme.BG_HOVER,
            activeforeground=theme.FG_TEXT,
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            command=_select,
        )
        btn.pack(side=tk.LEFT, padx=4)
        btn._freq_val = val

        if not hasattr(self, "_freq_buttons"):
            self._freq_buttons = []
        self._freq_buttons.append(btn)

    def _refresh_freq_buttons(self) -> None:
        val = self._freq_var.get()
        for btn in getattr(self, "_freq_buttons", []):
            if btn._freq_val == val:
                btn.configure(fg=theme.FG_ACCENT, bg=theme.BG_SEL)
            else:
                btn.configure(fg=theme.FG_MUTED, bg=theme.BG_CARD)

    def _build_optional_section(self, parent: tk.Frame) -> None:
        disc = tk.Frame(parent, bg=theme.BG_DARK)
        disc.pack(fill=tk.X, padx=60)

        # Toggle header
        self._opt_open = tk.BooleanVar(value=False)
        self._opt_content = None

        toggle_row = tk.Frame(disc, bg=theme.BG_DARK)
        toggle_row.pack(fill=tk.X)

        self._opt_arrow = tk.Label(
            toggle_row,
            text="▶  Optional: Add supporting evidence",
            font=theme.FONT_BOLD,
            fg=theme.FG_MUTED,
            bg=theme.BG_DARK,
            cursor="hand2",
        )
        self._opt_arrow.pack(side=tk.LEFT)

        tk.Label(
            toggle_row,
            text="(compiler output, logs, hardware notes)",
            font=theme.FONT_UI_S,
            fg=theme.FG_SUBTLE,
            bg=theme.BG_DARK,
        ).pack(side=tk.LEFT, padx=(8, 0))

        self._opt_frame = tk.Frame(disc, bg=theme.BG_DARK)

        def _toggle(_evt=None):
            if self._opt_open.get():
                self._opt_open.set(False)
                self._opt_frame.pack_forget()
                self._opt_arrow.configure(
                    text="▶  Optional: Add supporting evidence")
            else:
                self._opt_open.set(True)
                self._opt_frame.pack(fill=tk.X, pady=(12, 0))
                self._opt_arrow.configure(
                    text="▼  Optional: Add supporting evidence")

        toggle_row.bind("<Button-1>", _toggle)
        self._opt_arrow.bind("<Button-1>", _toggle)

        # Optional fields (built into _opt_frame, collapsed by default)
        self._steps = self._inline_field(
            self._opt_frame,
            label="Steps to reproduce  (optional)",
            placeholder="1. Power on the board\n2. Monitor UART output\n3. Observe…",
            height=3,
            prefill_key="steps",
        )
        widgets.vspace(self._opt_frame, 12).pack()

        self._compiler = self._evidence_field(
            self._opt_frame,
            label="Compiler output  (optional)",
            placeholder="Paste compiler errors or warnings here…",
            prefill_key="compiler_output",
        )
        widgets.vspace(self._opt_frame, 12).pack()

        self._serial = self._evidence_field(
            self._opt_frame,
            label="Serial / UART log  (optional)",
            placeholder="Paste serial output here…",
            prefill_key="serial_log",
        )
        widgets.vspace(self._opt_frame, 12).pack()

        self._hw_notes = self._inline_field(
            self._opt_frame,
            label="Hardware notes  (optional)",
            placeholder="Pin assignments, schematic notes, peripherals used…",
            height=3,
            prefill_key="hardware_notes",
        )

    # ── Field builders ────────────────────────────────────────────────────────

    def _field(
        self,
        parent: tk.Frame,
        label: str,
        placeholder: str = "",
        height: int = 3,
        prefill_key: str = "",
        required: bool = False,
    ) -> tk.Text:
        frame = tk.Frame(parent, bg=theme.BG_DARK)
        frame.pack(fill=tk.X, padx=60)

        lbl_row = tk.Frame(frame, bg=theme.BG_DARK)
        lbl_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(
            lbl_row,
            text=label,
            font=theme.FONT_BOLD,
            fg=theme.FG_TEXT,
            bg=theme.BG_DARK,
            anchor="w",
        ).pack(side=tk.LEFT)
        if required:
            tk.Label(lbl_row, text=" *", font=theme.FONT_BOLD,
                     fg=theme.FG_RED, bg=theme.BG_DARK).pack(side=tk.LEFT)

        # Border around input
        border = tk.Frame(frame, bg=theme.BORDER)
        border.pack(fill=tk.X)
        txt = widgets.styled_text_area(
            border,
            height=height,
            placeholder=placeholder,
        )
        txt.pack(fill=tk.X, padx=1, pady=1)

        if prefill_key and prefill_key in self._prefill:
            if hasattr(txt, "_placeholder") and txt._placeholder:
                txt.delete("1.0", tk.END)
                txt.configure(fg=theme.FG_TEXT)
            txt.insert("1.0", self._prefill[prefill_key])
            txt.configure(fg=theme.FG_TEXT)

        return txt

    def _inline_field(self, parent, label, placeholder="", height=3, prefill_key="") -> tk.Text:
        """Same as _field but uses parent's padx context (no extra indent)."""
        lbl_row = tk.Frame(parent, bg=theme.BG_DARK)
        lbl_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(
            lbl_row,
            text=label,
            font=theme.FONT_BOLD,
            fg=theme.FG_TEXT,
            bg=theme.BG_DARK,
            anchor="w",
        ).pack(side=tk.LEFT)

        border = tk.Frame(parent, bg=theme.BORDER)
        border.pack(fill=tk.X)
        txt = widgets.styled_text_area(border, height=height, placeholder=placeholder)
        txt.pack(fill=tk.X, padx=1, pady=1)

        if prefill_key and prefill_key in self._prefill:
            if hasattr(txt, "_placeholder") and txt._placeholder:
                txt.delete("1.0", tk.END)
                txt.configure(fg=theme.FG_TEXT)
            txt.insert("1.0", self._prefill[prefill_key])
            txt.configure(fg=theme.FG_TEXT)

        return txt

    def _evidence_field(self, parent, label: str, placeholder: str, prefill_key: str) -> tk.Text:
        lbl_row = tk.Frame(parent, bg=theme.BG_DARK)
        lbl_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(
            lbl_row,
            text=label,
            font=theme.FONT_BOLD,
            fg=theme.FG_TEXT,
            bg=theme.BG_DARK,
            anchor="w",
        ).pack(side=tk.LEFT)

        load_btn = tk.Button(
            lbl_row,
            text="Load file…",
            font=theme.FONT_UI_S,
            fg=theme.FG_ACCENT,
            bg=theme.BG_DARK,
            relief=tk.FLAT, bd=0, padx=0, pady=0,
            cursor="hand2",
        )
        load_btn.pack(side=tk.RIGHT)

        border = tk.Frame(parent, bg=theme.BORDER)
        border.pack(fill=tk.X)
        txt = tk.Text(
            border,
            height=4,
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
        txt.pack(fill=tk.X, padx=1, pady=1)
        txt._placeholder = ""

        if prefill_key in self._prefill and self._prefill[prefill_key]:
            txt.insert("1.0", self._prefill[prefill_key])

        load_btn.configure(command=lambda t=txt: self._load_file(t))
        return txt

    # ── File load ─────────────────────────────────────────────────────────────

    def _load_file(self, txt: tk.Text) -> None:
        path = filedialog.askopenfilename(
            title="Load file",
            filetypes=[("Text files", "*.txt *.log *.out"), ("All files", "*.*")],
        )
        if path:
            try:
                with open(path, encoding="utf-8", errors="replace") as f:
                    content = f.read()
                txt.delete("1.0", tk.END)
                txt.insert("1.0", content)
            except OSError:
                pass

    # ── Submit ────────────────────────────────────────────────────────────────

    def _submit(self) -> None:
        desc = widgets.get_text_value(self._desc)
        if not desc:
            self._error_lbl.configure(text="Please describe the problem before continuing.")
            self._desc.configure(bg="#2a1515")
            return

        self._error_lbl.configure(text="")

        # Collect optional fields safely
        def _val(w):
            return widgets.get_text_value(w) if w is not None else ""

        steps_txt = getattr(self, "_steps", None)
        compiler_txt = getattr(self, "_compiler", None)
        serial_txt = getattr(self, "_serial", None)
        hw_txt = getattr(self, "_hw_notes", None)

        self._on_submit(
            description=desc,
            expected=widgets.get_text_value(self._exp),
            actual=widgets.get_text_value(self._act),
            steps=_val(steps_txt),
            frequency=self._freq_var.get(),
            compiler_output=_val(compiler_txt),
            serial_log=_val(serial_txt),
            hardware_notes=_val(hw_txt),
        )

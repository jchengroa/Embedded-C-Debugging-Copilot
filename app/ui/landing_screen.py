"""
app/ui/landing_screen.py

Landing screen shown when the application first opens (or when no investigation
is active).  Answers the first-time user question immediately:
  "What is this?"  "What do I do first?"

Layout:
  ┌────────────────────────────────────────────────────────┐
  │                                                        │
  │   EMBEDDED DEBUGGING COPILOT                           │
  │   Find out why your embedded system isn't behaving     │
  │   the way you expect.                                  │
  │                                                        │
  │   ┌──────────────────────────────────────────────┐     │
  │   │  ▶  Start a New Investigation                │     │
  │   │     Diagnose a problem in an embedded project│     │
  │   └──────────────────────────────────────────────┘     │
  │                                                        │
  │   ── Try a Demo ──────────────────────────────────     │
  │   UART Failure   Sensor Error   Interrupt Sync   ...   │
  │                                                        │
  │   ── Import Project ───────────────────────────────    │
  │   [ Browse Folder ]   [ Select Files ]                 │
  │                                                        │
  └────────────────────────────────────────────────────────┘
"""
from __future__ import annotations

import os
import tkinter as tk
from typing import Callable, Optional

from app.ui import theme, widgets


class LandingScreen(tk.Frame):
    """
    Full-area landing screen.

    Callbacks:
      on_start_new()           — user clicked "Start a New Investigation"
      on_demo(rel_path, key)   — user selected a demo project
      on_browse()              — user clicked "Browse Folder"
    """

    DEMOS = [
        ("UART Communication\nFailure",  "demo/uart_failure/src",  "uart_failure",
         "Garbled / interleaved messages\non UART serial output."),
        ("Sensor Reading\nError",         "demo/sensor_error/src",   "sensor_error",
         "Sensor reports impossible\nvalues at room temperature."),
        ("Interrupt Sync\nBug",           "demo/interrupt_sync/src", "interrupt_sync",
         "Motor overshoots target;\nstate machine gets stuck."),
        ("Display / Keypad\nInput Bug",   "firmware",                "firmware",
         "Seven-segment display shows\nduplicate digit entries."),
    ]

    def __init__(
        self,
        parent,
        on_start_new: Callable,
        on_demo: Callable,
        on_browse: Callable,
        **kw,
    ):
        super().__init__(parent, bg=theme.BG_DARK, **kw)
        self._on_start_new = on_start_new
        self._on_demo = on_demo
        self._on_browse = on_browse
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        # Outer centering — vertical
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        center = tk.Frame(self, bg=theme.BG_DARK)
        center.grid(row=1, column=0, sticky="nsew")
        center.columnconfigure(0, weight=1)

        # Hero area
        self._build_hero(center)

        # Separator + primary CTA
        widgets.vspace(center, 36).pack()
        self._build_cta(center)

        # Demos
        widgets.vspace(center, 40).pack()
        self._build_demo_row(center)

        # Browse row
        widgets.vspace(center, 32).pack()
        self._build_browse_row(center)

        widgets.vspace(center, 40).pack()

    def _build_hero(self, parent) -> None:
        hero = tk.Frame(parent, bg=theme.BG_DARK)
        hero.pack()

        # App wordmark
        tk.Label(
            hero,
            text="Embedded Debugging Copilot",
            font=theme.FONT_HERO,
            fg=theme.FG_TEXT,
            bg=theme.BG_DARK,
        ).pack()

        tk.Label(
            hero,
            text="Find out why your embedded system isn't behaving the way you expect.",
            font=theme.FONT_UI_L,
            fg=theme.FG_MUTED,
            bg=theme.BG_DARK,
        ).pack(pady=(6, 0))

    def _build_cta(self, parent) -> None:
        """Primary action card — large, obvious."""
        outer = tk.Frame(parent, bg=theme.BORDER)
        outer.pack()

        inner = tk.Frame(outer, bg=theme.BG_CARD, cursor="hand2")
        inner.pack(padx=1, pady=1)

        content = tk.Frame(inner, bg=theme.BG_CARD)
        content.pack(padx=40, pady=22)

        top_row = tk.Frame(content, bg=theme.BG_CARD)
        top_row.pack()

        tk.Label(
            top_row,
            text="▶",
            font=("Segoe UI", 16),
            fg=theme.FG_ACCENT,
            bg=theme.BG_CARD,
        ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(
            top_row,
            text="Start a New Investigation",
            font=theme.FONT_BOLD_XL,
            fg=theme.FG_TEXT,
            bg=theme.BG_CARD,
        ).pack(side=tk.LEFT)

        tk.Label(
            content,
            text="Select an embedded project and describe your problem.",
            font=theme.FONT_UI_L,
            fg=theme.FG_MUTED,
            bg=theme.BG_CARD,
        ).pack(pady=(6, 0))

        # Bind the whole card as a button
        for widget in [inner, content, top_row]:
            widget.bind("<Button-1>", lambda e: self._on_start_new())
            widget.bind("<Enter>", lambda e: inner.configure(bg=theme.BG_HOVER))
            widget.bind("<Leave>", lambda e: inner.configure(bg=theme.BG_CARD))

    def _build_demo_row(self, parent) -> None:
        # Section header
        hdr_row = tk.Frame(parent, bg=theme.BG_DARK)
        hdr_row.pack(fill=tk.X, padx=60)

        tk.Label(
            hdr_row,
            text="TRY A DEMO",
            font=theme.FONT_LABEL_U,
            fg=theme.FG_MUTED,
            bg=theme.BG_DARK,
            anchor="w",
        ).pack(side=tk.LEFT)

        sep = tk.Frame(hdr_row, height=1, bg=theme.BORDER)
        sep.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(12, 0), pady=5)

        # Demo cards row
        demo_row = tk.Frame(parent, bg=theme.BG_DARK)
        demo_row.pack(pady=(10, 0))

        for label, rel_path, key, desc in self.DEMOS:
            self._demo_card(demo_row, label, rel_path, key, desc)

    def _demo_card(self, parent, label: str, rel_path: str, key: str, desc: str) -> None:
        outer = tk.Frame(parent, bg=theme.BORDER)
        outer.pack(side=tk.LEFT, padx=6)

        inner = tk.Frame(outer, bg=theme.BG_CARD, cursor="hand2", width=160, height=110)
        inner.pack(padx=1, pady=1)
        inner.pack_propagate(False)

        content = tk.Frame(inner, bg=theme.BG_CARD)
        content.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            content,
            text=label,
            font=theme.FONT_BOLD,
            fg=theme.FG_TEXT,
            bg=theme.BG_CARD,
            justify="center",
        ).pack()

        tk.Label(
            content,
            text=desc,
            font=theme.FONT_UI_S,
            fg=theme.FG_MUTED,
            bg=theme.BG_CARD,
            justify="center",
            wraplength=140,
        ).pack(pady=(4, 0))

        def _click(rp=rel_path, k=key, evt=None):
            self._on_demo(rp, k)

        def _enter(evt, w=inner, c=content):
            w.configure(bg=theme.BG_HOVER)
            c.configure(bg=theme.BG_HOVER)
            for child in c.winfo_children():
                child.configure(bg=theme.BG_HOVER)

        def _leave(evt, w=inner, c=content):
            w.configure(bg=theme.BG_CARD)
            c.configure(bg=theme.BG_CARD)
            for child in c.winfo_children():
                child.configure(bg=theme.BG_CARD)

        for w in [inner, content] + list(content.winfo_children()):
            w.bind("<Button-1>", _click)
            w.bind("<Enter>", _enter)
            w.bind("<Leave>", _leave)

    def _build_browse_row(self, parent) -> None:
        hdr_row = tk.Frame(parent, bg=theme.BG_DARK)
        hdr_row.pack(fill=tk.X, padx=60)

        tk.Label(
            hdr_row,
            text="YOUR OWN PROJECT",
            font=theme.FONT_LABEL_U,
            fg=theme.FG_MUTED,
            bg=theme.BG_DARK,
            anchor="w",
        ).pack(side=tk.LEFT)

        sep = tk.Frame(hdr_row, height=1, bg=theme.BORDER)
        sep.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(12, 0), pady=5)

        btn_row = tk.Frame(parent, bg=theme.BG_DARK)
        btn_row.pack(pady=(10, 0))

        widgets.primary_button(
            btn_row,
            "Browse Project Folder…",
            command=self._on_browse,
        ).pack(side=tk.LEFT, padx=6)

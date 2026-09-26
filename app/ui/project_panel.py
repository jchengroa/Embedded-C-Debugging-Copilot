"""
app/ui/project_panel.py

Step 1 — PROJECT SETUP

Shown as the main content area when the user is setting up their project.
Provides:
  - Folder browse (with large drop-zone style card)
  - Demo project quick-launch
  - Project analysis progress feedback (tick list)
  - File tree summary once loaded
"""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Callable, Optional

from app.ui import theme, widgets
from app.models.project import Project


class ProjectPanel(tk.Frame):
    """
    Full-content-area project setup step.

    Callbacks:
      on_project_loaded(path: str)
    """

    def __init__(self, parent, on_project_loaded: Callable[[str], None], **kw):
        super().__init__(parent, bg=theme.BG_DARK, **kw)
        self._on_project_loaded = on_project_loaded
        self._project: Optional[Project] = None
        self._analysis_items: list[dict] = []
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        # Scroll-container so content doesn't get clipped on small windows
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

        self._inner = inner
        self._build_content(inner)

    def _build_content(self, parent: tk.Frame) -> None:
        pad = dict(padx=60, pady=0)

        # Step header
        hdr = tk.Frame(parent, bg=theme.BG_DARK)
        hdr.pack(fill=tk.X, padx=60, pady=(36, 0))

        tk.Label(
            hdr,
            text="STEP 1",
            font=theme.FONT_LABEL_U,
            fg=theme.FG_ACCENT,
            bg=theme.BG_DARK,
            anchor="w",
        ).pack(anchor="w")

        tk.Label(
            hdr,
            text="Select Your Project",
            font=theme.FONT_BOLD_XL,
            fg=theme.FG_TEXT,
            bg=theme.BG_DARK,
            anchor="w",
        ).pack(anchor="w", pady=(4, 0))

        tk.Label(
            hdr,
            text="Choose the embedded project you want to investigate.",
            font=theme.FONT_UI_L,
            fg=theme.FG_MUTED,
            bg=theme.BG_DARK,
            anchor="w",
        ).pack(anchor="w", pady=(4, 0))

        # ── Primary: Browse card ──────────────────────────────────────────────
        widgets.vspace(parent, 24).pack()
        self._build_browse_card(parent)

        # ── Divider ──────────────────────────────────────────────────────────
        widgets.vspace(parent, 24).pack()
        div_row = tk.Frame(parent, bg=theme.BG_DARK)
        div_row.pack(fill=tk.X, **pad)

        tk.Frame(div_row, height=1, bg=theme.BORDER).pack(
            side=tk.LEFT, fill=tk.X, expand=True, pady=7)
        tk.Label(
            div_row,
            text="  or try a demo  ",
            font=theme.FONT_UI_S,
            fg=theme.FG_MUTED,
            bg=theme.BG_DARK,
        ).pack(side=tk.LEFT)
        tk.Frame(div_row, height=1, bg=theme.BORDER).pack(
            side=tk.LEFT, fill=tk.X, expand=True, pady=7)

        # ── Demo projects ─────────────────────────────────────────────────────
        widgets.vspace(parent, 16).pack()
        self._build_demo_section(parent)

        # ── Analysis progress (hidden until project loaded) ───────────────────
        widgets.vspace(parent, 32).pack()
        self._analysis_frame = tk.Frame(parent, bg=theme.BG_DARK)
        self._analysis_frame.pack(fill=tk.X, **pad)
        # Initially empty — populated by show_analysis_progress()

        # ── File summary (hidden until project loaded) ────────────────────────
        self._summary_frame = tk.Frame(parent, bg=theme.BG_DARK)
        self._summary_frame.pack(fill=tk.X, **pad)

        widgets.vspace(parent, 40).pack()

    def _build_browse_card(self, parent: tk.Frame) -> None:
        outer = tk.Frame(parent, bg=theme.BORDER)
        outer.pack(padx=60)

        inner = tk.Frame(outer, bg=theme.BG_CARD, cursor="hand2")
        inner.pack(padx=1, pady=1)

        content = tk.Frame(inner, bg=theme.BG_CARD)
        content.pack(padx=48, pady=28)

        tk.Label(
            content,
            text="📁",
            font=("Segoe UI", 28),
            fg=theme.FG_ACCENT,
            bg=theme.BG_CARD,
        ).pack()

        tk.Label(
            content,
            text="Browse Project Folder",
            font=theme.FONT_BOLD_L,
            fg=theme.FG_TEXT,
            bg=theme.BG_CARD,
        ).pack(pady=(8, 0))

        tk.Label(
            content,
            text="Choose the folder containing your source code and project files.",
            font=theme.FONT_UI,
            fg=theme.FG_MUTED,
            bg=theme.BG_CARD,
        ).pack(pady=(4, 0))

        def _click(_evt=None):
            folder = filedialog.askdirectory(title="Select Embedded Project Folder")
            if folder:
                self._on_project_loaded(folder)

        def _enter(_evt):
            inner.configure(bg=theme.BG_HOVER)
            content.configure(bg=theme.BG_HOVER)
            for child in content.winfo_children():
                try:
                    child.configure(bg=theme.BG_HOVER)
                except Exception:
                    pass

        def _leave(_evt):
            inner.configure(bg=theme.BG_CARD)
            content.configure(bg=theme.BG_CARD)
            for child in content.winfo_children():
                try:
                    child.configure(bg=theme.BG_CARD)
                except Exception:
                    pass

        for w in [inner, content]:
            w.bind("<Button-1>", _click)
            w.bind("<Enter>", _enter)
            w.bind("<Leave>", _leave)

        # Also store path label for updates
        self._path_var = tk.StringVar(value="")
        self._path_lbl = tk.Label(
            content,
            textvariable=self._path_var,
            font=theme.FONT_UI_S,
            fg=theme.FG_ACCENT,
            bg=theme.BG_CARD,
        )
        self._path_lbl.pack(pady=(6, 0))
        for w in [self._path_lbl]:
            w.bind("<Button-1>", _click)
            w.bind("<Enter>", _enter)
            w.bind("<Leave>", _leave)

    def _build_demo_section(self, parent: tk.Frame) -> None:
        demos = [
            ("UART Communication Failure",  "demo/uart_failure/src",  "uart_failure"),
            ("Sensor Reading Error",         "demo/sensor_error/src",  "sensor_error"),
            ("Interrupt Sync Bug",           "demo/interrupt_sync/src","interrupt_sync"),
            ("Display / Keypad Input Bug",   "firmware",               "firmware"),
        ]

        demo_row = tk.Frame(parent, bg=theme.BG_DARK)
        demo_row.pack(padx=60)

        for label, rel_path, _key in demos:
            btn = tk.Button(
                demo_row,
                text=label,
                font=theme.FONT_UI_S,
                fg=theme.FG_TEXT,
                bg=theme.BG_CARD,
                activebackground=theme.BG_HOVER,
                activeforeground=theme.FG_ACCENT,
                relief=tk.FLAT,
                bd=0,
                padx=14,
                pady=8,
                cursor="hand2",
                command=lambda rp=rel_path: self._load_demo(rp),
            )
            btn.pack(side=tk.LEFT, padx=4)

    # ── Public API ────────────────────────────────────────────────────────────

    def show_analysis_progress(self, items: list[tuple[str, bool]]) -> None:
        """
        Render analysis progress ticks.
        items: list of (label, done) tuples.
        """
        for child in self._analysis_frame.winfo_children():
            child.destroy()

        tk.Label(
            self._analysis_frame,
            text="ANALYZING PROJECT",
            font=theme.FONT_LABEL_U,
            fg=theme.FG_MUTED,
            bg=theme.BG_DARK,
            anchor="w",
        ).pack(anchor="w", pady=(0, 8))

        for label, done in items:
            row = tk.Frame(self._analysis_frame, bg=theme.BG_DARK)
            row.pack(fill=tk.X, pady=2)

            marker = "✓" if done else "○"
            fg = theme.FG_GREEN if done else theme.FG_MUTED

            tk.Label(
                row,
                text=marker,
                font=theme.FONT_UI_S,
                fg=fg,
                bg=theme.BG_DARK,
                width=2,
                anchor="w",
            ).pack(side=tk.LEFT)

            tk.Label(
                row,
                text=label,
                font=theme.FONT_UI_S,
                fg=fg if done else theme.FG_TEXT,
                bg=theme.BG_DARK,
                anchor="w",
            ).pack(side=tk.LEFT, padx=(4, 0))

    def show_project(self, project: Project) -> None:
        """Update the panel to reflect a newly loaded project."""
        self._project = project
        self._path_var.set(project.root)

        # Show analysis progress
        items = [
            (f"Found {len(project.source_files)} source file(s)", len(project.source_files) > 0),
            ("Detected project structure", True),
            (f"Found {len(project.test_files)} test file(s)", len(project.test_files) > 0),
            (f"Platform: {project.detected_platform or 'generic embedded'}", True),
        ]
        self.show_analysis_progress(items)

        # File summary
        self._build_file_summary(project)

    def _build_file_summary(self, project: Project) -> None:
        for child in self._summary_frame.winfo_children():
            child.destroy()

        widgets.vspace(self._summary_frame, 16).pack()
        tk.Label(
            self._summary_frame,
            text="PROJECT FILES",
            font=theme.FONT_LABEL_U,
            fg=theme.FG_MUTED,
            bg=theme.BG_DARK,
            anchor="w",
        ).pack(anchor="w", pady=(0, 6))

        # Compact tree
        tree_frame = tk.Frame(self._summary_frame, bg=theme.BG_DARK)
        tree_frame.pack(fill=tk.X)

        tree = ttk.Treeview(tree_frame, show="tree", selectmode="browse", height=8)
        tree_sb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=tree_sb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_sb.pack(side=tk.RIGHT, fill=tk.Y)

        groups = {
            "Source (.c/.cpp)": [f for f in project.files
                                  if f.extension in {".c",".cpp",".cc",".cxx",".s",".asm"}],
            "Headers (.h/.hpp)": [f for f in project.files
                                   if f.extension in {".h",".hpp"}],
            "Build files":       [f for f in project.files if f.is_build],
            "Tests":             [f for f in project.files if f.is_test],
        }
        for group_name, files in groups.items():
            if not files:
                continue
            parent_node = tree.insert("", tk.END,
                                      text=f"  {group_name}  ({len(files)})",
                                      open=True)
            for f in files[:30]:
                tree.insert(parent_node, tk.END, text=f"    {f.rel_path}")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _load_demo(self, rel_path: str) -> None:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        full = os.path.join(base, rel_path)
        if os.path.isdir(full):
            self._on_project_loaded(full)
        elif os.path.isdir(rel_path):
            self._on_project_loaded(os.path.abspath(rel_path))

    def _browse_folder(self) -> None:
        folder = filedialog.askdirectory(title="Select Embedded Project Folder")
        if folder:
            self._on_project_loaded(folder)

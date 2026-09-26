"""
app/ui/widgets.py — reusable widget helpers.

Provides building blocks for the redesigned developer-tool UI:
  - Consistent buttons (primary, secondary, ghost, danger)
  - Scrolled text areas
  - Section headers with optional badge
  - Bordered cards
  - Horizontal separators
  - Pill / badge labels
  - Icon-text rows
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.ui import theme


# ── Basic primitives ──────────────────────────────────────────────────────────

def separator(parent, color: str = None) -> tk.Frame:
    return tk.Frame(parent, height=1, bg=color or theme.BORDER)


def vspace(parent, height: int = 8) -> tk.Frame:
    return tk.Frame(parent, height=height, bg=theme.BG_DARK)


def card(parent, bg: str = None, padx: int = 0, pady: int = 0, **kw) -> tk.Frame:
    f = tk.Frame(
        parent,
        bg=bg or theme.BG_CARD,
        relief=tk.FLAT,
        bd=0,
        **kw,
    )
    return f


def bordered_card(parent, bg: str = None, **kw) -> tk.Frame:
    """A card with a 1-px border drawn via an outer frame + inner frame."""
    outer = tk.Frame(parent, bg=theme.BORDER, **kw)
    inner = tk.Frame(outer, bg=bg or theme.BG_CARD)
    inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
    inner.outer = outer
    return inner


# ── Labels ────────────────────────────────────────────────────────────────────

def make_label(parent, text="", font=None, fg=None, bg=None, **kw) -> tk.Label:
    return tk.Label(
        parent,
        text=text,
        font=font or theme.FONT_UI,
        fg=fg or theme.FG_TEXT,
        bg=bg or theme.BG_DARK,
        **kw,
    )


def section_header(parent, text: str, bg: str = None) -> tk.Label:
    """Small all-caps section label."""
    return tk.Label(
        parent,
        text=text.upper(),
        font=theme.FONT_LABEL_U,
        fg=theme.FG_MUTED,
        bg=bg or theme.BG_DARK,
        anchor="w",
    )


def make_section_header(parent, text: str) -> tk.Label:
    """Legacy alias — kept for back-compat."""
    return tk.Label(
        parent,
        text=f"  {text}  ",
        font=theme.FONT_BOLD,
        fg=theme.FG_ACCENT,
        bg=theme.BG_PANEL,
        anchor="w",
    )


def heading(parent, text: str, bg: str = None, fg: str = None,
            font=None) -> tk.Label:
    return tk.Label(
        parent,
        text=text,
        font=font or theme.FONT_BOLD_L,
        fg=fg or theme.FG_TEXT,
        bg=bg or theme.BG_DARK,
        anchor="w",
    )


def badge(parent, text: str, color: str) -> tk.Label:
    """Colored small pill-style label."""
    return tk.Label(
        parent,
        text=f"  {text}  ",
        font=theme.FONT_BOLD_S,
        fg=theme.BG_DARK,
        bg=color,
        relief=tk.FLAT,
        bd=0,
    )


# ── Buttons ───────────────────────────────────────────────────────────────────

def make_button(parent, text, command, fg=None, bg=None, **kw) -> tk.Button:
    """Primary button."""
    return tk.Button(
        parent,
        text=text,
        command=command,
        font=theme.FONT_BOLD,
        fg=fg or theme.BG_DARK,
        bg=bg or theme.FG_ACCENT,
        activebackground=theme.FG_PURPLE,
        activeforeground=theme.FG_TEXT,
        relief=tk.FLAT,
        bd=0,
        padx=12,
        pady=6,
        cursor="hand2",
        **kw,
    )


def primary_button(parent, text: str, command, wide: bool = False) -> tk.Button:
    """Blue primary CTA button."""
    return tk.Button(
        parent,
        text=text,
        command=command,
        font=theme.FONT_BOLD,
        fg="#ffffff",
        bg=theme.FG_ACCENT,
        activebackground="#4a8de8",
        activeforeground="#ffffff",
        relief=tk.FLAT,
        bd=0,
        padx=20 if wide else 14,
        pady=8,
        cursor="hand2",
    )


def secondary_button(parent, text: str, command) -> tk.Button:
    """Ghost/outline-style secondary button."""
    return tk.Button(
        parent,
        text=text,
        command=command,
        font=theme.FONT_UI,
        fg=theme.FG_TEXT,
        bg=theme.BG_CARD,
        activebackground=theme.BG_HOVER,
        activeforeground=theme.FG_TEXT,
        relief=tk.FLAT,
        bd=0,
        padx=14,
        pady=7,
        cursor="hand2",
    )


def danger_button(parent, text: str, command) -> tk.Button:
    return tk.Button(
        parent,
        text=text,
        command=command,
        font=theme.FONT_BOLD,
        fg="#ffffff",
        bg=theme.FG_RED,
        activebackground="#c04050",
        activeforeground="#ffffff",
        relief=tk.FLAT,
        bd=0,
        padx=14,
        pady=7,
        cursor="hand2",
    )


def success_button(parent, text: str, command) -> tk.Button:
    return tk.Button(
        parent,
        text=text,
        command=command,
        font=theme.FONT_BOLD,
        fg="#ffffff",
        bg=theme.FG_GREEN,
        activebackground="#3a9668",
        activeforeground="#ffffff",
        relief=tk.FLAT,
        bd=0,
        padx=14,
        pady=7,
        cursor="hand2",
    )


def icon_button(parent, text: str, command, fg: str = None) -> tk.Button:
    """Small text/icon link-style button."""
    return tk.Button(
        parent,
        text=text,
        command=command,
        font=theme.FONT_UI_S,
        fg=fg or theme.FG_ACCENT,
        bg=theme.BG_DARK,
        activebackground=theme.BG_HOVER,
        activeforeground=theme.FG_TEXT,
        relief=tk.FLAT,
        bd=0,
        padx=4,
        pady=2,
        cursor="hand2",
    )


# ── Inputs ────────────────────────────────────────────────────────────────────

def make_entry(parent, textvariable=None, width=40, **kw) -> tk.Entry:
    return tk.Entry(
        parent,
        textvariable=textvariable,
        width=width,
        font=theme.FONT_UI,
        bg=theme.BG_INPUT,
        fg=theme.FG_TEXT,
        insertbackground=theme.FG_TEXT,
        relief=tk.FLAT,
        bd=4,
        **kw,
    )


def make_scrolled_text(parent, height=10, font=None, bg=None, **kw) -> tk.Frame:
    frame = tk.Frame(parent, bg=bg or theme.BG_DARK)
    sb = ttk.Scrollbar(frame)
    sb.pack(side=tk.RIGHT, fill=tk.Y)
    txt = tk.Text(
        frame,
        height=height,
        font=font or theme.FONT_MONO,
        bg=bg or theme.BG_INPUT,
        fg=theme.FG_TEXT,
        insertbackground=theme.FG_TEXT,
        selectbackground=theme.BG_SEL,
        relief=tk.FLAT,
        bd=0,
        yscrollcommand=sb.set,
        **kw,
    )
    txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    sb.config(command=txt.yview)
    frame.txt = txt
    return frame


def styled_text_area(parent, height: int = 4, font=None,
                     bg: str = None, placeholder: str = "",
                     **kw) -> tk.Text:
    """A standalone styled text area (without scrollbar wrapper)."""
    txt = tk.Text(
        parent,
        height=height,
        font=font or theme.FONT_UI,
        bg=bg or theme.BG_INPUT,
        fg=theme.FG_TEXT,
        insertbackground=theme.FG_TEXT,
        selectbackground=theme.BG_SEL,
        relief=tk.FLAT,
        bd=0,
        wrap=tk.WORD,
        padx=10,
        pady=8,
        **kw,
    )
    # Placeholder behavior
    if placeholder:
        txt.insert("1.0", placeholder)
        txt.configure(fg=theme.FG_MUTED)

        def _on_focus_in(event):
            if txt.get("1.0", "end-1c") == placeholder:
                txt.delete("1.0", tk.END)
                txt.configure(fg=theme.FG_TEXT)

        def _on_focus_out(event):
            if not txt.get("1.0", "end-1c").strip():
                txt.insert("1.0", placeholder)
                txt.configure(fg=theme.FG_MUTED)

        txt.bind("<FocusIn>",  _on_focus_in)
        txt.bind("<FocusOut>", _on_focus_out)
        txt._placeholder = placeholder
    else:
        txt._placeholder = ""
    return txt


def get_text_value(txt: tk.Text) -> str:
    """Get text widget value, stripping placeholder content."""
    val = txt.get("1.0", "end-1c").strip()
    placeholder = getattr(txt, "_placeholder", "")
    if val == placeholder:
        return ""
    return val


# ── Progress / status indicators ──────────────────────────────────────────────

def activity_dot(parent, bg: str = None) -> tk.Label:
    """Animated activity indicator (● character with color)."""
    return tk.Label(
        parent,
        text="●",
        font=theme.FONT_UI_S,
        fg=theme.FG_ACCENT,
        bg=bg or theme.BG_DARK,
    )


# ── TTK style setup ───────────────────────────────────────────────────────────

def apply_dark_ttk_style() -> None:
    """Configure ttk widgets to match the dark theme."""
    style = ttk.Style()
    style.theme_use("clam")

    style.configure(".",
                    background=theme.BG_DARK,
                    foreground=theme.FG_TEXT,
                    fieldbackground=theme.BG_INPUT,
                    bordercolor=theme.BORDER,
                    darkcolor=theme.BG_DARK,
                    lightcolor=theme.BG_PANEL,
                    troughcolor=theme.BG_PANEL,
                    insertcolor=theme.FG_TEXT,
                    font=theme.FONT_UI)

    style.configure("TFrame",  background=theme.BG_DARK)
    style.configure("TLabel",  background=theme.BG_DARK, foreground=theme.FG_TEXT)

    style.configure("TNotebook",
                    background=theme.BG_PANEL,
                    bordercolor=theme.BORDER,
                    tabmargins=[0, 0, 0, 0])
    style.configure("TNotebook.Tab",
                    background=theme.BG_PANEL,
                    foreground=theme.FG_MUTED,
                    padding=[14, 6],
                    borderwidth=0)
    style.map("TNotebook.Tab",
              background=[("selected", theme.BG_DARK)],
              foreground=[("selected", theme.FG_ACCENT)])

    style.configure("Treeview",
                    background=theme.BG_CARD,
                    foreground=theme.FG_TEXT,
                    fieldbackground=theme.BG_CARD,
                    rowheight=26,
                    borderwidth=0)
    style.configure("Treeview.Heading",
                    background=theme.BG_PANEL,
                    foreground=theme.FG_MUTED,
                    font=theme.FONT_BOLD_S,
                    relief=tk.FLAT)
    style.map("Treeview",
              background=[("selected", theme.BG_SEL)],
              foreground=[("selected", theme.FG_TEXT)])

    style.configure("TScrollbar",
                    background=theme.BG_PANEL,
                    troughcolor=theme.BG_DARK,
                    arrowcolor=theme.FG_MUTED,
                    borderwidth=0,
                    arrowsize=12)

    style.configure("TCombobox",
                    fieldbackground=theme.BG_INPUT,
                    background=theme.BG_INPUT,
                    foreground=theme.FG_TEXT,
                    arrowcolor=theme.FG_ACCENT,
                    borderwidth=0)

    style.configure("TProgressbar",
                    background=theme.FG_ACCENT,
                    troughcolor=theme.BG_CARD,
                    borderwidth=0,
                    thickness=4)

    style.configure("Thin.TProgressbar",
                    background=theme.FG_ACCENT,
                    troughcolor=theme.BG_CARD,
                    borderwidth=0,
                    thickness=3)

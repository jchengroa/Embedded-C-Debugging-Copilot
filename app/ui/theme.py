"""
app/ui/theme.py — visual constants for the Embedded Debugging Copilot GUI.

Design language:
  - Dark developer-tool aesthetic (VS Code / Linear inspired)
  - Restrained palette — color communicates meaning, not decoration
  - Clean Segoe UI typography with generous line spacing
  - Subtle borders, no gradients
"""

# ── Core background layers ────────────────────────────────────────────────────
BG_APP      = "#0d0d0f"    # outermost app chrome
BG_DARK     = "#111113"    # main content area
BG_PANEL    = "#17171a"    # sidebar / panel backgrounds
BG_CARD     = "#1e1e22"    # card / surface
BG_INPUT    = "#1a1a1e"    # text inputs
BG_HOVER    = "#252529"    # hover state
BG_SEL      = "#2a2a30"    # selected row

# ── Foreground / text ─────────────────────────────────────────────────────────
FG_TEXT     = "#e2e2e6"    # primary text
FG_MUTED    = "#6b6b78"    # secondary / placeholder text
FG_SUBTLE   = "#3e3e48"    # very quiet text / disabled

# ── Semantic accent colors ────────────────────────────────────────────────────
FG_ACCENT   = "#5b9cf6"    # blue — active / informational
FG_GREEN    = "#4caf82"    # green — success / verified
FG_YELLOW   = "#d4a843"    # amber — warning / in-progress
FG_RED      = "#e05e6d"    # red — error / failed
FG_ORANGE   = "#c47d3e"    # orange — caution
FG_CYAN     = "#4ab5c8"    # cyan — secondary info
FG_PURPLE   = "#8b72d4"    # purple — AI / system

# ── Borders ───────────────────────────────────────────────────────────────────
BORDER      = "#25252b"    # standard border
BORDER_FOCUS = "#5b9cf6"   # focused input border

# Legacy aliases kept for compatibility
SEL_BG = BG_SEL

# ── Typography ────────────────────────────────────────────────────────────────
FONT_MONO    = ("Consolas",   10)
FONT_MONO_S  = ("Consolas",    9)
FONT_MONO_L  = ("Consolas",   11)
FONT_UI      = ("Segoe UI",   10)
FONT_UI_S    = ("Segoe UI",    9)
FONT_UI_L    = ("Segoe UI",   12)
FONT_UI_XL   = ("Segoe UI",   15)
FONT_BOLD    = ("Segoe UI",   10, "bold")
FONT_BOLD_S  = ("Segoe UI",    9, "bold")
FONT_BOLD_L  = ("Segoe UI",   13, "bold")
FONT_BOLD_XL = ("Segoe UI",   18, "bold")
FONT_TITLE   = ("Segoe UI",   11, "bold")
FONT_HERO    = ("Segoe UI",   22, "bold")
FONT_LABEL   = ("Segoe UI",    8)
FONT_LABEL_U = ("Segoe UI",    8, "bold")   # small caps-style label

# ── Status → color mapping ────────────────────────────────────────────────────
STATUS_COLORS: dict[str, str] = {
    "IDLE":                  FG_MUTED,
    "ANALYZING PROJECT":     FG_CYAN,
    "INVESTIGATING":         FG_ACCENT,
    "COLLECTING EVIDENCE":   FG_CYAN,
    "GENERATING HYPOTHESES": FG_YELLOW,
    "ROOT CAUSE IDENTIFIED": FG_ORANGE,
    "AWAITING APPROVAL":     FG_YELLOW,
    "APPLYING FIX":          FG_ORANGE,
    "RUNNING TESTS":         FG_CYAN,
    "VERIFYING":             FG_CYAN,
    "COMPLETE":              FG_GREEN,
    "BLOCKED":               FG_RED,
    "ERROR":                 FG_RED,
}

VERIFICATION_COLORS: dict[str, str] = {
    "VERIFIED":           FG_GREEN,
    "PARTIALLY_VERIFIED": FG_YELLOW,
    "UNVERIFIED":         FG_MUTED,
    "FAILED":             FG_RED,
}

EVIDENCE_KIND_COLORS: dict[str, str] = {
    "OBSERVED":   FG_GREEN,
    "INFERRED":   FG_YELLOW,
    "ASSUMED":    FG_ORANGE,
    "UNVERIFIED": FG_MUTED,
}

# ── Workflow step definitions ─────────────────────────────────────────────────
WORKFLOW_STEPS = [
    ("project",    "Project"),
    ("problem",    "Problem"),
    ("evidence",   "Evidence"),
    ("investigate","Investigate"),
    ("diagnose",   "Diagnose"),
    ("fix",        "Fix"),
    ("verify",     "Verify"),
]

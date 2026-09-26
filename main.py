#!/usr/bin/env python3
"""
main.py — Embedded Debugging Copilot entry point.

Usage:
    python main.py           # launch GUI
    python main.py --cli     # launch CLI (future)
"""
import sys
import os

# Ensure the project root is on sys.path regardless of where the script is run from
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env file if present (for API key configuration)
_env_path = os.path.join(os.path.dirname(__file__), "config", ".env")
if os.path.exists(_env_path):
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

# Also try root .env
_root_env = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_root_env):
    with open(_root_env) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())


def launch_gui():
    from app.ui.main_window import MainWindow
    app = MainWindow()
    app.mainloop()


def launch_cli():
    from app.cli import run_cli
    run_cli()


if __name__ == "__main__":
    if "--cli" in sys.argv:
        launch_cli()
    else:
        launch_gui()

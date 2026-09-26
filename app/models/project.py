"""
app/models/project.py

Hardware-agnostic project model.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# File types recognised by the project scanner
# ---------------------------------------------------------------------------
SOURCE_EXTENSIONS = {".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".s", ".asm"}
BUILD_FILES = {"Makefile", "makefile", "CMakeLists.txt", "build.gradle",
               "platformio.ini", "*.ioc", "*.uvprojx", "*.ewp"}
CONFIG_EXTENSIONS = {".json", ".yaml", ".yml", ".ini", ".cfg", ".toml", ".xml"}
DOC_EXTENSIONS = {".md", ".txt", ".rst", ".pdf"}
TEST_PATTERNS = {"test_", "_test.", "unittest", "spec_"}


@dataclass
class ProjectFile:
    """A single file belonging to the project."""
    path: str                    # absolute path
    rel_path: str                # path relative to project root
    extension: str
    size_bytes: int
    content: Optional[str] = None   # loaded on demand

    @property
    def filename(self) -> str:
        return os.path.basename(self.path)

    @property
    def is_source(self) -> bool:
        return self.extension.lower() in SOURCE_EXTENSIONS

    @property
    def is_header(self) -> bool:
        return self.extension.lower() in {".h", ".hpp"}

    @property
    def is_build(self) -> bool:
        return self.filename in BUILD_FILES or self.extension in {".cmake"}

    @property
    def is_test(self) -> bool:
        name = self.filename.lower()
        return any(p in name for p in TEST_PATTERNS)

    def load_content(self) -> str:
        """Load and cache file content; returns empty string on binary/error."""
        if self.content is not None:
            return self.content
        try:
            with open(self.path, encoding="utf-8", errors="replace") as fh:
                self.content = fh.read()
        except OSError:
            self.content = ""
        return self.content


@dataclass
class Project:
    """
    Represents an embedded firmware project.

    Platform-agnostic: no assumptions about MCU, IDE, or build system.
    Hardware-specific information is discovered from project files or
    supplied explicitly by the user.
    """
    name: str
    root: str                            # absolute path to project root
    files: list[ProjectFile] = field(default_factory=list)
    compiler_output: str = ""
    serial_log: str = ""
    hardware_notes: str = ""             # user-provided pin maps / schematic notes
    extra_docs: list[str] = field(default_factory=list)   # paths to datasheets etc.

    # Detected metadata (filled by the project scanner)
    detected_platform: Optional[str] = None   # "AVR", "STM32", "ESP32", …
    detected_build_system: Optional[str] = None
    detected_test_system: Optional[str] = None

    @property
    def source_files(self) -> list[ProjectFile]:
        return [f for f in self.files if f.is_source]

    @property
    def header_files(self) -> list[ProjectFile]:
        return [f for f in self.files if f.is_header]

    @property
    def build_files(self) -> list[ProjectFile]:
        return [f for f in self.files if f.is_build]

    @property
    def test_files(self) -> list[ProjectFile]:
        return [f for f in self.files if f.is_test]

    def get_file(self, rel_path: str) -> Optional[ProjectFile]:
        for f in self.files:
            if f.rel_path == rel_path or f.filename == rel_path:
                return f
        return None

    def all_source_text(self) -> dict[str, str]:
        """Return {rel_path: content} for every source/header file."""
        result = {}
        for f in self.source_files + self.header_files:
            result[f.rel_path] = f.load_content()
        return result

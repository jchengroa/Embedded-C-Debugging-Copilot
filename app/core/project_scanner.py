"""
app/core/project_scanner.py

Scans a filesystem directory and builds a Project model.
Platform-agnostic — detects toolchain/platform from file contents.
"""
from __future__ import annotations

import os
import re
from typing import Optional

from app.models.project import Project, ProjectFile, SOURCE_EXTENSIONS, CONFIG_EXTENSIONS, DOC_EXTENSIONS


# Patterns used to guess the MCU platform from source/config files
_PLATFORM_HINTS: list[tuple[str, str]] = [
    (r"#include\s+[<\"]avr/", "AVR (avr-libc)"),
    (r"#include\s+[<\"]stm32", "STM32 (STM32Cube)"),
    (r"#include\s+[<\"]esp_", "ESP-IDF (ESP32/ESP8266)"),
    (r"#include\s+[<\"]Arduino\.h", "Arduino"),
    (r"#include\s+[<\"]pic", "PIC"),
    (r"#include\s+[<\"]msp430", "MSP430"),
    (r"#include\s+[<\"]nrf_", "Nordic nRF"),
    (r"#include\s+[<\"]sam\.h", "Microchip SAM (SAMD)"),
    (r"\bplatformio\b", "PlatformIO"),
    (r"\bpico/stdlib\.h\b", "Raspberry Pi Pico"),
]

_BUILD_SYSTEM_HINTS: list[tuple[str, str]] = [
    (r"CMakeLists\.txt",     "CMake"),
    (r"[Mm]akefile",         "Make"),
    (r"platformio\.ini",     "PlatformIO"),
    (r"build\.gradle",       "Gradle"),
    (r"\.ioc$",              "STM32CubeMX"),
    (r"\.uvprojx$",          "Keil MDK"),
    (r"\.ewp$",              "IAR EWARM"),
]

_TEST_SYSTEM_HINTS: list[tuple[str, str]] = [
    (r"unity\.h",            "Unity"),
    (r"cmocka\.h",           "CMocka"),
    (r"cpputest",            "CppUTest"),
    (r"gtest",               "Google Test"),
    (r"pytest",              "pytest"),
    (r"#include.*test",      "unknown unit-test framework"),
]

MAX_FILE_SIZE = 2 * 1024 * 1024   # 2 MB — skip larger files


def scan_project(root: str) -> Project:
    """
    Walk *root* recursively and build a Project.
    Skips binary files, build artefacts, and hidden directories.
    """
    root = os.path.abspath(root)
    name = os.path.basename(root)
    project = Project(name=name, root=root)

    all_files: list[ProjectFile] = []
    skip_dirs = {".git", "__pycache__", "node_modules", ".vs", "Debug",
                 "Release", "build", "dist", ".pio", "cmake-build-debug",
                 "cmake-build-release"}

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune skip directories in-place
        dirnames[:] = [d for d in dirnames if d not in skip_dirs and not d.startswith(".")]

        for fname in filenames:
            full = os.path.join(dirpath, fname)
            rel  = os.path.relpath(full, root)
            ext  = os.path.splitext(fname)[1].lower()

            try:
                size = os.path.getsize(full)
            except OSError:
                continue

            if size > MAX_FILE_SIZE:
                continue

            pf = ProjectFile(path=full, rel_path=rel, extension=ext, size_bytes=size)
            all_files.append(pf)

    project.files = all_files
    _detect_metadata(project)
    return project


def _detect_metadata(project: Project) -> None:
    """Heuristically detect platform, build system, and test system."""
    platform_votes: dict[str, int] = {}
    build_votes:    dict[str, int] = {}
    test_votes:     dict[str, int] = {}

    for pf in project.files:
        if pf.extension not in SOURCE_EXTENSIONS | CONFIG_EXTENSIONS | {".ini", ""}:
            continue
        if pf.size_bytes > 512 * 1024:
            continue

        text = pf.load_content().lower()
        fname = pf.filename

        for pattern, label in _PLATFORM_HINTS:
            if re.search(pattern, text, re.IGNORECASE):
                platform_votes[label] = platform_votes.get(label, 0) + 1

        for pattern, label in _BUILD_SYSTEM_HINTS:
            if re.search(pattern, fname, re.IGNORECASE) or re.search(pattern, pf.rel_path):
                build_votes[label] = build_votes.get(label, 0) + 1

        for pattern, label in _TEST_SYSTEM_HINTS:
            if re.search(pattern, text, re.IGNORECASE):
                test_votes[label] = test_votes.get(label, 0) + 1

    if platform_votes:
        project.detected_platform = max(platform_votes, key=platform_votes.get)
    if build_votes:
        project.detected_build_system = max(build_votes, key=build_votes.get)
    if test_votes:
        project.detected_test_system = max(test_votes, key=test_votes.get)

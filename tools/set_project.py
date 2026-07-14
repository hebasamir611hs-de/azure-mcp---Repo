#!/usr/bin/env python3
"""Switch the active project context.

Usage:  python tools/set_project.py <project-name>

Copies .claude/context/projects/<name>/background.md and standards.md
into .claude/context/active/ and writes a PROJECT marker file.
"""

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROJECTS_DIR = REPO_ROOT / ".claude" / "context" / "projects"
ACTIVE_DIR = REPO_ROOT / ".claude" / "context" / "active"
REQUIRED_FILES = ["background.md", "standards.md"]


def available_projects() -> list[str]:
    if not PROJECTS_DIR.is_dir():
        return []
    return sorted(
        d.name for d in PROJECTS_DIR.iterdir()
        if d.is_dir() and all((d / f).is_file() for f in REQUIRED_FILES)
    )


def set_project(name: str) -> None:
    project_dir = PROJECTS_DIR / name
    projects = available_projects()

    if name not in projects:
        print(f"Error: '{name}' is not a valid project.")
        print(f"Available projects: {', '.join(projects) if projects else '(none)'}")
        sys.exit(1)

    ACTIVE_DIR.mkdir(parents=True, exist_ok=True)

    for fname in REQUIRED_FILES:
        shutil.copy2(project_dir / fname, ACTIVE_DIR / fname)

    (ACTIVE_DIR / "PROJECT").write_text(name, encoding="utf-8")

    print(f"Active project set to '{name}'.")
    print(f"  background.md -> {ACTIVE_DIR / 'background.md'}")
    print(f"  standards.md  -> {ACTIVE_DIR / 'standards.md'}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        projects = available_projects()
        print("Usage: python tools/set_project.py <project-name>")
        print(f"Available projects: {', '.join(projects) if projects else '(none)'}")
        sys.exit(1)
    set_project(sys.argv[1])

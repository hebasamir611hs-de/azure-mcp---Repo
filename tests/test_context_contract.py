"""
Context Contract Tests — validates the ACTIVE project context files' structure
and their consistency with the engine. Content-agnostic: passes for ANY project's
content, as long as the files keep the contract the agents and skills depend on.

Requires an active project to be set via `python tools/set_project.py <name>`.
If no active project is set, the entire module is skipped with a clear message.

Closes the gap: engine code has 92 tests, but the knowledge files the agents
read had zero validation — a broken table or leftover merge marker would
silently corrupt every analysis.
"""

import re
from pathlib import Path

import pytest

from core.utils import _CANONICAL_CATEGORIES

ROOT = Path(__file__).resolve().parent.parent
ACTIVE_DIR = ROOT / ".claude" / "context" / "active"
STANDARDS = ACTIVE_DIR / "standards.md"
BACKGROUND = ACTIVE_DIR / "background.md"
PROJECT_FILE = ACTIVE_DIR / "PROJECT"
PROJECTS_DIR = ROOT / ".claude" / "context" / "projects"

if not ACTIVE_DIR.exists():
    pytest.skip(
        "no active project set — run tools/set_project.py",
        allow_module_level=True,
    )

# Engine invariants — these must never change per project.
CANONICAL_PLATFORMS = {"IOS", "Android", "Web", "Control_Panel"}


@pytest.fixture(scope="module")
def standards_text():
    assert STANDARDS.exists(), f"Missing context file: {STANDARDS}"
    text = STANDARDS.read_text(encoding="utf-8")
    assert len(text) > 500, "standards file is suspiciously small — truncated?"
    return text


@pytest.fixture(scope="module")
def background_text():
    assert BACKGROUND.exists(), f"Missing context file: {BACKGROUND}"
    text = BACKGROUND.read_text(encoding="utf-8")
    assert len(text) > 500, "background file is suspiciously small — truncated?"
    return text


def _table_codes(text: str, heading: str) -> list:
    """Extracts `CODE` values from the first markdown table under a heading."""
    section = text.split(heading, 1)
    if len(section) < 2:
        return []
    body = section[1].split("\n## ", 1)[0]
    return re.findall(r"^\|\s*`([^`]+)`\s*\|", body, flags=re.MULTILINE)


# ─── Structure: required sections ────────────────────────────────────────────

REQUIRED_STANDARDS_SECTIONS = [
    "## Service / Module Codes",
    "## Platform / Surface Codes",
    "## Test Case ID Convention",
    "## Priority Rubric",
    "## Tag Taxonomy",
    "### Axis 1b",
    "## Money & Payment Rules",
    "## Definition of Done",
    "## Writing Rules",
    "## Default Scope",
]

REQUIRED_BACKGROUND_SECTIONS = [
    "## Company / Domain",
    "## Platforms",
    "## Services",
    "## User Roles",
    "## Integrations",
]


@pytest.mark.parametrize("section", REQUIRED_STANDARDS_SECTIONS)
def test_standards_has_required_section(standards_text, section):
    assert section in standards_text, (
        f"standards is missing '{section}' — agents and the review gate depend on it"
    )


@pytest.mark.parametrize("section", REQUIRED_BACKGROUND_SECTIONS)
def test_background_has_required_section(background_text, section):
    assert section in background_text, f"background is missing '{section}'"


# ─── Consistency: codes and taxonomy ─────────────────────────────────────────

def test_service_codes_exist_and_are_unique(standards_text):
    codes = _table_codes(standards_text, "## Service / Module Codes")
    assert len(codes) >= 3, "Service/Module Codes table is empty or unparseable"
    assert len(codes) == len(set(codes)), f"Duplicate service codes: {codes}"


def test_platform_codes_are_exactly_the_canonical_four(standards_text):
    codes = set(_table_codes(standards_text, "## Platform / Surface Codes"))
    assert codes == CANONICAL_PLATFORMS, (
        f"Platform codes must be exactly {CANONICAL_PLATFORMS} (engine invariant — "
        f"route-automation and the tag taxonomy depend on them); found {codes}"
    )


def test_tc_id_examples_use_declared_service_codes(standards_text):
    """Catches stale examples from another project (service codes left over in a
    different project's standards file) — the exact drift behind the multi-project mixup."""
    services = set(_table_codes(standards_text, "## Service / Module Codes"))
    section = standards_text.split("## Test Case ID Convention", 1)[1].split("\n## ", 1)[0]
    examples = re.findall(r"`([A-Z]+)-[A-Z0-9]+-TC-\d+`", section)
    assert examples, "No TC ID examples found under Test Case ID Convention"
    stale = [e for e in examples if e not in services]
    assert not stale, (
        f"TC ID examples use service codes not declared in this project's table: {stale} "
        f"— stale content from another project?"
    )


def test_axis4_categories_match_engine_classifier(standards_text):
    """The Category axis must list the same values core.utils.classify_tc_from_tags
    understands — otherwise injected tags won't classify."""
    for canonical in _CANONICAL_CATEGORIES.values():
        assert canonical in standards_text, (
            f"Category '{canonical}' (known to the engine classifier) is not mentioned "
            f"in the standards Tag Taxonomy"
        )


def test_axis1b_execution_tags_present(standards_text):
    for tag in ("Automation", "Manual"):
        assert f"`{tag}`" in standards_text, f"Axis 1b must define the `{tag}` tag"


def test_provenance_tag_documented(standards_text):
    assert "Ai_MCP_Injected" in standards_text, (
        "The MCP provenance tag must be documented (agents must know NOT to add it)"
    )


# ─── Hygiene ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("path", [STANDARDS, BACKGROUND])
def test_no_merge_conflict_markers(path):
    text = path.read_text(encoding="utf-8")
    for marker in ("<<<<<<<", ">>>>>>>", "\n=======\n"):
        assert marker not in text, f"Merge conflict marker left in {path.name}"


def test_files_reference_each_other_consistently(standards_text):
    assert "background.md" in standards_text, (
        "standards must point at the background file (stable filename contract)"
    )


# ─── Active project marker ──────────────────────────────────────────────────

def test_active_project_marker_valid():
    assert PROJECT_FILE.exists(), (
        "active/PROJECT marker is missing — run tools/set_project.py"
    )
    project_name = PROJECT_FILE.read_text(encoding="utf-8").strip()
    project_dir = PROJECTS_DIR / project_name
    assert project_dir.is_dir(), (
        f"active/PROJECT says '{project_name}' but "
        f".claude/context/projects/{project_name}/ does not exist"
    )

"""
Regression test for the July 2026 silent-registration bug: an unquoted ': ' inside
a frontmatter 'description:' value (e.g. "Reasoning only: never calls...") is valid
prose but invalid YAML - the colon-space mid-scalar reads as a nested mapping key,
so the whole frontmatter block fails to parse and the agent/skill/command never
registers. No error is shown to the user; it just silently doesn't appear.

Caught first in qa-engineer.md / quality-control-engineer.md / test-failure-triage.md
(agents) and create-bug-queries / create-user-manual (skills). The agents were fixed
manually in PR #16 (Fix_Agents_Not_valid) by removing the space after the colon -
a manual, one-off edit with no guard against recurrence. This test is that guard:
it parses EVERY agent/skill/command frontmatter with a real YAML parser (not visual
inspection) and fails the suite if any of them break the same way again, whether the
break is old, new, or reintroduced by a future edit.

Run: pytest tests/test_claude_frontmatter.py -v
"""

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_DIR = REPO_ROOT / ".claude"
FM_PATTERN = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

AGENT_FILES = sorted((CLAUDE_DIR / "agents").glob("*.md"))
SKILL_FILES = sorted(CLAUDE_DIR.glob("skills/*/SKILL.md"))
COMMAND_FILES = sorted((CLAUDE_DIR / "commands").glob("*.md"))


def _read_frontmatter(path):
    """Returns (yaml_text, parsed_dict_or_None, yaml_error_or_None)."""
    text = path.read_text(encoding="utf-8")
    m = FM_PATTERN.match(text)
    if not m:
        return None, None, None
    try:
        return m.group(1), yaml.safe_load(m.group(1)), None
    except yaml.YAMLError as e:
        return m.group(1), None, e


class TestAgentFrontmatter:
    """Agents MUST have frontmatter, and it MUST be valid YAML with name + description."""

    @pytest.mark.parametrize("path", AGENT_FILES, ids=lambda p: p.stem)
    def test_frontmatter_is_valid_yaml(self, path):
        _, data, err = _read_frontmatter(path)
        assert err is None, f"{path.name}: invalid YAML frontmatter - {err}"
        assert data is not None, f"{path.name}: missing frontmatter block"

    @pytest.mark.parametrize("path", AGENT_FILES, ids=lambda p: p.stem)
    def test_required_fields_present(self, path):
        _, data, err = _read_frontmatter(path)
        assert err is None, f"{path.name}: invalid YAML frontmatter - {err}"
        for key in ("name", "description"):
            assert data.get(key), f"{path.name}: missing or empty '{key}'"


class TestSkillFrontmatter:
    """Skills MUST have frontmatter, and it MUST be valid YAML with name + description."""

    @pytest.mark.parametrize("path", SKILL_FILES, ids=lambda p: p.parent.name)
    def test_frontmatter_is_valid_yaml(self, path):
        _, data, err = _read_frontmatter(path)
        assert err is None, f"{path.parent.name}/SKILL.md: invalid YAML frontmatter - {err}"
        assert data is not None, f"{path.parent.name}/SKILL.md: missing frontmatter block"

    @pytest.mark.parametrize("path", SKILL_FILES, ids=lambda p: p.parent.name)
    def test_required_fields_present(self, path):
        _, data, err = _read_frontmatter(path)
        assert err is None, f"{path.parent.name}/SKILL.md: invalid YAML frontmatter - {err}"
        for key in ("name", "description"):
            assert data.get(key), f"{path.parent.name}/SKILL.md: missing or empty '{key}'"


class TestCommandFrontmatter:
    """Legacy commands/*.md may have NO frontmatter (name falls back to filename) -
    but if a frontmatter block IS present, it must at least be valid YAML."""

    @pytest.mark.parametrize("path", COMMAND_FILES, ids=lambda p: p.stem)
    def test_frontmatter_if_present_is_valid_yaml(self, path):
        _, data, err = _read_frontmatter(path)
        assert err is None, f"{path.name}: invalid YAML frontmatter - {err}"


class TestKnownRegressionFiles:
    """The exact 5 files hit by the July 2026 bug - pinned by name so this test
    fails loudly (not just as one parametrized case among many) if the bug class
    ever resurfaces in these specific files."""

    REGRESSION_FILES = [
        CLAUDE_DIR / "agents" / "qa-engineer.md",
        CLAUDE_DIR / "agents" / "quality-control-engineer.md",
        CLAUDE_DIR / "agents" / "test-failure-triage.md",
        CLAUDE_DIR / "skills" / "create-bug-queries" / "SKILL.md",
        CLAUDE_DIR / "skills" / "create-user-manual" / "SKILL.md",
    ]

    @pytest.mark.parametrize("path", REGRESSION_FILES, ids=lambda p: p.stem or p.parent.name)
    def test_previously_broken_file_now_parses(self, path):
        assert path.exists(), f"{path} was moved or renamed - update this regression test"
        _, data, err = _read_frontmatter(path)
        assert err is None, (
            f"{path}: regression of the July 2026 bug - an unquoted ': ' inside "
            f"'description:' broke YAML parsing again. Error: {err}"
        )
        assert data.get("name") and data.get("description")

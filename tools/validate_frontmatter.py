#!/usr/bin/env python3
"""
Validates YAML frontmatter in every .claude/agents/*.md and .claude/skills/*/SKILL.md
(and .claude/commands/*.md) file. Exits non-zero if any file is missing frontmatter,
has invalid YAML, or is missing required keys - so a broken agent/skill/command can
never silently fail to register again.

Usage: python3 tools/validate_frontmatter.py
Wired as a git pre-commit hook - see tools/install_hooks.sh.
"""
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml not installed. Run: pip install pyyaml --break-system-packages")
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_DIR = REPO_ROOT / ".claude"

FM_PATTERN = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

# (base_dir, glob_pattern, required_keys, frontmatter_required)
TARGETS = [
    (CLAUDE_DIR / "agents", "*.md", {"name", "description"}, True),
    (CLAUDE_DIR / "commands", "*.md", {"name", "description"}, False),
    (CLAUDE_DIR, "skills/*/SKILL.md", {"name", "description"}, True),
]


def check_file(path, required_keys, frontmatter_required):
    errors = []
    text = path.read_text(encoding="utf-8")
    m = FM_PATTERN.match(text)
    if not m:
        if frontmatter_required:
            errors.append("no frontmatter block found (must start with '---' and close with '---')")
        # Legacy commands/*.md may be plain markdown with no frontmatter - invocation
        # name falls back to the filename. Nothing to validate in that case.
        return errors
    try:
        data = yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        msg = str(e).split("\n")[0]
        errors.append("invalid YAML - " + msg)
        if "mapping values are not allowed here" in msg:
            errors.append(
                "  hint: a colon-space inside an unquoted value (often in 'description:') "
                "is being read as a nested key. Quote the value, remove the space after "
                "that colon, or use a YAML block scalar (description: >-)."
            )
        return errors
    if not isinstance(data, dict):
        errors.append("frontmatter did not parse to a mapping")
        return errors
    missing = required_keys - set(data.keys())
    if missing:
        errors.append("missing required field(s): " + ", ".join(sorted(missing)))
    for key in required_keys:
        if key in data and (data[key] is None or str(data[key]).strip() == ""):
            errors.append("field '" + key + "' is empty")
    return errors


def main():
    if not CLAUDE_DIR.exists():
        print("No .claude/ directory found at " + str(CLAUDE_DIR) + " - nothing to validate.")
        return 0

    all_errors = []
    checked = 0
    for base, pattern, required_keys, frontmatter_required in TARGETS:
        for path in sorted(base.glob(pattern)):
            checked += 1
            errors = check_file(path, required_keys, frontmatter_required)
            if errors:
                all_errors.append((path.relative_to(REPO_ROOT), errors))

    if all_errors:
        print("")
        print("Frontmatter validation FAILED (" + str(len(all_errors)) + " of " + str(checked) + " files broken):")
        print("")
        for rel_path, errors in all_errors:
            print("  " + str(rel_path))
            for e in errors:
                print("    - " + e)
        print("")
        print("Fix these before committing - a broken frontmatter block means the agent,")
        print("skill, or command silently fails to register at runtime.")
        print("")
        return 1

    print("Frontmatter validation passed - " + str(checked) + " files OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

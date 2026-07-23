#!/usr/bin/env bash
# One-time setup: wires tools/validate_frontmatter.py as a git pre-commit hook.
# Run once per clone (works whether this repo is standalone or a submodule):
#   bash tools/install_hooks.sh
set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
HOOK="$(git rev-parse --git-path hooks/pre-commit)"
mkdir -p "$(dirname "$HOOK")"

cat > "$HOOK" <<'HOOKEOF'
#!/usr/bin/env bash
# Auto-installed by tools/install_hooks.sh — validates .claude/ frontmatter before every commit.
REPO_ROOT="$(git rev-parse --show-toplevel)"
python3 "$REPO_ROOT/tools/validate_frontmatter.py"
exit $?
HOOKEOF

chmod +x "$HOOK"
echo "Pre-commit hook installed at $HOOK"
echo "Every commit will now run tools/validate_frontmatter.py first."

"""
QA-Final-V4 — Enterprise-Grade MCP Server for Azure DevOps QA Automation

Entry point and tool aggregator. Imports plain functions from core/ modules
and registers them as MCP tools. No business logic lives here.

Architecture: core/utils.py  → shared helpers
              core/discovery.py → Skills 0, 1, legacy
              core/engines.py   → Skills 3, 4, 9, legacy
              core/analysis.py  → Skills 5, 7
              core/output_manager.py → Skill 11a

Credentials: loaded exclusively from .env — never hard-coded here or in mcp-config.json.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ─── Load .env BEFORE any core import that might read env vars at module level ───
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)


# ─────────────────────────────────────────────────────────────────────────────
# STARTUP VALIDATION — fail fast with actionable messages
# ─────────────────────────────────────────────────────────────────────────────

def _validate_config() -> None:
    """Validates required environment variables at startup. Aborts on failure."""
    required = {
        "AZURE_PAT": "Azure DevOps Personal Access Token",
        "AZURE_ORG_URL": "Azure DevOps Organization URL (e.g. https://dev.azure.com/yourorg)",
        "AZURE_PROJECT": "Azure DevOps Project Name"
    }
    missing = []
    for var, description in required.items():
        value = os.getenv(var)
        if not value or not value.strip():
            missing.append(f"  {var}: {description}")

    if missing:
        print(
            "\n[QA-Final-V4] STARTUP ERROR — Missing required environment variables:\n"
            + "\n".join(missing)
            + f"\n\nCreate or update {env_path} with the missing values.\n"
            "See CLAUDE.md for setup instructions.\n",
            file=sys.stderr
        )
        sys.exit(1)

    pat = os.getenv("AZURE_PAT", "")
    if len(pat.strip()) < 20:
        print(
            "\n[QA-Final-V4] STARTUP ERROR — AZURE_PAT appears invalid (too short).\n"
            "Regenerate your PAT in Azure DevOps → User Settings → Personal Access Tokens.\n",
            file=sys.stderr
        )
        sys.exit(1)


_validate_config()


# ─── Import core modules AFTER validation and dotenv load ────────────────────
from mcp.server.fastmcp import FastMCP

from core.discovery import (
    check_pbi_duplicates,
    get_pbis_from_sprint,
    get_story_for_analysis,
)
from core.reporting import (
    create_work_item_query,
    ensure_bug_query_hierarchy,
    get_query_summary,
    get_test_outcome_summary,
    get_test_run_outcome_summary,
)
from core.engines import (
    create_arabic_test_case,
    create_english_test_case,
    execute_qa_feedback,
    add_full_test_case,
)
from core.bugs import (
    find_existing_bug,
    create_bug,
    add_bug_occurrence,
)
from core.analysis import (
    review_test_coverage,
    generate_qa_report,
)
from core.output_manager import (
    review_uat_document,
)
from core.test_planner import (
    create_test_plan,
    create_test_suites_for_sprint,
    create_test_suite_for_pbi,
    get_test_cases_from_suite,
)


mcp = FastMCP("QA-Final-V4")


# ─────────────────────────────────────────────────────────────────────────────
# TOOL REGISTRATION
# Decorate each imported function exactly once. Docstrings are preserved from
# the core modules — FastMCP uses them as tool descriptions for the LLM.
# ─────────────────────────────────────────────────────────────────────────────

# ── Legacy (backward compatibility) ──────────────────────────────────────────
mcp.tool()(get_story_for_analysis)
mcp.tool()(add_full_test_case)

# ── Skill 0: PBI Deduplication ────────────────────────────────────────────────
mcp.tool()(check_pbi_duplicates)

# ── Skill 1: Smart PBI Discovery ─────────────────────────────────────────────
mcp.tool()(get_pbis_from_sprint)

# ── Skill 2: Query Creation (core/reporting.py) ──────────────────────────────
mcp.tool()(create_work_item_query)
mcp.tool()(ensure_bug_query_hierarchy)

# ── Skill 3: Query Summary (core/reporting.py) ───────────────────────────────
mcp.tool()(get_query_summary)

# ── Test Outcomes: Get Test Suite Results & Test Run Results ───────────────
mcp.tool()(get_test_outcome_summary)
mcp.tool()(get_test_run_outcome_summary)

# ── Skills 3 & 4: Bilingual TC Engines ───────────────────────────────────────
mcp.tool()(create_arabic_test_case)
mcp.tool()(create_english_test_case)

# ── Skill 5: Gap Analysis & Coverage ─────────────────────────────────────────
mcp.tool()(review_test_coverage)

# ── Skill 7: Executive QA Dashboard ──────────────────────────────────────────
mcp.tool()(generate_qa_report)

# ── Skill 9: Managerial Feedback Loop ────────────────────────────────────────
mcp.tool()(execute_qa_feedback)

# ── Skill 11a: UAT Review ────────────────────────────────────────────────────
# UAT document *creation* is not an MCP tool — the drafter subagent owns it
# (see .claude/skills/build-uat-doc). The MCP only parses docs for review.
mcp.tool()(review_uat_document)

# ── Skill 12: Test Plan Creation ──────────────────────────────────────────────
mcp.tool()(create_test_plan)

# ── Skill 13: Test Suite Creation — full sprint ───────────────────────────────
mcp.tool()(create_test_suites_for_sprint)

# ── Skill 14: Test Suite Creation — single PBI ───────────────────────────────
mcp.tool()(create_test_suite_for_pbi)

# ── Skill 15: Read All Test Cases from a Suite ───────────────────────────────
mcp.tool()(get_test_cases_from_suite)

# ── Bug Reporting: automated test failures → Azure DevOps (core/bugs.py) ────
mcp.tool()(find_existing_bug)
mcp.tool()(create_bug)
mcp.tool()(add_bug_occurrence)


if __name__ == "__main__":
    mcp.run(transport='stdio')

"""
core/test_planner.py — Skill 12 & 13: Test Plan and Test Suite creation.

Skill 12: create_test_plan            — creates an Azure DevOps test plan for a sprint
Skill 13: create_test_suites_for_sprint — creates one requirement-based suite per PBI

All functions are plain — no @mcp.tool() decorators. Registration happens in server.py.
"""

import os
import re
from urllib.parse import unquote

from azure.devops.connection import Connection
from azure.devops.v7_1.work_item_tracking.models import Wiql
from azure.devops.v7_1.test_plan.models import (
    TestPlanCreateParams,
    TestSuiteCreateParams,
    TestSuiteReference,
)
from msrest.authentication import BasicAuthentication

from core.utils import handle_error, sanitize_wiql_string, parse_steps_xml


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_connection() -> Connection:
    """Returns an authenticated Azure DevOps Connection."""
    credentials = BasicAuthentication('', os.getenv("AZURE_PAT"))
    return Connection(base_url=os.getenv("AZURE_ORG_URL"), creds=credentials)


def _get_test_plan_client():
    """
    Returns an authenticated TestPlanClient (the /testplan/ API).

    Note: this is NOT the same as get_test_client() — the older TestClient does
    not expose create_test_plan / create_test_suite. Plan and suite authoring
    lives exclusively on the TestPlanClient in this SDK.
    """
    return _get_connection().clients.get_test_plan_client()


def _parse_iteration_path(sprint_input: str) -> str:
    """
    Accepts either an iteration path string or a sprint URL (absolute or the
    relative path Azure DevOps copies) and returns a normalized iteration path
    (e.g. 'Woqod\\MCP-test-3').

    URL forms handled (with or without the https://org host prefix):
      .../_sprints/taskboard/{Team}/{Project}/{Sprint}?...
    The captured iteration path is {Project}/{Sprint}, slash-normalized to '\\'.
    """
    sprint_input = sprint_input.strip()
    if "_sprints" in sprint_input:
        decoded = unquote(sprint_input)
        # Skip the view segment (taskboard/backlog) and the team, capture Project/Sprint
        match = re.search(r'/_sprints/[^/]+/[^/]+/(.+?)(?:\?|$)', decoded)
        if match:
            return match.group(1).replace('/', '\\')
    return sprint_input


def _get_pbis_for_iteration(project: str, iteration_path: str) -> list:
    """
    Returns [{id, title}] for every active PBI in the given iteration.
    Uses a fresh WIT client to avoid state leaking from other operations.
    """
    wit_client = _get_connection().clients.get_work_item_tracking_client()
    safe_path = sanitize_wiql_string(iteration_path)
    safe_proj = sanitize_wiql_string(project)

    wiql = Wiql(query=f"""
        SELECT [System.Id], [System.Title]
        FROM WorkItems
        WHERE [System.WorkItemType] = 'Product Backlog Item'
          AND [System.IterationPath] = '{safe_path}'
          AND [System.TeamProject] = '{safe_proj}'
          AND [System.State] <> 'Removed'
        ORDER BY [System.Id] ASC
    """)

    result = wit_client.query_by_wiql(wiql)
    if not result.work_items:
        return []

    ids = [wi.id for wi in result.work_items]
    items = wit_client.get_work_items(ids=ids, fields=["System.Id", "System.Title"])
    return [
        {"id": item.id, "title": item.fields.get("System.Title", f"PBI {item.id}")}
        for item in items
        if item is not None
    ]


# ─────────────────────────────────────────────────────────────────────────────
# SKILL 12: CREATE TEST PLAN
# ─────────────────────────────────────────────────────────────────────────────

def create_test_plan(sprint_input: str, plan_name: str = "") -> dict:
    """
    SKILL 12: Create Test Plan for a Sprint

    Creates an Azure DevOps test plan scoped to the given sprint/iteration.
    The plan name defaults to 'Test Plan - <sprint name>' if not provided.

    Args:
        sprint_input (str): Iteration path (e.g. 'Woqod\\MCP-test-3') OR
                            the full sprint URL copied from the Azure DevOps browser.
        plan_name (str): Optional custom name for the test plan.

    Returns:
        {status, plan_id, plan_name, root_suite_id, iteration_path}
    """
    try:
        iteration_path = _parse_iteration_path(sprint_input)
        project = os.getenv("AZURE_PROJECT")

        if not plan_name.strip():
            sprint_short = iteration_path.split("\\")[-1]
            plan_name = f"Test Plan - {sprint_short}"

        plan_client = _get_test_plan_client()

        plan_params = TestPlanCreateParams(
            name=plan_name,
            iteration=iteration_path,
            description=f"Auto-generated test plan for sprint: {iteration_path}"
        )

        plan = plan_client.create_test_plan(plan_params, project)

        root_suite_id = plan.root_suite.id if plan.root_suite else None

        return {
            "status": "created",
            "plan_id": plan.id,
            "plan_name": plan.name,
            "root_suite_id": root_suite_id,
            "iteration_path": iteration_path
        }

    except Exception as e:
        return handle_error(e, "create_test_plan")


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL: SHARED SUITE CREATION CORE
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_root_suite_id(plan_client, project: str, plan_id: int):
    """
    Fetches the plan and returns its root suite ID.
    Returns (root_suite_id, error_dict_or_None).
    """
    plan = plan_client.get_test_plan_by_id(project, plan_id)
    if not plan:
        return None, {"error": f"Test plan {plan_id} not found in project '{project}'"}
    root_suite_id = plan.root_suite.id if plan.root_suite else None
    if not root_suite_id:
        return None, {"error": f"Could not resolve root suite for plan {plan_id}."}
    return root_suite_id, None


def _create_suite_for_pbi(plan_client, project: str, plan_id: int,
                          root_suite_id: int, pbi_id: int, pbi_title: str) -> dict:
    """
    Creates a single requirement-based test suite for one PBI, nested under the
    plan's root suite and linked to the PBI via Requirements traceability.
    Returns a result dict.
    """
    suite_params = TestSuiteCreateParams(
        name=f"{pbi_id} - {pbi_title}",
        suite_type="requirementTestSuite",
        requirement_id=pbi_id,
        parent_suite=TestSuiteReference(id=root_suite_id)
    )
    suite_obj = plan_client.create_test_suite(suite_params, project, plan_id)
    return {
        "suite_id": suite_obj.id,
        "suite_name": suite_obj.name,
        "pbi_id": pbi_id,
        "pbi_title": pbi_title
    }


# ─────────────────────────────────────────────────────────────────────────────
# SKILL 13: CREATE TEST SUITES FOR ALL PBIs IN A SPRINT
# ─────────────────────────────────────────────────────────────────────────────

def create_test_suites_for_sprint(plan_id: int, sprint_input: str) -> dict:
    """
    SKILL 13: Create Requirement-Based Test Suites for Each PBI in a Sprint

    Discovers all PBIs under the given sprint and creates one requirement-based
    test suite per PBI under the specified test plan. Each suite is linked to
    its PBI via Azure DevOps Requirements traceability.

    Typical workflow:
      1. Call create_test_plan         → get plan_id
      2. Call create_test_suites_for_sprint with that plan_id

    Args:
        plan_id (int): Test plan ID returned by create_test_plan.
        sprint_input (str): Iteration path (e.g. 'Woqod\\MCP-test-3') OR
                            the full sprint URL from Azure DevOps.

    Returns:
        {plan_id, iteration_path, total_pbis, created, errors_count,
         created_details, errors_details}
    """
    try:
        iteration_path = _parse_iteration_path(sprint_input)
        project = os.getenv("AZURE_PROJECT")

        plan_client = _get_test_plan_client()

        root_suite_id, err = _resolve_root_suite_id(plan_client, project, plan_id)
        if err:
            return err

        pbis = _get_pbis_for_iteration(project, iteration_path)
        if not pbis:
            return {
                "plan_id": plan_id,
                "iteration_path": iteration_path,
                "total_pbis": 0,
                "created": 0,
                "errors_count": 0,
                "message": "No PBIs found in the specified sprint.",
                "created_details": [],
                "errors_details": []
            }

        created = []
        errors = []

        for pbi in pbis:
            try:
                created.append(_create_suite_for_pbi(
                    plan_client, project, plan_id, root_suite_id,
                    pbi["id"], pbi["title"]
                ))
            except Exception as e:
                errors.append({
                    "pbi_id": pbi["id"],
                    "pbi_title": pbi["title"],
                    "error": str(e)
                })

        return {
            "plan_id": plan_id,
            "iteration_path": iteration_path,
            "total_pbis": len(pbis),
            "created": len(created),
            "errors_count": len(errors),
            "created_details": created,
            "errors_details": errors
        }

    except Exception as e:
        return handle_error(e, "create_test_suites_for_sprint")


# ─────────────────────────────────────────────────────────────────────────────
# SKILL 14: CREATE TEST SUITE FOR A SINGLE PBI
# ─────────────────────────────────────────────────────────────────────────────

def create_test_suite_for_pbi(plan_id: int, pbi_id: int) -> dict:
    """
    SKILL 14: Create a Requirement-Based Test Suite for a Single PBI

    Creates one test suite under the given test plan, linked to the specified
    PBI via Azure DevOps Requirements traceability.
    Use this when you want to add a suite for one PBI without touching the rest
    of the sprint.

    Args:
        plan_id (int): Test plan ID to create the suite under.
        pbi_id (int): Work item ID of the PBI to link the suite to.

    Returns:
        {status, suite_id, suite_name, pbi_id, pbi_title, plan_id}
    """
    try:
        project = os.getenv("AZURE_PROJECT")
        conn = _get_connection()
        plan_client = conn.clients.get_test_plan_client()
        wit_client = conn.clients.get_work_item_tracking_client()

        root_suite_id, err = _resolve_root_suite_id(plan_client, project, plan_id)
        if err:
            return err

        # Fetch the PBI title
        pbi = wit_client.get_work_item(pbi_id, fields=["System.Id", "System.Title"])
        pbi_title = pbi.fields.get("System.Title", f"PBI {pbi_id}")

        suite = _create_suite_for_pbi(
            plan_client, project, plan_id, root_suite_id, pbi_id, pbi_title
        )

        return {
            "status": "created",
            "plan_id": plan_id,
            **suite
        }

    except Exception as e:
        return handle_error(e, "create_test_suite_for_pbi")


# ─────────────────────────────────────────────────────────────────────────────
# SKILL 15: GET ALL TEST CASES FROM A TEST SUITE
# ─────────────────────────────────────────────────────────────────────────────

def get_test_cases_from_suite(plan_id: int, suite_id: int) -> dict:
    """
    SKILL 15: Get All Test Cases from a Test Suite (one consolidated JSON)

    Returns every test case contained in the given suite, fully expanded with
    title, state, priority, tags, description, and structured steps. Designed so
    an AI agent can consume the whole suite in a single payload and reuse it for
    anything downstream (review, UAT docs, automation, reporting).

    Args:
        plan_id (int): Test plan ID the suite belongs to.
        suite_id (int): Test suite ID to read test cases from.

    Returns:
        {
            "status": "success",
            "plan_id": int,
            "suite_id": int,
            "total_test_cases": int,
            "test_cases": [
                {
                    "id": int,
                    "title": str,
                    "state": str,
                    "priority": int | None,
                    "tags": [str, ...],
                    "description": str,
                    "area_path": str,
                    "iteration_path": str,
                    "steps": [{"action": str, "expected": str}, ...]
                },
                ...
            ]
        }
    """
    try:
        project = os.getenv("AZURE_PROJECT")
        conn = _get_connection()
        plan_client = conn.clients.get_test_plan_client()
        wit_client = conn.clients.get_work_item_tracking_client()

        # 1. Resolve the test case work item IDs contained in the suite
        suite_cases = plan_client.get_test_case_list(project, plan_id, suite_id)
        tc_ids = [
            tc.work_item.id
            for tc in suite_cases
            if getattr(tc, "work_item", None) and tc.work_item.id
        ]

        if not tc_ids:
            return {
                "status": "success",
                "plan_id": plan_id,
                "suite_id": suite_id,
                "total_test_cases": 0,
                "test_cases": [],
                "message": "No test cases found in this suite."
            }

        # 2. Batch-fetch full work item detail (chunks of 200 — Azure's per-call cap)
        test_cases = []
        for start in range(0, len(tc_ids), 200):
            chunk = tc_ids[start:start + 200]
            items = wit_client.get_work_items(ids=chunk, expand="All")
            for item in items:
                if item is None:
                    continue
                f = item.fields
                tags_raw = f.get("System.Tags", "")
                test_cases.append({
                    "id": item.id,
                    "title": f.get("System.Title", ""),
                    "state": f.get("System.State", ""),
                    "priority": f.get("Microsoft.VSTS.Common.Priority"),
                    "tags": [t.strip() for t in tags_raw.split(";") if t.strip()],
                    "description": f.get("System.Description", ""),
                    "area_path": f.get("System.AreaPath", ""),
                    "iteration_path": f.get("System.IterationPath", ""),
                    "steps": parse_steps_xml(f.get("Microsoft.VSTS.TCM.Steps", ""))
                })

        # Stable ordering by work item ID
        test_cases.sort(key=lambda tc: tc["id"])

        return {
            "status": "success",
            "plan_id": plan_id,
            "suite_id": suite_id,
            "total_test_cases": len(test_cases),
            "test_cases": test_cases
        }

    except Exception as e:
        return handle_error(e, "get_test_cases_from_suite")

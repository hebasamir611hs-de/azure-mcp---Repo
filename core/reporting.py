"""
core/reporting.py — Reporting & Query Management tools.

SKILL 2: Work Item Query Creation.
SKILL 3: Query Summary — run a saved query and return count breakdowns per field.

All functions are plain — no @mcp.tool() decorators. Registration happens in server.py.

Credentials are loaded from .env (AZURE_PAT, AZURE_ORG_URL, AZURE_PROJECT).
"""

import json
import os
import re
from base64 import b64encode
from urllib.parse import quote
from typing import List, Optional, Dict, Any

import requests

from core.utils import handle_error


# ─────────────────────────────────────────────────────────────────────────────
# AUTH HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _auth_headers() -> dict:
    """Builds Basic-auth headers for the Azure DevOps REST API from AZURE_PAT."""
    pat = os.getenv("AZURE_PAT", "").strip()
    token = b64encode(f":{pat}".encode("utf-8")).decode("ascii")
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }


# Default columns used when none are specified.
DEFAULT_COLUMNS = [
    "System.Id",
    "System.Title",
    "System.WorkItemType",
    "System.State",
    "System.AssignedTo",
]

# Common field reference names callers can pick from.
AVAILABLE_COLUMNS = {
    "Id":             "System.Id",
    "Title":          "System.Title",
    "WorkItemType":   "System.WorkItemType",
    "State":          "System.State",
    "AssignedTo":     "System.AssignedTo",
    "AreaPath":       "System.AreaPath",
    "IterationPath":  "System.IterationPath",
    "CreatedDate":    "System.CreatedDate",
    "CreatedBy":      "System.CreatedBy",
    "ChangedDate":    "System.ChangedDate",
    "ChangedBy":      "System.ChangedBy",
    "Priority":       "Microsoft.VSTS.Common.Priority",
    "Severity":       "Microsoft.VSTS.Common.Severity",
    "Tags":           "System.Tags",
    "Description":    "System.Description",
    "AcceptanceCriteria": "Microsoft.VSTS.Common.AcceptanceCriteria",
    "ResolvedDate":   "Microsoft.VSTS.Common.ResolvedDate",
    "ClosedDate":     "Microsoft.VSTS.Common.ClosedDate",
    "StoryPoints":    "Microsoft.VSTS.Scheduling.StoryPoints",
}


def _build_wiql(columns: List[str], where_clause: str) -> str:
    """Builds a full WIQL statement from a column list and a WHERE clause."""
    select_fields = ", ".join(f"[{c}]" for c in columns)
    return f"SELECT {select_fields} FROM WorkItems WHERE {where_clause}"


def _inject_columns(wiql: str, columns: List[str]) -> str:
    """Replaces the SELECT clause in an existing WIQL string with new columns."""
    select_fields = ", ".join(f"[{c}]" for c in columns)
    # Replace everything between SELECT and FROM (case-insensitive).
    return re.sub(
        r"(?i)SELECT\s+.+?\s+FROM",
        f"SELECT {select_fields} FROM",
        wiql,
        count=1,
        flags=re.DOTALL,
    )


# ─────────────────────────────────────────────────────────────────────────────
# QUERY HIERARCHY HELPERS (folders + idempotent query creation)
# ─────────────────────────────────────────────────────────────────────────────

_INVALID_NAME_CHARS = re.compile(r'[\\/:*?"<>|#]')


def _sanitize_name(name: str, max_len: int = 200) -> str:
    """Strips characters invalid in Azure DevOps query/folder names, collapses
    whitespace, and truncates to max_len. Falls back to 'Unnamed' if empty."""
    if not name:
        return "Unnamed"
    cleaned = _INVALID_NAME_CHARS.sub("-", name.strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:max_len] or "Unnamed"


def _get_query_item(org_url: str, project: str, path: str) -> Optional[dict]:
    """Looks up a query or folder by path. Returns None if it doesn't exist.

    For a top-level path (e.g. 'Shared Queries'), GETs it directly. For a
    nested path, lists the PARENT folder's children ($depth=1) and matches by
    name (case-insensitive) instead of GETting the full path directly — the
    by-path GET endpoint has been observed to return a stale 404 for an item
    that was created moments earlier, which would otherwise cause a duplicate
    to be created on top of an existing query/folder.
    """
    segments = path.strip("/").split("/")
    if len(segments) == 1:
        encoded = quote(segments[0], safe="/")
        url = f"{org_url}/{project}/_apis/wit/queries/{encoded}?api-version=7.1"
        resp = requests.get(url, headers=_auth_headers(), timeout=30)
        if resp.status_code == 200:
            return resp.json()
        return None

    parent_path = "/".join(segments[:-1])
    name = segments[-1]
    encoded_parent = quote(parent_path, safe="/")
    url = f"{org_url}/{project}/_apis/wit/queries/{encoded_parent}?$depth=1&api-version=7.1"
    resp = requests.get(url, headers=_auth_headers(), timeout=30)
    if resp.status_code != 200:
        return None
    for child in resp.json().get("children", []) or []:
        if child.get("name", "").lower() == name.lower():
            return child
    return None


def _create_folder(org_url: str, project: str, parent_path: str, name: str) -> dict:
    """Creates a new query folder under parent_path. Raises ValueError on failure."""
    encoded_parent = quote(parent_path.strip("/"), safe="/")
    url = f"{org_url}/{project}/_apis/wit/queries/{encoded_parent}?api-version=7.1"
    resp = requests.post(
        url, json={"name": name, "isFolder": True}, headers=_auth_headers(), timeout=30
    )
    if resp.status_code not in (200, 201):
        try:
            msg = resp.json().get("message", resp.text)
        except ValueError:
            msg = resp.text or f"HTTP {resp.status_code}"
        raise ValueError(f"Failed to create folder '{name}' under '{parent_path}': {msg}")
    return resp.json()


def _ensure_folder_path(org_url: str, project: str, full_path: str) -> None:
    """Ensures every segment of full_path exists as a query folder, creating any
    that are missing. The first segment (e.g. 'Shared Queries') must already
    exist — it cannot be auto-created."""
    segments = [s for s in full_path.strip("/").split("/") if s]
    current = ""
    for seg in segments:
        parent = current
        current = f"{current}/{seg}" if current else seg
        if _get_query_item(org_url, project, current) is not None:
            continue
        if not parent:
            raise ValueError(f"Root folder '{seg}' does not exist and cannot be auto-created.")
        _create_folder(org_url, project, parent, seg)


def _ensure_query(
    org_url: str,
    project: str,
    folder_path: str,
    name: str,
    wiql_where: str,
    columns: Optional[List[str]] = None,
) -> dict:
    """Ensures a saved query exists at folder_path/name. If it already exists,
    returns it untouched (status_action='existing'). If missing, creates it via
    create_work_item_query (status_action='created' or 'error')."""
    full_path = f"{folder_path}/{name}"
    existing = _get_query_item(org_url, project, full_path)
    if existing is not None:
        html_link = (
            existing.get("_links", {}).get("html", {}).get("href")
            or f"{org_url}/{project}/_queries/query/{existing.get('id')}"
        )
        return {
            "status_action": "existing",
            "query_id": str(existing.get("id", "")),
            "path": existing.get("path", full_path),
            "url": html_link,
        }

    created = create_work_item_query(name, folder_path, wiql_where, columns)
    created["status_action"] = "created" if created.get("status") == "success" else "error"
    return created


# ─────────────────────────────────────────────────────────────────────────────
# SKILL 2: QUERY CREATION
# ─────────────────────────────────────────────────────────────────────────────

def create_work_item_query(
    query_name: str,
    folder_path: str,
    wiql_criteria: str,
    columns: Optional[List[str]] = None,
) -> dict:
    """
    SKILL 2: Create a Work Item Query in Azure DevOps

    Creates a new saved query inside an existing folder with custom WIQL search
    criteria. Optionally override the SELECT columns that appear in the results.

    How the Azure DevOps REST API works (api-version 7.1):
        POST {org}/{project}/_apis/wit/queries/{parent_folder_path}
        body: {"name": <query_name>, "wiql": <full_wiql>}
    The PARENT folder path goes in the URL; the query name + WIQL go in the body.

    Args:
        query_name (str):   Name of the new query (e.g., "Critical Bugs")
        folder_path (str):  Existing parent folder path
                            (e.g., "Shared Queries/Bugs"). Must already exist.
        wiql_criteria (str): Either a full WIQL string
                             ("SELECT ... FROM WorkItems WHERE ...")
                             or just a WHERE clause
                             ("System.WorkItemType = 'Bug' AND ...").
                             If only a WHERE clause is supplied, the SELECT
                             is built from the `columns` argument (or defaults).
        columns (list, optional): Field reference names to show as result columns.
                             Pass short aliases (e.g. "Priority", "Tags") or full
                             reference names (e.g. "System.AssignedTo").
                             Available aliases:
                               Id, Title, WorkItemType, State, AssignedTo,
                               AreaPath, IterationPath, CreatedDate, CreatedBy,
                               ChangedDate, ChangedBy, Priority, Severity, Tags,
                               Description, AcceptanceCriteria, ResolvedDate,
                               ClosedDate, StoryPoints
                             Defaults: Id, Title, WorkItemType, State, AssignedTo

    Returns:
        {
            "status":     "success" | "error",
            "query_id":   str (UUID),
            "query_name": str,
            "path":       str (full path of the created query),
            "columns":    list (field reference names used),
            "url":        str (web link to open the query in Azure DevOps),
            "message":    str
        }
    """
    try:
        org_url = os.getenv("AZURE_ORG_URL", "").rstrip("/")
        project = os.getenv("AZURE_PROJECT")

        # ── Resolve column aliases → full reference names ─────────────────────
        resolved_columns = []
        for col in (columns or DEFAULT_COLUMNS):
            resolved_columns.append(AVAILABLE_COLUMNS.get(col, col))

        # ── Build the final WIQL ──────────────────────────────────────────────
        wiql_upper = wiql_criteria.strip().upper()
        if wiql_upper.startswith("SELECT"):
            # Full WIQL supplied — replace its SELECT clause with our columns.
            final_wiql = _inject_columns(wiql_criteria.strip(), resolved_columns)
        else:
            # Only a WHERE clause supplied — build the full statement.
            final_wiql = _build_wiql(resolved_columns, wiql_criteria.strip())

        # ── POST to Azure DevOps ──────────────────────────────────────────────
        encoded_parent = quote(folder_path.strip("/"), safe="/")
        url = (
            f"{org_url}/{project}/_apis/wit/queries/{encoded_parent}"
            "?api-version=7.1"
        )

        payload = {"name": query_name, "wiql": final_wiql}

        response = requests.post(
            url, json=payload, headers=_auth_headers(), timeout=30
        )

        if response.status_code in (200, 201):
            result = response.json()
            query_id = result.get("id", "")
            html_link = (
                result.get("_links", {}).get("html", {}).get("href")
                or f"{org_url}/{project}/_queries/query/{query_id}"
            )
            result_dict = {
                "status": "success",
                "query_id": str(query_id),
                "query_name": result.get("name", query_name),
                "path": result.get("path", f"{folder_path}/{query_name}"),
                "columns": resolved_columns,
                "url": html_link,
                "message": (
                    f"Query '{query_name}' created successfully under "
                    f"'{folder_path}' with {len(resolved_columns)} column(s)."
                ),
            }
            return result_dict

        try:
            api_msg = response.json().get("message", response.text)
        except ValueError:
            api_msg = response.text or f"HTTP {response.status_code}"

        error_dict = {
            "status": "error",
            "error_type": "api",
            "http_status": response.status_code,
            "error": f"[create_work_item_query] Failed to create query: {api_msg}",
        }
        return error_dict

    except Exception as e:
        error_result = handle_error(e, "create_work_item_query")
        return error_result


# ─────────────────────────────────────────────────────────────────────────────
# SKILL 3: QUERY SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

# Maps short aliases to Azure DevOps field reference names (same as AVAILABLE_COLUMNS).
_FIELD_MAP = {**AVAILABLE_COLUMNS}

# Fields that should be treated as dates — display as-is rather than counting.
_DATE_FIELDS = {"System.CreatedDate", "System.ChangedDate", "Microsoft.VSTS.Common.ResolvedDate",
                "Microsoft.VSTS.Common.ClosedDate"}


def _get_query_wiql(org_url: str, project: str, query_id_or_path: str) -> str:
    """Fetches the WIQL of an existing saved query by its ID or path."""
    encoded = quote(query_id_or_path.strip("/"), safe="/")
    url = (
        f"{org_url}/{project}/_apis/wit/queries/{encoded}"
        "?$expand=wiql&api-version=7.1"
    )
    resp = requests.get(url, headers=_auth_headers(), timeout=30)
    if resp.status_code != 200:
        try:
            msg = resp.json().get("message", resp.text)
        except ValueError:
            msg = resp.text or f"HTTP {resp.status_code}"
        raise ValueError(f"Could not fetch query: {msg}")
    return resp.json().get("wiql", "")


def _run_wiql(org_url: str, project: str, wiql: str) -> list:
    """Executes a WIQL string and returns a list of work item IDs."""
    url = f"{org_url}/{project}/_apis/wit/wiql?api-version=7.1"
    resp = requests.post(url, json={"query": wiql}, headers=_auth_headers(), timeout=60)
    if resp.status_code != 200:
        try:
            msg = resp.json().get("message", resp.text)
        except ValueError:
            msg = resp.text or f"HTTP {resp.status_code}"
        raise ValueError(f"WIQL execution failed: {msg}")
    return [item["id"] for item in resp.json().get("workItems", [])]


def _fetch_work_items(org_url: str, project: str, ids: list, fields: list) -> list:
    """
    Batch-fetches work items with the requested fields (200 per request).
    Raises ValueError on any failed batch — a partial fetch must fail loudly,
    never silently undercount a summary.
    """
    if not ids:
        return []
    results = []
    batch_size = 200
    fields_param = ",".join(fields)
    for i in range(0, len(ids), batch_size):
        batch = ids[i: i + batch_size]
        ids_param = ",".join(str(x) for x in batch)
        url = (
            f"{org_url}/{project}/_apis/wit/workitems"
            f"?ids={ids_param}&fields={fields_param}&api-version=7.1"
        )
        resp = requests.get(url, headers=_auth_headers(), timeout=60)
        if resp.status_code != 200:
            try:
                msg = resp.json().get("message", resp.text)
            except ValueError:
                msg = resp.text or f"HTTP {resp.status_code}"
            raise ValueError(
                f"Work-item batch fetch failed (ids {batch[0]}..{batch[-1]}): {msg}"
            )
        results.extend(resp.json().get("value", []))
    return results


def get_query_summary(
    query_id_or_path: str,
    group_by: Optional[List[str]] = None,
) -> dict:
    """
    SKILL 3: Query Summary — Run a Saved Query and Return Count Breakdowns

    Executes an existing saved Azure DevOps query and returns a statistical
    summary in JSON format: for each requested field, how many work items fall 
    into each distinct value (e.g. count per State, count per Severity, count per AssignedTo).

    Args:
        query_id_or_path (str): The saved query's UUID
                                (e.g. "8f131013-6e7c-45ce-a098-258d081992c0")
                                OR its path
                                (e.g. "Shared Queries/Bugs/test mcp create query 1").
        group_by (list, optional): Fields to aggregate by. Accepts short aliases
                                   or full reference names.
                                   Available aliases:
                                     State, AssignedTo, WorkItemType, AreaPath,
                                     IterationPath, Priority, Severity, Tags,
                                     CreatedDate, ChangedDate, CreatedBy, ChangedBy
                                   Default: ["State", "AssignedTo", "WorkItemType"]

    Returns:
        dict with structure:
        {
            "status":       "success" | "error",
            "query_id":     str,
            "total_items":  int,
            "summary": {
                "<field_label>": {
                    "<value>": int,   (count per distinct value)
                    ...
                },
                ...
            },
            "message": str
        }
    """
    try:
        org_url = os.getenv("AZURE_ORG_URL", "").rstrip("/")
        project = os.getenv("AZURE_PROJECT")

        # ── Resolve aliases ───────────────────────────────────────────────────
        default_group = ["State", "AssignedTo", "WorkItemType"]
        raw_fields = group_by if group_by else default_group
        resolved: Dict[str, str] = {}  # label → reference name
        for f in raw_fields:
            ref = _FIELD_MAP.get(f, f)
            resolved[f] = ref

        # Always fetch System.Id so the batch call works even if not in group_by.
        fetch_fields = list({"System.Id"} | set(resolved.values()))

        # ── Fetch the saved query's WIQL then execute it ──────────────────────
        wiql = _get_query_wiql(org_url, project, query_id_or_path)
        if not wiql:
            result: Dict[str, Any] = {
                "status": "error",
                "error_type": "api",
                "error": "[get_query_summary] Query returned empty WIQL.",
            }
            return result

        item_ids = _run_wiql(org_url, project, wiql)
        total = len(item_ids)

        if total == 0:
            result = {
                "status": "success",
                "query_id": query_id_or_path,
                "total_items": 0,
                "summary": {},
                "message": "Query returned 0 work items.",
            }
            return result

        # ── Batch-fetch work items ────────────────────────────────────────────
        work_items = _fetch_work_items(org_url, project, item_ids, fetch_fields)

        # ── Aggregate counts per field ────────────────────────────────────────
        summary: Dict[str, Dict[str, int]] = {}
        for label, ref in resolved.items():
            counts: Dict[str, int] = {}
            for wi in work_items:
                raw_val = wi.get("fields", {}).get(ref)

                # Normalise the value to a readable string.
                if raw_val is None:
                    val = "(not set)"
                elif isinstance(raw_val, dict):
                    # Identity fields return {"displayName": ..., "uniqueName": ...}
                    val = raw_val.get("displayName") or raw_val.get("uniqueName") or str(raw_val)
                elif ref in _DATE_FIELDS and isinstance(raw_val, str):
                    # Truncate timestamps to date only for readability.
                    val = raw_val[:10]
                else:
                    val = str(raw_val).strip() or "(empty)"

                counts[val] = counts.get(val, 0) + 1

            # Sort by count descending so the most common value is first.
            summary[label] = dict(sorted(counts.items(), key=lambda x: -x[1]))

        result = {
            "status": "success",
            "query_id": query_id_or_path,
            "total_items": total,
            "summary": summary,
            "message": (
                f"Summary of {total} work item(s) across "
                f"{len(resolved)} field(s)."
            ),
        }
        return result

    except Exception as e:
        error_result = handle_error(e, "get_query_summary")
        return error_result


# ─────────────────────────────────────────────────────────────────────────────
# TEST SUITE RESULTS & OUTCOMES
# ─────────────────────────────────────────────────────────────────────────────

def get_test_outcome_summary(test_suite_id: int, test_plan_id: int = None) -> dict:
    """
    Retrieves aggregated test outcomes from a test suite's Execute page.
    
    Fetches the final result of each test case in the test suite
    and returns comprehensive statistics. This data is equivalent to 
    what's displayed on the Test Plan > Execute page for the suite.
    
    Args:
        test_suite_id (int): The test suite ID
        test_plan_id (int, optional): The test plan ID (required for proper context)
    
    Returns:
        dict with structure:
        {
            "status": "success" | "error",
            "test_suite_id": int,
            "test_plan_id": int,
            "total_test_cases": int,
            "statistics": {
                "passed": int,
                "failed": int,
                "not_executed": int,
                "blocked": int,
                "in_progress": int,
                "paused": int,
                "timeout": int,
                "warning": int,
                "aborted": int,
                "not_applicable": int
            },
            "pass_rate": str (percentage),
            "fail_rate": str (percentage),
            "execution_rate": str (percentage),
            "outcomes_summary": {
                "Passed": int,
                "Failed": int,
                "Not Executed": int,
                "Blocked": int,
                "In Progress": int,
                "Paused": int,
                "Timeout": int,
                "Warning": int,
                "Aborted": int,
                "Not Applicable": int
            },
            "by_priority": {
                "Priority 0": int,
                "Priority 1": int,
                "Priority 2": int,
                "Priority 3": int
            },
            "message": str
        }
    """
    try:
        org_url = os.getenv("AZURE_ORG_URL", "").rstrip("/")
        project = os.getenv("AZURE_PROJECT")
        
        # ── Fetch test points for the suite (Execute page data) ────────────────
        # Test points contain the latest outcome for each test case in a suite.
        # Paginated via $skip/$top so suites larger than one page are not
        # silently truncated.
        if test_plan_id:
            base_points_url = (
                f"{org_url}/{project}/_apis/test/plans/{test_plan_id}/suites/{test_suite_id}/points"
            )
        else:
            base_points_url = (
                f"{org_url}/{project}/_apis/test/suites/{test_suite_id}/points"
            )

        test_points = []
        skip = 0
        page_size = 1000
        while True:
            test_points_url = (
                f"{base_points_url}?api-version=7.1&$top={page_size}&$skip={skip}"
            )
            points_resp = requests.get(test_points_url, headers=_auth_headers(), timeout=60)

            if points_resp.status_code != 200:
                try:
                    msg = points_resp.json().get("message", points_resp.text)
                except ValueError:
                    msg = points_resp.text or f"HTTP {points_resp.status_code}"
                error_result: Dict[str, Any] = {
                    "status": "error",
                    "error_type": "api",
                    "http_status": points_resp.status_code,
                    "error": f"[get_test_outcome_summary] Failed to fetch test points: {msg}",
                }
                return error_result

            page = points_resp.json().get("value", [])
            test_points.extend(page)
            if len(page) < page_size:
                break
            skip += page_size
        
        if not test_points:
            result: Dict[str, Any] = {
                "status": "success",
                "test_suite_id": test_suite_id,
                "test_plan_id": test_plan_id,
                "total_test_cases": 0,
                "statistics": {
                    "passed": 0,
                    "failed": 0,
                    "not_executed": 0,
                    "blocked": 0,
                    "in_progress": 0,
                    "paused": 0,
                    "timeout": 0,
                    "warning": 0,
                    "aborted": 0,
                    "not_applicable": 0
                },
                "pass_rate": "0%",
                "fail_rate": "0%",
                "execution_rate": "0%",
                "outcomes_summary": {},
                "by_priority": {},
                "message": f"No test cases found in test suite {test_suite_id}."
            }
            return result
        
        # ── Aggregate test outcomes ──────────────────────────────────────────
        total_test_cases = len(test_points)
        outcomes_count: Dict[str, int] = {
            "Passed": 0,
            "Failed": 0,
            "Not Executed": 0,
            "Blocked": 0,
            "In Progress": 0,
            "Paused": 0,
            "Timeout": 0,
            "Warning": 0,
            "Aborted": 0,
            "Not Applicable": 0
        }
        priority_counts: Dict[str, int] = {}
        
        # Map Azure DevOps API outcome enum values → display labels
        _outcome_map = {
            "Passed":        "Passed",
            "Failed":        "Failed",
            "Blocked":       "Blocked",
            "NotApplicable": "Not Applicable",
            "Paused":        "Paused",
            "InProgress":    "In Progress",
            "Timeout":       "Timeout",
            "Warning":       "Warning",
            "Aborted":       "Aborted",
            "Error":         "Failed",
            "Inconclusive":  "Not Executed",
            "None":          "Not Executed",
            "Unspecified":   "Not Executed",
            "MaxValue":      "Not Executed",
        }

        for test_point in test_points:
            # Read outcome directly from the test point object
            raw_outcome = test_point.get("outcome", "Unspecified") or "Unspecified"
            outcome = _outcome_map.get(raw_outcome, "Not Executed")
            
            outcomes_count[outcome] = outcomes_count.get(outcome, 0) + 1
            
            # Get priority from test case
            test_case = test_point.get("testCase", {})
            priority = test_case.get("priorityNumber", 0)
            priority_key = f"Priority {priority}"
            priority_counts[priority_key] = priority_counts.get(priority_key, 0) + 1
        
        # ── Calculate statistics ─────────────────────────────────────────────
        passed = outcomes_count.get("Passed", 0)
        failed = outcomes_count.get("Failed", 0)
        not_executed = outcomes_count.get("Not Executed", 0)
        blocked = outcomes_count.get("Blocked", 0)
        in_progress = outcomes_count.get("In Progress", 0)
        paused = outcomes_count.get("Paused", 0)
        timeout = outcomes_count.get("Timeout", 0)
        warning = outcomes_count.get("Warning", 0)
        aborted = outcomes_count.get("Aborted", 0)
        not_applicable = outcomes_count.get("Not Applicable", 0)
        
        # Executed = all test cases that have a result (not "Not Executed")
        executed = total_test_cases - not_executed
        
        pass_rate = f"{(passed / total_test_cases * 100):.1f}%" if total_test_cases > 0 else "0%"
        fail_rate = f"{(failed / total_test_cases * 100):.1f}%" if total_test_cases > 0 else "0%"
        execution_rate = f"{(executed / total_test_cases * 100):.1f}%" if total_test_cases > 0 else "0%"
        
        result = {
            "status": "success",
            "test_suite_id": test_suite_id,
            "test_plan_id": test_plan_id,
            "total_test_cases": total_test_cases,
            "statistics": {
                "passed": passed,
                "failed": failed,
                "not_executed": not_executed,
                "blocked": blocked,
                "in_progress": in_progress,
                "paused": paused,
                "timeout": timeout,
                "warning": warning,
                "aborted": aborted,
                "not_applicable": not_applicable
            },
            "pass_rate": pass_rate,
            "fail_rate": fail_rate,
            "execution_rate": execution_rate,
            "outcomes_summary": dict(sorted(
                outcomes_count.items(),
                key=lambda x: -x[1]
            )),
            "by_priority": dict(sorted(
                priority_counts.items(),
                key=lambda x: int(x[0].split()[-1]) if x[0].split()[-1].isdigit() else 0
            )) if priority_counts else {},
            "message": (
                f"Test outcomes summary for suite {test_suite_id}: "
                f"{total_test_cases} total test cases. "
                f"Passed: {passed}, Failed: {failed}, Not Executed: {not_executed}. "
                f"Pass rate: {pass_rate}, Execution rate: {execution_rate}."
            )
        }
        
        return result
    
    except Exception as e:
        error_result = handle_error(e, "get_test_outcome_summary")
        return error_result


# ─────────────────────────────────────────────────────────────────────────────
# TEST RUN RESULTS & OUTCOMES
# ─────────────────────────────────────────────────────────────────────────────

def get_test_run_outcome_summary(test_run_id: int) -> dict:
    """
    Retrieves aggregated test outcomes from a specific Azure DevOps Test Run.

    Fetches all test results within the given test run and returns
    comprehensive statistics, mirroring what Azure DevOps shows on the
    Test Run results page.

    Args:
        test_run_id (int): The test run ID to query.

    Returns:
        dict with structure:
        {
            "status": "success" | "error",
            "test_run_id": int,
            "run_name": str,
            "total_results": int,
            "statistics": {
                "passed": int,
                "failed": int,
                "not_executed": int,
                "blocked": int,
                "in_progress": int,
                "paused": int,
                "timeout": int,
                "warning": int,
                "aborted": int,
                "not_applicable": int
            },
            "pass_rate": str,
            "fail_rate": str,
            "execution_rate": str,
            "outcomes_summary": {
                "Passed": int,
                "Failed": int,
                ...
            },
            "message": str
        }
    """
    try:
        org_url = os.getenv("AZURE_ORG_URL", "").rstrip("/")
        project = os.getenv("AZURE_PROJECT")

        # ── Fetch run metadata ────────────────────────────────────────────────
        run_url = (
            f"{org_url}/{project}/_apis/test/runs/{test_run_id}"
            f"?api-version=7.1"
        )
        run_resp = requests.get(run_url, headers=_auth_headers(), timeout=30)
        if run_resp.status_code != 200:
            try:
                msg = run_resp.json().get("message", run_resp.text)
            except ValueError:
                msg = run_resp.text or f"HTTP {run_resp.status_code}"
            return {
                "status": "error",
                "error_type": "api",
                "http_status": run_resp.status_code,
                "error": f"[get_test_run_outcome_summary] Failed to fetch test run: {msg}",
            }

        run_data = run_resp.json()
        run_name = run_data.get("name", f"Run {test_run_id}")

        # ── Fetch all test results for this run (page in batches of 1000) ─────
        _outcome_map = {
            "Passed":        "Passed",
            "Failed":        "Failed",
            "Blocked":       "Blocked",
            "NotApplicable": "Not Applicable",
            "Paused":        "Paused",
            "InProgress":    "In Progress",
            "Timeout":       "Timeout",
            "Warning":       "Warning",
            "Aborted":       "Aborted",
            "Error":         "Failed",
            "Inconclusive":  "Not Executed",
            "None":          "Not Executed",
            "Unspecified":   "Not Executed",
            "MaxValue":      "Not Executed",
        }

        outcomes_count: Dict[str, int] = {
            "Passed": 0,
            "Failed": 0,
            "Not Executed": 0,
            "Blocked": 0,
            "In Progress": 0,
            "Paused": 0,
            "Timeout": 0,
            "Warning": 0,
            "Aborted": 0,
            "Not Applicable": 0,
        }

        skip = 0
        batch_size = 1000
        total_results = 0

        while True:
            results_url = (
                f"{org_url}/{project}/_apis/test/runs/{test_run_id}/results"
                f"?api-version=7.1&$top={batch_size}&$skip={skip}"
            )
            results_resp = requests.get(results_url, headers=_auth_headers(), timeout=60)

            if results_resp.status_code != 200:
                try:
                    msg = results_resp.json().get("message", results_resp.text)
                except ValueError:
                    msg = results_resp.text or f"HTTP {results_resp.status_code}"
                return {
                    "status": "error",
                    "error_type": "api",
                    "http_status": results_resp.status_code,
                    "error": f"[get_test_run_outcome_summary] Failed to fetch results: {msg}",
                }

            batch = results_resp.json().get("value", [])
            if not batch:
                break

            for item in batch:
                raw_outcome = item.get("outcome", "Unspecified") or "Unspecified"
                outcome = _outcome_map.get(raw_outcome, "Not Executed")
                outcomes_count[outcome] = outcomes_count.get(outcome, 0) + 1

            total_results += len(batch)
            if len(batch) < batch_size:
                break
            skip += batch_size

        if total_results == 0:
            return {
                "status": "success",
                "test_run_id": test_run_id,
                "run_name": run_name,
                "total_results": 0,
                "statistics": {k.lower().replace(" ", "_"): 0 for k in outcomes_count},
                "pass_rate": "0%",
                "fail_rate": "0%",
                "execution_rate": "0%",
                "outcomes_summary": {},
                "message": f"No test results found in test run {test_run_id}.",
            }

        # ── Calculate statistics ─────────────────────────────────────────────
        passed       = outcomes_count.get("Passed", 0)
        failed       = outcomes_count.get("Failed", 0)
        not_executed = outcomes_count.get("Not Executed", 0)
        executed     = total_results - not_executed

        pass_rate      = f"{(passed / total_results * 100):.1f}%"       if total_results > 0 else "0%"
        fail_rate      = f"{(failed / total_results * 100):.1f}%"       if total_results > 0 else "0%"
        execution_rate = f"{(executed / total_results * 100):.1f}%"     if total_results > 0 else "0%"

        result: Dict[str, Any] = {
            "status": "success",
            "test_run_id": test_run_id,
            "run_name": run_name,
            "total_results": total_results,
            "statistics": {
                "passed":         passed,
                "failed":         failed,
                "not_executed":   not_executed,
                "blocked":        outcomes_count.get("Blocked", 0),
                "in_progress":    outcomes_count.get("In Progress", 0),
                "paused":         outcomes_count.get("Paused", 0),
                "timeout":        outcomes_count.get("Timeout", 0),
                "warning":        outcomes_count.get("Warning", 0),
                "aborted":        outcomes_count.get("Aborted", 0),
                "not_applicable": outcomes_count.get("Not Applicable", 0),
            },
            "pass_rate":      pass_rate,
            "fail_rate":      fail_rate,
            "execution_rate": execution_rate,
            "outcomes_summary": dict(sorted(
                {k: v for k, v in outcomes_count.items() if v > 0}.items(),
                key=lambda x: -x[1]
            )),
            "message": (
                f"Test run '{run_name}' (ID {test_run_id}): "
                f"{total_results} total results. "
                f"Passed: {passed}, Failed: {failed}, Not Executed: {not_executed}. "
                f"Pass rate: {pass_rate}, Execution rate: {execution_rate}."
            ),
        }

        return result

    except Exception as e:
        error_result = handle_error(e, "get_test_run_outcome_summary")
        return error_result

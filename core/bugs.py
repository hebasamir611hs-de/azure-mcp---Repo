"""
core/bugs.py — Bug Reporting Engine: automated test failures → Azure DevOps Bugs.

Triggered after an automated test run (see .claude/skills/create-azure-bug). Every
failing test is eligible (automation-standards.md → "Bug Reporting on Failure").
No human confirmation gate on creation — duplicate filing is prevented instead by
find_existing_bug() before create_bug() is ever called.

All functions are plain — no @mcp.tool() decorators. Registration happens in server.py.

Credentials are loaded from .env (AZURE_PAT, AZURE_ORG_URL, AZURE_PROJECT).
"""

import os
import json
from base64 import b64encode
from datetime import datetime, timezone
from urllib.parse import quote
from typing import List, Optional

import requests
from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation

from core.utils import get_azure_client, handle_error
from core.reporting import ensure_bug_query_hierarchy


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS — severity mapping & carry-over tag taxonomy
# (see automation-standards.md → "Bug Reporting on Failure" for the contract)
# ─────────────────────────────────────────────────────────────────────────────

# QA Priority (1-4) → Azure Bug Severity. Mirrors the Allure severity mapping
# (P1->blocker ... P4->minor) already used for automated test reporting.
_SEVERITY_MAP = {
    1: "1 - Critical",
    2: "2 - High",
    3: "3 - Medium",
    4: "4 - Low",
}

# Service + Platform tag values (woqod-standards.md taxonomy) carried over
# verbatim from the Test Case onto the Bug so it's filterable the same way.
_CARRY_OVER_TAGS = {
    "TAG", "FAHES", "BOOK", "QJET", "CMS",
    "IOS", "Android", "Web", "Control_Panel",
}

# Bug states considered "open" for dedup purposes.
_CLOSED_STATES = {"Closed", "Removed"}


# ─────────────────────────────────────────────────────────────────────────────
# AUTH HELPER (raw REST — used for WIQL search + attachment upload, which the
# azure-devops SDK does not expose; mirrors the pattern in core/reporting.py)
# ─────────────────────────────────────────────────────────────────────────────

def _auth_headers() -> dict:
    pat = os.getenv("AZURE_PAT", "").strip()
    token = b64encode(f":{pat}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}


def _run_wiql(org_url: str, project: str, wiql: str) -> list:
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
    if not ids:
        return []
    fields_param = ",".join(fields)
    ids_param = ",".join(str(x) for x in ids)
    url = (
        f"{org_url}/{project}/_apis/wit/workitems"
        f"?ids={ids_param}&fields={fields_param}&api-version=7.1"
    )
    resp = requests.get(url, headers=_auth_headers(), timeout=60)
    if resp.status_code == 200:
        return resp.json().get("value", [])
    return []


def _upload_attachment(org_url: str, project: str, file_path: Optional[str]) -> Optional[dict]:
    """Uploads a local file (e.g. failure screenshot) to Azure DevOps. Returns
    {"url", "id"} on success, or None if no file was given / upload failed."""
    if not file_path or not os.path.isfile(file_path):
        return None
    file_name = os.path.basename(file_path)
    url = (
        f"{org_url}/{project}/_apis/wit/attachments"
        f"?fileName={quote(file_name)}&api-version=7.1"
    )
    pat = os.getenv("AZURE_PAT", "").strip()
    token = b64encode(f":{pat}".encode("utf-8")).decode("ascii")
    headers = {"Authorization": f"Basic {token}", "Content-Type": "application/octet-stream"}
    with open(file_path, "rb") as f:
        resp = requests.post(url, data=f.read(), headers=headers, timeout=60)
    if resp.status_code in (200, 201):
        result = resp.json()
        return {"url": result.get("url"), "id": result.get("id")}
    return None


def _build_repro_steps_html(
    test_name: str,
    repro_steps: Optional[List[str]],
    expected_result: str,
    actual_result: str,
    run_url: str,
) -> str:
    if repro_steps:
        steps_html = "".join(f"<li>{s}</li>" for s in repro_steps)
    else:
        steps_html = (
            f"<li>Run the automated test <code>{test_name}</code> "
            "(see the linked Test Case for the manual steps).</li>"
        )
    run_line = f'<div><b>Automation Run:</b> <a href="{run_url}">{run_url}</a></div>' if run_url else ""
    return (
        f"<div><b>Failing Test:</b> {test_name}</div>"
        f"<div><b>Steps to Reproduce:</b></div><ol>{steps_html}</ol>"
        f"<div><b>Expected Result:</b> {expected_result or 'Test should pass.'}</div>"
        f"<div><b>Actual Result:</b> {actual_result}</div>"
        f"{run_line}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# DEDUP CHECK
# ─────────────────────────────────────────────────────────────────────────────

def find_existing_bug(test_case_id: int) -> str:
    """
    Checks whether an open Bug already exists for a given Test Case.

    Searches for a Bug tagged 'TC:<test_case_id>' (the deterministic link tag
    every bug created by create_bug() carries) whose state is not Closed/Removed.
    Call this BEFORE create_bug() to avoid filing duplicate bugs for the same
    recurring failure — if a match is found, use add_bug_occurrence() instead.

    Args:
        test_case_id (int): The Azure DevOps Test Case work item ID.

    Returns:
        {
            "status": "success" | "error",
            "exists": bool,
            "test_case_id": int,
            "bug_id": int | None,
            "title": str | None,
            "state": str | None,
            "message": str
        }
    """
    try:
        org_url = os.getenv("AZURE_ORG_URL", "").rstrip("/")
        project = os.getenv("AZURE_PROJECT")

        wiql = (
            "SELECT [System.Id] FROM WorkItems "
            f"WHERE [System.WorkItemType] = 'Bug' AND [System.Tags] CONTAINS 'TC:{test_case_id}' "
            "AND [System.State] <> 'Closed' AND [System.State] <> 'Removed'"
        )
        ids = _run_wiql(org_url, project, wiql)

        if not ids:
            return json.dumps({
                "status": "success",
                "exists": False,
                "test_case_id": test_case_id,
                "bug_id": None,
                "title": None,
                "state": None,
                "message": f"No open bug found for test case {test_case_id}.",
            }, indent=2)

        items = _fetch_work_items(org_url, project, ids, ["System.Id", "System.Title", "System.State"])
        item = items[0]
        return json.dumps({
            "status": "success",
            "exists": True,
            "test_case_id": test_case_id,
            "bug_id": item["id"],
            "title": item["fields"].get("System.Title"),
            "state": item["fields"].get("System.State"),
            "message": f"Open bug #{item['id']} already exists for test case {test_case_id}.",
        }, indent=2)

    except Exception as e:
        return json.dumps(handle_error(e, "find_existing_bug"), indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# BUG CREATION
# ─────────────────────────────────────────────────────────────────────────────

def create_bug(
    test_case_id: int,
    test_name: str,
    error_message: str,
    expected_result: str = "",
    actual_result: str = "",
    repro_steps: Optional[List[str]] = None,
    priority: int = 3,
    screenshot_path: Optional[str] = None,
    run_url: str = "",
) -> str:
    """
    Creates a Bug work item from an automated test failure and links it to the
    originating Test Case. Call find_existing_bug() first — do not call this if
    an open bug already exists for the same test_case_id (use add_bug_occurrence
    instead).

    Inherits IterationPath and AreaPath from the Test Case (a Bug has no direct
    "Sprint" link in Azure DevOps — Sprint is the IterationPath field, not a
    linkable work item). Links to the Test Case via the same TestedBy-Reverse
    relation already used elsewhere in this codebase for Test Case <-> PBI links.

    Args:
        test_case_id (int): Azure DevOps Test Case work item ID this failure traces to.
        test_name (str): The automated test's name/identifier (e.g. pytest node id).
        error_message (str): The raw failure/assertion message.
        expected_result (str, optional): What should have happened.
        actual_result (str, optional): What actually happened (defaults to error_message).
        repro_steps (list[str], optional): Steps to reproduce. Defaults to a generic
            "run the automated test" step referencing the Test Case.
        priority (int): 1=Critical ... 4=Low. Maps to Azure Severity (default 3).
        screenshot_path (str, optional): Local path to a failure screenshot to attach.
        run_url (str, optional): Link to the automation run / Allure report.

    Returns:
        {status, bug_id, url, test_case_id, title, severity, priority,
         tags_applied, tags, screenshot_attached, message}
    """
    try:
        client = get_azure_client()
        project = os.getenv("AZURE_PROJECT")
        org_url = os.getenv("AZURE_ORG_URL", "").rstrip("/")

        test_case = client.get_work_item(test_case_id, expand="Relations")
        iteration = test_case.fields.get("System.IterationPath")
        area = test_case.fields.get("System.AreaPath")
        tc_tags = test_case.fields.get("System.Tags", "") or ""

        # The Test Case <-> PBI link is the same TestedBy-Reverse relation used at
        # injection time (see engines.py). Walk it backwards to find the backlog ID
        # so every Bug title is traceable to its PBI at a glance.
        backlog_id = None
        for rel in (test_case.relations or []):
            if rel.rel == "Microsoft.VSTS.Common.TestedBy-Reverse":
                backlog_id = rel.url.rstrip("/").split("/")[-1]
                break

        severity = _SEVERITY_MAP.get(priority, "3 - Medium")
        title = f"Automated test failure: {test_name} — {error_message[:80].strip()}"
        if backlog_id:
            title = f"[{backlog_id}] {title}"

        repro_html = _build_repro_steps_html(
            test_name, repro_steps, expected_result, actual_result or error_message, run_url
        )

        carried_tags = [t.strip() for t in tc_tags.split(";") if t.strip() in _CARRY_OVER_TAGS]
        pbi_tag = [f"PBI:{backlog_id}"] if backlog_id else []
        tag_parts = ["Automated", f"TC:{test_case_id}"] + pbi_tag + carried_tags
        tags = "; ".join(dict.fromkeys(tag_parts))

        patch_doc = [
            JsonPatchOperation(op="add", path="/fields/System.Title", value=title),
            JsonPatchOperation(op="add", path="/fields/Microsoft.VSTS.TCM.ReproSteps", value=repro_html),
            JsonPatchOperation(op="add", path="/fields/Microsoft.VSTS.Common.Severity", value=severity),
            JsonPatchOperation(op="add", path="/fields/Microsoft.VSTS.Common.Priority", value=priority),
            JsonPatchOperation(op="add", path="/fields/System.Tags", value=tags),
            JsonPatchOperation(op="add", path="/relations/-", value={
                "rel": "Microsoft.VSTS.Common.TestedBy-Reverse",
                "url": f"{org_url}/_apis/wit/workItems/{test_case_id}",
            }),
        ]
        if iteration:
            patch_doc.append(JsonPatchOperation(op="add", path="/fields/System.IterationPath", value=iteration))
        if area:
            patch_doc.append(JsonPatchOperation(op="add", path="/fields/System.AreaPath", value=area))

        attachment = _upload_attachment(org_url, project, screenshot_path)
        if attachment:
            patch_doc.append(JsonPatchOperation(op="add", path="/relations/-", value={
                "rel": "AttachedFile",
                "url": attachment["url"],
                "attributes": {"comment": "Screenshot captured on failure"},
            }))

        tags_applied = True
        try:
            new_bug = client.create_work_item(patch_doc, project, "Bug")
        except Exception as e:
            # TF401289 = tags permission error — retry without tags as graceful degradation
            if "tags" in str(e).lower() or "TF401289" in str(e):
                patch_doc = [op for op in patch_doc if op.path != "/fields/System.Tags"]
                new_bug = client.create_work_item(patch_doc, project, "Bug")
                tags = ""
                tags_applied = False
            else:
                raise

        query_provisioning = {"status": "skipped", "reason": "no backlog link found for this test case"}
        if backlog_id:
            try:
                backlog_item = client.get_work_item(int(backlog_id))
                feature_name = backlog_item.fields.get("System.Title") or f"PBI {backlog_id}"
                sprint_name = iteration.split("\\")[-1] if iteration else "Unassigned"
                query_provisioning = json.loads(
                    ensure_bug_query_hierarchy(sprint_name, feature_name, int(backlog_id))
                )
            except Exception as e:
                query_provisioning = {"status": "error", "error": str(e)}

        return json.dumps({
            "status": "created",
            "bug_id": new_bug.id,
            "url": f"{org_url}/{project}/_workitems/edit/{new_bug.id}",
            "test_case_id": test_case_id,
            "title": title,
            "severity": severity,
            "priority": priority,
            "tags_applied": tags_applied,
            "tags": tags.split("; ") if tags else [],
            "screenshot_attached": attachment is not None,
            "query_provisioning": query_provisioning,
            "message": f"Bug #{new_bug.id} created and linked to test case {test_case_id}.",
        }, indent=2)

    except Exception as e:
        return json.dumps(handle_error(e, "create_bug"), indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# REPEAT FAILURE — UPDATE EXISTING BUG
# ─────────────────────────────────────────────────────────────────────────────

def add_bug_occurrence(bug_id: int, error_message: str, run_url: str = "") -> str:
    """
    Appends a new-occurrence comment to an already-open Bug (found via
    find_existing_bug) instead of filing a duplicate. If the bug's current
    state is "Resolved", reopens it to "Active" — a fresh automated failure on
    the same Test Case is regression evidence, not noise.

    Args:
        bug_id (int): The existing Bug's work item ID.
        error_message (str): The new failure's error/assertion message.
        run_url (str, optional): Link to the automation run / Allure report.

    Returns:
        {status, bug_id, reopened, message}
    """
    try:
        client = get_azure_client()
        project = os.getenv("AZURE_PROJECT")

        bug = client.get_work_item(bug_id)
        current_state = bug.fields.get("System.State")

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        comment_lines = [f"Reproduced again on {timestamp}.", f"Error: {error_message}"]
        if run_url:
            comment_lines.append(f"Run: {run_url}")
        comment = "<br/>".join(comment_lines)

        patch_doc = [
            JsonPatchOperation(op="add", path="/fields/System.History", value=comment),
        ]
        reopened = current_state == "Resolved"
        if reopened:
            patch_doc.append(JsonPatchOperation(op="add", path="/fields/System.State", value="Active"))

        client.update_work_item(patch_doc, bug_id, project=project)

        return json.dumps({
            "status": "updated",
            "bug_id": bug_id,
            "reopened": reopened,
            "message": (
                f"Bug #{bug_id} updated with new occurrence."
                + (" Reopened from Resolved." if reopened else "")
            ),
        }, indent=2)

    except Exception as e:
        return json.dumps(handle_error(e, "add_bug_occurrence"), indent=2)

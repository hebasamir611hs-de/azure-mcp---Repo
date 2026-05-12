"""
core/discovery.py — Skill 0: PBI Deduplication, Skill 1: Smart PBI Discovery.

Also contains legacy get_story_for_analysis for backward compatibility.
All functions are plain — no @mcp.tool() decorators. Registration happens in server.py.
"""

import os
import re

from azure.devops.v7_1.work_item_tracking.models import Wiql

from core.utils import (
    get_azure_client,
    handle_error,
    is_arabic,
    sanitize_wiql_string,
)


# ─────────────────────────────────────────────────────────────────────────────
# LEGACY
# ─────────────────────────────────────────────────────────────────────────────

def get_story_for_analysis(story_id: int) -> dict:
    """
    Legacy helper: Fetches a single work item's title and acceptance criteria.
    Maintained for backward compatibility with existing workflows.

    Args:
        story_id: Azure work item ID

    Returns:
        {"title": str, "ac": str}
    """
    try:
        client = get_azure_client()
        item = client.get_work_item(story_id)
        return {
            "title": item.fields.get('System.Title'),
            "ac": item.fields.get('Microsoft.VSTS.Common.AcceptanceCriteria', 'No AC')
        }
    except Exception as e:
        return handle_error(e, "get_story_for_analysis")


# ─────────────────────────────────────────────────────────────────────────────
# SKILL 0: PBI DEDUPLICATION
# ─────────────────────────────────────────────────────────────────────────────

def check_pbi_duplicates(iteration_path: str) -> dict:
    """
    SKILL 0: PBI Deduplication & Validation

    ⚠️ STOP GATE — Must be the FIRST skill called in any workflow.
    Scans all PBIs in the sprint and flags potential duplicates based on
    matching Description, Acceptance Criteria, or content overlap.

    Duplicate Detection Rules:
    1. Exact match on cleaned Description text
    2. Exact match on cleaned Acceptance Criteria text
    3. Subset match: one PBI's content is fully contained within another's

    Returns:
        {
            "status": "clear" | "duplicates_detected",
            "total_pbis": int,
            "duplicate_groups": [...],
            "safe_to_proceed": bool,
            "user_action_required": str
        }
    """
    try:
        client = get_azure_client()
        project = os.getenv("AZURE_PROJECT")
        safe_iter = sanitize_wiql_string(iteration_path)
        safe_proj = sanitize_wiql_string(project)

        query = f"""
            SELECT [System.Id], [System.Title], [Microsoft.VSTS.Common.AcceptanceCriteria],
                   [System.Description]
            FROM WorkItems
            WHERE [System.WorkItemType] = 'Product Backlog Item'
              AND [System.IterationPath] = '{safe_iter}'
              AND [System.TeamProject] = '{safe_proj}'
            ORDER BY [System.Id] ASC
        """
        result = client.query_by_wiql(Wiql(query=query))

        if not result.work_items:
            return {
                "status": "clear",
                "total_pbis": 0,
                "duplicate_groups": [],
                "safe_to_proceed": True,
                "message": "No PBIs found in this sprint."
            }

        ids = [item.id for item in result.work_items]
        work_items = client.get_work_items(ids=ids, expand="All")

        def clean_text(text):
            if not text:
                return ""
            text = re.sub(r'<[^>]+>', ' ', text)
            return re.sub(r'\s+', ' ', text).strip().lower()

        pbi_list = [
            {
                "id": item.id,
                "title": item.fields.get('System.Title', ''),
                "ac_clean": clean_text(item.fields.get('Microsoft.VSTS.Common.AcceptanceCriteria', '')),
                "desc_clean": clean_text(item.fields.get('System.Description', ''))
            }
            for item in work_items
        ]

        duplicate_groups = []
        processed_ids = set()
        group_id = 1

        for i in range(len(pbi_list)):
            if pbi_list[i]["id"] in processed_ids:
                continue
            conflicts = []
            conflict_reasons = []
            conflict_fields = []

            for j in range(i + 1, len(pbi_list)):
                if pbi_list[j]["id"] in processed_ids:
                    continue

                reasons = []
                fields = []

                d_i, d_j = pbi_list[i]["desc_clean"], pbi_list[j]["desc_clean"]
                if d_i and d_j:
                    if d_i == d_j:
                        reasons.append("Identical Description")
                        fields.append("description")
                    elif len(d_i) > 30 and (d_i in d_j or d_j in d_i):
                        reasons.append("Description subset match")
                        fields.append("description")

                a_i, a_j = pbi_list[i]["ac_clean"], pbi_list[j]["ac_clean"]
                if a_i and a_j:
                    if a_i == a_j:
                        reasons.append("Identical Acceptance Criteria")
                        fields.append("ac")
                    elif len(a_i) > 30 and (a_i in a_j or a_j in a_i):
                        reasons.append("AC subset match")
                        fields.append("ac")

                if reasons:
                    conflicts.append(pbi_list[j])
                    conflict_reasons.extend(reasons)
                    conflict_fields.extend(fields)
                    processed_ids.add(pbi_list[j]["id"])

            if conflicts:
                unique_fields = list(set(conflict_fields))
                duplicate_groups.append({
                    "group_id": group_id,
                    "reason": "; ".join(set(conflict_reasons)),
                    "pbi_ids": [pbi_list[i]["id"]] + [c["id"] for c in conflicts],
                    "titles": [pbi_list[i]["title"]] + [c["title"] for c in conflicts],
                    "conflicting_field": "both" if len(unique_fields) > 1 else (unique_fields[0] if unique_fields else "unknown")
                })
                processed_ids.add(pbi_list[i]["id"])
                group_id += 1

        if duplicate_groups:
            return {
                "status": "duplicates_detected",
                "total_pbis": len(pbi_list),
                "duplicate_groups": duplicate_groups,
                "safe_to_proceed": False,
                "user_action_required": (
                    "⚠️ Potential duplicate PBIs detected. "
                    "For each group above: should I process ALL IDs, or only ONE? "
                    "If one — which ID should I proceed with? "
                    "Do NOT proceed with TC generation until you confirm."
                )
            }

        return {
            "status": "clear",
            "total_pbis": len(pbi_list),
            "duplicate_groups": [],
            "safe_to_proceed": True,
            "message": f"All {len(pbi_list)} PBIs are unique. Safe to proceed."
        }

    except Exception as e:
        return handle_error(e, "check_pbi_duplicates")


# ─────────────────────────────────────────────────────────────────────────────
# SKILL 1: SMART PBI DISCOVERY
# ─────────────────────────────────────────────────────────────────────────────

def get_pbis_from_sprint(iteration_path: str) -> dict:
    """
    SKILL 1: Smart PBI Discovery with Validation

    Fetches all PBIs from a sprint, validates them for TC readiness,
    and auto-detects language per PBI.

    Validation: skips PBIs with empty Description or missing Acceptance Criteria.

    Returns:
        {
            "count": int,
            "valid_count": int,
            "skipped_count": int,
            "arabic_count": int,
            "english_count": int,
            "pbis": [{id, title, ac, description, language, is_valid, validation_reason}],
            "skipped_pbis": [...]
        }
    """
    try:
        client = get_azure_client()
        project = os.getenv("AZURE_PROJECT")
        safe_iter = sanitize_wiql_string(iteration_path)
        safe_proj = sanitize_wiql_string(project)

        query = f"""
            SELECT [System.Id], [System.Title], [Microsoft.VSTS.Common.AcceptanceCriteria],
                   [System.Description]
            FROM WorkItems
            WHERE [System.WorkItemType] = 'Product Backlog Item'
              AND [System.IterationPath] = '{safe_iter}'
              AND [System.TeamProject] = '{safe_proj}'
            ORDER BY [System.Id] ASC
        """
        result = client.query_by_wiql(Wiql(query=query))

        if not result.work_items:
            return {
                "count": 0, "valid_count": 0, "skipped_count": 0,
                "pbis": [], "skipped_pbis": [],
                "message": "No PBIs found in this sprint."
            }

        ids = [item.id for item in result.work_items]
        work_items = client.get_work_items(ids=ids, expand="All")

        pbis, skipped_pbis = [], []
        arabic_count = english_count = 0

        for item in work_items:
            title = item.fields.get('System.Title', '')
            ac = item.fields.get('Microsoft.VSTS.Common.AcceptanceCriteria', '')
            description = item.fields.get('System.Description', '')

            detected_lang = "ar" if is_arabic(title) or is_arabic(ac) else "en"

            is_valid = True
            validation_reason = ""

            if not description or not description.strip():
                is_valid = False
                validation_reason = "Missing or empty Description field"
            elif not ac or not ac.strip():
                is_valid = False
                validation_reason = "Missing or empty Acceptance Criteria"

            pbi_data = {
                "id": item.id,
                "title": title,
                "ac": ac if ac else "[No AC provided]",
                "description": description if description else "[No Description provided]",
                "language": detected_lang,
                "is_valid": is_valid,
                "validation_reason": validation_reason if not is_valid else ""
            }

            if is_valid:
                pbis.append(pbi_data)
                arabic_count += 1 if detected_lang == "ar" else 0
                english_count += 1 if detected_lang == "en" else 0
            else:
                skipped_pbis.append(pbi_data)

        return {
            "count": len(work_items),
            "valid_count": len(pbis),
            "skipped_count": len(skipped_pbis),
            "arabic_count": arabic_count,
            "english_count": english_count,
            "pbis": pbis,
            "skipped_pbis": skipped_pbis
        }

    except Exception as e:
        return handle_error(e, "get_pbis_from_sprint")

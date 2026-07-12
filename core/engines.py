"""
core/engines.py — TC Creation Engines: Skills 3, 4, 9, and legacy add_full_test_case.

Bilingual Logic Router is embedded here (Skills 3 & 4 share the same creation
pipeline; language determines title prefix and tag language code only).

All functions are plain — no @mcp.tool() decorators. Registration happens in server.py.
"""

import os

from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation

from core.utils import (
    get_azure_client,
    handle_error,
    format_azure_steps,
    validate_tc_attributes,
    assess_priority,
    determine_execution_type,
    normalize_execution_type,
)


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL: SHARED TAGGING + CREATION HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _build_tags_string(extra_tags: list) -> str:
    """
    Unified tagging model: exactly ONE MCP provenance tag (Ai_MCP_Injected) plus
    the agent's decided tags passed through verbatim, deduped case-insensitively.
    """
    tag_parts = ["Ai_MCP_Injected"]
    seen = {t.lower() for t in tag_parts}
    for t in (extra_tags or []):
        t = (t or "").strip()
        if t and t.lower() not in seen:
            tag_parts.append(t)
            seen.add(t.lower())
    return "; ".join(tag_parts)


def _create_with_tag_fallback(client, project: str, patch_doc: list) -> tuple:
    """
    Creates the work item; on a tags-permission rejection (TF401289) retries
    once WITHOUT the System.Tags operation as graceful degradation.

    Returns: (work_item, tags_applied: bool)
    """
    try:
        return client.create_work_item(patch_doc, project, "Test Case"), True
    except Exception as e:
        if "tags" in str(e).lower() or "TF401289" in str(e):
            reduced = [op for op in patch_doc if op.path != "/fields/System.Tags"]
            return client.create_work_item(reduced, project, "Test Case"), False
        raise


# ─────────────────────────────────────────────────────────────────────────────
# LEGACY
# ─────────────────────────────────────────────────────────────────────────────

def add_full_test_case(parent_id: int, title: str, steps_list: list,
                       expected_list: list, priority: int = 2) -> dict:
    """
    DEPRECATED — Use create_english_test_case or create_arabic_test_case instead.
    Legacy TC creator: creates a basic test case without the six mandatory attributes.
    Maintained for backward compatibility only.
    """
    try:
        client = get_azure_client()
        project = os.getenv("AZURE_PROJECT")
        xml_steps = format_azure_steps(steps_list, expected_list)

        patch_doc = [
            JsonPatchOperation(op="add", path="/fields/System.Title", value=title),
            JsonPatchOperation(op="add", path="/fields/Microsoft.VSTS.TCM.Steps", value=xml_steps),
            JsonPatchOperation(op="add", path="/fields/Microsoft.VSTS.Common.Priority", value=priority),
            JsonPatchOperation(op="add", path="/relations/-", value={
                "rel": "Microsoft.VSTS.Common.TestedBy-Reverse",
                "url": f"{os.getenv('AZURE_ORG_URL')}/_apis/wit/workItems/{parent_id}"
            })
        ]
        new_tc = client.create_work_item(patch_doc, project, "Test Case")
        return {"status": "created", "test_case_id": new_tc.id}
    except Exception as e:
        return handle_error(e, "add_full_test_case")


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL: SHARED TC CREATION PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def _create_test_case(
    parent_id: int,
    title: str,
    description: str,
    steps_list: list,
    expected_list: list,
    test_type: str,
    scenario: str,
    priority: int,
    execution_type: str,
    impact_area: str,
    language: str,
    skill_name: str,
    extra_tags: list = None
) -> dict:
    """
    Internal pipeline shared by create_arabic_test_case and create_english_test_case.
    Validates, auto-assesses missing attributes, and creates the work item.

    extra_tags: optional list of WOQOD-layer tags (e.g. UAT, Regression, Smoke,
    platform/business keywords) merged into System.Tags alongside the auto
    dimension tags. Blank/duplicate entries are ignored.
    """
    try:
        execution_type = normalize_execution_type(execution_type)
        is_valid, error_msg = validate_tc_attributes(
            title, steps_list, expected_list, test_type, scenario,
            execution_type or "Automated", impact_area, language
        )
        if not is_valid:
            return {"error": error_msg}

        client = get_azure_client()

        parent = client.get_work_item(parent_id)
        project = parent.fields.get('System.TeamProject') or os.getenv("AZURE_PROJECT")
        parent_iteration = parent.fields.get('System.IterationPath')

        if priority == 0:
            parent_title = parent.fields.get('System.Title', '')
            parent_ac = parent.fields.get('Microsoft.VSTS.Common.AcceptanceCriteria', '')
            priority = assess_priority(parent_title, parent_ac, test_type, scenario)

        if not execution_type:
            execution_type = determine_execution_type(test_type, impact_area)

        xml_steps = format_azure_steps(steps_list, expected_list)
        lang_tag = language.upper()
        tag_parts = ["Automated-By-AI", test_type, scenario, execution_type, impact_area, lang_tag]
        if extra_tags:
            seen = {t.lower() for t in tag_parts}
            for t in extra_tags:
                t = (t or "").strip()
                if t and t.lower() not in seen:
                    tag_parts.append(t)
                    seen.add(t.lower())
        tags = "; ".join(tag_parts)
        # Unified tagging model: the MCP is a dumb transport. It applies exactly
        # ONE provenance tag (Ai_MCP_Injected) and passes through every tag the
        # agent decided (extra_tags) verbatim. All tag *judgement* — lifecycle,
        # service, platform, category, business — lives in the instruction files
        # and is the agent's call, never the MCP's. (See woqod-standards.md → Tag
        # Taxonomy.) test_type/scenario/execution_type/impact_area/language stay
        # as validated attributes but are no longer emitted as tags.
        tags = _build_tags_string(extra_tags)

        patch_doc = [
            JsonPatchOperation(op="add", path="/fields/System.Title", value=title),
            JsonPatchOperation(op="add", path="/fields/System.Description", value=description),
            JsonPatchOperation(op="add", path="/fields/Microsoft.VSTS.TCM.Steps", value=xml_steps),
            JsonPatchOperation(op="add", path="/fields/Microsoft.VSTS.Common.Priority", value=priority),
            JsonPatchOperation(op="add", path="/fields/System.Tags", value=tags),
            JsonPatchOperation(op="add", path="/fields/System.IterationPath", value=parent_iteration),
            JsonPatchOperation(op="add", path="/relations/-", value={
                "rel": "Microsoft.VSTS.Common.TestedBy-Reverse",
                "url": f"{os.getenv('AZURE_ORG_URL')}/_apis/wit/workItems/{parent_id}"
            })
        ]

        new_tc, tags_applied = _create_with_tag_fallback(client, project, patch_doc)
        if not tags_applied:
            tags = ""

        return {
            "status": "created",
            "tags_applied": tags_applied,
            "test_case_id": new_tc.id,
            "parent_id": parent_id,
            "title": title,
            "description": description,
            "test_type": test_type,
            "scenario": scenario,
            "priority": priority,
            "execution_type": execution_type,
            "impact_area": impact_area,
            "language": language,
            "tags": tags.split("; ") if tags else []
        }

    except Exception as e:
        return handle_error(e, skill_name)


# ─────────────────────────────────────────────────────────────────────────────
# SKILL 3: ARABIC TC ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def create_arabic_test_case(
    parent_id: int,
    title: str,
    description: str,
    steps_list: list,
    expected_list: list,
    test_type: str,
    scenario: str = "positive",
    priority: int = 2,
    execution_type: str = "",
    impact_area: str = "UI",
    extra_tags: list = None
) -> dict:
    """
    SKILL 3: Comprehensive TC Engine (Arabic)

    Creates a professional Arabic test case with ALL six mandatory attributes.
    Title must start with 'التحقق من أنه'.

    Args:
        parent_id (int): Parent PBI work item ID
        title (str): Must start with 'التحقق من أنه'
        description (str): 1-2 sentences explaining the test goal
        steps_list (list[str]): Sequential test steps in Arabic
        expected_list (list[str]): Expected results (same length as steps_list)
        test_type (str): 'UI' | 'Functional' | 'Edge' | 'Intensive'
        scenario (str): 'positive' | 'negative' (default: 'positive')
        priority (int): 1=Critical, 2=High, 3=Medium, 4=Low (auto-assessed if 0)
        execution_type (str): 'Automated' | 'Manual' (auto-determined if empty)
        impact_area (str): 'UI' | 'Backend' | 'Both' (default: 'UI')
        extra_tags (list[str]): Optional WOQOD-layer tags (e.g. ['UAT', 'Regression',
            'CMS', 'APP-iOS']) merged into System.Tags as queryable Azure tags.

    Returns:
        {status, tags_applied, test_case_id, parent_id, title, description,
         test_type, scenario, priority, execution_type, impact_area, language, tags}
    """
    return _create_test_case(
        parent_id=parent_id, title=title, description=description,
        steps_list=steps_list, expected_list=expected_list,
        test_type=test_type, scenario=scenario, priority=priority,
        execution_type=execution_type, impact_area=impact_area,
        language="ar", skill_name="create_arabic_test_case",
        extra_tags=extra_tags
    )


# ─────────────────────────────────────────────────────────────────────────────
# SKILL 4: ENGLISH TC ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def create_english_test_case(
    parent_id: int,
    title: str,
    description: str,
    steps_list: list,
    expected_list: list,
    test_type: str,
    scenario: str = "positive",
    priority: int = 2,
    execution_type: str = "",
    impact_area: str = "UI",
    extra_tags: list = None
) -> dict:
    """
    SKILL 4: Comprehensive TC Engine (English)

    Creates a professional English test case with ALL six mandatory attributes.
    Title must start with 'Verify that'.

    Args:
        parent_id (int): Parent PBI work item ID
        title (str): Must start with 'Verify that'
        description (str): 1-2 sentences explaining the test goal and context
        steps_list (list[str]): Sequential test steps
        expected_list (list[str]): Expected results (same length as steps_list)
        test_type (str): 'UI' | 'Functional' | 'Edge' | 'Intensive'
        scenario (str): 'positive' | 'negative' (default: 'positive')
        priority (int): 1=Critical, 2=High, 3=Medium, 4=Low (auto-assessed if 0)
        execution_type (str): 'Automated' | 'Manual' (auto-determined if empty)
        impact_area (str): 'UI' | 'Backend' | 'Both' (default: 'UI')
        extra_tags (list[str]): Optional WOQOD-layer tags (e.g. ['UAT', 'Regression',
            'CMS', 'APP-iOS']) merged into System.Tags as queryable Azure tags.

    Returns:
        {status, tags_applied, test_case_id, parent_id, title, description,
         test_type, scenario, priority, execution_type, impact_area, language, tags}
    """
    return _create_test_case(
        parent_id=parent_id, title=title, description=description,
        steps_list=steps_list, expected_list=expected_list,
        test_type=test_type, scenario=scenario, priority=priority,
        execution_type=execution_type, impact_area=impact_area,
        language="en", skill_name="create_english_test_case",
        extra_tags=extra_tags
    )


# ─────────────────────────────────────────────────────────────────────────────
# SKILL 9: MANAGERIAL FEEDBACK LOOP
# ─────────────────────────────────────────────────────────────────────────────

def execute_qa_feedback(parent_id: int, language: str, feedback_items: list) -> dict:
    """
    SKILL 9: Managerial Feedback Loop

    Batch-creates missing test cases from a QA Manager feedback list.
    Use AFTER review_test_coverage to fill identified coverage gaps.

    Workflow:
    1. Call review_test_coverage → identify gaps
    2. QA Manager prepares feedback_items list
    3. Call execute_qa_feedback → batch-creates missing TCs

    Args:
        parent_id (int): PBI work item ID
        language (str): 'ar' | 'en' — determines title prefix validation
        feedback_items (list[dict]): Each item:
            {comment, title, description, steps_list, expected_list,
             test_type, scenario, priority, execution_type, impact_area, tags}
            tags (list[str], optional): WOQOD-layer tags (e.g. ['UAT',
            'Regression', 'CMS', 'APP-iOS']) merged into System.Tags as
            queryable Azure tags alongside the auto dimension tags.

    Returns:
        {parent_id, total_feedback_items, created, errors_count,
         created_details, errors_details}
    """
    try:
        if language not in ["ar", "en"]:
            return {"error": "language must be 'ar' or 'en'"}

        if not feedback_items:
            return {"error": "feedback_items cannot be empty"}

        client = get_azure_client()

        parent = client.get_work_item(parent_id)
        project = parent.fields.get('System.TeamProject') or os.getenv("AZURE_PROJECT")
        parent_iteration = parent.fields.get('System.IterationPath')
        parent_title = parent.fields.get('System.Title', '')
        parent_ac = parent.fields.get('Microsoft.VSTS.Common.AcceptanceCriteria', '')

        created = []
        errors = []

        for i, item in enumerate(feedback_items):
            comment = item.get("comment", "No comment")
            title = item.get("title", "")
            description = item.get("description", "")
            steps_list = item.get("steps_list", [])
            expected_list = item.get("expected_list", [])
            test_type = item.get("test_type", "Functional")
            scenario = item.get("scenario", "positive")
            priority = item.get("priority", 0)
            execution_type = normalize_execution_type(item.get("execution_type", ""))
            impact_area = item.get("impact_area", "UI")
            extra_tags = item.get("tags", []) or []

            is_valid, error_msg = validate_tc_attributes(
                title, steps_list, expected_list, test_type, scenario,
                execution_type or "Automated", impact_area, language
            )

            if not is_valid:
                errors.append({"index": i, "comment": comment, "error": error_msg})
                continue

            if priority == 0:
                priority = assess_priority(parent_title, parent_ac, test_type, scenario)

            if not execution_type:
                execution_type = determine_execution_type(test_type, impact_area)

            try:
                xml_steps = format_azure_steps(steps_list, expected_list)
                tag_parts = ["Automated-By-AI", test_type, scenario, execution_type, impact_area, language.upper()]
                seen = {t.lower() for t in tag_parts}
                for t in extra_tags:
                    t = (t or "").strip()
                    if t and t.lower() not in seen:
                        tag_parts.append(t)
                        seen.add(t.lower())
                tags = "; ".join(tag_parts)
                # Unified tagging model: MCP applies only the Ai_MCP_Injected
                # provenance tag; every other tag is the agent's decision, passed
                # through verbatim. No tag judgement happens here.
                tags = _build_tags_string(extra_tags)

                patch_doc = [
                    JsonPatchOperation(op="add", path="/fields/System.Title", value=title),
                    JsonPatchOperation(op="add", path="/fields/System.Description", value=description),
                    JsonPatchOperation(op="add", path="/fields/Microsoft.VSTS.TCM.Steps", value=xml_steps),
                    JsonPatchOperation(op="add", path="/fields/Microsoft.VSTS.Common.Priority", value=priority),
                    JsonPatchOperation(op="add", path="/fields/System.Tags", value=tags),
                    JsonPatchOperation(op="add", path="/fields/System.IterationPath", value=parent_iteration),
                    JsonPatchOperation(op="add", path="/relations/-", value={
                        "rel": "Microsoft.VSTS.Common.TestedBy-Reverse",
                        "url": f"{os.getenv('AZURE_ORG_URL')}/_apis/wit/workItems/{parent_id}"
                    })
                ]
                new_tc, tags_applied = _create_with_tag_fallback(client, project, patch_doc)
                if not tags_applied:
                    tags = ""
                created.append({
                    "test_case_id": new_tc.id,
                    "tags_applied": tags_applied,
                    "comment_addressed": comment,
                    "title": title,
                    "description": description,
                    "test_type": test_type,
                    "scenario": scenario,
                    "priority": priority,
                    "execution_type": execution_type,
                    "impact_area": impact_area,
                    "language": language,
                    "tags": tags.split("; ") if tags else []
                })
            except Exception as e:
                errors.append({"index": i, "comment": comment, "error": str(e)})

        return {
            "parent_id": parent_id,
            "total_feedback_items": len(feedback_items),
            "created": len(created),
            "errors_count": len(errors),
            "created_details": created,
            "errors_details": errors
        }

    except Exception as e:
        return handle_error(e, "execute_qa_feedback")

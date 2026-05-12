"""
core/analysis.py — Coverage Analysis: Skill 5 (Gap Analysis), Skill 7 (QA Dashboard).

All functions are plain — no @mcp.tool() decorators. Registration happens in server.py.
"""

import os
from datetime import datetime

from azure.devops.v7_1.work_item_tracking.models import Wiql

from core.utils import (
    get_azure_client,
    handle_error,
    is_arabic,
    sanitize_wiql_string,
    infer_tc_attributes_from_title,
    parse_steps_xml,
)


# ─────────────────────────────────────────────────────────────────────────────
# SKILL 5: GAP ANALYSIS & COVERAGE
# ─────────────────────────────────────────────────────────────────────────────

def review_test_coverage(parent_id: int) -> dict:
    """
    SKILL 5: Gap Analysis & Coverage Review

    Analyzes all test cases linked to a PBI using a 2×4 coverage matrix
    (2 scenarios × 4 test types = 8 combinations).

    Coverage levels: full (8/8), partial (5-7), low (2-4), none (0-1)

    Args:
        parent_id (int): The PBI/User Story work item ID to analyze

    Returns:
        {parent_id, parent_title, acceptance_criteria, total_test_cases,
         coverage_matrix, coverage_level, gaps, test_cases, review_instructions}
    """
    try:
        client = get_azure_client()

        parent = client.get_work_item(parent_id, expand="Relations")
        parent_title = parent.fields.get('System.Title', '')
        parent_ac = parent.fields.get('Microsoft.VSTS.Common.AcceptanceCriteria', 'No AC')

        if not parent.relations:
            return {
                "parent_id": parent_id,
                "parent_title": parent_title,
                "acceptance_criteria": parent_ac,
                "total_test_cases": 0,
                "coverage_level": "none",
                "gaps": ["No test cases linked to this PBI"],
                "test_cases": [],
                "message": "No test cases linked to this PBI."
            }

        tc_ids = [
            int(rel.url.split("/")[-1])
            for rel in parent.relations
            if rel.rel == "System.LinkTypes.Hierarchy-Forward"
        ]

        if not tc_ids:
            return {
                "parent_id": parent_id,
                "parent_title": parent_title,
                "acceptance_criteria": parent_ac,
                "total_test_cases": 0,
                "coverage_level": "none",
                "gaps": ["No child test cases found"],
                "test_cases": []
            }

        work_items = client.get_work_items(ids=tc_ids, expand="All")

        coverage_matrix = {
            "UI": {"positive": 0, "negative": 0},
            "Functional": {"positive": 0, "negative": 0},
            "Edge": {"positive": 0, "negative": 0},
            "Intensive": {"positive": 0, "negative": 0}
        }

        tc_details = []
        for item in work_items:
            if item.fields.get('System.WorkItemType') != 'Test Case':
                continue

            title = item.fields.get('System.Title', '')
            tags = item.fields.get('System.Tags', '')
            tag_list = [t.strip() for t in tags.split(';')] if tags else []

            has_meaningful_tags = any(
                t in tag_list for t in ["UI", "Functional", "Edge", "Intensive", "positive", "negative"]
            )

            if has_meaningful_tags:
                test_type = next((t for t in tag_list if t in ["UI", "Functional", "Edge", "Intensive"]), "Functional")
                scenario = next((t for t in tag_list if t in ["positive", "negative"]), "positive")
                execution_type = next((t for t in tag_list if t in ["Automated", "Manual"]), "Automated")
                impact_area = next((t for t in tag_list if t in ["Backend", "Both"]), "UI")
            else:
                inferred = infer_tc_attributes_from_title(title)
                test_type = inferred["test_type"]
                scenario = inferred["scenario"]
                execution_type = inferred["execution_type"]
                impact_area = inferred["impact_area"]

            if test_type in coverage_matrix:
                coverage_matrix[test_type][scenario] += 1

            tc_details.append({
                "id": item.id,
                "title": title,
                "type": test_type,
                "scenario": scenario,
                "priority": item.fields.get('Microsoft.VSTS.Common.Priority', 0),
                "execution_type": execution_type,
                "impact_area": impact_area,
                "steps": parse_steps_xml(item.fields.get('Microsoft.VSTS.TCM.Steps', ''))
            })

        combinations_covered = sum(
            1 for t_type in coverage_matrix.values()
            for count in t_type.values()
            if count > 0
        )

        if combinations_covered >= 8:
            coverage_level = "full"
        elif combinations_covered >= 5:
            coverage_level = "partial"
        elif combinations_covered >= 2:
            coverage_level = "low"
        else:
            coverage_level = "none"

        gaps = [
            f"Missing: {scenario.capitalize()} {test_type} test case"
            for test_type in ["UI", "Functional", "Edge", "Intensive"]
            for scenario in ["Positive", "Negative"]
            if coverage_matrix[test_type][scenario.lower()] == 0
        ]

        return {
            "parent_id": parent_id,
            "parent_title": parent_title,
            "acceptance_criteria": parent_ac,
            "total_test_cases": len(tc_details),
            "coverage_matrix": coverage_matrix,
            "coverage_level": coverage_level,
            "gaps": gaps,
            "test_cases": tc_details,
            "review_instructions": (
                "As QA Manager, verify that test cases comprehensively cover all acceptance criteria. "
                "Ensure coverage across all four types (UI, Functional, Edge, Intensive) and both "
                "positive and negative scenarios. For any identified gaps, create additional test cases "
                "using the execute_qa_feedback tool."
            )
        }

    except Exception as e:
        return handle_error(e, "review_test_coverage")


# ─────────────────────────────────────────────────────────────────────────────
# SKILL 7: EXECUTIVE QA DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

def generate_qa_report(iteration_path: str) -> dict:
    """
    SKILL 7: Executive QA Dashboard

    Generates a comprehensive sprint-level QA analytics report covering
    9 metric categories: summary, priority, type, scenario, execution type,
    impact area, language, business impact, and per-PBI breakdown.

    Risk flags: negative coverage < 30%, edge cases < 20%, manual ratio > 50%.

    Args:
        iteration_path (str): Sprint path, e.g., 'MyProject\\Sprint 1'

    Returns:
        {sprint, generated_date, dashboard, priority_breakdown, type_breakdown,
         scenario_breakdown, execution_type_breakdown, impact_area_breakdown,
         language_breakdown, business_impact, pbis_covered, per_pbi_summary}
    """
    try:
        client = get_azure_client()
        project = os.getenv("AZURE_PROJECT")
        safe_iter = sanitize_wiql_string(iteration_path)
        safe_proj = sanitize_wiql_string(project)

        query = f"""
            SELECT [System.Id]
            FROM WorkItems
            WHERE [System.WorkItemType] = 'Test Case'
              AND [System.IterationPath] = '{safe_iter}'
              AND [System.TeamProject] = '{safe_proj}'
            ORDER BY [System.Id] ASC
        """
        result = client.query_by_wiql(Wiql(query=query))

        if not result.work_items:
            return {
                "sprint": iteration_path,
                "dashboard": {
                    "total_pbis_processed": 0, "total_pbis_valid": 0,
                    "total_pbis_skipped": 0, "total_test_cases": 0
                },
                "message": "No test cases found in this sprint."
            }

        ids = [item.id for item in result.work_items]
        work_items = client.get_work_items(ids=ids, expand="All")

        priority_count = {1: 0, 2: 0, 3: 0, 4: 0}
        type_count = {"UI": 0, "Functional": 0, "Edge": 0, "Intensive": 0}
        scenario_count = {"positive": 0, "negative": 0}
        exec_type_count = {"Automated": 0, "Manual": 0}
        impact_count = {"UI": 0, "Backend": 0, "Both": 0}
        lang_count = {"Arabic": 0, "English": 0}
        parent_map = {}

        for item in work_items:
            tags = item.fields.get('System.Tags', '')
            tag_list = [t.strip() for t in tags.split(';')] if tags else []
            prio = item.fields.get('Microsoft.VSTS.Common.Priority', 2)
            title = item.fields.get('System.Title', '')

            priority_count[prio] = priority_count.get(prio, 0) + 1

            has_meaningful_tags = any(
                t in tag_list for t in ["UI", "Functional", "Edge", "Intensive", "positive", "negative"]
            )

            if has_meaningful_tags:
                for tag in tag_list:
                    if tag in type_count:
                        type_count[tag] += 1
                    if tag in scenario_count:
                        scenario_count[tag] += 1
                    if tag in exec_type_count:
                        exec_type_count[tag] += 1
                    if tag in ["Backend", "Both"]:
                        impact_count[tag] += 1
                    elif tag == "UI" and tag not in ["Functional", "Edge", "Intensive"]:
                        impact_count["UI"] += 1
            else:
                inferred = infer_tc_attributes_from_title(title)
                type_count[inferred["test_type"]] += 1
                scenario_count[inferred["scenario"]] += 1
                exec_type_count[inferred["execution_type"]] += 1
                impact_count[inferred["impact_area"]] += 1

            if "AR" in tag_list or is_arabic(title):
                lang_count["Arabic"] += 1
            else:
                lang_count["English"] += 1

            inferred_type = None if has_meaningful_tags else infer_tc_attributes_from_title(title)["test_type"]

            if item.relations:
                for rel in item.relations:
                    if rel.rel == "System.LinkTypes.Hierarchy-Reverse":
                        pid = int(rel.url.split("/")[-1])
                        if pid not in parent_map:
                            parent_map[pid] = {"count": 0, "types": {}, "priorities": {}}
                        parent_map[pid]["count"] += 1

                        type_found = False
                        for tag in tag_list:
                            if tag in ["UI", "Functional", "Edge", "Intensive"]:
                                parent_map[pid]["types"][tag] = parent_map[pid]["types"].get(tag, 0) + 1
                                type_found = True
                        if not type_found and inferred_type:
                            parent_map[pid]["types"][inferred_type] = parent_map[pid]["types"].get(inferred_type, 0) + 1

                        parent_map[pid]["priorities"][prio] = parent_map[pid]["priorities"].get(prio, 0) + 1

        total = len(work_items)

        def calc_pct(count):
            return f"{(count / total * 100):.1f}%" if total > 0 else "0%"

        high_priority = priority_count.get(1, 0) + priority_count.get(2, 0)
        impact_level = "high" if high_priority > total * 0.5 else "medium" if high_priority > total * 0.25 else "low"

        risk_factors = []
        if scenario_count.get("negative", 0) < total * 0.3:
            risk_factors.append("Low coverage of negative test cases")
        if type_count.get("Edge", 0) < total * 0.2:
            risk_factors.append("Limited edge case testing")
        if exec_type_count.get("Automated", 0) < total * 0.5:
            risk_factors.append("High proportion of manual tests (maintenance overhead)")

        per_pbi = []
        for pid, data in sorted(parent_map.items()):
            parent_item = client.get_work_item(pid)
            per_pbi.append({
                "pbi_id": pid,
                "pbi_title": parent_item.fields.get('System.Title', ''),
                "test_case_count": data["count"],
                "type_distribution": data["types"],
                "priority_distribution": {f"P{k}": v for k, v in data["priorities"].items()}
            })

        return {
            "sprint": iteration_path,
            "generated_date": datetime.now().isoformat(),
            "dashboard": {
                "total_pbis_processed": len(parent_map),
                "total_pbis_valid": len(parent_map),
                "total_pbis_skipped": 0,
                "total_test_cases": total,
                "average_tcs_per_pbi": round(total / len(parent_map), 2) if parent_map else 0,
                "coverage_percentage": "100%" if total > 0 else "0%"
            },
            "priority_breakdown": {
                "P1_Critical": {"count": priority_count[1], "percentage": calc_pct(priority_count[1])},
                "P2_High": {"count": priority_count[2], "percentage": calc_pct(priority_count[2])},
                "P3_Medium": {"count": priority_count[3], "percentage": calc_pct(priority_count[3])},
                "P4_Low": {"count": priority_count[4], "percentage": calc_pct(priority_count[4])}
            },
            "type_breakdown": {t: {"count": type_count[t], "percentage": calc_pct(type_count[t])} for t in type_count},
            "scenario_breakdown": {s: {"count": scenario_count[s], "percentage": calc_pct(scenario_count[s])} for s in scenario_count},
            "execution_type_breakdown": {e: {"count": exec_type_count[e], "percentage": calc_pct(exec_type_count[e])} for e in exec_type_count},
            "impact_area_breakdown": {a: {"count": impact_count[a], "percentage": calc_pct(impact_count[a])} for a in impact_count},
            "language_breakdown": {l: {"count": lang_count[l], "percentage": calc_pct(lang_count[l])} for l in lang_count},
            "business_impact": {
                "level": impact_level,
                "assessment": (
                    f"High critical/high priority coverage ({calc_pct(high_priority)})" if impact_level == "high"
                    else "Moderate coverage" if impact_level == "medium"
                    else "Limited coverage of critical areas"
                ),
                "risk_factors": risk_factors
            },
            "pbis_covered": len(parent_map),
            "per_pbi_summary": per_pbi
        }

    except Exception as e:
        return handle_error(e, "generate_qa_report")

"""
Regression tests for the P1 findings in PROJECT_REVIEW.md:
  #1 link-type mismatch (TestedBy vs Hierarchy)
  #2 tags missing from review_test_coverage output
  #3 analytics on the current tag taxonomy

Azure client is mocked — no network.
Run: pytest tests/ -v
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import core.analysis as analysis
from core.utils import format_azure_steps


def _rel(rel_type, target_id):
    return SimpleNamespace(rel=rel_type, url=f"https://org/_apis/wit/workItems/{target_id}")


def _tc_item(tc_id, title, tags, priority=2, relations=None):
    return SimpleNamespace(
        id=tc_id,
        fields={
            "System.WorkItemType": "Test Case",
            "System.Title": title,
            "System.Tags": tags,
            "Microsoft.VSTS.Common.Priority": priority,
            "Microsoft.VSTS.TCM.Steps": format_azure_steps(["step"], ["result"]),
        },
        relations=relations or [],
    )


class TestReviewTestCoverageLinks:
    """P1 #1 — parent linked via TestedBy-Forward must be seen."""

    def _run(self, parent_relations, tc_items):
        client = MagicMock()
        client.get_work_item.return_value = SimpleNamespace(
            id=100,
            fields={"System.Title": "PBI", "Microsoft.VSTS.Common.AcceptanceCriteria": "AC"},
            relations=parent_relations,
        )
        client.get_work_items.return_value = tc_items
        with patch.object(analysis, "get_azure_client", return_value=client):
            return analysis.review_test_coverage(100)

    def test_testedby_forward_links_are_counted(self):
        # This is exactly what the injection engines produce on the parent side.
        rels = [_rel("Microsoft.VSTS.Common.TestedBy-Forward", 201)]
        tcs = [_tc_item(201, "Verify that top-up succeeds", "Functional-High; Automation; Web")]
        result = self._run(rels, tcs)
        assert result["total_test_cases"] == 1, (
            "MCP-injected cases (TestedBy links) must be visible to coverage review"
        )

    def test_hierarchy_links_still_counted(self):
        rels = [_rel("System.LinkTypes.Hierarchy-Forward", 202)]
        tcs = [_tc_item(202, "Verify that x", "Edge; Manual; Android")]
        assert self._run(rels, tcs)["total_test_cases"] == 1

    def test_both_link_types_deduped(self):
        rels = [
            _rel("Microsoft.VSTS.Common.TestedBy-Forward", 203),
            _rel("System.LinkTypes.Hierarchy-Forward", 203),
        ]
        tcs = [_tc_item(203, "Verify that x", "UI; Web")]
        assert self._run(rels, tcs)["total_test_cases"] == 1

    def test_unrelated_links_ignored(self):
        rels = [_rel("System.LinkTypes.Related", 204)]
        client = MagicMock()
        client.get_work_item.return_value = SimpleNamespace(
            id=100, fields={"System.Title": "PBI",
                            "Microsoft.VSTS.Common.AcceptanceCriteria": "AC"},
            relations=rels,
        )
        with patch.object(analysis, "get_azure_client", return_value=client):
            result = analysis.review_test_coverage(100)
        assert result["total_test_cases"] == 0


class TestReviewTestCoveragePayload:
    """P1 #2 + #3 — tags returned per case; classification uses current taxonomy."""

    def _run_one(self, tags, title="Verify that top-up succeeds"):
        client = MagicMock()
        client.get_work_item.return_value = SimpleNamespace(
            id=100, fields={"System.Title": "PBI",
                            "Microsoft.VSTS.Common.AcceptanceCriteria": "AC"},
            relations=[_rel("Microsoft.VSTS.Common.TestedBy-Forward", 301)],
        )
        client.get_work_items.return_value = [_tc_item(301, title, tags)]
        with patch.object(analysis, "get_azure_client", return_value=client):
            return analysis.review_test_coverage(100)

    def test_tags_present_in_payload(self):
        result = self._run_one("Ai_MCP_Injected; Functional-High; Regression; Automation; TAG; Web")
        tc = result["test_cases"][0]
        assert "Web" in tc["tags"], "route-automation needs Platform tags in the payload"
        assert "Regression" in tc["tags"]

    def test_current_taxonomy_classified_from_tags_not_title(self):
        result = self._run_one("Functional-Low; Manual; FAHES; Android")
        tc = result["test_cases"][0]
        assert tc["classification_source"] == "tags"
        assert tc["category"] == "Functional-Low"
        assert tc["execution_type"] == "Manual"

    def test_category_coverage_reported(self):
        result = self._run_one("Edge; Automation; BOOK; Web")
        assert result["category_coverage"]["Edge"] == 1

    def test_review_instructions_do_not_prescribe_injection(self):
        result = self._run_one("UI; Web")
        instructions = result["review_instructions"].lower()
        assert "execute_qa_feedback" not in instructions
        assert "do not create" in instructions or "not prescribe" in instructions


class TestGenerateQaReportLinks:
    """P1 #1 (reverse side) — TC → parent via TestedBy-Reverse must map to the PBI."""

    def test_testedby_reverse_maps_to_parent(self):
        tc = _tc_item(
            401, "Verify that payment fails gracefully",
            "Functional-High; Automation; TAG; Web",
            priority=1,
            relations=[_rel("Microsoft.VSTS.Common.TestedBy-Reverse", 100)],
        )
        client = MagicMock()
        client.query_by_wiql.return_value = SimpleNamespace(
            work_items=[SimpleNamespace(id=401)]
        )
        # First get_work_items call → TCs; second → batched parent titles
        client.get_work_items.side_effect = [
            [tc],
            [SimpleNamespace(id=100, fields={"System.Title": "Parent PBI"})],
        ]
        with patch.object(analysis, "get_azure_client", return_value=client):
            result = analysis.generate_qa_report("Woqod\\Sprint 8")

        assert result["pbis_covered"] == 1
        assert result["per_pbi_summary"][0]["pbi_id"] == 100
        assert result["per_pbi_summary"][0]["pbi_title"] == "Parent PBI"
        assert result["category_breakdown"]["Functional-High"]["count"] == 1
        assert result["execution_type_breakdown"]["Automated"]["count"] == 1

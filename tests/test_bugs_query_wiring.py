import json
from unittest.mock import patch, MagicMock

import core.bugs as bugs


def _make_relation(rel_type, target_id):
    rel = MagicMock()
    rel.rel = rel_type
    rel.url = f"https://org/_apis/wit/workItems/{target_id}"
    return rel


@patch("core.bugs.ensure_bug_query_hierarchy")
@patch("core.bugs.get_azure_client")
def test_create_bug_tags_pbi_and_provisions_queries(mock_get_client, mock_ensure_hierarchy, monkeypatch):
    monkeypatch.setenv("AZURE_ORG_URL", "https://org")
    monkeypatch.setenv("AZURE_PROJECT", "Proj")

    test_case = MagicMock()
    test_case.fields = {
        "System.IterationPath": "Woqod\\Sprint 23",
        "System.AreaPath": "Woqod",
        "System.Tags": "Functional-High; Web",
    }
    test_case.relations = [_make_relation("Microsoft.VSTS.Common.TestedBy-Reverse", 129744)]

    backlog_item = MagicMock()
    backlog_item.fields = {"System.Title": "contact us feature"}

    new_bug = MagicMock()
    new_bug.id = 6201

    client = MagicMock()
    client.get_work_item.side_effect = [test_case, backlog_item]
    client.create_work_item.return_value = new_bug
    mock_get_client.return_value = client

    mock_ensure_hierarchy.return_value = json.dumps({
        "status": "success", "sprint_folder": "Shared Queries/Bugs/Sprint bugs/Sprint 23",
        "general_query": {"status_action": "created"},
        "automation_query": {"status_action": "created"},
        "message": "ok",
    })

    result = json.loads(bugs.create_bug(
        test_case_id=129779, test_name="test_contact_us", error_message="AssertionError: boom",
    ))

    assert result["status"] == "created"
    assert "PBI:129744" in result["tags"]
    mock_ensure_hierarchy.assert_called_once_with("Sprint 23", "contact us feature", 129744)
    assert result["query_provisioning"]["status"] == "success"


@patch("core.bugs.ensure_bug_query_hierarchy")
@patch("core.bugs.get_azure_client")
def test_create_bug_skips_provisioning_when_no_backlog_link(mock_get_client, mock_ensure_hierarchy, monkeypatch):
    monkeypatch.setenv("AZURE_ORG_URL", "https://org")
    monkeypatch.setenv("AZURE_PROJECT", "Proj")

    test_case = MagicMock()
    test_case.fields = {"System.IterationPath": "Woqod\\Sprint 23", "System.AreaPath": "Woqod", "System.Tags": ""}
    test_case.relations = []

    new_bug = MagicMock()
    new_bug.id = 6202

    client = MagicMock()
    client.get_work_item.return_value = test_case
    client.create_work_item.return_value = new_bug
    mock_get_client.return_value = client

    result = json.loads(bugs.create_bug(
        test_case_id=129780, test_name="test_x", error_message="boom",
    ))

    assert result["query_provisioning"]["status"] == "skipped"
    assert not any(t.startswith("PBI:") for t in result["tags"])
    mock_ensure_hierarchy.assert_not_called()


@patch("core.bugs.ensure_bug_query_hierarchy")
@patch("core.bugs.get_azure_client")
def test_create_bug_reports_provisioning_error_without_failing(mock_get_client, mock_ensure_hierarchy, monkeypatch):
    monkeypatch.setenv("AZURE_ORG_URL", "https://org")
    monkeypatch.setenv("AZURE_PROJECT", "Proj")

    test_case = MagicMock()
    test_case.fields = {"System.IterationPath": "Woqod\\Sprint 23", "System.AreaPath": "Woqod", "System.Tags": ""}
    test_case.relations = [_make_relation("Microsoft.VSTS.Common.TestedBy-Reverse", 129744)]

    new_bug = MagicMock()
    new_bug.id = 6203

    client = MagicMock()
    # First call resolves the test case; second call (fetching the backlog title) raises.
    client.get_work_item.side_effect = [test_case, RuntimeError("backlog item deleted")]
    client.create_work_item.return_value = new_bug
    mock_get_client.return_value = client

    result = json.loads(bugs.create_bug(
        test_case_id=129781, test_name="test_y", error_message="boom",
    ))

    assert result["status"] == "created"
    assert result["bug_id"] == 6203
    assert result["query_provisioning"]["status"] == "error"
    mock_ensure_hierarchy.assert_not_called()


@patch("core.bugs.ensure_bug_query_hierarchy")
@patch("core.bugs.get_azure_client")
def test_add_bug_occurrence_provisions_when_test_case_id_given(mock_get_client, mock_ensure_hierarchy, monkeypatch):
    monkeypatch.setenv("AZURE_PROJECT", "Proj")

    bug = MagicMock()
    bug.fields = {"System.State": "Resolved"}

    test_case = MagicMock()
    test_case.fields = {"System.IterationPath": "Woqod\\Sprint 23"}
    test_case.relations = [_make_relation("Microsoft.VSTS.Common.TestedBy-Reverse", 129744)]

    backlog_item = MagicMock()
    backlog_item.fields = {"System.Title": "contact us feature"}

    client = MagicMock()
    client.get_work_item.side_effect = [bug, test_case, backlog_item]
    mock_get_client.return_value = client

    mock_ensure_hierarchy.return_value = json.dumps({
        "status": "success", "sprint_folder": "x", "general_query": {}, "automation_query": {}, "message": "ok",
    })

    result = json.loads(bugs.add_bug_occurrence(6188, "still failing", test_case_id=129779))

    assert result["reopened"] is True
    mock_ensure_hierarchy.assert_called_once_with("Sprint 23", "contact us feature", 129744)
    assert result["query_provisioning"]["status"] == "success"


@patch("core.bugs.ensure_bug_query_hierarchy")
@patch("core.bugs.get_azure_client")
def test_add_bug_occurrence_skips_provisioning_without_test_case_id(mock_get_client, mock_ensure_hierarchy, monkeypatch):
    monkeypatch.setenv("AZURE_PROJECT", "Proj")

    bug = MagicMock()
    bug.fields = {"System.State": "Active"}
    client = MagicMock()
    client.get_work_item.return_value = bug
    mock_get_client.return_value = client

    result = json.loads(bugs.add_bug_occurrence(6188, "still failing"))

    assert result["query_provisioning"]["status"] == "skipped"
    mock_ensure_hierarchy.assert_not_called()


@patch("core.bugs.ensure_bug_query_hierarchy")
@patch("core.bugs.get_azure_client")
def test_add_bug_occurrence_skips_when_context_unresolvable(mock_get_client, mock_ensure_hierarchy, monkeypatch):
    monkeypatch.setenv("AZURE_PROJECT", "Proj")

    bug = MagicMock()
    bug.fields = {"System.State": "Active"}

    test_case = MagicMock()
    test_case.fields = {"System.IterationPath": "Woqod\\Sprint 23"}
    test_case.relations = []  # no TestedBy-Reverse relation -> unresolvable

    client = MagicMock()
    client.get_work_item.side_effect = [bug, test_case]
    mock_get_client.return_value = client

    result = json.loads(bugs.add_bug_occurrence(6188, "still failing", test_case_id=129779))

    assert result["query_provisioning"]["status"] == "skipped"
    mock_ensure_hierarchy.assert_not_called()

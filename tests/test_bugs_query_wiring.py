import json
from unittest.mock import patch, MagicMock

import core.bugs as bugs


def _make_relation(rel_type, target_id):
    rel = MagicMock()
    rel.rel = rel_type
    rel.url = f"https://org/_apis/wit/workItems/{target_id}"
    return rel


@patch("core.bugs.get_azure_client")
def test_create_bug_tags_pbi_when_backlog_link_exists(mock_get_client, monkeypatch):
    monkeypatch.setenv("AZURE_ORG_URL", "https://org")
    monkeypatch.setenv("AZURE_PROJECT", "Proj")

    test_case = MagicMock()
    test_case.fields = {
        "System.IterationPath": "Woqod\\Sprint 23",
        "System.AreaPath": "Woqod",
        "System.Tags": "Functional-High; Web",
    }
    test_case.relations = [_make_relation("Microsoft.VSTS.Common.TestedBy-Reverse", 129744)]

    new_bug = MagicMock()
    new_bug.id = 6201

    client = MagicMock()
    client.get_work_item.return_value = test_case
    client.create_work_item.return_value = new_bug
    mock_get_client.return_value = client

    result = json.loads(bugs.create_bug(
        test_case_id=129779, test_name="test_contact_us", error_message="AssertionError: boom",
    ))

    assert result["status"] == "created"
    assert "PBI:129744" in result["tags"]
    assert "query_provisioning" not in result


@patch("core.bugs.get_azure_client")
def test_create_bug_omits_pbi_tag_when_no_backlog_link(mock_get_client, monkeypatch):
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

    assert not any(t.startswith("PBI:") for t in result["tags"])


@patch("core.bugs.get_azure_client")
def test_add_bug_occurrence_reopens_resolved_bug(mock_get_client, monkeypatch):
    monkeypatch.setenv("AZURE_PROJECT", "Proj")

    bug = MagicMock()
    bug.fields = {"System.State": "Resolved"}
    client = MagicMock()
    client.get_work_item.return_value = bug
    mock_get_client.return_value = client

    result = json.loads(bugs.add_bug_occurrence(6188, "still failing"))

    assert result["reopened"] is True
    assert "query_provisioning" not in result


@patch("core.bugs.get_azure_client")
def test_add_bug_occurrence_no_longer_accepts_test_case_id(mock_get_client, monkeypatch):
    monkeypatch.setenv("AZURE_PROJECT", "Proj")

    bug = MagicMock()
    bug.fields = {"System.State": "Active"}
    client = MagicMock()
    client.get_work_item.return_value = bug
    mock_get_client.return_value = client

    try:
        bugs.add_bug_occurrence(6188, "still failing", test_case_id=129779)
        assert False, "expected TypeError"
    except TypeError:
        pass

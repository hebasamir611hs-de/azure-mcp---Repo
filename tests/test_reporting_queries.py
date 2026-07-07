import json
from unittest.mock import patch, MagicMock

import core.reporting as reporting


def test_sanitize_name_strips_invalid_chars():
    assert reporting._sanitize_name('Top-up: "Card" / Wallet') == "Top-up- -Card- - Wallet"


def test_sanitize_name_empty_or_blank_falls_back_to_unnamed():
    assert reporting._sanitize_name("") == "Unnamed"
    assert reporting._sanitize_name("   ") == "Unnamed"


def test_sanitize_name_collapses_whitespace():
    assert reporting._sanitize_name("Contact   Us\tFeature") == "Contact Us Feature"


def test_sanitize_name_truncates_to_max_len():
    long_name = "x" * 300
    assert len(reporting._sanitize_name(long_name, max_len=50)) == 50


@patch("core.reporting.requests.get")
def test_get_query_item_returns_none_on_404(mock_get):
    mock_get.return_value = MagicMock(status_code=404)
    result = reporting._get_query_item("https://org", "Proj", "Shared Queries/Bugs")
    assert result is None


@patch("core.reporting.requests.get")
def test_get_query_item_returns_json_on_200(mock_get):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: {"id": "abc"})
    result = reporting._get_query_item("https://org", "Proj", "Shared Queries/Bugs")
    assert result == {"id": "abc"}


@patch("core.reporting.requests.post")
def test_create_folder_raises_on_failure(mock_post):
    mock_post.return_value = MagicMock(
        status_code=400, json=lambda: {"message": "bad request"}, text="bad request"
    )
    try:
        reporting._create_folder("https://org", "Proj", "Shared Queries", "Bugs")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "bad request" in str(e)


@patch("core.reporting._create_folder")
@patch("core.reporting._get_query_item")
def test_ensure_folder_path_creates_only_missing_segments(mock_get_item, mock_create):
    def get_item_side_effect(org_url, project, path):
        if path in ("Shared Queries", "Shared Queries/Bugs"):
            return {"id": "exists"}
        return None
    mock_get_item.side_effect = get_item_side_effect

    reporting._ensure_folder_path("https://org", "Proj", "Shared Queries/Bugs/Sprint bugs/Sprint 23")

    assert mock_create.call_count == 2
    mock_create.assert_any_call("https://org", "Proj", "Shared Queries/Bugs", "Sprint bugs")
    mock_create.assert_any_call("https://org", "Proj", "Shared Queries/Bugs/Sprint bugs", "Sprint 23")


@patch("core.reporting._get_query_item", return_value=None)
def test_ensure_folder_path_raises_if_root_missing(mock_get_item):
    try:
        reporting._ensure_folder_path("https://org", "Proj", "Nonexistent Root/Sub")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "Nonexistent Root" in str(e)


@patch("core.reporting._get_query_item")
def test_ensure_query_returns_existing_without_creating(mock_get_item):
    mock_get_item.return_value = {
        "id": "existing-id",
        "path": "Shared Queries/Bugs/Sprint bugs/Sprint 23/My Feature",
        "_links": {"html": {"href": "https://org/proj/_queries/query/existing-id"}},
    }
    result = reporting._ensure_query(
        "https://org", "Proj", "Shared Queries/Bugs/Sprint bugs/Sprint 23", "My Feature",
        "[System.WorkItemType] = 'Bug'",
    )
    assert result["status_action"] == "existing"
    assert result["query_id"] == "existing-id"


@patch("core.reporting.create_work_item_query")
@patch("core.reporting._get_query_item", return_value=None)
def test_ensure_query_creates_when_missing(mock_get_item, mock_create_query):
    mock_create_query.return_value = json.dumps({
        "status": "success", "query_id": "new-id",
        "path": "Shared Queries/Bugs/Sprint bugs/Sprint 23/My Feature",
        "columns": [], "url": "https://org/proj/_queries/query/new-id", "message": "created",
    })
    result = reporting._ensure_query(
        "https://org", "Proj", "Shared Queries/Bugs/Sprint bugs/Sprint 23", "My Feature",
        "[System.WorkItemType] = 'Bug'",
    )
    assert result["status_action"] == "created"
    assert result["query_id"] == "new-id"


@patch("core.reporting.create_work_item_query")
@patch("core.reporting._get_query_item", return_value=None)
def test_ensure_query_reports_error_action_on_failure(mock_get_item, mock_create_query):
    mock_create_query.return_value = json.dumps({
        "status": "error", "error_type": "api", "http_status": 400, "error": "bad wiql",
    })
    result = reporting._ensure_query(
        "https://org", "Proj", "Shared Queries/Bugs/Sprint bugs/Sprint 23", "My Feature",
        "[System.WorkItemType] = 'Bug'",
    )
    assert result["status_action"] == "error"


@patch("core.reporting._ensure_query")
@patch("core.reporting._ensure_folder_path")
def test_ensure_bug_query_hierarchy_builds_both_queries(mock_ensure_folder, mock_ensure_query, monkeypatch):
    monkeypatch.setenv("AZURE_ORG_URL", "https://org")
    monkeypatch.setenv("AZURE_PROJECT", "Proj")
    mock_ensure_query.side_effect = [
        {"status_action": "created", "query_id": "g1"},
        {"status_action": "created", "query_id": "a1"},
    ]

    result = json.loads(reporting.ensure_bug_query_hierarchy("Sprint 23", "Contact Us", 129744))

    assert result["status"] == "success"
    assert result["sprint_folder"] == "Shared Queries/Bugs/Sprint bugs/Sprint 23"
    mock_ensure_folder.assert_called_once_with(
        "https://org", "Proj", "Shared Queries/Bugs/Sprint bugs/Sprint 23"
    )
    assert mock_ensure_query.call_count == 2
    general_call, automation_call = mock_ensure_query.call_args_list
    assert general_call.args[3] == "Contact Us"
    assert "[System.Title] CONTAINS '129744'" in general_call.args[4]
    assert "NOT [System.Tags] CONTAINS 'Automated'" in general_call.args[4]
    assert automation_call.args[3] == "Contact Us - Automation"
    assert "[System.Title] CONTAINS '129744'" in automation_call.args[4]
    assert "AND [System.Tags] CONTAINS 'Automated'" in automation_call.args[4]


@patch("core.reporting._ensure_query")
@patch("core.reporting._ensure_folder_path")
def test_ensure_bug_query_hierarchy_defaults_missing_sprint_to_unassigned(
    mock_ensure_folder, mock_ensure_query, monkeypatch
):
    monkeypatch.setenv("AZURE_ORG_URL", "https://org")
    monkeypatch.setenv("AZURE_PROJECT", "Proj")
    mock_ensure_query.side_effect = [{"status_action": "created"}, {"status_action": "created"}]

    result = json.loads(reporting.ensure_bug_query_hierarchy("", "Contact Us", 129744))

    assert result["sprint_folder"] == "Shared Queries/Bugs/Sprint bugs/Unassigned"

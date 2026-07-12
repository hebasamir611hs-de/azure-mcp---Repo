import json
from unittest.mock import patch, MagicMock

import core.bugs as bugs


@patch("core.bugs.get_azure_client")
def test_create_bug_title_uses_actual_result_not_raw_error(mock_get_client, monkeypatch):
    monkeypatch.setenv("AZURE_ORG_URL", "https://org")
    monkeypatch.setenv("AZURE_PROJECT", "Proj")

    test_case = MagicMock()
    test_case.fields = {"System.IterationPath": "", "System.AreaPath": "", "System.Tags": ""}
    test_case.relations = []

    new_bug = MagicMock()
    new_bug.id = 1

    client = MagicMock()
    client.get_work_item.return_value = test_case
    client.create_work_item.return_value = new_bug
    mock_get_client.return_value = client

    result = json.loads(bugs.create_bug(
        test_case_id=129779,
        test_name="web/tests/contact_us/test_submission.py::test_contact_us_submit_happy_path",
        error_message=(
            "playwright._impl._errors.TimeoutError: Locator.wait_for: "
            "Timeout 10000ms exceeded"
        ),
        actual_result="No confirmation message appeared and the form fields were not cleared.",
    ))

    assert result["title"] == (
        "Automated test failure: "
        "web/tests/contact_us/test_submission.py::test_contact_us_submit_happy_path — "
        "No confirmation message appeared and the form fields were not cleared."
    )
    assert "TimeoutError" not in result["title"]
    assert "playwright" not in result["title"]


@patch("core.bugs.get_azure_client")
def test_create_bug_title_falls_back_to_error_message_when_no_actual_result(mock_get_client, monkeypatch):
    monkeypatch.setenv("AZURE_ORG_URL", "https://org")
    monkeypatch.setenv("AZURE_PROJECT", "Proj")

    test_case = MagicMock()
    test_case.fields = {"System.IterationPath": "", "System.AreaPath": "", "System.Tags": ""}
    test_case.relations = []

    new_bug = MagicMock()
    new_bug.id = 2

    client = MagicMock()
    client.get_work_item.return_value = test_case
    client.create_work_item.return_value = new_bug
    mock_get_client.return_value = client

    result = json.loads(bugs.create_bug(
        test_case_id=129780,
        test_name="test_x",
        error_message="AssertionError: expected True, got False",
    ))

    assert "Automated test failure: test_x" in result["title"]
    assert "AssertionError" not in result["title"]


@patch("core.bugs.get_azure_client")
def test_create_bug_title_truncates_long_actual_result(mock_get_client, monkeypatch):
    monkeypatch.setenv("AZURE_ORG_URL", "https://org")
    monkeypatch.setenv("AZURE_PROJECT", "Proj")

    test_case = MagicMock()
    test_case.fields = {"System.IterationPath": "", "System.AreaPath": "", "System.Tags": ""}
    test_case.relations = []

    new_bug = MagicMock()
    new_bug.id = 3

    client = MagicMock()
    client.get_work_item.return_value = test_case
    client.create_work_item.return_value = new_bug
    mock_get_client.return_value = client

    long_actual = "X" * 300
    result = json.loads(bugs.create_bug(
        test_case_id=129781,
        test_name="test_y",
        error_message="boom",
        actual_result=long_actual,
    ))

    title_summary = result["title"].split(" — ", 1)[1]
    assert len(title_summary) <= 100


@patch("core.bugs.get_azure_client")
def test_create_bug_repro_steps_include_full_error_under_root_cause(mock_get_client, monkeypatch):
    monkeypatch.setenv("AZURE_ORG_URL", "https://org")
    monkeypatch.setenv("AZURE_PROJECT", "Proj")

    test_case = MagicMock()
    test_case.fields = {"System.IterationPath": "", "System.AreaPath": "", "System.Tags": ""}
    test_case.relations = []

    captured_patch_doc = {}

    def fake_create_work_item(patch_doc, project, work_item_type):
        for op in patch_doc:
            if op.path == "/fields/Microsoft.VSTS.TCM.ReproSteps":
                captured_patch_doc["repro_html"] = op.value
        new_bug = MagicMock()
        new_bug.id = 4
        return new_bug

    client = MagicMock()
    client.get_work_item.return_value = test_case
    client.create_work_item.side_effect = fake_create_work_item
    mock_get_client.return_value = client

    long_error = (
        "playwright._impl._errors.TimeoutError: Locator.wait_for: "
        "Timeout 10000ms exceeded while waiting for locator '#confirmation-banner' "
        "to become visible after form submission on the Contact Us page."
    )

    bugs.create_bug(
        test_case_id=129782,
        test_name="test_z",
        error_message=long_error,
        actual_result="No confirmation message appeared.",
    )

    repro_html = captured_patch_doc["repro_html"]
    assert "Automation Failure Root Cause" in repro_html
    assert long_error in repro_html
    assert "No confirmation message appeared." in repro_html

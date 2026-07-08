"""
Tests for core/discovery.py — sprint PBI validation gate.
Policy: Description is the hard requirement; missing AC does NOT skip a PBI,
it only flags it (has_ac=False + validation_note) so assumptions are stated.
Azure client is mocked.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import core.discovery as discovery


def _pbi(pbi_id, title, description, ac):
    return SimpleNamespace(
        id=pbi_id,
        fields={
            "System.Title": title,
            "System.Description": description,
            "Microsoft.VSTS.Common.AcceptanceCriteria": ac,
        },
    )


def _run(items):
    client = MagicMock()
    client.query_by_wiql.return_value = SimpleNamespace(
        work_items=[SimpleNamespace(id=i.id) for i in items]
    )
    client.get_work_items.return_value = items
    with patch.object(discovery, "get_azure_client", return_value=client):
        return discovery.get_pbis_from_sprint("Asiacell eCommerce Platform\\Headless Implementation")


class TestSprintValidationGate:
    def test_desc_and_ac_is_valid(self):
        r = _run([_pbi(1, "Checkout API", "desc", "AC list")])
        assert r["valid_count"] == 1 and r["skipped_count"] == 0
        assert r["pbis"][0]["has_ac"] is True
        assert r["pbis"][0]["validation_note"] == ""

    def test_missing_ac_is_STILL_valid_but_flagged(self):
        r = _run([_pbi(2, "Headless PDP", "Technical description of the PDP API", "")])
        assert r["valid_count"] == 1, "PBI with description but no AC must NOT be skipped"
        assert r["skipped_count"] == 0
        assert r["no_ac_count"] == 1
        pbi = r["pbis"][0]
        assert pbi["has_ac"] is False
        assert "ASSUMPTIONS" in pbi["validation_note"]
        assert pbi["ac"] == "[No AC provided]"

    def test_missing_description_is_skipped(self):
        r = _run([_pbi(3, "Empty one", "", "has AC though")])
        assert r["valid_count"] == 0 and r["skipped_count"] == 1
        assert r["skipped_pbis"][0]["validation_reason"] == "Missing or empty Description field"

    def test_whitespace_description_is_skipped(self):
        r = _run([_pbi(4, "Whitespace", "   \n  ", "")])
        assert r["skipped_count"] == 1

    def test_mixed_sprint_counts(self):
        r = _run([
            _pbi(1, "Full", "d", "a"),
            _pbi(2, "No AC", "d", ""),
            _pbi(3, "No desc", "", ""),
        ])
        assert r["count"] == 3
        assert r["valid_count"] == 2
        assert r["skipped_count"] == 1
        assert r["no_ac_count"] == 1

    def test_arabic_detection_still_works(self):
        r = _run([_pbi(5, "التحقق من الدفع", "وصف بالعربي", "")])
        assert r["pbis"][0]["language"] == "ar"
        assert r["arabic_count"] == 1

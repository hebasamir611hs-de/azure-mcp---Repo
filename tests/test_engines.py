"""
Unit tests for core/engines.py shared helpers — tag string building and the
TF401289 tag-permission fallback. Azure client is mocked.
Run: pytest tests/ -v
"""

from unittest.mock import MagicMock

from core.engines import _build_tags_string, _create_with_tag_fallback


class TestBuildTagsString:
    def test_provenance_always_first(self):
        assert _build_tags_string([]).startswith("Ai_MCP_Injected")
        assert _build_tags_string(None) == "Ai_MCP_Injected"

    def test_agent_tags_passed_verbatim(self):
        tags = _build_tags_string(["UAT", "Regression", "TAG", "Web", "Functional-High"])
        assert tags == "Ai_MCP_Injected; UAT; Regression; TAG; Web; Functional-High"

    def test_dedupe_case_insensitive(self):
        tags = _build_tags_string(["uat", "UAT", "ai_mcp_injected", "Web", "web"])
        assert tags == "Ai_MCP_Injected; uat; Web"

    def test_blank_entries_ignored(self):
        tags = _build_tags_string(["", "  ", None, "Web"])
        assert tags == "Ai_MCP_Injected; Web"


class _Op:
    def __init__(self, path):
        self.path = path


class TestTagFallback:
    def test_success_first_try(self):
        client = MagicMock()
        client.create_work_item.return_value = MagicMock(id=1)
        wi, applied = _create_with_tag_fallback(client, "P", [_Op("/fields/System.Title")])
        assert applied is True
        assert client.create_work_item.call_count == 1

    def test_tf401289_retries_without_tags(self):
        client = MagicMock()
        ok = MagicMock(id=2)
        client.create_work_item.side_effect = [Exception("TF401289: tags denied"), ok]
        patch_doc = [_Op("/fields/System.Title"), _Op("/fields/System.Tags")]
        wi, applied = _create_with_tag_fallback(client, "P", patch_doc)
        assert applied is False
        assert wi.id == 2
        # Second call must NOT contain the tags operation
        retry_doc = client.create_work_item.call_args_list[1][0][0]
        assert all(op.path != "/fields/System.Tags" for op in retry_doc)

    def test_other_errors_propagate(self):
        client = MagicMock()
        client.create_work_item.side_effect = Exception("VS402323: iteration invalid")
        try:
            _create_with_tag_fallback(client, "P", [_Op("/fields/System.Title")])
            assert False, "should have raised"
        except Exception as e:
            assert "VS402323" in str(e)

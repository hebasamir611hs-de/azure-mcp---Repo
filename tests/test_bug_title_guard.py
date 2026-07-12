"""
Tests for the plain-English bug-title guard (team review feedback, July 2026):
titles must never carry raw technical errors — those live in Repro Steps.
"""

from core.bugs import _sanitize_title_summary


class TestTitleGuard:
    def test_plain_english_actual_result_used(self):
        s = _sanitize_title_summary(
            "No confirmation message appeared and the form was not cleared", "TimeoutError: xyz"
        )
        assert s == "No confirmation message appeared and the form was not cleared"

    def test_missing_actual_result_never_falls_back_to_error(self):
        s = _sanitize_title_summary("", "TimeoutError: locator('#submit') waited 30000ms")
        assert "TimeoutError" not in s
        assert "Repro Steps" in s

    def test_technical_actual_result_replaced(self):
        s = _sanitize_title_summary("AssertionError: expected 200 got 500", "trace...")
        assert "AssertionError" not in s and "500" not in s

    def test_stack_trace_fragment_replaced(self):
        s = _sanitize_title_summary('File "checkout.py", at line 42', "")
        assert "line 42" not in s

    def test_http_status_replaced(self):
        s = _sanitize_title_summary("Server returned HTTP 500 on submit", "")
        assert "500" not in s

    def test_business_words_containing_error_like_tokens_pass(self):
        # 'error message' as a business phrase is fine — user-facing behaviour
        s = _sanitize_title_summary("No validation message shown for the empty field", "")
        assert s.startswith("No validation message")

    def test_truncated_to_100(self):
        s = _sanitize_title_summary("A" * 300, "")
        assert len(s) <= 100

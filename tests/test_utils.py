"""
Unit tests for core/utils.py — pure functions only, no Azure I/O.
Run: pytest tests/ -v
"""

import pytest

from core.utils import (
    is_arabic,
    format_azure_steps,
    parse_steps_xml,
    validate_tc_attributes,
    normalize_execution_type,
    assess_priority,
    classify_tc_from_tags,
    sanitize_wiql_string,
    infer_tc_attributes_from_title,
)


# ─── is_arabic ────────────────────────────────────────────────────────────────

class TestIsArabic:
    def test_arabic_text(self):
        assert is_arabic("التحقق من أنه يمكن الدفع")

    def test_english_text(self):
        assert not is_arabic("Verify that payment works")

    def test_empty(self):
        assert not is_arabic("")
        assert not is_arabic(None)

    def test_mixed(self):
        assert is_arabic("Verify دفع flow")


# ─── steps XML round-trip ─────────────────────────────────────────────────────

class TestStepsXml:
    def test_round_trip(self):
        steps = ["Open app", "Tap Top-Up", "Enter 50 QAR"]
        expected = ["App opens", "Top-Up screen shows", "Amount accepted"]
        xml = format_azure_steps(steps, expected)
        parsed = parse_steps_xml(xml)
        assert [p["action"] for p in parsed] == steps
        assert [p["expected"] for p in parsed] == expected

    def test_special_chars_escaped(self):
        xml = format_azure_steps(['Enter "<script>"'], ["Rejected & sanitized"])
        parsed = parse_steps_xml(xml)
        assert parsed[0]["action"] == 'Enter "<script>"'
        assert parsed[0]["expected"] == "Rejected & sanitized"

    def test_empty_xml(self):
        assert parse_steps_xml("") == []

    def test_corrupt_xml(self):
        out = parse_steps_xml("<steps><broken")
        assert out[0]["action"] == "XML parse error"


# ─── validate_tc_attributes ──────────────────────────────────────────────────

class TestValidate:
    def _valid_args(self, **over):
        args = dict(
            title="Verify that top-up succeeds with 50 QAR",
            steps_list=["step"], expected_list=["result"],
            test_type="Functional", scenario="positive",
            execution_type="Automated", impact_area="Both", language="en",
        )
        args.update(over)
        return args

    def test_valid_english(self):
        ok, msg = validate_tc_attributes(**self._valid_args())
        assert ok, msg

    def test_valid_arabic_prefix(self):
        ok, _ = validate_tc_attributes(**self._valid_args(
            title="التحقق من أنه يمكن الشحن", language="ar"))
        assert ok

    def test_wrong_prefix_rejected(self):
        ok, msg = validate_tc_attributes(**self._valid_args(title="Check top-up"))
        assert not ok and "Verify that" in msg

    def test_step_count_mismatch(self):
        ok, msg = validate_tc_attributes(**self._valid_args(expected_list=["a", "b"]))
        assert not ok

    def test_bad_exec_type(self):
        ok, _ = validate_tc_attributes(**self._valid_args(execution_type="Robot"))
        assert not ok


# ─── normalize_execution_type (Automation-tag ↔ Automated-attribute friction) ─

class TestNormalizeExecType:
    @pytest.mark.parametrize("raw,expected", [
        ("Automation", "Automated"),
        ("automation", "Automated"),
        ("Automated", "Automated"),
        ("Manual", "Manual"),
        ("manual", "Manual"),
        ("", ""),
        (None, ""),
    ])
    def test_normalization(self, raw, expected):
        assert normalize_execution_type(raw) == expected

    def test_normalized_value_passes_validation(self):
        ok, _ = validate_tc_attributes(
            title="Verify that x", steps_list=["s"], expected_list=["e"],
            test_type="Functional", scenario="positive",
            execution_type=normalize_execution_type("Automation"),
            impact_area="Both", language="en",
        )
        assert ok


# ─── assess_priority (bilingual money rule) ──────────────────────────────────

class TestAssessPriority:
    def test_english_payment_negative_is_p1(self):
        assert assess_priority("Top-up payment", "", "Functional", "negative") == 1

    def test_arabic_payment_negative_is_p1(self):
        assert assess_priority("شحن رصيد المحفظة", "عملية دفع", "Functional", "negative") == 1

    def test_arabic_login_positive_is_p2(self):
        assert assess_priority("تسجيل الدخول للتطبيق", "", "Functional", "positive") == 2

    def test_non_critical_positive(self):
        assert assess_priority("Change avatar", "", "UI", "positive") == 2


# ─── classify_tc_from_tags (current taxonomy) ────────────────────────────────

class TestClassify:
    def test_current_taxonomy_functional_high(self):
        cls = classify_tc_from_tags(
            ["Ai_MCP_Injected", "Functional-High", "Regression", "Automation", "TAG", "Web"],
            "Verify that top-up succeeds",
        )
        assert cls["test_type"] == "Functional"
        assert cls["category"] == "Functional-High"
        assert cls["execution_type"] == "Automated"
        assert cls["source"] == "tags"

    def test_current_taxonomy_edge_manual(self):
        cls = classify_tc_from_tags(["Edge", "Manual", "FAHES", "Android"], "Verify that x")
        assert cls["test_type"] == "Edge"
        assert cls["category"] == "Edge"
        assert cls["execution_type"] == "Manual"

    def test_specific_category_beats_ui(self):
        cls = classify_tc_from_tags(["UI", "Functional-Low", "Web"], "Verify that field rejects empty")
        assert cls["category"] == "Functional-Low"
        assert cls["test_type"] == "Functional"

    def test_legacy_tags_still_work(self):
        cls = classify_tc_from_tags(["Functional", "negative", "Automated"], "Verify that x")
        assert cls["test_type"] == "Functional"
        assert cls["scenario"] == "negative"
        assert cls["execution_type"] == "Automated"

    def test_untagged_falls_back_to_title(self):
        cls = classify_tc_from_tags([], "Verify that invalid card is rejected with error")
        assert cls["scenario"] == "negative"
        assert cls["category"] is None
        assert cls["source"] == "inferred_from_title"

    def test_case_insensitive(self):
        cls = classify_tc_from_tags(["functional-high", "AUTOMATION"], "Verify that x")
        assert cls["test_type"] == "Functional"
        assert cls["execution_type"] == "Automated"

    def test_scenario_inferred_when_not_tagged(self):
        # Current model never emits positive/negative tags — must infer from title
        cls = classify_tc_from_tags(["Functional-High", "Automation"], "Verify that error appears on failed payment")
        assert cls["scenario"] == "negative"


# ─── sanitize_wiql_string ────────────────────────────────────────────────────

class TestSanitize:
    def test_escapes_quotes(self):
        assert sanitize_wiql_string("Sprint 'X'") == "Sprint ''X''"

    def test_passthrough(self):
        assert sanitize_wiql_string("Woqod\\Sprint 8") == "Woqod\\Sprint 8"
        assert sanitize_wiql_string("") == ""


# ─── infer_tc_attributes_from_title ──────────────────────────────────────────

class TestInference:
    def test_negative_keywords(self):
        assert infer_tc_attributes_from_title("Verify invalid OTP is rejected")["scenario"] == "negative"

    def test_arabic_negative(self):
        assert infer_tc_attributes_from_title("التحقق من رسالة خطأ")["scenario"] == "negative"

    def test_edge_keyword(self):
        assert infer_tc_attributes_from_title("Verify maximum length boundary")["test_type"] == "Edge"

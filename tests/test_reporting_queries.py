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

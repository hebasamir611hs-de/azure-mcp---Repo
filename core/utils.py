"""
core/utils.py — Shared helpers, validators, classifiers, and Azure client factory.

All functions here are pure utilities with no MCP or Azure I/O side-effects,
except get_azure_client() which constructs a client from environment vars.
"""

import os
import re
import xml.etree.ElementTree as ET

from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from msrest.exceptions import AuthenticationError, ClientRequestError, HttpOperationError
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml


# ─────────────────────────────────────────────────────────────────────────────
# LANGUAGE DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def is_arabic(text: str) -> bool:
    """Returns True if text contains Arabic characters (full Unicode range)."""
    if not text:
        return False
    arabic_pattern = re.compile(r'[؀-ۿݐ-ݿࢠ-ࣿ]+')
    return len(arabic_pattern.findall(text)) > 0


# ─────────────────────────────────────────────────────────────────────────────
# AZURE CLIENT
# ─────────────────────────────────────────────────────────────────────────────

def get_azure_client():
    """Returns an authenticated Azure DevOps Work Item Tracking client."""
    pat = os.getenv("AZURE_PAT")
    org_url = os.getenv("AZURE_ORG_URL")
    credentials = BasicAuthentication('', pat)
    connection = Connection(base_url=org_url, creds=credentials)
    return connection.clients.get_work_item_tracking_client()


# ─────────────────────────────────────────────────────────────────────────────
# XML / STEPS FORMATTING
# ─────────────────────────────────────────────────────────────────────────────

def format_azure_steps(steps_list: list, expected_list: list) -> str:
    """Converts step/expected pairs to Azure DevOps TCM.Steps XML format."""
    steps_xml = ET.Element("steps", version="1.0", last="0")
    for i, (step, exp) in enumerate(zip(steps_list, expected_list), 1):
        step_node = ET.SubElement(steps_xml, "step", id=str(i), type="ActionStep")
        action_node = ET.SubElement(step_node, "parameterizedString", isformatted="true")
        action_node.text = step
        expected_node = ET.SubElement(step_node, "parameterizedString", isformatted="true")
        expected_node.text = exp
        desc_node = ET.SubElement(step_node, "description")
        desc_node.text = ""
    return ET.tostring(steps_xml, encoding="unicode")


def parse_steps_xml(steps_xml: str) -> list:
    """Parses Azure TCM.Steps XML into list of {action, expected} dicts."""
    if not steps_xml:
        return []
    try:
        root = ET.fromstring(steps_xml)
        steps = []
        for step_node in root.findall('.//step'):
            params = step_node.findall('parameterizedString')
            if len(params) >= 2:
                steps.append({
                    "action": params[0].text or '',
                    "expected": params[1].text or ''
                })
        return steps
    except ET.ParseError:
        return [{"action": "XML parse error", "expected": ""}]


# ─────────────────────────────────────────────────────────────────────────────
# TC ATTRIBUTE VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

VALID_TEST_TYPES = ["UI", "Functional", "Edge", "Intensive"]
VALID_SCENARIOS = ["positive", "negative"]
VALID_EXEC_TYPES = ["Automated", "Manual"]
VALID_IMPACT_AREAS = ["UI", "Backend", "Both"]


def normalize_execution_type(value: str) -> str:
    """
    Normalizes execution-type vocabulary to the canonical attribute values.
    The tag taxonomy (woqod-standards.md Axis 1b) uses 'Automation'/'Manual';
    the work-item attribute uses 'Automated'/'Manual'. Accept both, emit one.
    """
    if not value:
        return ""
    v = value.strip().lower()
    if v in ("automation", "automated", "auto"):
        return "Automated"
    if v == "manual":
        return "Manual"
    return value.strip()


def validate_tc_attributes(
    title: str, steps_list: list, expected_list: list,
    test_type: str, scenario: str, execution_type: str,
    impact_area: str, language: str
) -> tuple:
    """
    Validates all six mandatory TC attributes.
    Returns: (is_valid: bool, error_message: str)
    """
    prefix = "التحقق من أنه" if language == "ar" else "Verify that"
    if not title.strip().startswith(prefix):
        return False, f"Title must start with '{prefix}'"

    if len(steps_list) != len(expected_list):
        return False, f"Steps count ({len(steps_list)}) != Expected count ({len(expected_list)})"

    if not steps_list:
        return False, "Steps list cannot be empty"

    if test_type not in VALID_TEST_TYPES:
        return False, f"test_type must be one of {VALID_TEST_TYPES}"

    if scenario not in VALID_SCENARIOS:
        return False, "scenario must be 'positive' or 'negative'"

    if execution_type not in VALID_EXEC_TYPES:
        return False, f"execution_type must be one of {VALID_EXEC_TYPES}"

    if impact_area not in VALID_IMPACT_AREAS:
        return False, f"impact_area must be one of {VALID_IMPACT_AREAS}"

    return True, ""


# ─────────────────────────────────────────────────────────────────────────────
# SMART ATTRIBUTE INFERENCE
# ─────────────────────────────────────────────────────────────────────────────

def assess_priority(pbi_title: str, pbi_ac: str, test_type: str, scenario: str) -> int:
    """
    Heuristic priority assessment based on PBI content and test scenario.
    Returns: 1 (Critical), 2 (High), 3 (Medium), 4 (Low)
    """
    critical_keywords = [
        # English
        "payment", "security", "authentication", "checkout",
        "login", "critical", "must", "billing", "top-up", "topup",
        "wallet", "balance", "refund",
        # Arabic — the project is bilingual; money/access flows must hit P1
        # regardless of PBI language (woqod-standards.md → Money & Payment Rules).
        "دفع", "سداد", "فوترة", "شحن", "رصيد", "محفظة",
        "تسجيل الدخول", "دخول", "مصادقة", "أمان", "أمن", "استرداد"
    ]
    pbi_text = (pbi_title + " " + pbi_ac).lower()

    for keyword in critical_keywords:
        if keyword in pbi_text:
            return 1 if scenario == "negative" else 2

    if scenario == "positive":
        return 2 if test_type in ["UI", "Functional"] else 3

    if scenario == "negative" or test_type == "Edge":
        return 3

    return 4


def determine_execution_type(test_type: str, impact_area: str) -> str:
    """
    Auto-determines Automated vs Manual based on test complexity.
    UI-only and Intensive tests default to Manual; everything else Automated.
    """
    if test_type == "UI" and impact_area == "UI":
        return "Manual"
    if test_type == "Intensive":
        return "Manual"
    return "Automated"


def infer_tc_attributes_from_title(title: str) -> dict:
    """
    Fallback: infers test_type, scenario, execution_type, impact_area from
    TC title keywords when Azure tags are absent. Used by Skills 5 and 7.
    """
    title_lower = title.lower()

    if any(kw in title_lower for kw in ["ui", "interface", "display", "layout", "button", "screen", "واجهة", "عرض"]):
        test_type = "UI"
    elif any(kw in title_lower for kw in ["boundary", "edge", "limit", "maximum", "minimum", "حدود", "حدية"]):
        test_type = "Edge"
    elif any(kw in title_lower for kw in ["intensive", "performance", "load", "stress", "complex", "أداء", "مكثف"]):
        test_type = "Intensive"
    else:
        test_type = "Functional"

    if any(kw in title_lower for kw in ["invalid", "error", "fail", "reject", "negative", "wrong", "خطأ", "غير صالح", "رفض"]):
        scenario = "negative"
    else:
        scenario = "positive"

    execution_type = "Manual" if test_type in ["UI", "Intensive"] else "Automated"
    impact_area = "UI" if test_type == "UI" else "Both"

    return {
        "test_type": test_type,
        "scenario": scenario,
        "execution_type": execution_type,
        "impact_area": impact_area,
        "source": "inferred_from_title"
    }


# ─────────────────────────────────────────────────────────────────────────────
# TC CLASSIFICATION FROM TAGS (current taxonomy) — shared by Skills 5 & 7
# ─────────────────────────────────────────────────────────────────────────────

# Axis 4 Category tags (woqod-standards.md) → coverage-matrix test_type
_CATEGORY_TO_TEST_TYPE = {
    "ui": "UI",
    "compatibility": "Functional",
    "auth": "Functional",
    "functional-high": "Functional",
    "functional-low": "Functional",
    "api": "Functional",
    "edge": "Edge",
}

_CANONICAL_CATEGORIES = {
    "ui": "UI", "compatibility": "Compatibility", "auth": "Auth",
    "functional-high": "Functional-High", "functional-low": "Functional-Low",
    "api": "API", "edge": "Edge",
}


def classify_tc_from_tags(tag_list: list, title: str) -> dict:
    """
    Derives test_type / scenario / execution_type / impact_area / category for a
    test case from its Azure tags under the CURRENT unified tagging model
    (woqod-standards.md → Tag Taxonomy), with legacy-tag and title-inference
    fallbacks per attribute.

    Sources, in priority order per attribute:
      1. Current taxonomy tags — Category (Axis 4): UI/Compatibility/Auth/
         Functional-High/Functional-Low/API/Edge; Execution method (Axis 1b):
         Automation/Manual.
      2. Legacy attribute tags (older injections): UI/Functional/Edge/Intensive,
         positive/negative, Automated/Manual, Backend/Both.
      3. Title-keyword inference (infer_tc_attributes_from_title).

    Returns:
        {test_type, scenario, execution_type, impact_area,
         category (canonical Axis-4 value or None), source}
    """
    tags_lower = [t.strip().lower() for t in (tag_list or []) if t and t.strip()]
    inferred = infer_tc_attributes_from_title(title or "")
    used_tags = False

    # ── Category / test_type ────────────────────────────────────────────────
    category = None
    test_type = None
    for t in tags_lower:
        if t in _CATEGORY_TO_TEST_TYPE:
            # Prefer the most specific category tag; first match wins except
            # plain 'ui' loses to a more specific functional/edge category.
            if category is None or category == "UI":
                category = _CANONICAL_CATEGORIES[t]
                test_type = _CATEGORY_TO_TEST_TYPE[t]
    if test_type is None and "intensive" in tags_lower:   # legacy
        test_type = "Intensive"
    if test_type is None and "functional" in tags_lower:  # legacy
        test_type = "Functional"
    if test_type is not None:
        used_tags = True
    else:
        test_type = inferred["test_type"]

    # ── Scenario (never emitted as a tag in the current model) ──────────────
    if "positive" in tags_lower:      # legacy
        scenario, used_tags = "positive", True
    elif "negative" in tags_lower:    # legacy
        scenario, used_tags = "negative", True
    else:
        scenario = inferred["scenario"]

    # ── Execution type — Axis 1b (Automation/Manual) or legacy (Automated) ──
    if "automation" in tags_lower or "automated" in tags_lower:
        execution_type, used_tags = "Automated", True
    elif "manual" in tags_lower:
        execution_type, used_tags = "Manual", True
    else:
        execution_type = inferred["execution_type"]

    # ── Impact area (legacy tags only; 'UI' is ambiguous with Category) ─────
    if "backend" in tags_lower:
        impact_area = "Backend"
    elif "both" in tags_lower:
        impact_area = "Both"
    else:
        impact_area = inferred["impact_area"]

    return {
        "test_type": test_type,
        "scenario": scenario,
        "execution_type": execution_type,
        "impact_area": impact_area,
        "category": category,
        "source": "tags" if used_tags else "inferred_from_title",
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECURITY & QUERY HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def sanitize_wiql_string(value: str) -> str:
    """Escapes single quotes in WIQL parameters to prevent query injection."""
    if not value:
        return value
    return value.replace("'", "''")


# ─────────────────────────────────────────────────────────────────────────────
# ERROR HANDLING
# ─────────────────────────────────────────────────────────────────────────────

def handle_error(e: Exception, skill_name: str) -> dict:
    """Centralized structured error handler with actionable messages per exception type."""
    if isinstance(e, AuthenticationError):
        return {
            "error": f"[{skill_name}] Authentication failed — check AZURE_PAT is valid and not expired.",
            "error_type": "auth"
        }
    elif isinstance(e, ClientRequestError):
        return {
            "error": f"[{skill_name}] Network/connection error — Azure DevOps may be unreachable. Details: {str(e)}",
            "error_type": "network"
        }
    elif isinstance(e, HttpOperationError):
        return {
            "error": f"[{skill_name}] Azure API rejected the request — check iteration_path, project name, or work item IDs. Details: {str(e)}",
            "error_type": "api"
        }
    elif isinstance(e, ET.ParseError):
        return {
            "error": f"[{skill_name}] XML parsing failed — corrupted TCM.Steps field. Details: {str(e)}",
            "error_type": "parse"
        }
    elif isinstance(e, (FileNotFoundError, PermissionError)):
        return {
            "error": f"[{skill_name}] File system error — {str(e)}",
            "error_type": "file"
        }
    elif isinstance(e, (ValueError, KeyError, TypeError)):
        return {
            "error": f"[{skill_name}] Data validation error — unexpected data format. Details: {str(e)}",
            "error_type": "validation"
        }
    else:
        return {
            "error": f"[{skill_name}] Unexpected error: {type(e).__name__}: {str(e)}",
            "error_type": "unknown"
        }


# ─────────────────────────────────────────────────────────────────────────────
# DOCX HELPERS (used by output_manager.py)
# ─────────────────────────────────────────────────────────────────────────────

def apply_rtl(paragraph):
    """Applies RTL direction to a paragraph for Arabic text rendering."""
    pPr = paragraph._p.get_or_add_pPr()
    bidi = parse_xml(f'<w:bidi {nsdecls("w")} val="1"/>')
    pPr.append(bidi)


def set_cell_shading(cell, color: str):
    """Applies background shading to a table cell."""
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color}" w:val="clear"/>')
    cell._tc.get_or_add_tcPr().append(shading)


def merge_cells_in_row(table, row_idx: int, start_col: int, end_col: int):
    """Merges a range of cells in a single table row."""
    table.cell(row_idx, start_col).merge(table.cell(row_idx, end_col))

"""
core/utils.py — Shared helpers, validators, and Azure client factory.

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
        "payment", "security", "authentication", "checkout",
        "login", "critical", "must", "billing"
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

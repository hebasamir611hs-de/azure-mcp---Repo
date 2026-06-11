"""
core/output_manager.py — Document parsing & review: Skill 11a.

Deliverable *creation* (UAT docs, automation suites) is intentionally not an
MCP tool — the agent layer owns production (see .claude/skills/build-uat-doc
and the drafter subagent). This module only parses documents for review.

All functions are plain — no @mcp.tool() decorators. Registration happens in server.py.
"""

import os

from docx import Document as DocxDocument
from docx.oxml.ns import qn

from core.utils import (
    handle_error,
    is_arabic,
)


# ─────────────────────────────────────────────────────────────────────────────
# SKILL 11a: UAT DOCUMENT REVIEW
# ─────────────────────────────────────────────────────────────────────────────

def review_uat_document(uat_file_path: str) -> dict:
    """
    SKILL 11a: UAT Review & Analysis

    Parses an existing UAT .docx and extracts structured content for QA review.

    Args:
        uat_file_path (str): Path to UAT .docx file

    Returns:
        {status, file_path, language, total_sections, sections, review_instructions}
    """
    try:
        if not os.path.exists(uat_file_path):
            return {"error": f"File not found: {uat_file_path}"}

        doc = DocxDocument(uat_file_path)
        sections = []
        current_section = {"heading": "Document Start", "content": [], "tables": []}

        for element in doc.element.body:
            tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
            if tag == 'p':
                pPr = element.find(qn('w:pPr'))
                if pPr is not None:
                    pStyle = pPr.find(qn('w:pStyle'))
                    if pStyle is not None and 'Heading' in pStyle.get(qn('w:val'), ''):
                        if current_section["content"] or current_section["tables"]:
                            sections.append(current_section)
                        text = ''.join(node.text or '' for node in element.iter(qn('w:t')))
                        current_section = {"heading": text, "content": [], "tables": []}
                        continue
                text = ''.join(node.text or '' for node in element.iter(qn('w:t')))
                if text.strip():
                    current_section["content"].append(text.strip())
            elif tag == 'tbl':
                table_data = [
                    [''.join(node.text or '' for node in cell.iter(qn('w:t'))).strip()
                     for cell in row.findall(qn('w:tc'))]
                    for row in element.findall(qn('w:tr'))
                ]
                current_section["tables"].append(table_data)

        if current_section["content"] or current_section["tables"]:
            sections.append(current_section)

        all_text = " ".join(" ".join(s["content"]) for s in sections)
        detected_lang = "ar" if is_arabic(all_text) else "en"

        return {
            "status": "parsed",
            "file_path": uat_file_path,
            "language": detected_lang,
            "total_sections": len(sections),
            "sections": sections,
            "review_instructions": "As QA Manager, review this UAT document for completeness, quality, and gaps."
        }

    except Exception as e:
        return handle_error(e, "review_uat_document")

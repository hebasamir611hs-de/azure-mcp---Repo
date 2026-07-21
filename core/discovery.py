"""
core/discovery.py — Skill 0: PBI Deduplication, Skill 1: Smart PBI Discovery.

Also contains legacy get_story_for_analysis for backward compatibility.
All functions are plain — no @mcp.tool() decorators. Registration happens in server.py.
"""

import os
import re
from base64 import b64decode, b64encode

import requests
from azure.devops.v7_1.work_item_tracking.models import Wiql
from mcp.server.fastmcp import Image

from core.utils import (
    get_azure_client,
    handle_error,
    is_arabic,
    sanitize_wiql_string,
)


# ─────────────────────────────────────────────────────────────────────────────
# IMAGE DETECTION HELPERS (shared by get_story_for_analysis[_with_images])
#
# Two ways an image reaches a PBI, both resolving to an attachment URL:
#   (A) uploaded as a backlog Attachment  → work-item relation rel == "AttachedFile"
#   (B) pasted into Description / AC       → <img src=".../_apis/wit/attachments/..">
# Detection below is METADATA-ONLY (no download, no vision cost). Actual image
# bytes are fetched only by get_story_for_analysis_with_images().
# ─────────────────────────────────────────────────────────────────────────────

_IMG_SRC_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
_IMAGE_EXT_RE = re.compile(r'\.(png|jpe?g|gif|bmp|webp|tiff?|svg)(?:$|\?)', re.IGNORECASE)


def _auth_headers_basic() -> dict:
    """Basic-auth header from the PAT in .env (for raw attachment GETs the SDK
    does not expose)."""
    pat = os.getenv("AZURE_PAT", "").strip()
    token = b64encode(f":{pat}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def _guess_image_format(name_or_url: str) -> str:
    m = _IMAGE_EXT_RE.search(name_or_url or "")
    if not m:
        return "png"
    ext = m.group(1).lower()
    return "jpeg" if ext in ("jpg", "jpeg") else ext


def _looks_like_image_attachment(name: str) -> bool:
    return bool(name and _IMAGE_EXT_RE.search(name))


def _collect_image_sources(item, description: str, ac: str) -> list:
    """Returns metadata-only descriptors for every image referenced by a work
    item — NO bytes downloaded. Each entry: {index, type, filename, url}.
      type == "inline"     → pasted into Description/AC (case B)
      type == "attachment" → uploaded as a backlog attachment (case A)
    """
    sources, seen = [], set()

    # (B) inline <img> in Description + Acceptance Criteria HTML
    for html in (description or "", ac or ""):
        for src in _IMG_SRC_RE.findall(html):
            key = src.strip()
            if not key or key in seen:
                continue
            seen.add(key)
            fname = ""
            m = re.search(r'fileName=([^&"\']+)', src, re.IGNORECASE)
            if m:
                fname = m.group(1)
            elif src.lower().startswith("data:image"):
                fname = "(pasted inline image)"
            sources.append({"type": "inline", "filename": fname, "url": src})

    # (A) backlog attachments — relation rel == "AttachedFile", image types only
    for rel in (getattr(item, "relations", None) or []):
        if getattr(rel, "rel", "") != "AttachedFile":
            continue
        attrs = getattr(rel, "attributes", None) or {}
        name = attrs.get("name", "") if isinstance(attrs, dict) else ""
        url = getattr(rel, "url", "")
        if not url or url in seen or not _looks_like_image_attachment(name):
            continue
        seen.add(url)
        sources.append({"type": "attachment", "filename": name, "url": url})

    for i, s in enumerate(sources, 1):
        s["index"] = i
    return sources


def _download_image(source: dict):
    """Fetches one image source → a FastMCP Image (or None on failure).
    Handles data: URIs, attachment URLs, and external <img> URLs."""
    url = source.get("url", "")
    fname = source.get("filename", "")
    try:
        if url.lower().startswith("data:image"):
            header, _, b64data = url.partition(",")
            fmt = "jpeg" if "jpeg" in header or "jpg" in header else (
                "gif" if "gif" in header else "png")
            return Image(data=b64decode(b64data), format=fmt)
        params = {"download": "true", "api-version": "7.1"}
        if fname and "filename=" not in url.lower():
            params["fileName"] = fname
        resp = requests.get(url, params=params, headers=_auth_headers_basic(), timeout=60)
        if resp.status_code != 200:
            return None
        return Image(data=resp.content, format=_guess_image_format(fname or url))
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# LEGACY (+ metadata-only image detection)
# ─────────────────────────────────────────────────────────────────────────────

def get_story_for_analysis(story_id: int) -> dict:
    """
    Fetches a single work item's title, acceptance criteria, and description,
    plus METADATA-ONLY detection of any images it references (no download, no
    vision cost). Maintained for backward compatibility — title/ac keys are
    unchanged; description + image_* keys are additive.

    If images are detected (has_images == True), the skill layer must STOP and
    ask the human whether to treat them as design input. Only on "yes" does it
    fall back to get_story_for_analysis_with_images() — which actually downloads
    the pixels and costs vision tokens.

    Args:
        story_id: Azure work item ID

    Returns:
        {
            "title": str,
            "ac": str,
            "description": str,
            "has_images": bool,
            "image_count": int,
            "image_sources": [{index, type, filename}],  # metadata only, no bytes
            "image_note": str                            # human-gate instruction when has_images
        }
    """
    try:
        client = get_azure_client()
        item = client.get_work_item(story_id, expand="All")
        title = item.fields.get('System.Title')
        ac = item.fields.get('Microsoft.VSTS.Common.AcceptanceCriteria', 'No AC')
        description = item.fields.get('System.Description', '') or ''

        sources = _collect_image_sources(item, description, ac)
        return {
            "title": title,
            "ac": ac,
            "description": description,
            "has_images": bool(sources),
            "image_count": len(sources),
            # metadata only — never the bytes; strip the internal url from the payload
            "image_sources": [
                {"index": s["index"], "type": s["type"], "filename": s["filename"]}
                for s in sources
            ],
            "image_note": (
                "" if not sources else
                f"{len(sources)} image(s) detected in this PBI (description and/or "
                "attachments). STOP and ask the human: 'Should I consider the attached "
                "image(s) as design?' If YES → call get_story_for_analysis_with_images "
                "to view them (vision cost). If NO → neglect the images and proceed on "
                "text only."
            ),
        }
    except Exception as e:
        return handle_error(e, "get_story_for_analysis")


def get_story_for_analysis_with_images(story_id: int) -> list:
    """
    VISION-COST fallback of get_story_for_analysis. Call this ONLY after the
    human has confirmed the PBI's images should be treated as design input —
    the ask-gate lives in the analyze-pbi / quick-test-cases skill procedures,
    not here.

    Returns the same text fields AS JSON (first list item) followed by one
    viewable Image per detected source, so the agent sees the actual pixels in
    the tool result — not just a filename.

    Args:
        story_id: Azure work item ID

    Returns:
        [ "<json: {title, ac, description, image_sources[]}>", Image, Image, ... ]
        (on error, a single error dict is returned instead)
    """
    try:
        import json
        client = get_azure_client()
        item = client.get_work_item(story_id, expand="All")
        title = item.fields.get('System.Title')
        ac = item.fields.get('Microsoft.VSTS.Common.AcceptanceCriteria', 'No AC')
        description = item.fields.get('System.Description', '') or ''

        sources = _collect_image_sources(item, description, ac)
        images, downloaded_meta = [], []
        for s in sources:
            img = _download_image(s)
            meta = {"index": s["index"], "type": s["type"], "filename": s["filename"],
                    "downloaded": img is not None}
            downloaded_meta.append(meta)
            if img is not None:
                images.append(img)

        summary = {
            "title": title,
            "ac": ac,
            "description": description,
            "image_count": len(sources),
            "images_downloaded": len(images),
            "image_sources": downloaded_meta,
            "note": (
                "Images follow as viewable content. Each corresponds to an "
                "image_sources entry by order. Use them as design input for the "
                "analysis and state in the sign-off which images were considered."
                if images else
                "No images could be downloaded (all sources failed or none present)."
            ),
        }
        return [json.dumps(summary, ensure_ascii=False)] + images
    except Exception as e:
        return handle_error(e, "get_story_for_analysis_with_images")


# ─────────────────────────────────────────────────────────────────────────────
# SKILL 0: PBI DEDUPLICATION
# ─────────────────────────────────────────────────────────────────────────────

def check_pbi_duplicates(iteration_path: str) -> dict:
    """
    SKILL 0: PBI Deduplication & Validation

    ⚠️ STOP GATE — Must be the FIRST skill called in any workflow.
    Scans all PBIs in the sprint and flags potential duplicates based on
    matching Description, Acceptance Criteria, or content overlap.

    Duplicate Detection Rules:
    1. Exact match on cleaned Description text
    2. Exact match on cleaned Acceptance Criteria text
    3. Subset match: one PBI's content is fully contained within another's

    Returns:
        {
            "status": "clear" | "duplicates_detected",
            "total_pbis": int,
            "duplicate_groups": [...],
            "safe_to_proceed": bool,
            "user_action_required": str
        }
    """
    try:
        client = get_azure_client()
        project = os.getenv("AZURE_PROJECT")
        safe_iter = sanitize_wiql_string(iteration_path)
        safe_proj = sanitize_wiql_string(project)

        query = f"""
            SELECT [System.Id], [System.Title], [Microsoft.VSTS.Common.AcceptanceCriteria],
                   [System.Description]
            FROM WorkItems
            WHERE [System.WorkItemType] = 'Product Backlog Item'
              AND [System.IterationPath] = '{safe_iter}'
              AND [System.TeamProject] = '{safe_proj}'
            ORDER BY [System.Id] ASC
        """
        result = client.query_by_wiql(Wiql(query=query))

        if not result.work_items:
            return {
                "status": "clear",
                "total_pbis": 0,
                "duplicate_groups": [],
                "safe_to_proceed": True,
                "message": "No PBIs found in this sprint."
            }

        ids = [item.id for item in result.work_items]
        work_items = client.get_work_items(ids=ids, expand="All")

        def clean_text(text):
            if not text:
                return ""
            text = re.sub(r'<[^>]+>', ' ', text)
            return re.sub(r'\s+', ' ', text).strip().lower()

        pbi_list = [
            {
                "id": item.id,
                "title": item.fields.get('System.Title', ''),
                "ac_clean": clean_text(item.fields.get('Microsoft.VSTS.Common.AcceptanceCriteria', '')),
                "desc_clean": clean_text(item.fields.get('System.Description', ''))
            }
            for item in work_items
        ]

        duplicate_groups = []
        processed_ids = set()
        group_id = 1

        for i in range(len(pbi_list)):
            if pbi_list[i]["id"] in processed_ids:
                continue
            conflicts = []
            conflict_reasons = []
            conflict_fields = []

            for j in range(i + 1, len(pbi_list)):
                if pbi_list[j]["id"] in processed_ids:
                    continue

                reasons = []
                fields = []

                d_i, d_j = pbi_list[i]["desc_clean"], pbi_list[j]["desc_clean"]
                if d_i and d_j:
                    if d_i == d_j:
                        reasons.append("Identical Description")
                        fields.append("description")
                    elif len(d_i) > 30 and (d_i in d_j or d_j in d_i):
                        reasons.append("Description subset match")
                        fields.append("description")

                a_i, a_j = pbi_list[i]["ac_clean"], pbi_list[j]["ac_clean"]
                if a_i and a_j:
                    if a_i == a_j:
                        reasons.append("Identical Acceptance Criteria")
                        fields.append("ac")
                    elif len(a_i) > 30 and (a_i in a_j or a_j in a_i):
                        reasons.append("AC subset match")
                        fields.append("ac")

                if reasons:
                    conflicts.append(pbi_list[j])
                    conflict_reasons.extend(reasons)
                    conflict_fields.extend(fields)
                    processed_ids.add(pbi_list[j]["id"])

            if conflicts:
                unique_fields = list(set(conflict_fields))
                duplicate_groups.append({
                    "group_id": group_id,
                    "reason": "; ".join(set(conflict_reasons)),
                    "pbi_ids": [pbi_list[i]["id"]] + [c["id"] for c in conflicts],
                    "titles": [pbi_list[i]["title"]] + [c["title"] for c in conflicts],
                    "conflicting_field": "both" if len(unique_fields) > 1 else (unique_fields[0] if unique_fields else "unknown")
                })
                processed_ids.add(pbi_list[i]["id"])
                group_id += 1

        if duplicate_groups:
            return {
                "status": "duplicates_detected",
                "total_pbis": len(pbi_list),
                "duplicate_groups": duplicate_groups,
                "safe_to_proceed": False,
                "user_action_required": (
                    "⚠️ Potential duplicate PBIs detected. "
                    "For each group above: should I process ALL IDs, or only ONE? "
                    "If one — which ID should I proceed with? "
                    "Do NOT proceed with TC generation until you confirm."
                )
            }

        return {
            "status": "clear",
            "total_pbis": len(pbi_list),
            "duplicate_groups": [],
            "safe_to_proceed": True,
            "message": f"All {len(pbi_list)} PBIs are unique. Safe to proceed."
        }

    except Exception as e:
        return handle_error(e, "check_pbi_duplicates")


# ─────────────────────────────────────────────────────────────────────────────
# SKILL 1: SMART PBI DISCOVERY
# ─────────────────────────────────────────────────────────────────────────────

def get_pbis_from_sprint(iteration_path: str) -> dict:
    """
    SKILL 1: Smart PBI Discovery with Validation

    Fetches all PBIs from a sprint, validates them for TC readiness,
    and auto-detects language per PBI.

    Validation: a PBI is skipped ONLY if its Description is missing/empty.
    Missing Acceptance Criteria does NOT skip the PBI — it stays valid and is
    flagged (has_ac=False, validation_note set) so the analysis derives scope
    from the Description and states its assumptions explicitly at the review gate.

    Returns:
        {
            "count": int,
            "valid_count": int,
            "skipped_count": int,
            "no_ac_count": int,
            "arabic_count": int,
            "english_count": int,
            "pbis": [{id, title, ac, description, language, is_valid,
                      has_ac, validation_note, validation_reason}],
            "skipped_pbis": [...]
        }
    """
    try:
        client = get_azure_client()
        project = os.getenv("AZURE_PROJECT")
        safe_iter = sanitize_wiql_string(iteration_path)
        safe_proj = sanitize_wiql_string(project)

        query = f"""
            SELECT [System.Id], [System.Title], [Microsoft.VSTS.Common.AcceptanceCriteria],
                   [System.Description]
            FROM WorkItems
            WHERE [System.WorkItemType] = 'Product Backlog Item'
              AND [System.IterationPath] = '{safe_iter}'
              AND [System.TeamProject] = '{safe_proj}'
            ORDER BY [System.Id] ASC
        """
        result = client.query_by_wiql(Wiql(query=query))

        if not result.work_items:
            return {
                "count": 0, "valid_count": 0, "skipped_count": 0,
                "pbis": [], "skipped_pbis": [],
                "message": "No PBIs found in this sprint."
            }

        ids = [item.id for item in result.work_items]
        work_items = client.get_work_items(ids=ids, expand="All")

        pbis, skipped_pbis = [], []
        arabic_count = english_count = no_ac_count = 0

        for item in work_items:
            title = item.fields.get('System.Title', '')
            ac = item.fields.get('Microsoft.VSTS.Common.AcceptanceCriteria', '')
            description = item.fields.get('System.Description', '')

            detected_lang = "ar" if is_arabic(title) or is_arabic(ac) else "en"

            is_valid = True
            validation_reason = ""
            has_ac = bool(ac and ac.strip())

            # Description is the hard requirement. Missing AC does NOT skip the
            # PBI — the analysis proceeds from the Description with explicit
            # assumptions (flagged via has_ac / validation_note below).
            if not description or not description.strip():
                is_valid = False
                validation_reason = "Missing or empty Description field"

            pbi_data = {
                "id": item.id,
                "title": title,
                "ac": ac if has_ac else "[No AC provided]",
                "description": description if description else "[No Description provided]",
                "language": detected_lang,
                "is_valid": is_valid,
                "has_ac": has_ac,
                "validation_note": (
                    "" if has_ac else
                    "No Acceptance Criteria — derive scope from the Description and "
                    "STATE ALL ASSUMPTIONS explicitly; the review gate must see them."
                ),
                "validation_reason": validation_reason if not is_valid else ""
            }

            if is_valid:
                pbis.append(pbi_data)
                arabic_count += 1 if detected_lang == "ar" else 0
                english_count += 1 if detected_lang == "en" else 0
                no_ac_count += 0 if has_ac else 1
            else:
                skipped_pbis.append(pbi_data)

        return {
            "count": len(work_items),
            "valid_count": len(pbis),
            "skipped_count": len(skipped_pbis),
            "no_ac_count": no_ac_count,
            "arabic_count": arabic_count,
            "english_count": english_count,
            "pbis": pbis,
            "skipped_pbis": skipped_pbis
        }

    except Exception as e:
        return handle_error(e, "get_pbis_from_sprint")

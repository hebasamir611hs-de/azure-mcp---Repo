---
name: build-chat-uat-doc
description: Build a client-facing UAT .docx directly from the approved Phase-1 chat output — filter to UAT-tagged cases, group by PBI, and produce a formatted Word document with cover page, change log, introduction, scope of work, and per-PBI test-case tables (Step / Action / Expected System Response / Feedback). No Azure read required — works from the signed-off set in conversation. Use when the user asks for a UAT document from the chat cases, or wants the client doc before injection.
---

# Build Chat UAT Document — Client Deliverable from Phase-1 Output

Build the **client-facing UAT document** directly from the **approved Phase-1 chat
output** (no Azure suite needed). Filters to `UAT`-tagged cases and produces a `.docx`
in the standard client format.

**Argument:** `$ARGUMENTS` — optional: project name, sprint name, or PBI IDs to scope.
If not provided, use all UAT-tagged cases from the most recent signed-off set in chat.

> Precondition: a signed-off test-case set exists in the current conversation with
> `UAT`-tagged cases. If no signed-off set exists, tell the user to run `analyze-pbi`
> first.

## Document Format — Mandatory Structure

The `.docx` MUST follow this exact layout:

### Page 1 — Cover Page
- "Prepared For" (small, centered, gray)
- **Project Name — Sprint N** (large, dark blue, italic, centered)
- "By" (small, centered)
- **AI-Assisted QA (Claude)** (bold, centered)
- Date (centered, format: `Month DDth, YYYY`)

### Page 2 — Document Info
- **Document Change Log** (blue heading)
  - Table: `Date | Changed By | Reason Of Change | Description of Change`
  - One row: today's date, "AI-Assisted QA (Claude)", "Document Creation", blank
- **Introduction** (blue heading)
  - "This document represents {Project Name — Sprint N} acceptance Checklist
    for {Project Name — Sprint N} Site, and all its functional specifications."
- **Pre-Requisite Checklist(s)** (blue heading)
  - "It's recommended that the user is already acquainted with the system."

### Page 3 — Scope
- **Scope of Work (Product Backlog Items)** (blue heading)
  - Bulleted list of all PBIs covered: `• PBI {ID}: {Title}`

### Remaining Pages — Test Cases
- **Test Cases** (large heading)
- For each PBI, a subheading: **"PBI Title"** (blue italic)
- For each UAT-tagged test case under that PBI:
  - **Header row** (light green background, full width):
    `TC: {Test Case Title}` (bold, underlined)
  - *Prerequisites:* (italic) — from the test case description/preconditions
  - **Steps table** with columns:

    | Step | Action | Expected System Response | Feedback |
    |------|--------|--------------------------|----------|
    | 1    | ...    | ...                      |          |
    | 2    | ...    | ...                      |          |

  - The **Feedback** column is always **empty** — it's for the client to fill during UAT.
  - `Step` = step number, `Action` = from `steps_list`, `Expected System Response` = from `expected_list`

### Language
- Detect the language of the test cases (Arabic or English).
- If Arabic: the entire document is RTL, headings and labels in Arabic.
  - "Prepared For" → "مُعد لـ"
  - "By" → "بواسطة"
  - "Document Change Log" → "سجل تغييرات المستند"
  - "Introduction" → "المقدمة"
  - "Pre-Requisite Checklist(s)" → "المتطلبات المسبقة"
  - "Scope of Work (Product Backlog Items)" → "نطاق العمل (عناصر قائمة المنتج)"
  - "Test Cases" → "حالات الاختبار"
  - Table headers: `الخطوة | الإجراء | استجابة النظام المتوقعة | الملاحظات`
- If English: LTR, headings and labels in English as shown above.

## Procedure

1. **Collect UAT cases** — from the signed-off set in the current conversation, filter
   to cases whose `Tags` include `UAT`. Group them by PBI.
   - If zero UAT-tagged cases exist, **stop and tell the user** — offer to either tag
     some cases UAT or build from all cases on explicit say-so.
2. **Detect language** — check the test case titles/steps. Arabic titles → full Arabic
   doc (RTL). English titles → full English doc (LTR).
3. **Extract metadata** — project name, sprint, date, list of PBIs with IDs and titles.
   Ask the user for project name / sprint if not obvious from context.
4. **Delegate to the `drafter` subagent** — hand it:
   - The filtered UAT cases (grouped by PBI, full fields)
   - The document format specification above (copy it verbatim into the prompt)
   - Project name, sprint, date, language direction
   The drafter produces the `.docx` file following the format exactly.
5. **Review the output** — verify the `.docx` has all sections, correct grouping, no
   missing cases, and the Feedback column is empty.
6. **Report back** — the `.docx` file path, how many UAT cases included, how many PBIs
   covered, and any cases that were excluded (not UAT-tagged).

## Hard Boundary

This skill only **formats** approved content. It does not invent, re-judge, or inject
test cases. If coverage gaps are found, route back to `analyze-pbi`.

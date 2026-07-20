---
name: build-uat-doc
description: Build the client-facing UAT .docx from a TEST SUITE — read the suite's test cases via the MCP (plan_id + suite_id), filter to the Tag=UAT acceptance cases in the agent layer, and delegate the .docx production to the drafter subagent, then review and revise. Use when the user asks for a UAT document, client acceptance doc, or sign-off document. Precondition — the cases are already injected into Azure DevOps with UAT tags and collected in a test suite under a test plan; if not, route to analyze-pbi → inject-test-cases first.
---

# Build UAT Document — Client Deliverable

Build the **client-facing UAT document** from the `Tag = UAT` cases of a **test
suite**, then review and revise it. This is a separate deliverable from the full
internal test set.

**Arguments:** the **test plan ID** and **test suite ID** → `$ARGUMENTS`
(both are in the Azure Test Plans URL: `?planId=XXXXX&suiteId=YYYYY`.
If either is missing, ask before starting — the suite reader needs both.)

> Precondition: the test cases are already injected (via `inject-test-cases`) with
> `UAT` tags applied, and the suite exists under the plan (see
> `create_test_suite_for_pbi` / `create_test_suites_for_sprint`).
>
> Division of labor: the **MCP reads** the raw suite data; **you filter** by tag;
> the **`drafter` subagent formats** the client document. No injection happens here.


## Language & Direction — Mandatory

The document **language and direction follow the test cases**, not the user's
prompt. Detect from the filtered set:

- **Arabic test cases** (titles start with `التحقق من أنه` or contain
  Arabic-script majority) → **full RTL** `.docx`. All headings, labels, table
  headers, and body text are in Arabic. Document direction = right-to-left.
  Translation reference for headings:
  - "Cover Page" → "صفحة الغلاف"
  - "Purpose & Scope" → "الغرض والنطاق"
  - "How to Read This Document" → "كيفية قراءة هذا المستند"
  - "UAT Test Cases" → "حالات اختبار قبول المستخدم"
  - "Client Sign-off" → "اعتماد العميل"
  - Table headers: `العنوان | المتطلبات المسبقة | الخطوات | النتيجة المتوقعة | الملاحظات`
- **English test cases** (titles start with `Verify that`) → **full LTR**
  `.docx`. Headings and labels in English as in the drafter's standard structure.
  Table headers: `Title | Preconditions | Steps | Expected Result | Feedback`.

**Never mix:** if the filtered set contains both languages, **stop and ask the
user** which language to produce (or produce two documents — one per language).
Never produce a half-Arabic / half-English document.

The drafter subagent is responsible for applying the correct direction —
pass the detected language as an explicit argument when delegating.


## Procedure

1. **Confirm plan and suite IDs** — parse both from `$ARGUMENTS`. Do not guess.
2. **Read the suite** — call `mcp__azure-devops__get_test_cases_from_suite` with
   `plan_id` and `suite_id`. It returns every case fully expanded:
   `{id, title, state, priority, tags, description, steps: [{action, expected}]}`.
3. **Filter to `Tag = UAT`** — keep only cases whose `tags` contain `UAT`
   (case-insensitive). Report the split (e.g. "9 cases in suite, 4 tagged UAT").
   - **If zero cases carry the `UAT` tag, stop and tell the user** — offer to either
     fix the tagging upstream (re-tag in Azure) or, on their explicit say-so, build
     from all suite cases instead. Never silently include untagged cases.
4. **Detect language and delegate to the `drafter` subagent** — first apply the
   *Language & Direction* rule above to classify the filtered set. Hand the drafter:
   - The filtered cases (full JSON).
   - The feature / PBI name.
   - **The explicit language argument**: `language=ar` for Arabic (RTL) or
     `language=en` for English (LTR). The drafter applies the direction throughout
     the document — headings, body, table headers, page numbering, sign-off — per
     the translation table above.
   The drafter produces the client `.docx` per its own definition: cover page,
   purpose & scope, how-to-read, the case table (*Title · Preconditions · Steps ·
   Expected Result · Feedback*), and a client sign-off section. Plain business
   language — no internal fields, priorities, or jargon.
5. **Review** — call `mcp__azure-devops__review_uat_document` with `uat_file_path` =
   the `.docx` the drafter produced. Read the findings: missing acceptance scenarios,
   vague steps, client-readability issues.
6. **Revise** — if the review surfaces fixable issues, send them back to the same
   `drafter` agent (SendMessage) to correct the document. Keep one owner of formatting.
7. **Report back** — the final `.docx` path, how many UAT cases it covers, how many
   suite cases were excluded (not UAT-tagged), and any open gaps that need a human
   decision.

## Note

If the review shows real coverage holes (not just wording), the fix belongs
upstream — flag it and consider returning to `analyze-pbi` to add the missing
acceptance cases, then `inject-test-cases`, before finalizing the client doc.

---
name: inject-test-cases
description: Phase-2 transport only — push an ALREADY-APPROVED, signed-off test-case set into Azure DevOps under a parent PBI, mapping fields and Tags per the template and reporting created work-item IDs. Dumb transport, zero analysis. Use only when the user has reviewed a generated set and explicitly asks to inject / push / create the cases in Azure. Do NOT use to generate or edit cases, and do NOT auto-run on an unapproved set — if no signed-off set exists, send the user to analyze-pbi first.
---

# Inject Test Cases — Phase 2 Transport

Push an **already-approved** test-case set into Azure DevOps. This is **dumb
transport** — zero analysis, zero creative work. If the set has not been generated
and signed off via `analyze-pbi` (or `quick-test-cases`), stop and do that first.

**Argument:** the parent PBI ID to link the cases under → `$ARGUMENTS`
(If not provided, ask for the parent PBI ID before injecting.)

> This skill never invents, edits, or re-judges a test case. It maps the approved
> set to Azure fields and pushes it. All reasoning already happened in Phase 1.

## Procedure

1. **Confirm the parent PBI** — `$ARGUMENTS`. Do not proceed without it.
2. **Confirm sign-off** — the set being injected must be the approved Phase-1 output.
   If anything is unapproved, return to `analyze-pbi`.
3. **Map fields** per `@.claude/context/test-case-template.md` — `test_type`,
   `scenario`, `impact_area`, `priority`, `execution_type`, and `Tags`
   (passed via the `tags` key per item). Do not duplicate the auto dimension tags;
   the MCP adds and dedupes those.
4. **Inject the batch** — prefer `mcp__azure-devops__execute_qa_feedback` for the full
   approved set in one call. Use `mcp__azure-devops__create_english_test_case` /
   `mcp__azure-devops__create_arabic_test_case` only for individual cases or fallback.
5. **Report back** — how many TCs were created and their Azure work item IDs.
6. **Handle rejections** — if any case is rejected, fix the field that caused it and
   retry. **Never silently skip a case.**

## Optional follow-up

After injection, suggest auditing coverage and outcomes for `$ARGUMENTS`.

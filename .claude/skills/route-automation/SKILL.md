---
name: route-automation
description: Phase 2.5 router — reads the INJECTED test cases under a parent PBI from Azure DevOps, classifies them by Platform tag (Web / Android / iOS / Control_Panel), runs prep-automation-env per surface, and on user approval hands off each ready surface to automate-test-case with the matching engineer (senior-web-automation-eng for web, senior-mobile-automation-eng for mobile). Hybrid trigger — does NOT auto-run after injection; the QA Manager proposes it at the Phase 2→3 boundary and waits for explicit approval. iOS on a non-macOS host is reported as skipped with an actionable warning (find a macOS host); other ACTIONABLE blocks stop the run with a clear report. Use at the start of Phase 3 — after inject-test-cases succeeded and the user wants to begin automation. Does NOT generate, edit, or re-judge test cases (reads them as-is from Azure) and does NOT post results back to Azure (integration is deferred).
---

# Route Automation — Phase 2.5 Surface Router

The **Development Manager hat lives here.** This skill is the explicit hand-off
between Phase 2 (cases injected to Azure) and Phase 3 (runnable tests). It reads
the injected set, picks the automation paths from the Platform tags, prepares each
surface, and delegates the implementation work — never authoring tests itself.

**Argument:** the parent PBI ID whose injected cases should be automated →
`$ARGUMENTS`. If no PBI ID is given, ask before doing anything.

> The QA Manager's hat-switch happens here. From this point the orchestrator is
> wearing the **Development Manager** hat: it decides surfaces, chooses MCPs, and
> delegates engineers. It does **not** re-judge coverage — coverage was signed off
> in Phase 1.

## Procedure

1. **Confirm the parent PBI.** `$ARGUMENTS` is required. Without it, stop and ask.
2. **Read the injected set from Azure.** Use the Azure DevOps MCP read tools
   (`mcp__azure-devops__review_test_coverage` or equivalent) under the parent PBI.
   This is the **only** Azure read in this skill — no writes, ever.
3. **Classify by Platform tag.** Each case carries one or more Platform tags
   (`Web` / `IOS` / `Android` / `Control_Panel` — taxonomy in
   `@.claude/context/active/standards.md`). Group the set:
   - `web_set`            ← cases tagged `Web`
   - `control_panel_set`  ← cases tagged `Control_Panel` (treated as web internally)
   - `android_set`        ← cases tagged `Android`
   - `ios_set`            ← cases tagged `IOS`
   A case with both `Web` + `Android` lands in both sets — it gets two tests, one
   per surface, mirroring the case's intent.
4. **Determine the surface plan.** Compose the list of surfaces to prep:
   - any web or control_panel cases → include `web`
   - any android cases → include `mobile/android`
   - any ios cases → include `mobile/ios`
5. **Invoke `prep-automation-env`** for each surface needed (single call with the
   combined argument `web` / `mobile` / `both` when both are present). Capture
   per-surface status:
   - **All green** → surface ready, proceed.
   - **iOS ACTIONABLE on non-macOS host** → mark `ios_set` as **skipped (needs
     macOS)** and continue with web + Android.
   - **Any other ACTIONABLE** → **stop**. Return the prep report verbatim and let
     the user fix the environment before retrying.
6. **Pause for approval (hybrid trigger).** Before delegating any engineer, show a
   compact plan to the user and wait:

   ```
   Plan from PBI <ID>:
     Web         : <N> cases  → senior-web-automation-eng (Playwright)
     Android     : <N> cases  → senior-mobile-automation-eng (Appium)
     iOS         : <N> cases  → SKIPPED (needs macOS host)
   Total to automate now: <N>
   Proceed? (yes / no)
   ```

   If the user says no — stop. **Never auto-run.**

7. **Delegate per surface** via the Agent tool:
   - `web_set` ∪ `control_panel_set` → **`senior-web-automation-eng`** with the
     `automate-test-case` skill, passing the case batch.
   - `android_set` → **`senior-mobile-automation-eng`** with `automate-test-case`,
     passing the Android batch. The engineer uses the Appium MCP tools for
     locator extraction.
   - `ios_set` → not delegated on a non-macOS host — surfaced as skipped.

   For each engineer call: pass the case IDs + titles + steps from Azure verbatim;
   do not re-author or reinterpret content.

8. **Consolidate the report.** When the engineers return, produce a single summary:
   - per surface: cases attempted, cases automated successfully, cases blocked
     (with first failure reason and traceability IDs)
   - skipped iOS: list and the reason (needs macOS)
   - next step: point at `run-automation` to execute the suite + report

## Hard boundaries

- **Reads from Azure, writes nothing back.** No `execute_qa_feedback`, no
  `create_*_test_case`. Azure result post-back is part of the deferred integration
  step in `automation-standards.md`, not this skill.
- **Does not generate or re-judge cases.** The set comes from Azure as-is. If
  coverage looks wrong, flag it to the QA Manager — do NOT silently rewrite.
- **No auto-trigger.** Always pauses for explicit user approval at step 6, even if
  the prep report is green across the board.
- **No silent iOS skip.** iOS being skipped is always called out in the plan and
  in the consolidated report.
- **Single hand-off only.** This skill delegates engineers; it does not call
  `automate-test-case` directly nor write test files itself.

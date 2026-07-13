---
name: analyze-pbi
description: Run the Phase-1 QA analysis on a single PBI/user story in the chosen mode — Normal (default; UI / Functional-High / Functional-Low focus, optional Compatibility / Auth / lighter Edge, no API / Additional / non-functional) or Deep (all 8 framework categories + the full 4-step edge methodology). Format per the test-case template, run the coverage review gate, and sign off. Reasoning only — produces cases in chat, never injects. Use when the user gives a PBI ID or feature to analyze, asks for full test coverage, or says "analyze this story" / "deep analysis". Do NOT use for quick subsets (use quick-test-cases) or for pushing cases to Azure (use inject-test-cases).
---

# Analyze PBI — Full Phase-1 Coverage

Run the **complete Phase-1 analysis** for one PBI and produce the full test-case set
in chat. This is reasoning work — **no injection happens here.**

**Arguments:** the PBI ID to analyze, and optionally the analysis **mode** → `$ARGUMENTS`
(e.g. `12345 deep`. **If no mode is given, default to Normal** and say so. If no ID was
given, ask for it before starting.)

> Knowledge lives in the context files. This skill only orchestrates — it does not
> restate the framework, the format, or the standards. It points at them.

## Procedure

1. **Load project context** — read `@.claude/context/woqod-background.md` so scope,
   surfaces, roles, and objects are in mind.
2. **Read the PBI** — call `mcp__azure-devops__get_story_for_analysis` for `$ARGUMENTS`
   to pull the description and any acceptance criteria. This is the **only** MCP call
   in this skill.
3. **Define scope & mode** — determine the **analysis mode** from `$ARGUMENTS`
   (**default Normal** if unspecified; state which you're using). List every surface,
   role, object, and integration point the feature touches. State assumptions explicitly;
   if acceptance criteria are missing, ask before filling the gap.
4. **Delegate the derivation to the `qa-engineer` subagent** — launch it via the
   Agent tool with the **active mode**, the full PBI spec/AC from step 2, and your scope
   and assumptions from step 3. The agent applies the framework **for that mode** per
   `@.claude/context/analysis-framework.md` → *Analysis Modes* (**Deep** = all 8
   categories + the **full** 4-step edge methodology, objects → statuses → relations →
   derivation; **Normal** = UI / Functional-High / Functional-Low focus, optional
   Compatibility / Auth / a **lighter** Edge sweep, and **no** API / Additional /
   non-functional), shows that edge reasoning, and formats every case per
   `@.claude/context/test-case-template.md` — all required fields, including `Tags`
   (Lifecycle + Service + Platform + Category; `UAT` only on **direct acceptance**
   scenarios, `Regression` only on the feature's **MAIN functional** scenarios — never
   on deep field/boundary/edge cases — values from
   `@.claude/context/woqod-standards.md`). The agent is reasoning-only; it never
   calls the MCP. *(Fallback: if the agent is unavailable, derive inline applying
   the exact same mode, framework, methodology, and format.)*
5. **Relay the full set to chat** — the agent's final message comes back to you, not
   the user. Present ALL derived cases in chat unabridged.
6. **Run the review gate** — verify the agent's output against the coverage checklist
   in `CLAUDE.md` (*Reviewing Output*) **for the active mode**. In **Normal** mode the
   API, Additional, and non-functional categories are **out of scope** — their absence
   is correct, not a gap. Reject and **send back to the `qa-engineer` for another pass**
   (via SendMessage to the same agent, with the specific gaps) any **in-scope** category
   that is absent without a documented N/A, any field missing Functional-Low cases, any
   vague expected result, or any case missing its `Tags`.
7. **Detect automation surface** — switch hat to **Development Manager** for one
   moment. Scan the Platform tags across the approved set and classify the project
   surface:
   - `Web` only → web automation path (Playwright)
   - `IOS` / `Android` (one or both) → mobile automation path (Appium)
   - Both Web + Mobile → cross-surface, two automation trees
   - `Control_Panel` only → web automation path (CMS surface)
   - **Unclear** — Platform tags inconsistent or missing → flag for explicit question
     at the Phase 2→3 boundary (`route-automation` will ask).
   State the detected surface in the sign-off below. This drives the automation
   handoff later.
8. **Sign off** — publish a short QA sign-off: categories covered, total TC count,
   **detected automation surface** (from step 7), open risks or assumptions. If
   surface is clear and the user has not yet injected, offer the lookahead:
   *"Surface is `{surface}` — want me to prep the automation environment in parallel
   while you review? (runs `prep-automation-env`)"*

## Hard boundary

This skill ends at sign-off. **Do not call any injection tool.** When the user
approves the set, they run `inject-test-cases` to push it to Azure DevOps.

---
name: analyze-pbi
description: Run the full Phase-1 QA analysis on a single PBI/user story — derive complete test-case coverage across all 8 framework categories (UI, Compatibility, Auth, Functional-High, Functional-Low, API, Edge, Additional) with the mandatory 4-step edge methodology, format per the test-case template, run the coverage review gate, and sign off. Reasoning only — produces cases in chat, never injects. Use when the user gives a PBI ID or feature to analyze, asks for full/complete test coverage, or says "analyze this story". Do NOT use for quick subsets (use quick-test-cases) or for pushing cases to Azure (use inject-test-cases).
---

# Analyze PBI — Full Phase-1 Coverage

Run the **complete Phase-1 analysis** for one PBI and produce the full test-case set
in chat. This is reasoning work — **no injection happens here.**

**Argument:** the PBI ID to analyze → `$ARGUMENTS`
(If no ID was given, ask for it before starting.)

> Knowledge lives in the context files. This skill only orchestrates — it does not
> restate the framework, the format, or the standards. It points at them.

## Procedure

1. **Gather project context** — from the PBI and the user, so scope, surfaces,
   roles, and objects are in mind; ask when scope, roles, or platforms are unclear.
2. **Read the PBI** — call `mcp__azure-devops__get_story_for_analysis` for `$ARGUMENTS`
   to pull the description and any acceptance criteria. This is the **only** MCP call
   in this skill.
3. **Define scope** — list every surface, role, object, and integration point the
   feature touches. State assumptions explicitly; if acceptance criteria are missing,
   ask before filling the gap.
4. **Delegate the derivation to the `qa-engineer` subagent** — launch it via the
   Agent tool with the full PBI spec/AC from step 2 plus your scope and assumptions
   from step 3. The agent applies the full framework in
   `@.claude/context/analysis-framework.md` across **all 8 categories** (happy, sad,
   beyond), runs the **4-step edge methodology explicitly** (objects → statuses →
   relations → derivation) showing that reasoning, and formats every case per
   `@.claude/context/test-case-template.md` — all required fields, including `Tags`
   (Service + Platform + Category + Lifecycle; `UAT` on client-facing acceptance
   cases, `Regression` on automation candidates — Service/Platform/business tag
   values come from the project context; ask the user if not provided). The agent
   is reasoning-only; it never calls the MCP. *(Fallback: if the agent is
   unavailable, derive inline applying the exact same framework, methodology, and
   format.)*
5. **Relay the full set to chat** — the agent's final message comes back to you, not
   the user. Present ALL derived cases in chat unabridged.
6. **Run the review gate** — verify the agent's output against the coverage checklist
   in `CLAUDE.md` (*Reviewing Output*). Reject and **send back to the `qa-engineer`
   for another pass** (via SendMessage to the same agent, with the specific gaps) any
   category that is absent without a documented N/A, any field missing Functional-Low
   cases, any vague expected result, or any case missing its `Tags`.
7. **Sign off** — publish a short QA sign-off: categories covered, total TC count,
   open risks or assumptions.

## Hard boundary

This skill ends at sign-off. **Do not call any injection tool.** When the user
approves the set, they run `inject-test-cases` to push it to Azure DevOps.

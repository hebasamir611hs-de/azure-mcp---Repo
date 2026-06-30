---
name: quick-test-cases
description: Produce a tight, prioritized SUBSET of test cases for fast feedback — happy path + top critical negatives + sharpest edges — output to chat, clearly labeled as not full coverage, no injection. Use when the user says quick, adhoc, smoke, "just the critical ones", or wants a fast prioritized set rather than exhaustive coverage. Do NOT use when full coverage is requested (use analyze-pbi).
---

# Quick Test Cases — Prioritized Subset

Produce a **tight, prioritized** test-case set for fast feedback — **not** full
coverage. Use for smoke / ad-hoc / "give me the critical ones" requests.

**Argument:** the feature, PBI ID, or description to cover → `$ARGUMENTS`

> Same format and standards as full analysis — just a deliberate subset. This is the
> Quick/Ad-hoc mode from `CLAUDE.md`, made an invokable verb.
>
> **No subagent here.** Unlike `analyze-pbi`, do NOT delegate to the `qa-engineer`
> subagent — its mandate is maximum coverage, which contradicts a quick subset (and
> the spawn overhead defeats the speed goal). Derive the subset inline.
>
> **Not an analysis mode.** The Normal / Deep **modes** belong to `analyze-pbi` and are
> two depths of a *full* analysis. `quick-test-cases` is neither — it is a deliberately
> tiny prioritized subset, lighter than even Normal mode. If the user wants a real (if
> lighter) full pass, that is **Normal mode in `analyze-pbi`**, not this skill.

## Procedure

1. **Load context** — read `@.claude/context/woqod-background.md` if `$ARGUMENTS` is a
   real feature/PBI needing project scope. (Pull the PBI with
   `mcp__azure-devops__get_story_for_analysis` only if an ID was given.)
2. **Pick the sharp subset** — from `@.claude/context/analysis-framework.md`, select:
   - the **happy path** (the core successful journey),
   - the **top critical negatives** (money flow, auth, data-loss risks first),
   - the **sharpest edges** (a quick objects → statuses → relations pass; show the
     reasoning briefly).
3. **Format** each case per `@.claude/context/test-case-template.md`, including `Tags`.
   Money flows are always P1.
4. **Detect automation surface (lightweight)** — quick scan of the Platform tags on
   the produced subset. Classify as `Web` / `Mobile (IOS/Android)` / `Both` /
   `Control_Panel` / `Unclear`. This is informational only here (no env prep is
   triggered from a quick subset — the full run via `analyze-pbi` is the right place
   for that), but it tells the user which automation MCP would apply later.
5. **Output to chat** — and **state clearly that this is a subset, not full coverage.**
   Include the detected surface in the closing note (e.g., *"Subset surface: Android
   — full coverage via analyze-pbi will confirm."*).

## Hard boundary

No injection. If the user wants these in Azure DevOps, they explicitly run
`inject-test-cases`. For complete coverage, run `analyze-pbi` instead.

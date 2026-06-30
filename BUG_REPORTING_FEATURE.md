# New: Automated Bug Reporting (Test Failure → Azure DevOps Bug)

We just closed the loop on our QA automation system: when an automated test fails, the
system now **files (or updates) the Azure DevOps Bug itself** — fully unattended, with
dedup built in so reruns of a flaky/broken test don't spam the backlog.

This is **Phase 3b** of our QA Manager system (analysis → injection → automation →
**bug reporting**). No more "test failed, someone please go log a bug."

---

## How it works

```
run-automation finishes a pass
        │
        ▼
quality-control-engineer triages every failure
   (test → Test Case ID → error / expected / actual / screenshot)
        │
        ▼
For EACH failure → create-azure-bug skill:
   1. find_existing_bug(test_case_id)   ── dedup check
        │
        ├─ open bug already exists ──► add_bug_occurrence(bug_id, ...)
        │                                 (reopens it if it was "Resolved")
        │
        └─ no open bug ──────────────► create_bug(...)
                                          (new Bug, linked to the Test Case)
```

**Key design choice: no confirmation gate.** Every failing test is eligible, automatically
— no tag filter, no "should I file this?" prompt. The thing standing in for a gate is the
**dedup check**, which always runs first.

---

## Example

A regression run finds 3 failures:

```
You: run the regression suite

→ 142 passed, 3 failed

quality-control-engineer hands off 3 failures:
  1. TAG-TOPUP-TC-014  — "Top-up amount field accepts negative value"
  2. TAG-TOPUP-TC-022  — "Top-up confirmation timeout under slow network"
  3. FAHES-LOGIN-TC-003 — "Login fails with valid credentials after session expiry"

create-azure-bug processes each:

  #1 → find_existing_bug(TAG-TOPUP-TC-014) → no match
      → create_bug(...) → Bug #5310 created
         Title: "[4821] Automated test failure: test_topup_negative_amount —
                 AssertionError: expected validation error, got success"
         Severity: 2 - High (from TC priority)
         Tags: Automated; TC:5021; TAG; Web
         Screenshot attached ✓

  #2 → find_existing_bug(TAG-TOPUP-TC-022) → Bug #5298 already open
      → add_bug_occurrence(5298, "Timeout after 30s, expected confirmation", run_url)
         → comment added: "Reproduced again on 2026-06-30 14:02 UTC..."
         → state was "Resolved" → reopened to "Active"  (regression!)

  #3 → find_existing_bug(FAHES-LOGIN-TC-003) → no match
      → create_bug(...) → Bug #5311 created
         Severity: 1 - Critical

Report back:
  • 2 new bugs filed (#5310, #5311)
  • 1 existing bug updated + reopened (#5298 — was marked Resolved, just regressed)
  • 0 skipped
```

That reopen on #2 is the part worth calling out to QA leads — **a "fixed" bug that fails
again on the next automated run gets caught automatically**, instead of quietly passing as
a false "still resolved."

---

## What a filed Bug actually contains

Every Bug created by the system has, with zero manual entry:

| Field | How it's populated |
|---|---|
| **Title** | `[<PBI ID>] Automated test failure: <test name> — <first ~80 chars of error>` — PBI ID resolved automatically from the Test Case's own link, so every bug is traceable to its backlog item at a glance |
| **Repro Steps** | Failing test name, steps (from the test if known, else a pointer to the Test Case), Expected Result, Actual Result, link to the automation run/report |
| **Severity** | Mapped straight from the Test Case's QA Priority (P1→Critical … P4→Low) — same mapping already used for Allure |
| **Screenshot** | Auto-attached if the failure captured one |
| **Link to Test Case** | Proper Azure relation (`TestedBy-Reverse`) — not just a text mention |
| **Tags** | `Automated`, `TC:<test_case_id>` (the dedup key), plus Service/Platform tags carried over verbatim from the Test Case (`TAG`/`FAHES`/`Web`/`IOS`/etc.) |
| **Iteration / Area Path** | Inherited from the Test Case (Bugs have no direct Sprint link in Azure — Sprint *is* the Iteration Path) |

Because of the `TC:<id>` tag, anyone can build a saved query like:

```
[System.WorkItemType] = 'Bug' AND [System.Tags] CONTAINS 'Automated'
```

...to see every auto-filed bug at a glance, separate from manually-logged ones.

---

## Guardrails worth knowing

- **It never decides whether a failure is "real."** That judgment already happened —
  every failure from an automated run is in scope by design (see
  `automation-standards.md` → *Bug Reporting on Failure*). This skill is pure transport.
- **Never double-files.** The dedup check is mandatory before every create — one open Bug
  per Test Case, period.
- **Doesn't touch test code.** If a failure looks like a framework/flake issue rather than
  a real product defect, it still gets logged (with that caveat noted) rather than
  silently dropped — silent skipping isn't allowed.
- **Degrades gracefully.** If Azure rejects tags (permissions), the Bug still gets created
  — just without tags — and the report says so plainly instead of claiming full success.

---

## Try it

Bug filing runs automatically as the tail end of an automation pass — you don't invoke it
separately. Just:

```
run the smoke suite
```
or
```
run the regression suite
```

If there are failures, you'll see the triage + filed/updated bugs in the same response.

Happy to demo this live on the next failing run if useful.

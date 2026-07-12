---
name: triage-failures
description: Triage the failed/broken tests of an automation run — feed the Allure artifacts (allure-results *-result.json + screenshots/logs, plus allure-report history for retries/flakiness) to the test-failure-triage agent, which classifies each failure as PRODUCT_BUG / AUTOMATION_BUG / ENVIRONMENT_ERROR / NEEDS_INVESTIGATION with confidence, quoted evidence, and a suggested owner, then route each verdict to its owner. Use after run-automation reports failures, or when the user asks why tests failed / who should fix them. Analysis-only — it does NOT fix tests (route to the engineers), rerun the suite (use run-automation), or open tickets / call Azure DevOps (integration deferred).
---

# Triage Failures — Classify Every Failed Test from Allure Evidence

Turn a red run into an **owned, evidence-backed verdict per failure** — product bug,
automation bug, environment error, or needs-investigation — so nobody wastes time
re-running or mis-assigning failures.

**Argument:** the run to triage → `$ARGUMENTS` (default: the latest results in
`./automation/reports/`; or a path to a specific `allure-results` folder, or a
marker/test filter to triage a subset).

> The classification method, failure signatures, output JSON schema, and rules live in
> the **`test-failure-triage`** agent definition. This skill collects the inputs,
> delegates, reviews, and routes; it does not re-derive the analysis inline.

## Procedure

1. **Preconditions.** Confirm `./automation/reports/allure-results/` exists (or the
   path given in `$ARGUMENTS`). If there are no results, run `run-automation` first —
   there is nothing to triage. If the run is green, say so and stop.
2. **Collect the inputs:**
   - Enumerate failed/broken tests from `allure-results/*-result.json`
     (`status: failed | broken`), with their failure message, trace, steps, and
     attachment references (screenshots, video, logs).
   - If `allure-report/` was generated, also point the agent at
     `allure-report/data/test-cases/*.json` for **history and retries** (flakiness
     signals).
   - Note any failing test with missing evidence attachments — per the standards that
     is itself a framework defect to report.
3. **Delegate to the `test-failure-triage` agent** (via the Agent tool) with the
   collected file paths and any context the user supplied (recent app changes, known
   environment issues). The agent returns the JSON verdicts + summary per its output
   format.
4. **Review the output** before presenting it: every failed test has exactly one
   verdict; evidence quotes exact error lines; duplicates are grouped; LOW-confidence
   verdicts were downgraded to NEEDS_INVESTIGATION. Send it back for another pass if
   any of these fail.
5. **Route each verdict:**
   - **AUTOMATION_BUG** → the responsible engineer
     (`senior-web-automation-eng` / `senior-mobile-automation-eng`) with the
     recommended fix; the fix itself goes through the normal automation flow.
   - **PRODUCT_BUG** → present to the user/QA Manager with the evidence bundle
     (screenshot, quoted error, steps) ready for a dev bug ticket. **Do not** create
     the ticket or write to Azure DevOps — integration is deferred.
   - **ENVIRONMENT_ERROR** → report to the environment owner; recommend rerun timing
     via `run-automation` after recovery.
   - **NEEDS_INVESTIGATION** → state exactly what evidence is missing and how to get
     it (e.g., fix evidence attachment wiring per the standards, add logs, rerun once).
6. **Report** — the verdict table (test, verdict, confidence, owner, one-line cause),
   the summary counts, recurring root causes / suspicious patterns, and the grouped
   duplicates so one ticket covers one root cause.

## Hard boundary
Triage only. This skill never edits test code or app code, never reruns the suite,
never creates bug tickets, and makes **no** Azure DevOps calls. Fixing goes through the
engineers; execution through `run-automation`; ticketing stays with the user until
integration is explicitly enabled.

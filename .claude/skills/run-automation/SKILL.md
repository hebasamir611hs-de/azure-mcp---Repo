---
name: run-automation
description: Run the pytest automation suite in ./automation/ and produce the readable Allure report with screenshots + video/screen-recording attached on failure. Supports running everything, a marker subset (smoke / sanity / regression / web / mobile), or a single test, then summarizes pass/fail and gives the report path. Use when the user wants to execute the automated tests, run a smoke/regression pass, or regenerate the report. Read-only on the test code — it executes and reports; it does NOT write tests (use automate-test-case) and makes no Azure DevOps calls (integration deferred).
---

# Run Automation — Execute the Suite + Allure Report

Execute the pytest suite in `./automation/` and produce the **Allure** report with
screenshots and video/screen-recording attached on failure. This skill runs and reports;
it does not author tests.

**Argument:** the selection → `$ARGUMENTS`
(`all` | a marker like `smoke` / `sanity` / `regression` / `web` / `mobile` | a single
test path/ID). Default to `smoke` if nothing is given, and say so.

> Reporting conventions (Allure, screenshot-on-failure, video/trace retain-on-failure,
> severity from QA priority) live in `@.claude/context/automation-standards.md`.

## Procedure

1. **Preconditions.** Confirm `./automation/` exists and deps are installed
   (`pip install -r requirements.txt`; `playwright install` for web). For **mobile**,
   confirm an Appium server + emulator/device are reachable; if not, report that mobile
   execution is blocked on the environment and run only the runnable selection.
2. **Pick the engineer** for the selection — **`senior-web-automation-eng`** for web,
   **`senior-mobile-automation-eng`** for mobile (either may run a mixed `all` pass).
3. **Run pytest into Allure** — e.g. `pytest -m <marker> --alluredir=reports/allure-results`
   (full path/ID for a single test). Screenshots capture on failure; video/trace and
   screen recording retain on failure per the contract.
4. **Generate/serve the report** — `allure generate reports/allure-results -o
   reports/allure-report --clean` (or `allure serve`). Confirm screenshots and video are
   attached to failing steps.
5. **Report honestly** — totals (passed / failed / skipped), the failing tests with their
   traceability IDs and the first real failure reason, and the report path. **Never claim
   green you did not observe**; surface flaky/skipped tests explicitly.

## Hard boundary
Execution + reporting only. Does **not** write or fix tests (route failures to
`automate-test-case` / the relevant engineer) and makes **no** Azure DevOps calls. Posting
results back to Azure is part of the deferred integration step, not this skill.

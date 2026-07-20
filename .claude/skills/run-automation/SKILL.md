---
name: run-automation
description: Run the pytest automation suite in ./automation/ and produce the readable Allure report with screenshots + video/screen-recording attached on failure. Supports running everything, a marker subset (smoke / sanity / regression / web / mobile), or a single test, then summarizes pass/fail and gives the report path. Use when the user wants to execute the automated tests, run a smoke/regression pass, or regenerate the report. Read-only on the test code — it executes and reports; it does NOT write tests (use automate-test-case) and makes no Azure DevOps calls (integration deferred).
---

# Run Automation — Execute the Suite + Allure Report

Execute the pytest suite in `./automation/` and produce the **Allure** report with
screenshots and video/screen-recording attached on failure. This skill runs and reports;
it does not author tests.

**Argument:** the selection → `$ARGUMENTS`
(`all` | a marker like `regression` / `web` / `ios` / `android` / `control_panel` |
a single test path/ID). Default to `regression` if nothing is given, and say so.

> Reporting conventions (Allure, screenshot-on-failure, video/trace retain-on-failure,
> severity from QA priority) live in `@.claude/context/automation-standards.md`.

## Procedure

1. **Preconditions.** Confirm `./automation/` exists and deps are installed
   (`pip install -r requirements.txt`; `playwright install` for web). For **mobile**,
   confirm an Appium server + emulator/device are reachable; if not, report that mobile
   execution is blocked on the environment and run only the runnable selection.
2. **Pick the engineer** for the selection — **`senior-web-automation-eng`** for web,
   **`senior-mobile-automation-eng`** for mobile. A mixed `all` pass is **split into two
   delegations** — the web selection (`-m web`) to the web engineer, the mobile
   selection (`-m mobile`) to the mobile engineer — and this skill merges the two
   results into one summary; neither engineer runs or triages the other's surface.
3. **Run pytest into Allure** — e.g. `pytest -m <marker> --alluredir=reports/allure-results`
   (full path/ID for a single test). Screenshots capture on failure; video/trace and
   screen recording retain on failure per the contract.
4. **Generate/serve the report** — `allure generate reports/allure-results -o
   reports/allure-report --clean` (or `allure serve`). Confirm screenshots and video are
   attached to failing steps. A failing test whose Allure entry lacks its screenshot or
   video is a **framework defect** — report it explicitly and route the conftest/hook
   fix to the responsible engineer; do not present a report with missing evidence as
   complete.
5. **Report honestly** — totals (passed / failed / skipped), the failing tests with their
   traceability IDs and the first real failure reason, and the report path. **Never claim
   green you did not observe**; surface flaky/skipped tests explicitly. If there are
   failures, offer **`triage-failures`** as the next step — it classifies each failure
   (product / automation / environment) from the Allure evidence and assigns an owner.

## Hard boundary
Execution + reporting only. Does **not** write or fix tests (route failures to
`automate-test-case` / the relevant engineer), does **not** classify failures (that is
`triage-failures`), and makes **no** Azure DevOps calls. Posting results back to Azure
is part of the deferred integration step, not this skill.

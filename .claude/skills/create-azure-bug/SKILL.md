---
name: create-azure-bug
description: File or update an Azure DevOps Bug for a single automated test failure — check for an existing open bug first (dedup), then either create a new Bug (title, repro steps, severity, screenshot, link to the Test Case) or add an occurrence comment to the existing one. Use when an automated test has failed and the failure needs to be reported to Azure DevOps. Do NOT use to decide WHETHER a failure should be reported (automation-standards.md → "Bug Reporting on Failure" already scopes that to every failure) and do NOT use for manually-found bugs — this skill is for automation-sourced failures only.
---

# Create Azure Bug — File or Update From a Test Failure

Takes one failed automated test's details and gets it into Azure DevOps as a Bug —
filing a new one or updating an existing one, never both. This skill is **dumb
transport with one decision in it (dedup)** — it does not judge whether the failure is
real, does not retry the test, and does not fix anything.

> Contract: bug validity rules, title convention, severity mapping, dedup rule, and the
> Bug tag taxonomy live in `@.claude/context/automation-standards.md` →
> *"Bug Reporting on Failure"*. Apply that, don't improvise it here.

**Argument:** the failure context, normally handed off by the `quality-control-engineer`
agent after a `run-automation` pass — test name, the Azure Test Case ID it traces to
(from the test's traceability marker), the error message, expected/actual result,
repro steps if known, a screenshot path if one was captured, and the run/report URL.

## Procedure

1. **Resolve the Test Case ID.** The failing test's traceability marker
   (`# TAG-TOPUP-TC-014`) maps to an Azure Test Case work item ID. If only the marker
   string is available, resolve it to a numeric ID before continuing (e.g. via the
   suite/PBI context already in hand) — `create_bug` needs the numeric ID.
2. **Dedup check** — call `find_existing_bug(test_case_id)`.
3. **If `exists: true`** — call `add_bug_occurrence(bug_id, error_message, run_url,
   test_case_id)` (passing the resolved numeric Test Case ID from step 1 so the
   Sprint/Feature bug-query hierarchy gets provisioned for this occurrence too).
   Done; report which bug was updated and whether it was reopened from `Resolved`.
4. **If `exists: false`** — map the Test Case's QA Priority to severity per the
   standards file, build repro steps from what's known (or let `create_bug` fall back
   to its generic "run the automated test" step), then call:
   `create_bug(test_case_id, test_name, error_message, expected_result, actual_result, repro_steps, priority, screenshot_path, run_url)`.
5. **Report back** — bug ID, URL, severity, whether tags applied, whether a screenshot
   was attached, and the `query_provisioning` outcome (created/existing/skipped/error
   for the Sprint/Feature queries). If `create_bug` degraded (tags rejected, no
   screenshot found) or query provisioning errored, say so plainly — don't silently
   report success.

## Hard boundary

- **Does not decide if a bug is warranted.** Scope (which failures are eligible) is
  fixed in `automation-standards.md` — every failure, no human gate. This skill only
  executes once asked.
- **Never files a duplicate.** Step 2 is mandatory before step 4, every time.
- **Does not edit test code or re-run the test.** That's `automate-test-case` /
  `run-automation`'s job — if the failure looks like a framework issue rather than a
  product defect, say so in the report but still log it; don't silently skip it.
- **Does not generate the QA summary report.** That's `generate-summary-report`,
  invoked separately after all failures in a run have been processed.

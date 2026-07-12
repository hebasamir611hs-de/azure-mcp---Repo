---
name: automate-test-case
description: Turn an APPROVED QA test case into a runnable pytest test in the existing ./automation/ framework — building the Page/Screen Object methods, requesting locators as needed, mirroring the case's concrete data, tagging with markers + the QA traceability ID, and asserting in the test. Web → Playwright, mobile → Appium, chosen by the case's target surface. Use after the framework is scaffolded and a signed-off case (from qa-engineer / the chat set) is ready to automate. Does NOT generate, edit, or re-judge the test case itself, and makes no Azure DevOps calls (integration deferred) — it reads cases from the approved set.
---

# Automate Test Case — Approved Case → Runnable pytest Test

Translate an **already-approved** QA test case into a clean, runnable pytest test inside
`./automation/`, using Page/Screen Objects and the wrapper layer. This is engineering of
*existing* coverage — **no test-case creation or re-judging happens here.**

**Argument:** the case(s) to automate → `$ARGUMENTS` (a test case ID/title or the approved
chat set). If no approved case is in hand, stop — route to `analyze-pbi` /
`quick-test-cases` first.

> Structure, wrapper API, markers↔tags mapping, naming, and the Definition of Done live
> in `@.claude/context/automation-standards.md`. This skill applies them.

## Procedure

1. **Preconditions.** Confirm (a) `./automation/` exists — if not, run
   `scaffold-automation-framework` first; (b) the case is **approved/signed-off** — if
   not, send the user to `analyze-pbi` / `quick-test-cases`.
2. **Read the contract** — `@.claude/context/automation-standards.md` (test structure,
   AAA, markers, traceability, "no locators in tests", "no `sleep`").
3. **Pick the engineer** by the case's target surface:
   - website / CMS → **`senior-web-automation-eng`** (Playwright)
   - mobile app → **`senior-mobile-automation-eng`** (Appium)
   A case covering both → automate one test per surface via each engineer.
4. **Get locators** — for any page/screen the test touches whose object lacks locators,
   run `extract-locators` for that target. Locators land in the Page/Screen Object, never
   in the test.
5. **Build the layers, top-down — into the per-page structure:**
   - **Placement first.** Each artifact goes in the folder named after its page/module:
     Page/Screen Object → `pages/<page>/` (or `screens/<screen>/`; shared cross-page
     components → `pages/components/` / `screens/components/`), test →
     `tests/<page>/test_<page>.py` (module name mirrors the folder). If the page already
     has a folder, **extend and append to whatever `test_*.py` module exists in it**;
     create a new folder + module only for the first case of a page. **Never create one
     file per test case** — all of a page's cases live in its single test module.
   - **Page/Screen Object** — add/extend action methods (`login`, `top_up`) and state
     queries; no asserts, no `sleep`, no test data inside.
   - **Test** — AAA shape, concrete data **mirrored from the case** (e.g. `Top-up = 50
     QAR`), assertions in the test, wrapped meaningful steps in `allure.step(...)`.
   - **Tag it** — markers per the case's lifecycle tags (`regression` / `smoke` /
     `sanity` + `web`/`mobile`) and the QA **traceability ID** in a marker/docstring
     (e.g. `# TAG-TOPUP-TC-014`).
6. **Run the structure & redundancy scan** — mandatory after every batch, per the
   *Structure & redundancy scan* section of `automation-standards.md`: per-page folders
   respected, no one-file-per-case modules, no duplicate tests/locators/POM methods, no
   contract violations. Fix findings before proceeding, and include the scan outcome in
   the report.
7. **Validate against the Definition of Done** — no raw driver in the test, locators from
   `extract-locators`, independent/idempotent, Allure title + severity (from QA priority).
   Run the single test (or its marker) and confirm green on a clean state; for mobile
   without a device, statically validate and state that execution is pending the
   environment — never claim an unobserved pass.
8. **Report** — files added/changed, the marker(s) and traceability ID applied, the scan
   outcome, and the run result (or why it couldn't run yet). For full-suite runs, use
   `run-automation`.

## Hard boundary
Automates approved cases only. **Never** invents, edits, or re-prioritizes a test case;
if coverage looks wrong, flag it to the QA Manager. No Azure DevOps calls — the backlog
comes from the approved set until integration is explicitly enabled.

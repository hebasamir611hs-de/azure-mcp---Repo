---
name: extract-locators
description: Extract REAL element locators on demand from the live app — web (Playwright DOM/accessibility tree) or mobile (Appium UI hierarchy / UIAutomator / XCUITest) — and write them as named constants inside the relevant Page/Screen Object following the locator-priority order. Pulls only the locators a test actually needs, when it needs them; never bulk-guesses or commits placeholder dumps. Use when an automated test or Page/Screen Object needs selectors for a specific page/screen. Requires access to the running app (URL/build + creds); if unavailable, it scaffolds clearly-marked TODO locators instead. Do NOT use to write the test logic (use automate-test-case).
---

# Extract Locators — On-Demand, Real, Prioritized

Pull the **real locators** for a specific page/screen from the **running app**, and write
them into the Page/Screen Object. Locators are fetched **when a test needs them**, not
guessed in bulk and not committed as static placeholder dumps.

**Argument:** the target → `$ARGUMENTS` (e.g. `web: WOQOD-Web login page` or
`mobile: Top-up screen (Android)`). If the surface or screen is unclear, ask.

> The locator-priority order and hygiene rules live in
> `@.claude/context/automation-standards.md` (*Locator strategy*). This skill applies
> them; it does not restate them.

## Procedure

1. **Read the contract** — `@.claude/context/automation-standards.md` (locator priority,
   naming, RTL/Arabic rule, "no locators in tests").
2. **Pick the engineer** — delegate via the Agent tool:
   - web target → **`senior-web-automation-eng`**
   - mobile target → **`senior-mobile-automation-eng`**
3. **Confirm app access.** Need a reachable target + credentials:
   - **Web:** base URL + route + login creds (from `.env`), driven via Playwright.
   - **Mobile:** Appium server + emulator/device + app build + capabilities.
   If access is **not** available, do **not** invent selectors. Scaffold the
   Page/Screen Object with `TODO(locator)` named constants and clearly report that real
   extraction is pending access.
4. **Inspect the live target** and harvest only the elements the requested flow touches:
   - **Web:** read the DOM + accessibility tree; prefer `data-testid` → role/label →
     stable `id` → scoped CSS → relative XPath (last resort).
   - **Mobile:** dump the page source / inspector hierarchy; prefer `accessibility id` →
     `resource-id`/iOS `name` → uiautomator/class-chain → XPath (last resort).
   Where a high-tier locator is missing (e.g. no `data-testid`), note it as a
   recommendation for the dev team rather than silently falling to XPath.
5. **Write them into the object** — named constants (intent-named, not tag-named), one per
   element, **inside** the relevant Page/Screen Object in `./automation/`. Never inline a
   raw selector at a call site; never put a locator in a test.
6. **Report** — which elements were captured, the tier used for each, and any element that
   fell back to a fragile locator (with the suggested `data-testid`/`accessibility id` to
   request from the developers).

## Hard boundary
Locators only. No test logic, no assertions, no Azure DevOps calls. Writing the test that
*uses* these locators is `automate-test-case`.

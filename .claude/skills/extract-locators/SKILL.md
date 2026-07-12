---
name: extract-locators
description: Extract REAL element locators on demand from the live app — via the Playwright MCP for web (DOM/accessibility tree) or the Appium/mobile MCP for mobile (UI hierarchy / UIAutomator / XCUITest) — and write them as named constants inside the relevant Page/Screen Object following the locator-priority order. Pulls only the locators a test actually needs, when it needs them; never bulk-guesses or commits placeholder dumps. Use when an automated test or Page/Screen Object needs selectors for a specific page/screen. Requires access to the running app (URL/build + creds); if unavailable, it scaffolds clearly-marked TODO locators instead. Do NOT use to write the test logic (use automate-test-case).
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
   naming, RTL/Arabic rule, "no locators in tests", and the per-page structure/placement
   rules — a Page/Screen Object this skill touches must live in its per-page folder).
2. **Pick the engineer** — delegate via the Agent tool:
   - web target → **`senior-web-automation-eng`**
   - mobile target → **`senior-mobile-automation-eng`**
3. **Confirm app access.** Need a reachable target + credentials:
   - **Web:** base URL + route + login creds (from `.env`), driven via the
     **Playwright MCP**.
   - **Mobile:** Appium server + emulator/device + app build + capabilities, driven via
     the **Appium/mobile MCP**.
   Two distinct failure modes — do not conflate them:
   - App **not reachable** → do **not** invent selectors. Scaffold the Page/Screen
     Object with `TODO(locator)` named constants and clearly report that real extraction
     is pending access.
   - App reachable but the **MCP server unavailable** → fall back to a scripted
     inspection (see step 4) and say so in the report; `TODO(locator)` placeholders are
     only for missing app access.
4. **Inspect the live target via MCP** and harvest only the elements the requested flow
   touches. **The MCP servers are the required discovery mechanism** — they are far more
   token/cost-efficient than screenshots or ad-hoc inspection scripts; prefer their
   text-based tree/find tools over any visual capture. Fall back to a scripted
   inspection only if the relevant MCP server is unavailable, and say so in the report.
   - **Web — use the Playwright MCP:** set the inspection browser's viewport to the
     framework default (**1920×1080**, or the `VIEWPORT_WIDTH`/`VIEWPORT_HEIGHT`
     override) so locators are harvested from the same layout the tests will run
     against, then navigate to the page and read the DOM + accessibility tree through
     the MCP's snapshot/tree tools; prefer `data-testid` → role/label → stable `id` →
     scoped CSS → relative XPath (last resort).
   - **Mobile — use the Appium/mobile MCP:** drive the app and read the UI hierarchy
     through the MCP's tree/find tools (not screenshots); prefer `accessibility id` →
     `resource-id`/iOS `name` → uiautomator/class-chain → XPath (last resort).
   Where a high-tier locator is missing (e.g. no `data-testid`), note it as a
   recommendation for the dev team rather than silently falling to XPath.
5. **Write them into the object** — named constants (intent-named, not tag-named), one per
   element, **inside** the relevant Page/Screen Object in `./automation/`, placed per the
   structure contract: `pages/<page>/` / `screens/<screen>/` (shared cross-page elements →
   the component object in `pages/components/` / `screens/components/`), extending the
   existing folder/object if one exists — never a flat file. **Reuse before add:** first
   check the target object and the component objects for an existing constant covering
   the element and reuse/extend it — do not write a duplicate constant for the same
   element. Never inline a raw selector at a call site; never put a locator in a test.
6. **Report** — which elements were captured, the tier used for each, and any element that
   fell back to a fragile locator (with the suggested `data-testid`/`accessibility id` to
   request from the developers).

## Hard boundary
Locators only. No test logic, no assertions, no Azure DevOps calls. Writing the test that
*uses* these locators is `automate-test-case`.

---
name: scaffold-automation-framework
description: Generate the runnable test-automation framework at the PROJECT ROOT (./automation/) — Playwright+Python for web or Appium+Python for mobile, on pytest with Allure reporting (screenshots + video). Produces the full structure, core wrappers, config, conftest hooks, pytest.ini, requirements, README, and one working example test per the automation-standards contract. Use when the user wants to create/initialize/set up the automation framework, or before automating the first test on a new surface. The generated framework is git-ignored — it is NOT committed to this MCP repo. Do NOT use to write individual tests (use automate-test-case) or to run the suite (use run-automation).
---

# Scaffold Automation Framework — Generate `./automation/`

Create the runnable automation framework at the **project root**, exactly per the
contract. This skill builds the *structure and the generic `core/` layer* — not feature
tests.

**Argument:** the surface to scaffold → `$ARGUMENTS` (`web` | `mobile` | `both`).
(If not given, ask. Default per project: WOQOD has both surfaces — confirm which the
user needs first.)

> Knowledge lives in `@.claude/context/automation-standards.md`. This skill orchestrates
> generation; it does not restate the structure, stack, or rules — it applies them.

## Procedure

1. **Read the contract** — `@.claude/context/automation-standards.md` (structure, stack,
   wrapper API, locator strategy, reporting, Definition of Done). Also skim
   `@.claude/context/woqod-background.md` for surfaces/services.
2. **Pick the engineer** — delegate the build via the Agent tool:
   - `web` → **`senior-web-automation-eng`** (Playwright)
   - `mobile` → **`senior-mobile-automation-eng`** (Appium)
   - `both` → run both; they share `core/utils`, `conftest.py`, `config/`, `pytest.ini`,
     and Allure setup, and add their own `core/web` + `web/` or `core/mobile` + `mobile/`
     trees. Build the shared base once, then each tree.
3. **Generate the tree** at `./automation/` exactly as in the contract: `README.md`,
   `requirements.txt` (pinned), `pytest.ini` (markers + `--alluredir`), `.env.example`,
   `conftest.py` (config + driver/browser fixtures + screenshot-on-failure + video/
   recording + Allure hooks), `config/settings.py`, the generic `core/` wrappers
   (`base_page.py` / `base_screen.py` — the only place raw driver is touched), and empty
   `pages`/`screens` + `tests` trees.
4. **Produce one working example** that exercises the whole stack end to end (wrapper →
   Page/Screen Object → test → Allure with a screenshot). Web example should run with no
   device. For mobile, include the example but document that execution needs an Appium
   server + emulator/device; don't claim a green run you didn't observe.
5. **Confirm it's git-ignored** — verify `automation/` and Allure/media artifacts are in
   this repo's `.gitignore`; if missing, add them. The framework must never be committed
   to this MCP repo.
6. **Report** — what was generated, how to install (`pip install -r requirements.txt`,
   `playwright install` where relevant), and how to run (point at `run-automation`).

## Hard boundary
This skill generates structure + `core/` + one example only. It does **not** write the
feature test suite (that's `automate-test-case`), does **not** run the full suite (that's
`run-automation`), and makes **no** Azure DevOps calls (it generates structure only).

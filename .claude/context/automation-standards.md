# Automation Standards & Conventions

> The contract for the test-automation layer. Every automation agent and skill reads
> this before writing a line of code. It defines the framework structure, naming, the
> locator strategy, wrapper/Page-Object rules, reporting, and how automation maps back
> to the QA test cases. Project/business facts live in `@.claude/context/woqod-background.md`;
> QA tagging/IDs live in `@.claude/context/woqod-standards.md`. This file governs **how
> the automation is built**, not what to test.

---

## Where the framework lives — read this first

The generated framework is **NOT part of this repository.** This git repo is the
MCP / QA-orchestration system only. The runnable automation framework is a **local,
generated artifact**:

- It is scaffolded at the **project root** (`./automation/`) **only when the user asks**
  (via the `scaffold-automation-framework` skill).
- It is **git-ignored** here — `automation/`, `allure-results/`, `allure-report/`,
  `.env`, videos, and screenshots never get committed to this repo.
- What *is* committed here is the **intelligence layer**: these standards, the two
  automation agents, and the automation skills. They know how to *produce* the
  framework; they are not the framework.

If `./automation/` does not exist yet, the correct move is to run
`scaffold-automation-framework`, not to hand-write files ad hoc.

---

## Stack — pinned

| Surface | Driver | Language | Runner | Report |
|---|---|---|---|---|
| **Web** (WOQOD / FAHES / Qjet sites, CMS) | **Playwright** | Python 3.11+ | **pytest** | **Allure** + Playwright trace/video |
| **Mobile** (app — iOS + Android) | **Appium** | Python 3.11+ | **pytest** | **Allure** + screen recording |

- One runner everywhere: **pytest**. One report everywhere: **Allure**.
- Surface is chosen **per feature**, from the WOQOD Service ↔ Platform matrix
  (`woqod-background.md`). A feature on the app → mobile/Appium; a feature on a website
  or CMS → web/Playwright. A feature on both → a test in each tree, shared step intent.

---

## Repository structure (generated at `./automation/`)

```
automation/
├─ README.md                  # setup + run instructions (incl. mobile prereqs)
├─ requirements.txt           # pinned deps
├─ pytest.ini                 # markers, addopts (--alluredir, etc.)
├─ .env.example               # URLs, Appium caps, creds — copied to .env locally
├─ conftest.py                # root fixtures: config, driver/browser, hooks
├─ config/
│  └─ settings.py             # typed config loaded from env; NO secrets in code
├─ core/                      # the reusable framework — never feature-specific
│  ├─ web/
│  │  ├─ browser.py           # Playwright launch/context/page factory
│  │  └─ base_page.py         # BasePage wrapper (the only place raw Playwright is touched)
│  ├─ mobile/
│  │  ├─ driver.py            # Appium driver factory (iOS/Android caps)
│  │  └─ base_screen.py       # BaseScreen wrapper (the only place raw Appium is touched)
│  └─ utils/
│     ├─ reporting.py         # screenshot/video attach → Allure
│     ├─ waits.py             # explicit-wait helpers
│     └─ logger.py
├─ web/
│  ├─ pages/
│  │  └─ <feature>/           # ONE FOLDER PER FEATURE (e.g. contact_us/) with __init__.py
│  │     └─ <page>_page.py    # Page Objects — one class per page/component
│  └─ tests/
│     └─ <feature>/           # ONE FOLDER PER FEATURE (e.g. contact_us/) with __init__.py
│        ├─ test_<area>.py    # group related cases by sub-area/story — many tests per module
│        └─ test_<area>.py
├─ mobile/
│  ├─ screens/
│  │  └─ <feature>/           # one folder per feature; one class per screen
│  └─ tests/
│     └─ <feature>/           # one folder per feature, modules grouped by sub-area
└─ reports/                   # generated allure-results / allure-report (git-ignored)
```

Rules:
- **Organize by feature, then sub-area.** Both `pages/`/`screens/` and `tests/` are
  split into **one folder per feature** (e.g. `contact_us/`), each with an `__init__.py`.
  Page/Screen Objects for that feature live in its `pages/<feature>/` (or
  `screens/<feature>/`) folder; tests live in `tests/<feature>/`.
- **Group tests by sub-area, never one file per test case.** Inside a feature's test
  folder, group related cases into a module by sub-area/story
  (`test_submission.py`, `test_validation.py`, `test_attachments.py`, …) with **many
  test functions per module**. pytest runs test *functions*, not files — a file per
  case just fragments the suite. (Markers + the per-test traceability ID still map each
  function back to its Azure case.)
- **`core/` is generic.** Nothing in `core/` references WOQOD, a specific page, or a
  specific feature. Feature knowledge lives only in `pages/`, `screens/`, and `tests/`.
- **Tests never touch raw Playwright/Appium.** A test calls Page/Screen-Object methods,
  which call `BasePage`/`BaseScreen` wrappers. If a test imports `playwright` or
  `appium` directly, that's a defect.
- **No locators in tests.** Locators live only inside Page/Screen Objects.

---

## The wrapper layer (`BasePage` / `BaseScreen`)

Every interaction goes through a wrapper that is **self-waiting, self-logging, and
self-screenshotting**. The wrapper is where flakiness is killed and where Allure
attachments are produced.

Minimum wrapper API (both web and mobile mirror these):

| Method | Guarantees |
|---|---|
| `open(target)` / `launch()` | navigate / start session |
| `click(locator)` | wait-for-actionable → click → log |
| `type(locator, text)` | wait → clear → type → log (mask secrets) |
| `text(locator)` | wait-for-visible → return text |
| `is_visible(locator)` | bounded wait → bool, never throws |
| `wait_for(locator, state)` | explicit wait, no `sleep()` |
| `screenshot(name)` | capture → attach to Allure |
| `assert_visible / assert_text` | soft-fail aware, attaches on failure |

Hard rules:
- **No `time.sleep()`.** Ever. Use explicit waits from `core/utils/waits.py`.
- **No bare asserts in Page Objects.** Page Objects expose state; tests assert. (A small
  set of `assert_*` wrappers is fine for readability, but the assertion intent lives in
  the test.)
- **Every action logs** what it did and on which locator.
- **Secrets are masked** in logs and reports (passwords, OTP, card numbers, tokens).

---

## Locator strategy — priority order

Locators are **extracted on demand** by the `extract-locators` skill (never hand-guessed
in bulk, never committed as static placeholder dumps). When choosing a locator, prefer
the highest available tier:

**Web (Playwright):**
1. `data-testid` / `data-test` (ask the team to add these where missing — most stable)
2. Role + accessible name (`get_by_role`, `get_by_label`) — survives restyling
3. Stable `id`
4. Scoped CSS (short, semantic — no deep descendant chains)
5. **XPath — last resort only**, and only relative/text-anchored, never absolute

**Mobile (Appium):**
1. `accessibility id` (the cross-platform first choice)
2. Android: `resource-id`; iOS: `name` / predicate on stable attributes
3. `-android uiautomator` / iOS class chain for lists/repeating items
4. **XPath — last resort only** (slowest on mobile; flag it in the PO)

Locator hygiene:
- One named constant per element inside its Page/Screen Object — never inline a raw
  selector at a call site.
- Name locators by intent (`login_button`), not by tag (`blue_div`).
- RTL/Arabic: locate by `testid`/role/`accessibility id`, **never by visible Arabic
  text** unless the test is specifically asserting that text.

---

## Page Object / Screen Object rules

- **One class per page/screen/component.** File name = snake_case; class = PascalCase
  (`login_page.py` → `LoginPage`).
- A Page Object holds: its locators (constants) + action methods (`login(user, pwd)`) +
  state queries (`error_message_text()`). It returns the next Page Object on navigation.
- **No assertions, no test data, no waits-by-sleep** inside Page Objects.
- Reusable cross-feature components (header, nav, OTP modal) get their own component
  object and are composed in, not copy-pasted.

---

## Test structure & naming

- One test module per feature: `test_<service>_<feature>.py`
  (e.g. `test_tag_topup.py`, `test_fahes_booking.py`).
- One test function per scenario, named for intent:
  `test_topup_with_expired_card_is_rejected`.
- **AAA shape:** Arrange (fixtures/preconditions) → Act (Page-Object calls) →
  Assert (in the test).
- **Independent & idempotent:** no test depends on another's side effects; each sets up
  and tears down its own data. Parallel-safe.
- **Concrete data, mirrored from the QA case** — use the same concrete values the test
  case specifies (`Top-up = 50 QAR`), via a data builder/fixture, not hard-coded literals
  scattered in the test body.
- Every test carries the QA **traceability ID** in a marker/docstring
  (`# TAG-TOPUP-TC-014`) so an automated test maps back to its source case.

### pytest markers ↔ QA tags

Markers **mirror the Azure tags 1:1** (`woqod-standards.md`) so the suite slices the
same way the test cases do. A marker **never introduces a tag key that isn't in the
taxonomy** — it reuses the Lifecycle and Platform axis values exactly.

| Marker | Mirrors tag | Meaning |
|---|---|---|
| `@pytest.mark.regression` | `Regression` | The automated suite = the feature's MAIN functional scenarios. |
| `@pytest.mark.web` · `@pytest.mark.ios` · `@pytest.mark.android` · `@pytest.mark.control_panel` | Platform (`Web` / `IOS` / `Android` / `Control_Panel`) | Surface selector — mirrors the Platform axis exactly. |

There is **no `automated` marker** (`regression` already *is* the automated set) and no
`smoke`/`sanity` markers (those lifecycle tags were removed). Register every marker in
`pytest.ini` (no unknown-marker warnings).

---

## Reporting — Allure (mandatory)

The report must be **readable by a non-engineer** and must show, per failing step, *what
the app looked like*:

- **Allure** is the aggregator: `pytest --alluredir=reports/allure-results`, served with
  `allure serve` / `allure generate`.
- **Screenshots:** auto-captured **on every failure** (conftest hook) and on demand via
  `screenshot()`; attached to the failing Allure step.
- **Video:**
  - Web — Playwright context `record_video_dir` always on; trace
    (`tracing.start(screenshots, snapshots, sources)`) retained **on failure**.
  - Mobile — Appium screen recording (`start_recording_screen` /
    `stop_recording_screen`) around each test, attached **on failure** (retain-on-failure
    by default to save space; configurable to always-on).
- **Structure the report:** use Allure `epic`/`feature`/`story` from the Service/Feature,
  `severity` from QA priority (P1→blocker … P4→minor), and `@allure.title` from the test
  case title.
- **Steps:** wrap meaningful Page-Object actions in `allure.step(...)` so the report reads
  like the manual test case's steps.

---

## Configuration & secrets

- All environment data (base URLs per site, Appium server URL, device/OS caps, test
  credentials) comes from **env / `.env`** via `config/settings.py`. **Never** hard-code
  URLs, caps, or credentials in tests or Page Objects.
- `.env.example` is committed *inside the generated framework* (which itself is
  git-ignored here) as a template; the real `.env` is never committed anywhere.
- Default environment = **QA/UAT** (confirm with the team per `woqod-background.md`).

---

## Definition of Done (an automated test)

A test is done only when ALL hold:
- Lives in the right tree (`web/` or `mobile/`), imports **no** raw driver.
- All interactions go through Page/Screen Objects → wrappers; **zero `sleep()`**.
- Locators came from `extract-locators` and follow the priority order.
- Carries its QA traceability ID and the correct markers (`regression` etc.).
- Independent, idempotent, parallel-safe; concrete data mirrored from the QA case.
- Produces a clean Allure entry: titled, severity-tagged, steps named, screenshot+video
  attached on failure.
- Passes locally on a clean checkout (`pytest -m smoke` green) before it's called done.

---

## Azure DevOps integration — DEFERRED

The loop closes later, after the framework is proven standalone. When enabled:
- **Source the backlog** from Azure cases tagged `Regression` (the existing automation
  candidates) instead of the chat set.
- **Post results back** via the MCP audit tools (`get_test_outcome_summary`,
  `review_test_coverage`).
Until the user explicitly turns this on, automation runs **standalone** — tests are
authored from the approved chat/QA set, and nothing reads from or writes to Azure.

---
*Living document. Refine as the framework matures — but keep `core/` generic and keep
the repo free of the generated framework.*

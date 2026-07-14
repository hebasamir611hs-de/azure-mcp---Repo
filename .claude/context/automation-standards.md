# Automation Standards & Conventions

> The contract for the test-automation layer. Every automation agent and skill reads
> this before writing a line of code. It defines the framework structure, naming, the
> locator strategy, wrapper/Page-Object rules, reporting, and how automation maps back
> to the QA test cases. Project/business facts and QA tagging/IDs come from the
> project context — ask the user if not provided. This file governs **how
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
- Surface is chosen **per feature**, per the project's service ↔ platform mapping —
  ask the user when a feature's surface is unclear. A feature on the app →
  mobile/Appium; a feature on a website or CMS → web/Playwright. A feature on both →
  a test in each tree, shared step intent.
- **API accuracy — docs over memory.** When unsure about a Playwright, Appium, pytest,
  or Allure API (signature, option name, deprecation), consult the **official
  documentation** (playwright.dev/python, appium.io, docs.pytest.org,
  allurereport.org) via WebFetch/WebSearch rather than coding from training memory.
  *(An offline docs snapshot as a local RAG source is under consideration; until then,
  the online docs are the reference.)*

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
│  ├─ pages/                  # Page Objects — grouped by page/module, never flat
│  │  ├─ components/          #   shared cross-page component objects (header, nav, OTP modal)
│  │  └─ login/               #   e.g. pages/login/login_page.py
│  └─ tests/                  # pytest tests — mirrors pages/, one folder per page/module
│     └─ login/               #   e.g. tests/login/test_login.py — ALL login cases in ONE module
├─ mobile/
│  ├─ screens/                # Screen Objects — grouped by screen/module, never flat
│  │  ├─ components/          #   shared cross-screen component objects
│  │  └─ tag_topup/           #   e.g. screens/tag_topup/tag_topup_screen.py
│  └─ tests/                  # mirrors screens/
│     └─ tag_topup/           #   e.g. tests/tag_topup/test_tag_topup.py — ALL top-up cases in ONE module
└─ reports/                   # generated allure-results / allure-report (git-ignored)
```

Rules:
- **`core/` is generic.** Nothing in `core/` references WOQOD, a specific page, or a
  specific feature. Feature knowledge lives only in `pages/`, `screens/`, and `tests/`.
- **Group by page/module — never flat.** Every Page/Screen Object and every test module
  lives in a folder named after the page/module it belongs to (`pages/login/`,
  `tests/login/`), with matching folder names between the object tree and the test tree
  (each folder gets an `__init__.py`). Folder names are snake_case; a service-scoped
  feature uses `<service>_<feature>` (e.g. `tag_topup`, `fahes_booking`). The folder is
  created with the first artifact for that page; new artifacts for an already-covered
  page go **into the existing folder**. The one exception to page-naming: reusable
  cross-page component objects (header, nav, OTP modal) live in `pages/components/` /
  `screens/components/` — never flat and never duplicated into page folders.
- **One spec module per page/feature — NEVER one file per test case.** The single test
  module's name mirrors its folder: `tests/<page>/test_<page>.py` (e.g.
  `tests/login/test_login.py`, `tests/tag_topup/test_tag_topup.py`). All test cases for
  a page/feature accumulate in that one module. The existing module is identified **by
  the page folder**: if any `test_*.py` already exists in `tests/<page>/`, append to it
  regardless of its exact name — creating a second module, or a new file per case, is a
  defect.
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
in bulk, never committed as static placeholder dumps).

**Fetch via MCP — required mechanism.** Locator discovery drives the live app through
the MCP servers: the **Playwright MCP** for web (DOM + accessibility tree) and the
**Appium/mobile MCP** for the app (UI hierarchy). MCP inspection is far more
token/cost-efficient than screenshot-driven discovery or ad-hoc throwaway scripts —
prefer the text-based tree/find tools over screenshots. Fall back to a scripted
inspection only when the relevant MCP server is unavailable, and say so explicitly.

When choosing a locator, prefer the highest available tier:

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
  object in `pages/components/` / `screens/components/` and are composed in, not
  copy-pasted.

---

## Test structure & naming

- One test module per page/feature, inside that page's folder, module name mirroring
  the folder name: `tests/<page>/test_<page>.py`
  (e.g. `tests/tag_topup/test_tag_topup.py`, `tests/fahes_booking/test_fahes_booking.py`,
  `tests/login/test_login.py`).
- **All test cases for a page/feature live in that one module.** A new case for an
  already-covered page is **appended** to the existing module as a new test function —
  never a new file. Identify the module by the folder: append to whatever `test_*.py`
  already exists in `tests/<page>/`. One-file-per-test-case is a defect.
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

### pytest markers ↔ QA lifecycle tags

Markers mirror the Azure lifecycle tags (from the project's tag taxonomy — ask the
user if not provided) so the suite slices the same way the test cases do:

| Marker | Mirrors tag | Meaning |
|---|---|---|
| `@pytest.mark.regression` | `Regression` | The **critical re-run subset** — run on every change. A subset of the automated suite, not all of it. |
| `@pytest.mark.web` · `@pytest.mark.ios` · `@pytest.mark.android` · `@pytest.mark.control_panel` | Platform (`Web` / `IOS` / `Android` / `Control_Panel`) | Surface selector — mirrors the Platform axis exactly. |

The **automated suite itself = every case tagged `Automation`** (the broad automatable set
the Automation engineer classified pre-injection); a `Manual`-tagged case has no test at
all. So there is **no `automation` / `manual` marker** — every test that exists is by
definition an `Automation` case, and `Manual` cases are never authored. `regression` marks
the critical subset *within* the suite. There are no `smoke` / `sanity` markers (those
tags were removed). Register every marker in `pytest.ini` (no unknown-marker warnings).

---

## Automation classification pass (before injection)

Before the QA Manager injects an approved set, the surface's Automation engineer reviews
**every** case and assigns the **`Automation` / `Manual`** execution-method tag (Axis 1b
in `woqod-standards.md`) — exactly one per case, **100% coverage**, never both. **Bias
toward `Automation`:** tag `Manual` only for cases that genuinely can't be automated
(physical/hardware steps, purely visual checks, CAPTCHA, human judgement). Align each
case's `execution_type` to match. The automation build then sources **every
`Automation`-tagged case**, not just `Regression`. This pass is pure judgement — no
framework code is written and the case content is never rewritten.

---

## Reporting — Allure (mandatory)

The report must be **readable by a non-engineer** and must show, per failing step, *what
the app looked like*:

- **Allure** is the aggregator: `pytest --alluredir=reports/allure-results`, served with
  `allure serve` / `allure generate`.
- **Attachment is the deliverable, not the file.** A screenshot/video sitting in a
  folder is NOT evidence — both must land in the failing test's Allure entry via
  `allure.attach(...)` / `allure.attach.file(...)`. The two attach at different points:
  the **screenshot** in the `pytest_runtest_makereport` failure hook, the **video/
  recording** in fixture teardown (see the Video bullet — it does not exist earlier).
  Wiring that makes this work: implement `pytest_runtest_makereport` as a hookwrapper
  that stashes the call-phase report on the item (e.g. `item.rep_call`); the browser/
  driver fixture teardown reads that flag to decide whether to attach the video. A
  failing test whose Allure entry lacks its screenshot **and** video is a framework
  defect: fix the wiring before trusting the report.
- **Screenshots:** auto-captured **on every failure** (conftest hook) and on demand via
  `screenshot()`; attached to the failing Allure step (`attachment_type=PNG`).
- **Video:**
  - Web — Playwright context `record_video_dir` always on; trace
    (`tracing.start(screenshots, snapshots, sources)`) retained **on failure**.
    ⚠ Playwright only finalizes the video file when the **context closes** — attach it
    in fixture teardown *after* `context.close()`, via `page.video.path()`, guarded by
    the test's failure status.
  - Mobile — Appium screen recording (`start_recording_screen` /
    `stop_recording_screen`) around each test, attached **on failure** (retain-on-failure
    by default to save space; configurable to always-on).
- **Prove it once:** after scaffolding (or any change to the failure hooks), run one
  deliberately failing probe test and open the report — confirm the screenshot and the
  video are attached to the failing entry, then delete the probe.
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
- **Web viewport default = 1920×1080 (Full HD).** Set once in the browser context
  factory (`core/web/browser.py`) — not per test — and overridable via env
  (`VIEWPORT_WIDTH` / `VIEWPORT_HEIGHT`). Responsive/mobile-web cases override it
  per test through the fixture (the browser/context fixture must accept a per-test
  viewport parameter, e.g. via indirect parametrization or a `viewport` marker), never
  by editing the default. Locator extraction inspects the page at this same default
  viewport so harvested locators match the runtime layout.
- `.env.example` is committed *inside the generated framework* (which itself is
  git-ignored here) as a template; the real `.env` is never committed anywhere. It must
  enumerate **every** value the framework reads, each with a realistic example: base URL
  per site, environment type (`ENV=dev|staging|uat|prod`), credential placeholders,
  viewport overrides, Appium server URL + device capabilities.
- **Scaffolding ends with a configuration summary.** The final reply of
  `scaffold-automation-framework` must list every configuration value the framework
  needs, pre-filled with example values, so the user knows exactly what to fill in
  (see that skill's report step).
- Default environment = **QA/UAT** (confirm with the team).

---

## Structure & redundancy scan — after every batch

After **every** batch of test-case additions or changes, run a scan of the framework
(the `automate-test-case` skill runs this as a mandatory step) and fix findings
**before** reporting done:

1. **Structure** — every Page/Screen Object and test module sits in its per-page folder
   (`pages/<page>/`, `tests/<page>/`, names mirrored between the two trees); naming
   follows the conventions above; no flat/stray files at the tree root; no
   one-file-per-test-case modules — cases for the same page merged into its single
   module.
2. **Redundancy** — no two tests cover the same case (same traceability ID, or same
   Arrange/Act/Assert intent under different names); no duplicated locator constants for
   the same element across objects; no copy-pasted Page/Screen-Object methods that
   should be a shared component object or base helper.
3. **Contract** — no raw driver imports in tests, no `sleep()`, no locators in tests,
   all markers registered in `pytest.ini`; the web browser-factory viewport default is
   still 1920×1080 (env-overridable) — per-test overrides go through the fixture, the
   default is never edited.

Report the scan outcome explicitly: *clean*, or what was found and how it was fixed.

---

## Definition of Done (an automated test)

A test is done only when ALL hold:
- Lives in the right per-page folder of the right tree
  (`web/tests/<page>/` or `mobile/tests/<screen>/`), inside that page's **single** test
  module; imports **no** raw driver.
- All interactions go through Page/Screen Objects → wrappers; **zero `sleep()`**.
- Locators came from `extract-locators` (MCP-driven) and follow the priority order.
- Carries its QA traceability ID and the correct markers (`regression` etc.).
- Independent, idempotent, parallel-safe; concrete data mirrored from the QA case.
- Produces a clean Allure entry: titled, severity-tagged, steps named, screenshot+video
  attached on failure.
- The post-batch **structure & redundancy scan** is clean.
- Passes locally on a clean checkout (`pytest -m smoke` green) before it's called done.

---

## Azure DevOps integration — READ enabled · post-back DEFERRED

- **READ (enabled).** The automation engineers **source the backlog from Azure**: they
  read a test suite via `mcp__azure-devops__get_test_cases_from_suite` (`plan_id`,
  `suite_id`) and build from the cases tagged **`Automation`** (the full automatable set;
  `Regression` is the critical re-run subset within it). They may still author from the
  approved chat set when no suite exists yet.
- **POST-BACK (deferred).** Writing results back to Azure (run outcomes,
  `get_test_outcome_summary`, `review_test_coverage`) stays **off** until the user
  explicitly enables it. Until then the engineers **read** cases but **write nothing** to
  Azure.
---
*Living document. Refine as the framework matures — but keep `core/` generic and keep
the repo free of the generated framework.*

# QA-Final-V4 — Azure DevOps QA Automation MCP Server

An end-to-end **QA orchestration system** powered by an MCP (Model Context Protocol)
server that bridges Azure DevOps with Claude / Claude Code. The system acts as a
single intelligent QA Manager that handles the full lifecycle: deriving test cases
from PBIs in two analysis modes (Normal default / Deep), classifying them for
automation, injecting cases into Azure DevOps, generating client UAT documents and
end-user feature manuals, and — at the end of the loop — preparing and running
automated tests through Playwright (web) and Appium (mobile) MCP servers.

> Built by the iHorizons QA team. The engine is **project-agnostic**: all
> project/business specifics live in `.claude/context/` — swap those two files to
> retarget (currently serving multiple projects: WOQOD, Asiacell eCommerce Platform,
> Awqaf Smart Khotba). On writes, the MCP derives the Azure team project from the
> **parent PBI itself** (`System.TeamProject`), so one org-level PAT can serve all
> projects; `AZURE_PROJECT` in `.env` scopes the sprint-level read queries.

---

## Why this exists

QA work on a sprint typically fragments across many tools: someone reads the PBI in
Azure, someone derives test cases in Word/Excel, someone pastes them into Azure
manually, someone writes the UAT doc by hand, someone else writes automated tests
later. Mistakes leak between the stages: missed edge cases, mismatched tags,
hand-rolled UAT formatting, stale automation. This repo collapses the whole pipeline
into a single conversation: you point the QA Manager at a PBI ID and it carries the
work through analysis → review → classification → injection → UAT doc / user manual
→ automation, with explicit hand-offs and sign-offs at each phase.

---

## High-level architecture

```mermaid
flowchart TB
    %% ═════════ LEGEND — one shape per concept ═════════
    subgraph Legend["Legend"]
        direction LR
        LP((P1)):::phaseStart
        LS[skill]:::skill
        LA{{sub-agent}}:::agent
        LM[(MCP server)]:::mcp
        LG[/user gate/]:::gate
        LP -->|flow| LS
        LS -.delegates.-> LA
    end

    User([User / QA Lead]):::user

    subgraph Brain["QA Manager Orchestrator (CLAUDE.md)"]
        QM{{QA Manager Hat}}:::agent
        DM{{Development Manager Hat}}:::agent
    end

    subgraph Phase1["Phase 1 — Analysis & Generation (chat only)"]
        P1((P1)):::phaseStart
        Mode[/"Mode: Normal default / Deep"/]:::gate
        AP[analyze-pbi]:::skill
        QT[quick-test-cases]:::skill
        QE{{qa-engineer}}:::agent
        G1[/SIGN-OFF GATE/]:::gate
    end

    subgraph Phase2["Phase 2 — Classification, Injection & Deliverables"]
        P2((P2)):::phaseStart
        CLS[Automation / Manual classification pass]:::skill
        IT[inject-test-cases]:::skill
        CBQ[create-bug-queries]:::skill
        BUD[build-uat-doc]:::skill
        BCUD[build-chat-uat-doc]:::skill
        CUM[create-user-manual]:::skill
        GSR[generate-summary-report]:::skill
        DR{{drafter}}:::agent
    end

    subgraph Phase3["Phase 3 — Automation Layer (Dev Manager hat)"]
        P3((P3)):::phaseStart
        G3[/APPROVAL GATE/]:::gate
        PAE[prep-automation-env]:::skill
        RA[route-automation]:::skill
        SAF[scaffold-automation-framework]:::skill
        EL[extract-locators]:::skill
        ATC[automate-test-case]:::skill
        RAU[run-automation]:::skill
        SWE{{senior-web-automation-eng}}:::agent
        SME{{senior-mobile-automation-eng}}:::agent
    end

    subgraph Phase3b["Phase 3b — Bug Reporting on Failure (auto — the only ungated writer)"]
        P3B((P3b)):::phaseStart
        QCE{{quality-control-engineer}}:::agent
        CAB[create-azure-bug]:::skill
    end

    subgraph MCPs["MCP Servers (.mcp.json)"]
        AZ[(azure-devops MCP)]:::mcp
        AP_MCP[(appium MCP)]:::mcp
        PW_MCP[(playwright MCP)]:::mcp
    end

    subgraph Quality["Reliability Layer"]
        TESTS["tests/ — pytest suite (92 tests)<br/>link-types · tag classifier · validation gate · bug queries · title guard"]:::mcp
        SMOKE["scratch/smoke_e2e.py<br/>live E2E: inject → read-back → cleanup"]:::mcp
    end

    TESTS -.guards.-> AZ
    SMOKE -.verifies.-> AZ

    %% ═════════ PHASE 1 — starts when the user submits a PBI ═════════
    User -->|"'Analyze PBI &lt;id&gt; [deep]'"| P1
    P1 --> Mode --> AP
    QM --> Phase1
    AP -.delegates derivation.-> QE
    QT -.optional read.-> AZ
    AP -- get_story_for_analysis --> AZ
    QE --> G1

    %% ═════════ PHASE 2 — starts on the user's explicit approval ═════════
    G1 -->|user approves the set| P2
    P2 --> CLS
    QM --> Phase2
    QM -.delegates classification.-> SWE
    QM -.delegates classification.-> SME
    SWE -.classifies web.-> CLS
    SME -.classifies mobile.-> CLS
    CLS --> IT
    IT -- execute_qa_feedback --> AZ
    IT -->|final step, auto| CBQ
    CBQ -- ensure_bug_query_hierarchy --> AZ
    BUD -.delegates formatting.-> DR
    BCUD -.delegates formatting.-> DR
    CUM -.delegates formatting.-> DR
    DR -- screenshots via --> PW_MCP

    %% ═════════ PHASE 3 — starts when the user asks to automate ═════════
    QM -.hat switch.-> DM
    DM -->|"user: 'automate PBI &lt;id&gt;'"| P3
    P3 --> RA
    RA --> PAE
    PAE -- verify and scaffold --> SAF
    RA --> G3
    G3 -->|user approves plan| ATC
    ATC -.delegates web.-> SWE
    ATC -.delegates mobile.-> SME
    SWE -- web automation --> PW_MCP
    SME -- mobile automation --> AP_MCP
    RA -- read Tag=Automation --> AZ
    RAU --> SWE
    RAU --> SME
    EL -.on demand.-> SWE

    %% ═════════ PHASE 3b — auto-starts when a run has failures ═════════
    RAU -->|failures detected — auto| P3B
    P3B --> QCE
    DM -.delegates triage.-> QCE
    QCE -- structured failure list --> CAB
    CAB -- find_existing_bug / create_bug / add_bug_occurrence --> AZ
    QCE -- summary payload --> GSR

    %% ═════════ STYLES ═════════
    classDef phaseStart fill:#37474f,color:#ffffff,stroke:#263238,stroke-width:2px
    classDef skill fill:#e3f2fd,color:#0d47a1,stroke:#1976d2
    classDef agent fill:#fff3e0,color:#e65100,stroke:#fb8c00
    classDef mcp fill:#e8f5e9,color:#1b5e20,stroke:#43a047
    classDef gate fill:#fffde7,color:#f57f17,stroke:#fbc02d,stroke-width:2px
    classDef user fill:#f3e5f5,color:#4a148c,stroke:#8e24aa
```

---

## The three phases

| Phase | Goal | Skills involved | Writes to |
|---|---|---|---|
| **1. Analysis & Generation** | Derive test coverage from a PBI in chat, in the chosen **mode** (Normal default / Deep) | `analyze-pbi`, `quick-test-cases` | Chat only (no Azure, no files) |
| **2. Classification, Injection & Deliverables** | Tag every case `Automation` / `Manual` (pre-injection), push to Azure, produce client UAT doc and end-user manual | `inject-test-cases`, `build-uat-doc`, `build-chat-uat-doc`, `create-user-manual`, `generate-summary-report` | Azure DevOps + `.docx` |
| **3. Automation Layer** | Stand up runnable tests for the chosen surface | `prep-automation-env`, `route-automation`, `scaffold-automation-framework`, `extract-locators`, `automate-test-case`, `run-automation` | `./automation/` (project root, git-ignored here) |

Each phase has a hard sign-off gate — Phase 1 never injects, Phase 2 never invents
cases, Phase 3 never re-judges coverage. The QA Manager owns the gates.

---

## Analysis modes — Normal (default) vs Deep

Every analysis runs in one of two modes. The user names the mode when submitting the
PBI; **if unspecified, the default is Normal.**

| Category | Normal (default) | Deep |
|---|---|---|
| UI / Functional-High / Functional-Low | ✅ Core focus | ✅ |
| Compatibility / Auth | ✅ Optional | ✅ |
| Edge | ✅ Lighter — key edges, abbreviated sweep | ✅ Full 4-step methodology |
| API | ❌ Excluded | ✅ |
| Additional / Non-functional / Security / Performance | ❌ Excluded | ✅ |

Mode controls **scope**, not format — the template, concrete-data rule, and tag
taxonomy are identical in both modes.

---

## The hat-switch: QA Manager → Development Manager

The same orchestrator wears two hats:

- **QA Manager** (Phase 1 + 2): defines scope and mode, runs the coverage review,
  signs off, pushes to Azure, produces UAT docs and user manuals.
- **Development Manager** (Phase 3): detects the project surface from Platform tags,
  picks the automation path (Playwright for web, Appium for mobile), prepares the
  environment, and delegates the implementation to the senior automation engineers.

The hat-switch is explicit: it happens at the end of Phase 1 (surface is recorded in
the sign-off) and again at the Phase 2 → 3 boundary (`route-automation` confirms and
hands off).

---

## Tag taxonomy — at a glance

Every injected case carries tags across multiple axes. The QA Engineer decides
Lifecycle / Service / Platform / Category; the **Automation engineer** assigns
`Automation` or `Manual` in a dedicated pre-injection classification pass.

| Axis | Tag(s) | Decided by |
|---|---|---|
| 0 — Provenance | `Ai_MCP_Injected` | MCP (automatic) |
| 1a — Lifecycle | `UAT`, `Regression` | QA Engineer |
| 1b — Execution method | `Automation`, `Manual` (exactly one) | **Automation Engineer** (pre-injection pass) |
| 2 — Service | **Per-project codes** from the active `*-standards.md` (e.g. WOQOD: `TAG`/`FAHES`/`BOOK`; Asiacell: `CHECKOUT`/`SIM`/`CATALOG`/`PAYMENT`…) | QA Engineer |
| 3 — Platform | `Web`, `IOS`, `Android`, `Control_Panel` | QA Engineer |
| 4 — Category | UI, Functional-High, Functional-Low, etc. | QA Engineer |
| 5 — Business | Optional keyword (e.g. `Payment`) | QA Engineer |

`Regression ⊆ Automation`: every `Regression` case is also `Automation` (never
`Manual`). `Automation` is the broader automatable set; `Regression` is the focused
re-run subset within it.

---

## Skills router

> Procedures live in skills — the QA Manager does not improvise them inline.

| Skill | Phase | What it does |
|---|---|---|
| `analyze-pbi` | 1 | Full Phase-1 coverage for a PBI in the chosen mode (Normal/Deep); sign-off includes detected automation surface |
| `quick-test-cases` | 1 | Tight prioritized subset (happy + critical negatives + sharpest edges) |
| `inject-test-cases` | 2 | Phase-2 transport — pushes the approved, classified set into Azure DevOps under a parent PBI |
| `build-uat-doc` | 2 | Client UAT `.docx` from the Azure suite filtered by `Tag = UAT` — RTL for Arabic, LTR for English |
| `build-chat-uat-doc` | 2 | Client UAT `.docx` from the approved chat set (no Azure read needed) — same RTL/LTR handling |
| `create-user-manual` | 2 | End-user feature manual `.docx` — iHorizons-branded fixed template, screenshot-gated |
| `generate-summary-report` | 2 | HTML quality summary of the injected batch |
| `prep-automation-env` | 3 | Verifies MCP + host + framework readiness for the chosen surface; auto-scaffolds if missing |
| `route-automation` | 3 | Phase 2.5 hybrid router — reads Azure batch, classifies surfaces, runs prep, waits for approval; iOS on non-macOS = skipped with warning |
| `scaffold-automation-framework` | 3 | Generates `./automation/` (web / mobile / both) with the canonical structure |
| `extract-locators` | 3 | Pulls real locators on demand from the live app into the Page/Screen Object |
| `automate-test-case` | 3 | Translates one approved `Automation`-tagged QA case into a runnable pytest test |
| `run-automation` | 3 | Executes the pytest suite, produces an Allure report |
| `create-bug-queries` | 2 (infra) | Provisions the PBI's bug-query hierarchy (`ensure_bug_query_hierarchy`) — invoked automatically as `inject-test-cases`' final step; call directly to backfill |
| `create-azure-bug` | 3b | Files/updates a Bug per failed automated test — dedup via `find_existing_bug` (`TC:<id>` tag), plain-English titles, raw error preserved in Repro Steps. **Auto-triggered, no confirmation gate** |

---

## Sub-agents

| Agent | Type | Role |
|---|---|---|
| `qa-engineer` | Reasoning (no MCP, no code) | Derives test cases from a PBI spec for the active analysis mode (Normal/Deep); applies the framework, the 4-step edge methodology, and the template format |
| `drafter` | Reasoning + file I/O + Playwright MCP for screenshots | Turns approved sets into `.docx` deliverables (client UAT, end-user feature manual). Applies RTL/LTR by language. Never re-judges coverage |
| `senior-web-automation-eng` | Coding + Azure read | **Phase 2:** classifies web/CMS cases `Automation`/`Manual`. **Phase 3:** builds and runs the Playwright + pytest web framework |
| `senior-mobile-automation-eng` | Coding + Azure read | **Phase 2:** classifies app cases `Automation`/`Manual`. **Phase 3:** builds and runs the Appium + pytest mobile framework; uses the Appium MCP for locator extraction |
| `quality-control-engineer` | Reasoning + extraction only (no MCP) | **Phase 3b:** triages a failed `run-automation` pass's Allure results into a structured failure list (test name, TC ID, error, expected/actual, screenshot, run URL) and drafts the summary payload. Never files bugs itself |

---

## MCP servers (registered in `.mcp.json`)

| Server | Purpose | Status |
|---|---|---|
| `azure-devops` | Read PBIs, inject test cases, query coverage / outcomes, read suite cases for automation backlog | ✅ Active |
| `appium` | Mobile UI inspection + locator extraction (`appium-mcp@latest` via npx) | ✅ Active |
| `playwright` | Web UI inspection + screenshot capture for user manuals; web automation (`@playwright/mcp@latest` via npx) | ✅ Active — registered in `.mcp.json` |

---

## Context files (the engine's knowledge)

| File | Owns |
|---|---|
| `.claude/context/woqod-background.md` | Project / business facts: services, surfaces, roles. **May carry a local per-machine override** for a different project (marked with a `⚠️ LOCAL OVERRIDE` banner + `git skip-worktree`) — the filename is stable, the content is per-project |
| `.claude/context/woqod-standards.md` | QA standards: IDs, priorities, tag taxonomy (including Axis 1b — Automation/Manual), test-case authoring language policy (follows the PBI's language). Same local-override mechanism |
| `.claude/context/analysis-framework.md` | The 8 test categories + the 4-step edge methodology + Normal/Deep mode definitions |
| `.claude/context/test-case-template.md` | Field-level test case format + Azure mapping |
| `.claude/context/automation-standards.md` | Automation framework contract: structure, locator strategy, wrapper rules, Allure |
| `.claude/context/documents-assets/logo.png` | iHorizons logo asset for user manuals |

---

## Setup

### Prerequisites

- Python 3.11+ (3.14 in the working `.venv`)
- Node.js 18+ (22.x recommended) — required for the `appium` MCP via `npx`
- Appium 2+ with the `uiautomator2` driver installed (for Android automation)
- Android SDK + ADB on PATH (for Android device automation)
- **macOS host** with Xcode + `xcuitest` driver (for iOS automation only — not Windows-compatible)
- Azure DevOps PAT with read + work-item write permissions

### Install

```powershell
git clone <repo-url>
cd azure-mcp
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Configure

Create a `.env` file in the repo root (**never commit it** — `.gitignore` blocks it):

```
AZURE_PAT=<your personal access token>
AZURE_ORG_URL=https://dev.azure.com/<your-org>
AZURE_PROJECT=<your project name>
```

### Run

Cursor / Claude Code reads `.mcp.json` automatically. Open the repo in an
MCP-aware client and start a conversation:

> Analyze PBI 123456

The QA Manager will pick up `analyze-pbi` and run the full Phase-1 flow.

For a deep analysis: `Analyze PBI 123456 deep`.

---

## Repository layout

```
azure-mcp/
├─ server.py                      # MCP entry point (FastMCP)
├─ core/                          # MCP business logic
│  ├─ analysis.py                 # coverage review + QA dashboard (tag-taxonomy classifier)
│  ├─ discovery.py                # sprint PBI discovery (AC-optional validation gate)
│  ├─ engines.py                  # TC creation engines (multi-project: project from parent PBI)
│  ├─ output_manager.py
│  ├─ reporting.py
│  ├─ test_planner.py
│  └─ utils.py                    # shared: validators, classify_tc_from_tags, bilingual priority
│  ├─ bugs.py                     # Phase 3b: find/create/update bugs (dedup via TC:<id> tag)
├─ tests/                         # pytest suite (92 tests) — run: pytest tests/ -q
├─ scratch/                       # git-ignored: smoke_e2e.py + discovery source data
├─ deliverables/                  # git-ignored: generated client .docx files
├─ docs/                          # git-ignored: review/verification records
├─ requirements.txt
├─ .mcp.json                      # MCP registry (azure-devops + appium + playwright)
├─ CLAUDE.md                      # QA Manager prompt / orchestration rules
├─ PROJECT_SUMMARY.md             # Compact executive summary of the system
├─ README.md                      # This file
└─ .claude/
   ├─ agents/                     # Sub-agent definitions (5 agents)
   ├─ commands/                   # Slash commands (qa-mode, dev-mode)
   ├─ context/                    # Engine knowledge (5 files + documents-assets/)
   ├─ skills/                     # 15 skills, one folder each with SKILL.md
   └─ settings.json
```

The generated automation framework (`./automation/`) lives at the project root and
is **git-ignored** — it is not committed to this repo.

---

## Changelog — Bug Reporting on Failure (Phase 3b, merged July 2026)

Merged from the team's `logging-bugs-on-latest` branch (PRs #5/#6) and reconciled
with the hardening work below (dict contract, Phase-3 renumbering).

- **Phase 3b** — automatic tail of any `run-automation` pass with failures:
  `quality-control-engineer` (new sub-agent) triages Allure results into a
  structured failure list → `create-azure-bug` files or updates one Bug per
  failure. **No confirmation gate by design** — dedup, not a human, prevents
  duplicates (`find_existing_bug` on the `TC:<test_case_id>` tag; reopens
  `Resolved` bugs via `add_bug_occurrence`).
- **Bug hygiene rules:** titles stay plain English (from `actual_result`); the raw
  exception/stack trace is preserved verbatim under *"Automation Failure Root
  Cause"* in Repro Steps — never in the title. Fixed tags: `Automated`,
  `TC:<id>`, `PBI:<backlog_id>`, plus Service/Platform tags copied from the test
  case. Title carries the `[<PBI ID>]` prefix (query scoping key — never reword it).
- **`create-bug-queries`** (new skill) + `ensure_bug_query_hierarchy` (new MCP
  tool): idempotent per-PBI query-folder hierarchy so filed bugs surface in saved
  queries automatically; provisioned as `inject-test-cases`' final step, backfill
  on demand.
- **New module `core/bugs.py`** (find/create/update bugs) + 3 new test files.
  Suite total: **85 tests**.
- Merge reconciliation: query provisioning aligned with the dict return contract;
  CLAUDE.md Phase 3b renumbered to steps 14–17 after the Phase-3 renumbering.
- ⚠️ Known debt: `core/bugs.py` + `ensure_bug_query_hierarchy` still return JSON
  strings (pre-hardening contract) — functional, but should be unified to dicts.

---

## Changelog — July 2026 hardening (post-review fixes)

A full senior review of the engine surfaced and fixed three P1 bugs plus a set of
reliability gaps. All fixes are covered by the new pytest suite and were verified
end-to-end against live Azure DevOps (smoke E2E + a full production sprint run of
11 PBIs / 400+ injected cases on the Asiacell Headless Implementation sprint).

**P1 bug fixes**
- **Link-type mismatch (blindness bug):** injection links TC → PBI via
  `TestedBy-Reverse`, but `review_test_coverage` / `generate_qa_report` only read
  `Hierarchy` links — coverage review was blind to the MCP's own injected cases.
  Both now accept **TestedBy + Hierarchy** (deduped).
- **Analytics on the wrong tag model:** classification assumed legacy attribute tags
  (`positive`/`Functional`/…) that the unified tagging model no longer emits. New
  shared classifier (`classify_tc_from_tags`) understands the current taxonomy
  (Axis-4 Category + Axis-1b Automation/Manual), falls back to legacy tags, then
  title inference — and reports its source per case (`classification_source`).
- **Missing tags in coverage payload:** `review_test_coverage` now returns each
  case's `tags` (required by `route-automation` for Platform classification) plus
  `category_coverage` per Axis-4 category.

**Reliability & correctness**
- Multi-project support: TC creation derives the Azure **team project from the
  parent PBI** (`System.TeamProject`) — fixes TF401346 when the parent lives in a
  different project than `AZURE_PROJECT`.
- Sprint discovery validation relaxed by policy: **Description is the hard
  requirement; missing AC no longer skips a PBI** — it is flagged
  (`has_ac=false`, `no_ac_count`, mandatory-assumptions note) so analysis proceeds
  from the Description with explicit assumptions at the review gate.
- `execution_type` vocabulary normalized (`Automation` tag ⇄ `Automated` attribute)
  — no more injection rejects from the naming mismatch.
- TF401289 tag-permission fallback unified across both creation paths
  (`tags_applied` reported per case).
- Reporting: work-item batch fetch now **fails loudly** instead of silently
  undercounting; suite test-points **paginated** (no truncation at 2000); all
  reporting tools return dicts (one contract).
- `assess_priority` is bilingual — Arabic money/access keywords (دفع، شحن، رصيد،
  دخول…) now hit P1 like their English equivalents.
- `review_test_coverage`'s instructions are informational-only and **mode-aware** —
  the tool no longer prescribes creating cases for out-of-scope (Normal-mode) gaps.

**Test infrastructure (new)**
- `tests/` — 59 pytest tests: XML round-trip, validators, exec-type normalization,
  bilingual priority, tag classifier (current + legacy + inference), link-type
  regression tests, TF401289 fallback, discovery validation gate.
- `scratch/smoke_e2e.py` — live E2E harness: inject 2 tagged smoke cases →
  read-back through the full pipeline → cleanup.

**Config & docs**
- `playwright` MCP registered in `.mcp.json` (drafter screenshots + web automation).
- Machine-specific permissions moved out of shared `.claude/settings.json`.
- CLAUDE.md: Phase-3 steps renumbered (10–13), `build-chat-uat-doc` added to the
  skills router.
- Context files support a **local per-project override** (banner + `git
  skip-worktree`) so one shared repo serves multiple projects without collisions.
- Standards: test-case authoring language follows the PBI (EN PBI → EN cases, AR →
  AR); Kurdish is tested as a UI locale, never used as an authoring language.

---

## What the previous PR added (history)

This PR brings the Appium MCP integration and the Phase-3 orchestration layer that
makes the system runnable end-to-end on mobile. It also merges cleanly with the
previously-merged PR #4 (Analysis Modes + create-user-manual).

**New skills**
- `prep-automation-env` — verifies MCP, host (Node, Appium, drivers, ADB), and the
  `./automation/` framework are ready for the requested surface; auto-scaffolds when
  missing; iOS on non-macOS reported as ACTIONABLE.
- `route-automation` — Phase 2.5 hybrid router. Reads the injected batch from Azure,
  classifies by Platform tag, runs `prep-automation-env` per surface, waits for
  explicit approval, then delegates engineers. iOS skipped with an explicit
  "needs macOS" warning — never silently dropped.

**Orchestration changes**
- `CLAUDE.md` now formalizes the **Development Manager hat** — the orchestrator
  explicitly switches role at the Phase 2 → 3 boundary. Phase 3 numbered steps
  (9–12) added.
- `analyze-pbi` and `quick-test-cases` now include a **Surface Detection** step in
  Phase 1: the QA Manager scans Platform tags and surfaces the detected automation
  path in the sign-off, with a lookahead offer to prep the env in parallel.

**MCP**
- Registered the official `appium-mcp@latest` in `.mcp.json` alongside Azure DevOps.

**UAT / user manuals**
- `build-uat-doc` and `drafter` now carry explicit **RTL / LTR handling**: Arabic
  test cases produce a fully RTL document; English produces LTR; mixed sets are
  rejected with an explicit question — never half-Arabic / half-English.

**Quality / housekeeping**
- Removed the legacy `smoke` / `sanity` / `mobile` / `automated` pytest markers
  (aligned with `automation-standards.md`). Only `regression` + Platform markers
  (`web` / `ios` / `android` / `control_panel`) remain.
- Repaired null-byte file corruption in `senior-mobile-automation-eng.md` and
  `run-automation/SKILL.md`.
- Added missing `python-docx==1.2.0` to `requirements.txt`.
- Cleaned up project-specific scratch scripts; moved them to `scratch/` (git-ignored).
- Hardened `.gitignore` to block `.env.*`, `*credentials*`, `*secrets*`, `*.pat`,
  `*.token`, `*.pem`, `*.key`, and other credential file patterns recursively.
- Rewrote `README.md` and `CLAUDE.md` with the architecture diagram + Phase 3 steps.

---

## Already on main before this PR

Carried over from PR #4 (Analysis Modes + create-user-manual):

- **Two analysis modes** (Normal default / Deep) across the framework, the agents,
  and the analyze-pbi / quick-test-cases skills.
- **Automation / Manual tag taxonomy** (Axis 1b in `woqod-standards.md`) — every
  case gets exactly one, assigned by the Automation engineer in a pre-injection
  classification pass.
- `create-user-manual` skill — fixed iHorizons-branded user manual template,
  screenshot-gated (provided directly, via Playwright MCP for web, or via Appium MCP
  for app).
- Automation engineers can **read** injected suites from Azure via
  `get_test_cases_from_suite`; post-back to Azure is still **deferred**.

---

## License

Internal — iHorizons QA team (multi-project: WOQOD · Asiacell eCommerce · Awqaf Smart Khotba).

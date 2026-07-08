# Project Summary — QA-Final-V4

> A one-page brief on what this repo is, how it works, and what's in it. For depth,
> see `README.md` and `CLAUDE.md`.

---

## What it is

An MCP server that turns Claude / Claude Code into a single, opinionated **QA
Manager** for a sprint. The user points it at a PBI; the system handles analysis,
review, classification, injection into Azure DevOps, UAT documents, end-user
manuals, and — at the end of the loop — sets up and runs the automated tests on
the appropriate surface (web via Playwright, mobile via Appium).

---

## What problem it solves

QA work fragments across Azure, Word, Excel, and code. Missed edges, mismatched
tags, hand-rolled UAT, stale automation. This system collapses the whole pipeline
into one conversation with explicit gates, so nothing leaks between stages.

---

## How it's organized — three hard phases

```
Phase 1 (chat only)           Phase 2 (Azure + deliverables)        Phase 3 (./automation/)
─────────────────────         ────────────────────────────         ────────────────────────
analyze-pbi  (Normal/Deep)    Automation/Manual classify           prep-automation-env
quick-test-cases              inject-test-cases  →  Azure         route-automation
qa-engineer                   └─ create-bug-queries (auto)         automate-test-case
                              build-uat-doc (RTL/LTR)              run-automation
SIGN-OFF GATE                 build-chat-uat-doc                   senior-web-eng
                              create-user-manual                   senior-mobile-eng
                              generate-summary-report              SUITE + Allure report
                              drafter                                     │ failures?
                              SIGN-OFF GATE                               ▼
                                                          Phase 3b (auto — no gate)
                                                          ─────────────────────────
                                                          quality-control-engineer
                                                          create-azure-bug → Azure Bugs
                                                          generate-summary-report (HTML)

  QA Manager hat ─────────────────────────────────────►  hat switch  ►──── Dev Manager hat
```

**Rules of the gates:**
- Phase 1 never writes to Azure. The set lives in chat until the user signs off.
- Phase 2 never invents cases — it transports and decorates.
- Phase 3 never re-judges coverage — the Azure set is the contract.
- Phase 3b never fixes tests or filters failures — every failure gets logged
  (dedup, not a human, prevents duplicates). It is the **only ungated writer**.

---

## What's in the repo

| Component | Count | Where |
|---|---|---|
| Skills (procedures) | 15 | `.claude/skills/` |
| Sub-agents | 5 | `.claude/agents/` |
| Context files (knowledge) | 5 + assets — **per-project local override supported** | `.claude/context/` |
| MCP servers registered | 3 (azure-devops, appium, playwright) | `.mcp.json` |
| Slash commands | 2 (qa-mode, dev-mode) | `.claude/commands/` |
| Core Python modules | 8 (incl. `bugs.py` — Phase 3b) | `core/` |
| **Unit tests (pytest)** | **92** | `tests/` |
| Live E2E harness | 1 (`smoke_e2e.py` — inject → read-back → cleanup) | `scratch/` |
| Documentation | README, CLAUDE.md, this file | repo root |

---

## The 15 skills

**Phase 1 — Analysis & Generation**
1. `analyze-pbi` — full Phase-1 coverage in Normal (default) or Deep mode
2. `quick-test-cases` — tight prioritized subset

**Phase 2 — Classification, Injection & Deliverables**
3. `inject-test-cases` — push the approved, classified set to Azure (+ provisions the PBI's bug-query hierarchy as its final step)
4. `create-bug-queries` — idempotent per-PBI bug-query hierarchy (auto from inject; backfill on demand)
5. `build-uat-doc` — client UAT `.docx` from Azure suite (RTL for AR, LTR for EN)
6. `build-chat-uat-doc` — client UAT `.docx` from the chat set (no Azure read)
7. `create-user-manual` — end-user feature manual (iHorizons template, screenshot-gated)
8. `generate-summary-report` — HTML quality summary (also renders the Phase 3b payload)

**Phase 3 — Automation Layer**
9. `prep-automation-env` — verify MCP + host + framework readiness; auto-scaffold
10. `route-automation` — Phase 2.5 hybrid router; reads Azure, asks before delegating
11. `scaffold-automation-framework` — generate `./automation/` (web / mobile / both)
12. `extract-locators` — pull real locators from the live app
13. `automate-test-case` — translate one approved Automation case to pytest
14. `run-automation` — execute pytest suite + Allure report

**Phase 3b — Bug Reporting on Failure (auto, no gate)**
15. `create-azure-bug` — one Bug per failed automated test; dedup via `TC:<id>` tag
    (`find_existing_bug` → `create_bug` or `add_bug_occurrence`); plain-English titles,
    raw error preserved in Repro Steps

---

## The 5 sub-agents

| Agent | Layer | Writes code? |
|---|---|---|
| `qa-engineer` | Reasoning only | No |
| `drafter` | Reasoning + `.docx` build + Playwright screenshots | No (only documents) |
| `senior-web-automation-eng` | Reasoning + Playwright + pytest code + Azure read | **Yes** |
| `senior-mobile-automation-eng` | Reasoning + Appium + pytest code + Azure read | **Yes** |
| `quality-control-engineer` | Reasoning + Allure extraction only (no MCP, no bug-filing decisions) | No |

---

## Tag taxonomy at a glance

| Axis | Tag(s) | Decided by |
|---|---|---|
| 0 — Provenance | `Ai_MCP_Injected` | MCP (auto) |
| 1a — Lifecycle | `UAT`, `Regression` | QA Engineer |
| **1b — Execution method** | `Automation` / `Manual` (exactly one) | **Automation Engineer** (pre-injection) |
| 2 — Service | Per-project codes from the active standards file (WOQOD: `TAG`/`FAHES`/… · Asiacell: `CHECKOUT`/`SIM`/`PAYMENT`/…) | QA Engineer |
| 3 — Platform | `Web` / `IOS` / `Android` / `Control_Panel` | QA Engineer |
| 4 — Category | UI / Functional-High / Functional-Low / etc. | QA Engineer |
| 5 — Business | Optional keyword | QA Engineer |

**Relationship:** `Regression ⊆ Automation`. Regression is the critical re-run subset;
Automation is the broader automatable set. The automation build sources from
`Tag = Automation`.

---

## Analysis modes

| Mode | Scope | Default? |
|---|---|---|
| **Normal** | UI / Functional-High / Functional-Low + optional Compatibility / Auth + lighter Edge. No API, no Additional, no non-functional. | ✅ Yes |
| **Deep** | Full 8 categories + full 4-step edge methodology + non-functional where warranted | No (must be requested) |

User invokes: `Analyze PBI 12345` (Normal) or `Analyze PBI 12345 deep` (Deep).

---

## MCP servers

| Server | Used for | Status |
|---|---|---|
| `azure-devops` | Read PBI, inject cases, read suite for automation backlog | ✅ Active |
| `appium` | Mobile UI inspection, locator extraction, app screenshots | ✅ Active |
| `playwright` | Web UI inspection, screenshots for user manuals, web automation | ✅ Active — in `.mcp.json` |

---

## What's enabled vs deferred

| Capability | Status |
|---|---|
| Azure PBI read | ✅ |
| Azure case injection | ✅ (project derived from parent PBI — multi-project org supported) |
| Azure suite read (for automation backlog) | ✅ |
| Coverage review sees MCP-injected cases (TestedBy links) | ✅ Fixed July 2026 |
| Tag-taxonomy classification in analytics (`classification_source` per case) | ✅ Fixed July 2026 |
| Description-only PBIs (no AC) flow through flagged, with mandatory assumptions | ✅ Policy, July 2026 |
| Unit tests (92) + live smoke E2E harness | ✅ July 2026 |
| Plain-English bug titles enforced in code (title guard in `create_bug`) | ✅ July 2026 — team review feedback |
| **Automated bug filing on failed runs (Phase 3b)** | ✅ Merged July 2026 — dedup via `TC:<id>`, auto (no gate), per-PBI query hierarchy |
| **Azure test-result post-back from automation runs** | 🔜 Deferred — planned for the next PR |
| iOS automation on macOS host | ✅ (needs Xcode + xcuitest driver) |
| iOS automation on Windows / Linux host | ❌ Not possible — reported as ACTIONABLE |
| Android automation on Windows | ✅ |
| Web automation | ✅ |

---

## Setup quick reference

```powershell
git clone <repo-url>
cd azure-mcp
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
# Create .env with AZURE_PAT, AZURE_ORG_URL, AZURE_PROJECT
```

Open the repo in Cursor / Claude Code. The MCPs auto-load from `.mcp.json`.
Start with: `Analyze PBI <id>` for the default Normal mode, or add `deep` for Deep.

---

## Proven in production

July 2026: full sprint run on **Asiacell eCommerce Platform \ Headless Implementation**
— 11 PBIs analyzed (10 of them Description-only, no AC), classified, and injected
(~400 cases, e.g. Guest Checkout: 40/40, 30 Automation / 10 Manual, 0 rejected),
then verified back through `review_test_coverage` with 100% tag-sourced
classification.

---

*Last updated July 2026 — post-review hardening (P1 link-type fix, taxonomy
classifier, multi-project support, AC-optional discovery, pytest suite) + the
**Bug Reporting on Failure (Phase 3b)** merge (quality-control-engineer,
create-azure-bug, create-bug-queries, core/bugs.py — see `BUG_REPORTING_FEATURE.md`).
For the full architecture, see `README.md`. For the orchestrator's behavior rules,
see `CLAUDE.md`. Review & verification records: `docs/`.*

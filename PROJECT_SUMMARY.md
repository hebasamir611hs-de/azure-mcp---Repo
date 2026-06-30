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
qa-engineer                   build-uat-doc (RTL/LTR)              automate-test-case
                              build-chat-uat-doc                   run-automation
SIGN-OFF GATE                 create-user-manual                   senior-web-eng
                              generate-summary-report              senior-mobile-eng
                              drafter                              SUITE + Allure
                              SIGN-OFF GATE                        report
                                                                   
  QA Manager hat ─────────────────────────────────────►  hat switch  ►──── Dev Manager hat
```

**Rules of the gates:**
- Phase 1 never writes to Azure. The set lives in chat until the user signs off.
- Phase 2 never invents cases — it transports and decorates.
- Phase 3 never re-judges coverage — the Azure set is the contract.

---

## What's in the repo

| Component | Count | Where |
|---|---|---|
| Skills (procedures) | 13 | `.claude/skills/` |
| Sub-agents | 4 | `.claude/agents/` |
| Context files (knowledge) | 5 + assets | `.claude/context/` |
| MCP servers registered | 3 (azure-devops, appium, playwright) | `.mcp.json` + `.claude/settings.json` |
| Slash commands | 2 (qa-mode, dev-mode) | `.claude/commands/` |
| Core Python modules | 7 | `core/` |
| Documentation | README, CLAUDE.md, this file | repo root |

---

## The 13 skills

**Phase 1 — Analysis & Generation**
1. `analyze-pbi` — full Phase-1 coverage in Normal (default) or Deep mode
2. `quick-test-cases` — tight prioritized subset

**Phase 2 — Classification, Injection & Deliverables**
3. `inject-test-cases` — push the approved, classified set to Azure
4. `build-uat-doc` — client UAT `.docx` from Azure suite (RTL for AR, LTR for EN)
5. `build-chat-uat-doc` — client UAT `.docx` from the chat set (no Azure read)
6. `create-user-manual` — end-user feature manual (iHorizons template, screenshot-gated)
7. `generate-summary-report` — HTML quality summary

**Phase 3 — Automation Layer**
8. `prep-automation-env` — verify MCP + host + framework readiness; auto-scaffold
9. `route-automation` — Phase 2.5 hybrid router; reads Azure, asks before delegating
10. `scaffold-automation-framework` — generate `./automation/` (web / mobile / both)
11. `extract-locators` — pull real locators from the live app
12. `automate-test-case` — translate one approved Automation case to pytest
13. `run-automation` — execute pytest suite + Allure report

---

## The 4 sub-agents

| Agent | Layer | Writes code? |
|---|---|---|
| `qa-engineer` | Reasoning only | No |
| `drafter` | Reasoning + `.docx` build + Playwright screenshots | No (only documents) |
| `senior-web-automation-eng` | Reasoning + Playwright + pytest code + Azure read | **Yes** |
| `senior-mobile-automation-eng` | Reasoning + Appium + pytest code + Azure read | **Yes** |

---

## Tag taxonomy at a glance

| Axis | Tag(s) | Decided by |
|---|---|---|
| 0 — Provenance | `Ai_MCP_Injected` | MCP (auto) |
| 1a — Lifecycle | `UAT`, `Regression` | QA Engineer |
| **1b — Execution method** | `Automation` / `Manual` (exactly one) | **Automation Engineer** (pre-injection) |
| 2 — Service | `TAG` / `FAHES` / `BOOK` / `QJET` / `CMS` | QA Engineer |
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
| `playwright` | Web UI inspection, screenshots for user manuals, web automation | ✅ Allowlisted |

---

## What's enabled vs deferred

| Capability | Status |
|---|---|
| Azure PBI read | ✅ |
| Azure case injection | ✅ |
| Azure suite read (for automation backlog) | ✅ |
| **Azure result post-back from automation runs** | 🔜 Deferred — planned for the next PR |
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

*Last updated as part of the Appium MCP integration + orchestration PR. For the full
architecture, see `README.md`. For the orchestrator's behavior rules, see `CLAUDE.md`.*

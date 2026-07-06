# Project Review — Azure DevOps QA MCP (QA-Final-V4)
**Date:** 2026-07-06 · **Reviewer:** Senior QA Director review pass
**Scope:** `server.py`, `core/*` (2,800+ LOC), `.claude/` governance layer (agents, skills, context), config & repo hygiene.

---

## Verdict

Architecture is genuinely strong: clean separation (MCP = dumb transport, agents = reasoning, skills = procedures), phase gates, explicit tag taxonomy, good error handling, WIQL sanitization, secrets hygiene. **But the analytics layer (`core/analysis.py`) is out of sync with the tagging model you shipped, and there is one likely-critical link-type bug that can make `review_test_coverage` blind to the very test cases this MCP injects.** Fix P1s before the next sprint run.

Health score: **7/10** — governance 9/10, injection pipeline 8/10, analytics/reporting 4/10, test coverage of the tool itself 0/10.

---

## P1 — Likely Bugs (verify against live Azure data, then fix)

### 1. Link-type mismatch: injection writes `TestedBy`, coverage reads `Hierarchy`
- `engines.py` (both `_create_test_case` and `execute_qa_feedback`) links TC → PBI via `Microsoft.VSTS.Common.TestedBy-Reverse`. The parent ends up with **TestedBy-Forward** links.
- `analysis.py → review_test_coverage` collects children by `rel == "System.LinkTypes.Hierarchy-Forward"` — a **different link type**.
- `generate_qa_report` maps TCs to parents via `System.LinkTypes.Hierarchy-Reverse` — same mismatch.
- **Consequence:** coverage review and the per-PBI dashboard may report **0 test cases** for PBIs whose cases were injected by this very server. `route-automation` step 2 depends on `review_test_coverage` → Phase 3 routing breaks too.
- **Action:** run `review_test_coverage` on a PBI you know was injected. If it returns 0, change the filters to `Microsoft.VSTS.Common.TestedBy-Forward` / `-Reverse` (or accept both link types).

### 2. `review_test_coverage` doesn't return `tags` — but `route-automation` needs them
`tc_details` includes type/scenario/priority/steps but **no `tags` key**. `route-automation` step 3 classifies cases by Platform tag (`Web`/`IOS`/`Android`/`Control_Panel`) read "from Azure". With the current payload, the router has nothing to classify on. Add `"tags": [...]` to `tc_details`.

### 3. Analytics still assumes the OLD tag model
You moved to the unified model: attributes (`test_type`, `scenario`, `execution_type`, `impact_area`) are **no longer emitted as tags** (engines.py comment + woqod-standards Axis rules). But:
- `analysis.py` `has_meaningful_tags` looks for tags `UI / Functional / Edge / Intensive / positive / negative` — newly injected cases will **never** carry `positive`/`negative`, and carry `Functional-High`/`Functional-Low` (Axis 4), not `Functional`.
- Result: nearly every case falls back to `infer_tc_attributes_from_title()` **keyword guessing** → the 2×4 coverage matrix and the executive dashboard are heuristics presented as data.
- Collision bonus: Category tag `UI` gets double-counted as both test_type and impact_area; the condition `elif tag == "UI" and tag not in ["Functional", "Edge", "Intensive"]` is always true — dead logic.
- **Decide (design choice, see Ideas #1):** either persist attributes somewhere machine-readable, or rewrite the matrix around the real Axis-4 taxonomy.

---

## P2 — Inconsistencies & Design Debt

### 4. `review_test_coverage` fights your own governance
Its `review_instructions` tell the agent: coverage is complete only at 8/8 combos and "create additional test cases using execute_qa_feedback". That contradicts:
- **Normal mode** (API/Additional/non-functional are out of scope by design — not gaps).
- **CLAUDE.md rule** that MCP tools "do not drive or influence analysis" and that injection only happens after user approval.
An eager model following those instructions could auto-generate filler cases and inject them. Neuter the instruction text: report the matrix, recommend nothing.

### 5. `execution_type` attribute is validated but never persisted
`_create_test_case` validates it, auto-derives it, returns it — but it's **not in `patch_doc`**. Azure never stores it. The only real signal is the `Automation`/`Manual` tag. Either write it to a field (e.g. `Microsoft.VSTS.TCM.AutomationStatus` or a custom field) or drop the attribute and the `Automation→Automated` mapping friction entirely (see #6).

### 6. Naming friction: tag `Automation` vs attribute `Automated`
`VALID_EXEC_TYPES = ["Automated", "Manual"]` but the taxonomy tag is `Automation`. Every instruction file carries a "remember to map it" footnote. That's a standing invitation for validation rejects at injection time. One vocabulary, one place.

### 7. Tag-permission fallback is inconsistent
`_create_test_case` retries without tags on TF401289 (graceful, flags `tags_applied: false`). `execute_qa_feedback` — the **preferred** batch path — has no such retry: the case just lands in `errors_details`. Same failure, two behaviors. Extract the retry into a shared helper.

### 8. `assess_priority` is English-only in a bilingual project
Critical keywords (`payment`, `login`, …) never match Arabic PBIs (`دفع`, `تسجيل الدخول`, `شحن الرصيد`). Arabic money-flow cases with `priority=0` silently get P2/P3 instead of P1 — directly violating your own "money flows are P1" rule in woqod-standards. Add Arabic keywords or drop auto-assess for AR.

### 9. Silent data loss in reporting paths
- `reporting.py → _fetch_work_items`: non-200 batch responses are **silently skipped** → undercounted summaries with `status: success`.
- `get_test_outcome_summary`: `$top=2000`, no pagination → suites beyond 2000 points silently truncated (the run-level tool paginates correctly; the suite-level one doesn't).
- `generate_qa_report`: N+1 `get_work_item(pid)` calls per parent — slow on big sprints; batch them.

### 10. Return-type inconsistency across tools
`discovery/engines/analysis/test_planner` return **dicts**; `reporting.py` returns **`json.dumps(...)` strings**. FastMCP handles both, but consumers (and any future tests) deal with two contracts. Standardize on dicts.

### 11. Drafter depends on a Playwright MCP that isn't registered
`drafter.md` lists `mcp__playwright__*` tools and the screenshot-gate flow depends on them; `.mcp.json` has only `azure-devops` + `appium`. `prep-automation-env` even says "treat playwright as present, registration PR in flight". Until that lands, the user-manual and web-screenshot paths fail at runtime. Register it or gate the instructions.

---

## P3 — Hygiene

12. **`scratch/` bypasses governance.** `inject_all.py`, `inject_final.py`, `create_sprint8_tcs.py` are direct-injection scripts with zero review gate. They're gitignored, but they exist and they work. Delete or move to a `tools/` folder with an explicit "break-glass" README.
13. **`.claude/settings.json` (shared, committed) contains machine-specific junk:** stale temp-path Bash allows from the old `d:/Ai/AzureMCP` location, and `additionalDirectories` pointing at `D:\Ai\2_WoqodAutomatioTest`. Belongs in `settings.local.json`.
14. **Root clutter:** `UAT_Document_Asiacell_Headless.docx` at repo root (and Asiacell artifacts in scratch) — different client name inside the WOQOD repo. Move deliverables out.
15. **5 modified files uncommitted** (agents + commands). Commit or revert — the repo state doesn't match HEAD.
16. **CLAUDE.md step numbering:** Phase 2 ends at step 9 and Phase 3 starts at step 9. Cosmetic, but the phases quote step numbers at each other.
17. **`build-chat-uat-doc` skill exists on disk but isn't in the CLAUDE.md router table** (the table routes the chat path to "delegate to drafter directly"). Doc drift — pick one.
18. **`requirements.txt` claims Python 3.14** with `azure-devops==7.1.0b4` (beta) and `msrest` (deprecated/archived). Works today; note it as a known fragility, and pin the Python version in README explicitly.

---

## The Irony Finding

**This is a QA system with zero tests of itself.** No pytest suite for `core/`, no CI. Bugs #1–#3 are exactly the class a 30-minute unit-test pass (mock the Azure client, assert link types / tag parsing / matrix math) would have caught. `validate_tc_attributes`, `format_azure_steps`, `parse_steps_xml`, `_parse_iteration_path`, `sanitize_wiql_string` are pure functions — trivially testable. This is the highest-leverage improvement in the whole list.

---

## Ideas Worth Discussing

1. **Attribute persistence decision (feeds P1 #3).** Three options:
   a) re-emit two machine tags (`scenario:positive|negative` namespaced so they don't pollute Axis 4);
   b) write attributes to Azure custom fields;
   c) accept that the matrix is dead and rebuild analytics on the Axis-4 Category tags + priority. My lean: (c) — your taxonomy is already richer than the 2×4 matrix.
2. **`update_test_case` tool.** Today the pipeline is create-only. Any review-gate fix after injection = manual Azure edits or duplicate cases. An update/edit tool (title, steps, tags, priority) closes the loop.
3. **Idempotency / duplicate guard on injection.** Re-running `execute_qa_feedback` after a partial failure re-creates the already-created cases. Pre-check by title under the same parent (you already have `check_pbi_duplicates` for PBIs — mirror it for TCs).
4. **Dry-run mode for `inject-test-cases`.** Validate the full batch (titles, prefix, tag axes, exactly-one execution tag) and return a pass/fail report **before** any write. Cheap, kills the fix-and-retry churn in step 6 of the skill.
5. **AC→TC traceability tool.** Definition of Done requires "each acceptance criterion maps to ≥1 TC" but nothing measures it. A tool that parses AC bullets and asks the agent to map TC IDs per criterion would make the sign-off evidence-based.
6. **Genericize the context layer.** CLAUDE.md promises "swap two files to retarget", but filenames are `woqod-*.md` and referenced by that name in 10+ places. Rename to `project-background.md` / `project-standards.md` once, and retargeting truly becomes content-only.
7. **Structured logging.** `print` to stderr at startup only; injection batches have no audit trail beyond the chat. A one-line JSONL log per write (timestamp, tool, parent, TC id, tags) gives you provenance you can hand to an auditor — fits the `Ai_MCP_Injected` story.
8. **Rate-limit / 429 handling.** Batch injection of 50+ cases hits Azure throttling eventually; there's no retry-with-backoff anywhere. One decorator on the write path.
9. **Fuzzy duplicate detection.** `check_pbi_duplicates` is exact/substring only. Sprint-real duplicates are usually paraphrases. Token-set similarity (difflib is stdlib) would catch far more, still cheap.

---

## Suggested Order of Attack

| # | Action | Effort | Payoff |
|---|---|---|---|
| 1 | Verify + fix link-type mismatch (#1) | S | Unblocks coverage + Phase 3 routing |
| 2 | Add `tags` to `review_test_coverage` output (#2) | XS | Unblocks route-automation |
| 3 | Rebuild analytics on real taxonomy (#3, Idea 1c) | M | Dashboard becomes truthful |
| 4 | pytest suite for `core/` pure functions + mocked writes | M | Regression net for everything above |
| 5 | Neuter `review_instructions` (#4), unify exec-type vocab (#6), persist or drop `execution_type` (#5) | S | Governance consistency |
| 6 | Hygiene sweep (#12–#17) | S | Repo credibility |
| 7 | Dry-run + idempotent injection (Ideas 3–4) | M | Safe re-runs |

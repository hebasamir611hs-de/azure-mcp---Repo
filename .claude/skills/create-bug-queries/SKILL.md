---
name: create-bug-queries
description: Provision the Sprint/Feature bug-query hierarchy in Azure DevOps for a single backlog item (PBI) — Shared Queries/Bugs/Sprint bugs/<Sprint>/<Feature> (manual bugs) and <Feature> - Automation (automated bugs). Use once, right after a PBI's test cases have been written/injected into Azure DevOps — not per bug filed. Idempotent: safe to re-run on the same PBI, never overwrites an existing folder/query. Do NOT use to decide whether a bug is warranted, and do NOT invoke it from bug-filing (create-azure-bug) — that skill files bugs only; this one only sets up where they'll be found.
---

# Create Bug Queries — Provision the Sprint/Feature Query Hierarchy

Ensures a PBI has a home for its bugs in Azure DevOps's Shared Queries, so bugs
that get filed later (manually or via `create-azure-bug`) are already
discoverable the moment they land. This is **pure infrastructure setup** — it
creates saved queries, never bugs, and never judges anything.

> Contract: the hierarchy shape, WIQL scoping, and idempotency rule live in
> `ensure_bug_query_hierarchy`'s own docstring in `core/reporting.py`. Apply
> that, don't improvise it here.

**Argument:** the parent PBI (backlog item) work item ID → `$ARGUMENTS`.

## Procedure

1. **Confirm the parent PBI ID.** If not provided, ask for it.
2. **Call `mcp__azure-devops__ensure_bug_query_hierarchy(backlog_id)`.** That's
   the whole job — the tool fetches the PBI's own title and iteration path
   itself; nothing else needs to be looked up or passed in.
3. **Report back** — the `sprint_folder` path, and for each of the two
   queries (`<Feature>` and `<Feature> - Automation`) whether it was
   `created`, already `existing`, or `error`. If either errored, say so
   plainly — don't report success unless both queries are confirmed usable.

## When to run this

- **Primary trigger:** once per PBI, right after its test cases have been
  written into Azure DevOps (i.e. after `inject-test-cases` completes for
  that PBI) — regardless of whether injection went through
  `execute_qa_feedback` or the `create_english_test_case` /
  `create_arabic_test_case` fallback.
- **Also safe** to run standalone/repeatedly at any time — for backfill on a
  PBI that predates this skill, or as a repair pass. Re-running on an
  already-provisioned PBI is a no-op (both queries report `existing`).

## Hard boundary

- **Never triggered by bug filing.** `create-azure-bug` does not call this
  skill and does not know it exists — a bug being filed or updated is not
  this skill's concern. The bug still shows up in the right query on its own,
  because the query's WIQL matches on the backlog ID already embedded in the
  Bug's Title (`[<backlog_id>] ...`) — no write happens at bug-filing time.
- **Never overwrites.** If a query/folder with the target name already
  exists, it's left exactly as-is, even if you'd expect its WIQL to differ.
- **Does not create bugs, PBIs, or test cases.** Read-and-provision only.

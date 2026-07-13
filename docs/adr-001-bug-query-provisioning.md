# ADR-001 — Who provisions the bug-query hierarchy, and when

**Status:** Accepted · **Date:** 2026-07-08 · **Owner:** QA Lead
**Context:** Team review comments on the bug-reporting feature (PR #5/#6) raised the
same design question twice, with different answers: (a) "the QC engineer should create
the query ONCE, before and not related to any automation run", and (b — retracted)
"prefer NOT to invoke create-bug-queries inside inject-test-cases". Without a recorded
decision, this resurfaces every PR.

## Decision

**`inject-test-cases` provisions the bug-query hierarchy (via the `create-bug-queries`
skill → `ensure_bug_query_hierarchy`) as its final step — once per PBI, at injection
time. The `quality-control-engineer` agent never touches Azure DevOps.**
`create-bug-queries` remains directly invocable to backfill pre-existing PBIs.

## Rationale

1. **The requested timing is already satisfied.** Provisioning at injection IS "once,
   before, and unrelated to any automation run" — injection happens in Phase 2; runs
   happen in Phase 3. There is no run-coupling to remove.
2. **The QC engineer's no-MCP guardrail is a safety feature, not an omission.** The
   agent that triages failures must not hold write access — that separation is what
   keeps Phase 3b's "no confirmation gate" acceptable. Granting it MCP access to
   create queries would widen the only ungated write path in the system.
3. **Idempotency makes auto-provisioning harmless.** `ensure_bug_query_hierarchy`
   creates-if-missing and returns "existing" otherwise; a repeat call costs one read.
4. **One less human step.** A separate "now provision queries" order adds a manual
   checkpoint with no review value — nothing subjective is being decided.

## Alternatives rejected

- **QC engineer provisions the queries** — breaks the no-MCP guardrail (see #2).
- **Standalone-only provisioning (manual order)** — adds process overhead, and every
  forgotten invocation means filed bugs that no saved query surfaces.
- **Provision lazily on first bug filed** — couples provisioning to failures and
  re-introduces the race `90adb23` explicitly fixed.

## Consequences

- `inject-test-cases` documentation keeps the "final step" note; CLAUDE.md router
  table stays as merged.
- Backfill path stays documented for PBIs injected before this feature existed.
- Revisit only if the query hierarchy design itself changes (e.g. per-sprint instead
  of per-PBI folders).

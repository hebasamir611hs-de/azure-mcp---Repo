# ADR-002 — Where project knowledge lives: per-project context folders

**Status:** Accepted · **Date:** 2026-07-14 · **Owner:** QA Lead
**Supersedes:** the implicit single-project layout (`woqod-background.md` / `woqod-standards.md` as THE context)

## Context

The repo serves one QA engine but **many client projects across the whole team** —
each member runs 1–2 different projects, and new members are expected to join and
continue existing ones. Two approaches collided in recent merges, silently:

- **A. Fixed context files** (current): agents read `woqod-background.md` /
  `woqod-standards.md`. Deep, persistent, testable knowledge — but the single fixed
  filename caused real cross-project contamination (one member analyzed project X
  with project Y's business rules), and merge wars over the files' content.
- **B. "Ask the user per engagement"** (introduced in the automation-overhaul
  branch): no context files; the user describes the project each session. Fixes the
  contamination — but throws away accumulated knowledge, makes analysis depth depend
  on how much the user types that day, breaks sub-agent delegation (sub-agents start
  cold and read files, not chat history), and kills the 24 context-contract tests.

Both sides diagnosed the same real problem: **a multi-project team cannot share one
fixed context file.** They differ only on where knowledge should live.

## Decision (proposed)

**C. Per-project context folders + a local active-project switch.**

```
.claude/context/projects/
├── <project-a>/background.md + standards.md
├── <project-b>/background.md + standards.md
└── ...one folder per client project, committed and versioned

.claude/context/active/          ← git-ignored, per machine
├── background.md                ← copy of the chosen project's files
└── standards.md

tools/set-project.py <name>      ← copies projects/<name>/* into active/
```

All agents/skills reference the stable `active/` paths. Each member switches
projects with one command; nothing is retyped; nothing collides.

## Rationale

1. **Knowledge is an asset, not chat.** A project's standards (service codes,
   priority rubric, payment rules, platform matrix) are built once — often mined
   from hundreds of real PBIs — and reused by everyone, including sub-agents that
   start with empty context and can only read files.
2. **Consistency on Azure.** Tags, TC-ID prefixes, and queries are built from the
   standards file. "Describe the project each time" guarantees drift: two members
   (or the same member on two days) will invent different service codes for the
   same project, and every downstream query breaks.
3. **Onboarding.** A new member continuing an existing project reads the folder in
   an hour instead of reconstructing tribal knowledge.
4. **Testable.** The context-contract tests (24) keep guarding structure and
   engine-consistency of whatever project is active.
5. Both original concerns are satisfied: no shared mutable file (B's goal), no
   knowledge loss (A's goal).

## Prerequisite — repo visibility ⚠️

Project folders contain client business detail. The repo is currently **public**;
one project's context is already committed. Before (or with) this migration the repo
**must be made private** — this is independent of which option wins, and urgent.

## Alternatives rejected

- **A (status quo):** proven contamination + merge wars; the filename lies.
- **B (ask each time):** knowledge loss, sub-agent blindness, Azure naming drift,
  analysis quality tied to session effort, contract tests die.
- **B + "paste a context blob per session":** same as B with extra steps; the blob
  IS a context file, just unversioned and untested.

## Consequences / migration

1. Make repo private (prerequisite).
2. Create `projects/<name>/` per active client project; move existing content in.
3. Add `set-project` script + git-ignore `active/`; update all agent/skill
   references from `woqod-*.md` to `active/*.md` (one-time sweep, ~15 files).
4. Adapt the context-contract tests to validate `active/` (unchanged checks).
5. Each member runs `set-project <their-project>` once per machine/switch.
6. The previous per-machine `skip-worktree` workaround is retired.

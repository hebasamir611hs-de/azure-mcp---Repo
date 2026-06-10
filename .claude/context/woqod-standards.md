# WOQOD — QA Standards & Conventions

> Process-level rules for the WOQOD QA system. Keep test cases and deliverables
> consistent with these. Service and platform details come from
> `@.claude/context/woqod-background.md`.

## Service / Module Codes
Use in test case IDs and grouping:

| Code | Service |
|---|---|
| `TAG` | WOQOD Tag (top-up, fueling, payment) |
| `FAHES` | FAHES inspection & licensing |
| `BOOK` | Booking system (slots, vehicles, holidays) |
| `QJET` | Qjet content |
| `CMS` | CMS (content / settings / configuration / logs) |

## Platform / Surface Codes
| Code | Surface |
|---|---|
| `APP-iOS` | Mobile app — iOS |
| `APP-Android` | Mobile app — Android |
| `WOQOD-Web` | WOQOD website |
| `FAHES-Web` | FAHES website |
| `QJET-Web` | Qjet website |
| `CMS` | CMS admin backend |
| `All` | applies to all relevant surfaces |

## Test Case ID Convention
`<SERVICE>-<FEATURE>-TC-<NNN>` — numbers zero-padded and sequential within a feature.

Examples:
- `TAG-TOPUP-TC-001`
- `TAG-FUEL-TC-014`
- `FAHES-BOOKING-TC-007`
- `BOOK-SLOT-TC-022`
- `CMS-CONTENT-TC-003`

## Priority Rubric
- **P1 — Critical:** money or core access. Top-up, fueling payment, FAHES payment,
  login. Blocker if broken.
- **P2 — High:** major function — booking creation, tag pairing, CMS publish.
- **P3 — Medium:** secondary function, workaround exists.
- **P4 — Low:** cosmetic, rare, or minor.

## Tag Taxonomy

Every test case carries a **`Tags`** attribute — one or more keywords that describe
it at a glance. Tags are **queryable in Azure DevOps** (they land in `System.Tags`
via the MCP), so they are how we slice the suite later: build the automation set,
export the client doc, run a smoke pass, etc.

Tags are organized in axes. A typical case carries **one tag from several axes**
(at minimum a Service, a Platform, a Category, and any applicable Lifecycle tag).

### Axis 1 — Lifecycle / Suite *(the important ones)*
These mark **what the case is used for**. `UAT` and `Regression` are **separate but
overlapping** — a case can carry both.

| Tag | Meaning | Used for |
|---|---|---|
| `UAT` | Client-facing acceptance case — happy-path + key business scenarios in plain language. | **Client Word doc** (the Drafter filters `Tag = UAT`). |
| `Regression` | Part of the regression set — **the automation candidates**. | **The automation suite is built from `Tag = Regression`.** Re-run after every change. |
| `Smoke` | Minimal critical-path checks (e.g. login → top-up → fuel at gun). | Fast pre-release confidence pass. |
| `Sanity` | Narrow checks after a specific fix. | Post-fix verification. |

> **UAT vs Regression — the rule that matters:**
> - Tag a case `UAT` when it is something the **client** signs off on.
> - Tag a case `Regression` when it should be **re-run / automated** going forward.
> - Most core happy-path + critical negative cases are **both** — tag them with both.
> - The **automation backlog = every case tagged `Regression`.** That is the whole
>   point of the tag; never leave an automation-bound case untagged.

### Axis 2 — Service
One of: `TAG` · `FAHES` · `BOOK` · `QJET` · `CMS` *(see Service / Module Codes above)*.

### Axis 3 — Platform / Surface
One or more of: `APP-iOS` · `APP-Android` · `WOQOD-Web` · `FAHES-Web` · `QJET-Web` ·
`CMS` · `All` *(see Platform / Surface Codes above)*.

### Axis 4 — Category *(from the analysis framework)*
One of: `UI` · `Compatibility` · `Auth` · `Functional-High` · `Functional-Low` ·
`API` · `Edge` · `Additional`. Captures the framework category precisely (richer than
the auto `test_type` dimension tag).

### Axis 5 — Business keyword *(optional, but keep consistent)*
A single domain keyword when it helps later filtering, e.g. `Payment`, `Wallet`,
`QR-Scan`, `Biometric`, `TopUp`, `Booking`, `AuditLog`, `ErrorMessages`.

### Do not re-tag the auto dimensions
The MCP **automatically** applies these to `System.Tags` at injection — do **not**
repeat them in `Tags`: `Automated-By-AI`, `test_type`, `scenario`, `execution_type`,
`impact_area`, and language (`EN`/`AR`). Your `Tags` attribute is the **WOQOD layer
on top** of those.

## Money & Payment Rules (special attention)
WOQOD handles **real payments** — top-up, fueling at the pump, and FAHES payments.
For any money flow, always:
- Verify balance / amount math **exactly** (no rounding errors).
- Cover **failed and interrupted** payments and how the system reconciles.
- Cover **double-charge / duplicate-submit** prevention.
- Cover balance state at every transition (before, during, after, on failure).
- Treat any money flow as **P1**.

## Definition of Done (coverage)
A feature's analysis is complete only when ALL are addressed:
- Every analysis-framework category covered (or explicitly marked N/A with a reason).
- Happy + sad paths for each flow and each field.
- Edge cases derived via the mandatory 4-step methodology.
- Each acceptance criterion maps to ≥ 1 test case (traceability).
- Money/payment rules applied wherever value changes hands.
- Every test case carries a `Tags` value (≥1 tag — see Tag Taxonomy).
- `UAT` cases tagged for the client deliverable.
- `Regression` cases tagged for the automation suite — no automation-bound case left untagged.

## Writing Rules
- **Titles:** action + condition (e.g. "Top up WOQOD account with expired card").
- **Steps:** numbered, one action each, no ambiguity.
- **Expected results:** specific and verifiable — never "works correctly".
- **Test data:** concrete values, not "valid data" (e.g. `Top-up = 50 QAR`).

## Default Scope
- **Surfaces:** use the Service ↔ Platform matrix in `woqod-background.md`; default to
  all relevant surfaces for the service unless narrowed.
- **Languages:** Arabic (RTL) + English unless told otherwise.

## Do / Don't
- ✅ State assumptions when requirements are incomplete.
- ✅ Ask for acceptance criteria before deep analysis.
- ✅ Treat physical/hardware steps (tag at the gun) as real test steps with preconditions.
- ❌ Don't merge multiple verifications into one case.
- ❌ Don't include internal-only fields in client deliverables.

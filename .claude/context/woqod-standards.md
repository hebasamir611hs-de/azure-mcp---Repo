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
The Platform tag is **exactly one (or more) of these four values — no others**:

| Code | Surface |
|---|---|
| `IOS` | Mobile app — iOS |
| `Android` | Mobile app — Android |
| `Web` | Any website (WOQOD / FAHES / Qjet) |
| `Control_Panel` | CMS / admin backend |

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
via the MCP), so they are how we slice the suite later: build the automation set
(`Tag = Regression`), export the client doc (`Tag = UAT`), etc.

**The agent decides every tag.** Tag selection is pure QA judgement and lives here in
the standards — the agent applies it when it writes each case. The MCP does **no** tag
thinking: it injects the tags the agent decided, verbatim, and adds exactly one
provenance tag of its own (Axis 0). If the agent decides
`Functional-High; Regression; FAHES; Web`, those four land on Azure unchanged.

Tags are organized in axes. A typical case carries **one tag from several axes**
(at minimum a Service, a Platform, a Category, and any applicable Lifecycle tag).

### Axis 0 — Provenance *(MCP-applied — the ONLY automatic tag)*
| Tag | Applied by | Meaning |
|---|---|---|
| `Ai_MCP_Injected` | The MCP, automatically, on every injected case | Marks the case as created through the AI/MCP pipeline. The **agent never adds this**; the **MCP always does**. It is the single exception to "all tags come from the agent". |

This is the **only** tag the MCP contributes. Everything in Axes 1–5 below is the
agent's decision, passed through untouched.

### Axis 1 — Lifecycle / Suite *(the important ones)*
These mark **what the case is used for**.

| Tag | Meaning | Used for |
|---|---|---|
| `Regression` | A **MAIN / basic functional scenario** that should be **automated**. `Regression` **is** the automated set — there is **no separate `Automated` tag**. | The automation suite is built from `Tag = Regression`. Re-run after every change. |
| `UAT` | A **direct, primary** acceptance scenario in plain business language — what the **client** signs off on. | Client UAT document (the Drafter filters `Tag = UAT`). |

> **How to decide `Regression` — this is the rule that keeps the set sane:**
> - `Regression` = the case is a **MAIN functional scenario** of the feature: the
>   primary happy path and the critical, headline negative paths a real user hits.
> - **Be intelligent about it** — understand the feature, identify its handful of
>   *main* scenarios, and tag only those. A large feature must yield a **focused**
>   regression subset, **not** most of its cases.
> - **Do NOT tag deeper cases `Regression`:** exhaustive field validations, boundary
>   perturbations, rare edge combinations, and minor UI checks are **not** automation
>   candidates. They stay in the full set, simply without the `Regression` tag.
> - `Regression` already means "automated" — **never** add a separate `Automated` tag.
>
> **How to decide `UAT`:**
> - `UAT` = a **direct, primary** scenario the client validates — the main success
>   journeys and key business rules, in plain language. Keep it to what belongs in a
>   client sign-off document; **not** every case is a UAT case.
> - Main happy paths are often **both** `UAT` and `Regression`, but the two are decided
>   independently — neither implies the other.

### Axis 2 — Service
Per the **project's** service codes. For this project: `TAG` · `FAHES` · `BOOK` ·
`QJET` · `CMS` *(see Service / Module Codes above)*. For a different project, use that
project's service codes from its standards.

### Axis 3 — Platform / Surface
**Exactly one or more of these four** *(see Platform / Surface Codes above)* — no other
values: `IOS` · `Android` · `Web` · `Control_Panel`.

### Axis 4 — Category *(from the analysis framework)*
One of: `UI` · `Compatibility` · `Auth` · `Functional-High` · `Functional-Low` ·
`API` · `Edge`. Captures the framework category. *(The framework's "Additional /
Conditional" bucket is **not** a tag value — tag those cases with the concrete category
they most resemble: e.g. a concurrency case → `Edge`, an integration-failure flow →
`Functional-High`.)*

### Axis 5 — Business keyword *(optional, but keep consistent)*
A single project domain keyword when it helps later filtering, e.g. `Payment`, `Wallet`,
`QR-Scan`, `Biometric`, `TopUp`, `Booking`, `AuditLog`, `ErrorMessages`.

### Do not re-add the provenance tag
The MCP **automatically** applies `Ai_MCP_Injected` at injection — do **not** include it
in your `Tags`. Your `Tags` attribute is the full WOQOD-layer decision (Lifecycle +
Service + Platform + Category + optional Business); the MCP adds nothing else and
dedupes. There are **no** other auto-applied tags — `test_type`, `scenario`,
`execution_type`, `impact_area`, and language remain case attributes but are **not**
emitted as tags.

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
- `UAT` applied to the **direct, primary** acceptance scenarios for the client deliverable.
- `Regression` applied **only** to the feature's MAIN functional scenarios (the focused
  automation subset) — never to deep field-validation, boundary, or edge cases.

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

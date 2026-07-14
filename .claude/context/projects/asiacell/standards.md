# Asiacell eCommerce Platform — QA Standards & Conventions

> Process-level rules for the Asiacell QA system. Keep test cases and deliverables
> consistent with these. Service and platform details come from
> `@.claude/context/active/background.md`.

## Service / Module Codes
Use in test case IDs and grouping:

| Code | Service |
|---|---|
| `HOME` | Homepage (landing page, banners, quick-links, recommendations) |
| `CATALOG` | Product catalog (category pages, PLP, PDP, vendor widget, 3D images) |
| `CART` | Shopping cart & quick cart (add/remove, selective checkout, abandoned cart) |
| `CHECKOUT` | Checkout (personal details, delivery, payment, guest checkout, order placement) |
| `PAYMENT` | Payment methods (DCB, Asiapay, COD, online card) |
| `ORDER` | Order management (success page, history, tracking, delivery status, reports) |
| `AUTH` | Authentication & registration (email, mobile+OTP, social, SSO, forgot password) |
| `PROFILE` | User profile & my account (edit details, avatar, address book) |
| `SIM` | SIM purchase, number reservation, SIM swap, eSIM, eKYC |
| `VOUCH` | Digital vouchers & licenses (Karti Store, multi-vendor vouchers) |
| `PROMO` | Promotions (flash sale, coupons, countdown banners, price-drop alerts, pre-orders) |
| `SEARCH` | Search & filtering (product search, category filters, sort) |
| `PARTNER` | Partner integrations (Air & Travel, Kaspersky, Rehlat, iCenter) |
| `VENDOR` | Vendor portal (registration, login, product CRUD, orders, notifications) |
| `CMS` | Admin / CMS (content, settings, reporting, banner scheduling, SEO, B2B groups) |
| `SEO` | SEO & performance (meta tags, schema, URL structure, Core Web Vitals) |
| `NOTIFY` | Notifications (SMS, email, push, order alerts, stock alerts) |

## Platform / Surface Codes
The Platform tag is **exactly one (or more) of these four values — no others**:

| Code | Surface |
|---|---|
| `IOS` | Mobile webview — iOS (inside ODP app) |
| `Android` | Mobile webview — Android (inside ODP app) |
| `Web` | Web storefront (AsiaMall desktop + responsive mobile browser) |
| `Control_Panel` | Magento admin backend + vendor portal |

## Test Case ID Convention
`<SERVICE>-<FEATURE>-TC-<NNN>` — numbers zero-padded and sequential within a feature.

Examples:
- `CHECKOUT-GUEST-TC-001`
- `CHECKOUT-PAY-TC-003`
- `SIM-PURCHASE-TC-007`
- `SIM-SWAP-TC-012`
- `CATALOG-PDP-TC-005`
- `AUTH-LOGIN-TC-001`
- `VOUCH-KARTI-TC-002`
- `CMS-BANNER-TC-004`
- `VENDOR-PRODUCT-TC-008`

## Priority Rubric
- **P1 — Critical:** money or core access. Checkout payment (DCB/Asiapay/card/COD),
  login/registration, SIM purchase payment, order placement, number reservation lock.
  Blocker if broken.
- **P2 — High:** major function — SIM swap flow, guest checkout, cart operations,
  delivery method selection, product catalog browsing, vendor product approval.
- **P3 — Medium:** secondary function, workaround exists — profile edit, search/filter,
  flash-sale popup, coupon application, notification delivery, SEO metadata.
- **P4 — Low:** cosmetic, rare, or minor — avatar upload, countdown timer styling,
  3D image viewer, tooltip text.

## Tag Taxonomy

Every test case carries a **`Tags`** attribute — one or more keywords that describe
it at a glance. Tags are **queryable in Azure DevOps** (they land in `System.Tags`
via the MCP), so they are how we slice the suite later: build the automation set
(`Tag = Automation`), pick the regression re-run subset (`Tag = Regression`), export the
client doc (`Tag = UAT`), etc.

**The agent decides every tag.** Tag selection is pure QA judgement and lives here in
the standards — the agent applies it when it writes each case. The MCP does **no** tag
thinking: it injects the tags the agent decided, verbatim, and adds exactly one
provenance tag of its own (Axis 0). If the agent decides
`Functional-High; Regression; CHECKOUT; Web`, those four land on Azure unchanged.

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
| `Regression` | A **MAIN / basic functional scenario** — the feature's headline happy + critical-negative paths that must be **re-run after every change**. A focused subset, not most of the cases. | The regression **re-run** suite. Every `Regression` case is also `Automation` (it must be automatable), so it is part of the automation build; the `regression` marker selects it as the critical subset to run most often. |
| `UAT` | A **direct, primary** acceptance scenario in plain business language — what the **client** signs off on. | Client UAT document (the Drafter filters `Tag = UAT`). |

> **How to decide `Regression` — this is the rule that keeps the set sane:**
> - `Regression` = the case is a **MAIN functional scenario** of the feature: the
>   primary happy path and the critical, headline negative paths a real user hits.
> - **Be intelligent about it** — understand the feature, identify its handful of
>   *main* scenarios, and tag only those. A large feature must yield a **focused**
>   regression subset, **not** most of its cases.
> - **Do NOT tag deeper cases `Regression`:** exhaustive field validations, boundary
>   perturbations, rare edge combinations, and minor UI checks are **not** part of the
>   re-run suite. They stay in the full set, simply without the `Regression` tag.
> - `Regression` is a **suite** tag (what to re-run), **not** the execution-method tag.
>   Whether a case is automated is the separate **`Automation` / `Manual`** decision
>   (Axis 1b below) — every `Regression` case is `Automation`, never `Manual`.
>
> **How to decide `UAT`:**
> - `UAT` = a **direct, primary** scenario the client validates — the main success
>   journeys and key business rules, in plain language. Keep it to what belongs in a
>   client sign-off document; **not** every case is a UAT case.
> - Main happy paths are often **both** `UAT` and `Regression`, but the two are decided
>   independently — neither implies the other.

### Axis 1b — Execution Method *(`Automation` / `Manual` — mandatory, exactly one)*
Marks **how the case is executed**. **Every case carries exactly one** of these — never
both, never neither. Together they cover **100%** of the set.

| Tag | Meaning |
|---|---|
| `Automation` | The case **can be automated** and therefore **will be** — it joins the automation backlog. **Bias toward this:** anything technically automatable gets `Automation`, not just the `Regression` subset. |
| `Manual` | The case **cannot reasonably be automated** — physical/hardware steps (e.g. scanning a physical QR code at a kiosk), purely visual / look-and-feel checks, CAPTCHA, OTP/biometric by a human, device-permission dialogs, exploratory / usability judgement. |

> **Who & when — this axis is different from every other tag.** `Automation` / `Manual`
> is decided by the **Automation engineer** (`senior-web-automation-eng` or
> `senior-mobile-automation-eng`, by surface), **not** by the `qa-engineer`. It is
> assigned in a dedicated **classification pass that runs after Phase-1 sign-off and
> *before* injection**, so every case already carries it when it lands in Azure. The
> `qa-engineer` leaves this axis blank.
>
> **Relationship to `Regression`:** `Regression` ⊆ `Automation`. A `Regression` case is
> always `Automation` (never `Manual`). `Automation` is the **broader** set — the whole
> automation build sources from `Tag = Automation`; `Regression` is only the critical
> re-run subset within it.
>
> **Alignment with the `execution_type` attribute:** the tag is authoritative — set the
> case's `execution_type` to match (`Automation` → `Automated`, `Manual` → `Manual`).

### Axis 2 — Service
Per the **project's** service codes. For this project: `HOME` · `CATALOG` · `CART` ·
`CHECKOUT` · `PAYMENT` · `ORDER` · `AUTH` · `PROFILE` · `SIM` · `VOUCH` · `PROMO` ·
`SEARCH` · `PARTNER` · `VENDOR` · `CMS` · `SEO` · `NOTIFY`
*(see Service / Module Codes above)*. For a different project, use that project's
service codes from its standards.

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
A single project domain keyword when it helps later filtering, e.g. `GuestCheckout`,
`DCB`, `Asiapay`, `SIMSwap`, `eSIM`, `Voucher`, `FlashSale`, `Vendor`, `B2B`,
`eKYC`, `Delivery`, `Affiliate`, `Review`, `PreOrder`.

### Do not re-add the provenance tag
The MCP **automatically** applies `Ai_MCP_Injected` at injection — do **not** include it
in your `Tags`. Your `Tags` attribute is the full project-layer decision (Lifecycle +
Execution method + Service + Platform + Category + optional Business); the MCP adds
nothing else and dedupes. There are **no** auto-applied tags beyond `Ai_MCP_Injected` —
`test_type`, `scenario`, `execution_type`, `impact_area`, and language remain case
**attributes** and are **not** auto-emitted as tags. *(The `Automation` / `Manual` tag of
Axis 1b is **not** an auto-emission of the `execution_type` attribute — it is a deliberate
decision the Automation engineer adds; keep the two aligned.)*

## Money & Payment Rules (special attention)
Asiacell handles **real payments** — DCB (carrier billing), Asiapay wallet, online card
payments, and cash on delivery. For any money flow, always:
- Verify total/subtotal/delivery-fee math **exactly** (no rounding errors, correct
  currency display in IQD).
- Cover **failed and interrupted** payments and how the system reconciles (e.g. DCB
  timeout, Asiapay QR expiry, card decline).
- Cover **double-charge / duplicate-submit** prevention (especially on QR scan and
  DCB where network latency may cause retries).
- Cover balance/order state at every transition (before, during, after, on failure —
  e.g. number reservation lock must release on payment failure).
- Treat any money flow as **P1**.
- For guest checkout: verify payment works without account, and that order is
  trackable post-purchase.
- For selective checkout: verify payment total matches only selected items, not
  full cart.

## Definition of Done (coverage)
A feature's analysis is complete only when ALL are addressed **for the active analysis
mode** (Normal default / Deep — see `analysis-framework.md` → *Analysis Modes*):
- Every **in-scope** analysis-framework category covered (or explicitly marked N/A with a
  reason). *In Normal mode, API, the Additional/Conditional category, and all
  non-functional/security/performance cases are out of scope by design — not gaps.*
- Happy + sad paths for each in-scope flow and each field.
- Edge cases derived via the 4-step methodology (**full** in Deep mode; a **lighter**
  key-edge sweep in Normal mode).
- Each acceptance criterion maps to ≥ 1 test case (traceability).
- Money/payment rules applied wherever value changes hands.
- Every test case carries a `Tags` value (≥1 tag — see Tag Taxonomy).
- `UAT` applied to the **direct, primary** acceptance scenarios for the client deliverable.
- `Regression` applied **only** to the feature's MAIN functional scenarios (the focused
  re-run subset) — never to deep field-validation, boundary, or edge cases.
- **Every case classified `Automation` or `Manual`** (Axis 1b — exactly one, 100%
  coverage) by the Automation engineer in the **pre-injection** pass; no case left
  unclassified, none carrying both.

## Writing Rules
- **Titles:** action + condition (e.g. "Complete guest checkout with Asiapay QR payment").
- **Steps:** numbered, one action each, no ambiguity.
- **Expected results:** specific and verifiable — never "works correctly".
- **Test data:** concrete values, not "valid data" (e.g. `Total = 150,000 IQD`,
  `MSISDN = 07701234567`, `Coupon = FLASH20`).

## Default Scope
- **Surfaces:** use the Service ↔ Platform matrix in `active/background.md`; default to
  all relevant surfaces for the service unless narrowed.
- **Languages:** Arabic (RTL) + English unless told otherwise.
  <!-- TODO: confirm with QA Lead — is Kurdish a supported language? -->

## Do / Don't
- ✅ State assumptions when requirements are incomplete.
- ✅ Ask for acceptance criteria before deep analysis.
- ✅ Treat integration-dependent steps (DCB callback, eKYC verification, delivery
  partner API) as real test steps with preconditions and mock/stub notes.
- ✅ Verify number reservation lock/unlock timing in SIM flows.
- ❌ Don't merge multiple verifications into one case.
- ❌ Don't include internal-only fields in client deliverables.

# Test Analysis Framework

> The method for analyzing any feature. The QA Engineer applies this; the QA Manager
> reviews against it. Every test case uses the attributes in
> `@.claude/context/test-case-template.md` (including the `Tags` field — apply `UAT`
> to client-facing acceptance cases).

---

## Analysis Modes — Normal (default) vs Deep

Every analysis runs in **one of two modes**. The **user names the mode when submitting
the PBI / sprint**; **if they don't say, default to Normal.**

| Framework category | Normal (default) | Deep |
|---|---|---|
| 1. UI | ✅ **core focus** | ✅ |
| 2. Compatibility | ✅ may include | ✅ |
| 3. Auth | ✅ may include | ✅ |
| 4. Functional-High | ✅ **core focus** | ✅ |
| 5. Functional-Low | ✅ **core focus** | ✅ |
| 6. API | ❌ **excluded** | ✅ |
| 7. Edge | ✅ **lighter** — key edges, abbreviated sweep | ✅ **full** 4-step methodology |
| 8. Additional / Conditional | ❌ **excluded** | ✅ |
| Non-functional / security / performance | ❌ **excluded** | ✅ where warranted |

**Normal mode** is the default day-to-day analysis. It concentrates on **UI,
Functional-High, and Functional-Low** above all; it *may* include **Compatibility**,
**Auth**, and a **lighter** pass of **Edge** cases; and it **deliberately omits** the
**API** category, the **Additional / Conditional** category, and **all non-functional,
security, and performance** cases. In Normal mode those omissions are **expected** — they
are **not** coverage gaps and must **not** be flagged as missing at the review gate.

**Deep mode** is the **full framework** — all 8 categories below, the complete 4-step
edge methodology, plus non-functional / security / performance where the feature
warrants it. Use it for money flows, integrations, public APIs, security-sensitive
features, or any time the user explicitly asks for "deep" analysis.

> **Mode controls scope, not format.** Whichever mode is active, every produced case
> still uses the full template, the concrete-data rule, and the tag taxonomy. Mode
> changes *which categories* are produced — never *how* a produced case is written.

---

When given a feature, spec, or user story, cover the categories **in scope for the
active mode** (above) — **happy, sad, and beyond**. In Deep mode that is all 8; in
Normal mode it is the functional-focused subset. If an **in-scope** category genuinely
doesn't apply to the feature, say so and why.

## 1. UI Test Cases
Layout, alignment, responsiveness, labels, fonts, colors, spacing, RTL/Arabic
rendering, empty/loading/error states, accessibility basics, cross-screen
consistency, localization.

## 2. Compatibility Test Cases
Supported browsers, OS versions, devices, screen sizes/orientations; light/dark mode;
network conditions (3G/4G/wifi/offline); app upgrade/downgrade behavior.

## 3. Authentication & Authorization
Login/logout, registration, OTP/2FA, session timeout, token refresh, password rules
& reset, lockout after failed attempts, role-based access (each role sees only what
it should), forced-browsing / deep-link to protected resources, concurrent sessions.

## 4. Functional — High Level (End-to-End Flow)
- **Happy:** the intended successful journey, start to finish.
- **Sad:** the journey broken at each decision point (cancel, back, timeout, invalid
  input, insufficient balance, etc.).

## 5. Functional — Low Level (Element / Field)
Each field, button, toggle, control.
- **Happy:** valid values, correct enabling/disabling, correct messages.
- **Sad:** empty, max/min length, invalid format, special characters, boundaries,
  injection-like input.
- **More:** defaults, field dependencies, mandatory vs optional, validation order,
  persistence on navigation, copy/paste, autofill.

## 6. API Test Cases *(Deep mode only — skip in Normal)*
For raw APIs and functional scenarios driven through APIs.
- Each endpoint: valid request → correct response, schema, status code.
- Negative: missing/invalid params, wrong types, unauthorized/expired token, bad
  method, oversized payload.
- Status codes (200/201/400/401/403/404/409/422/429/500) and error message correctness.
- Functional-through-API: chain calls to reproduce a real user flow; assert state changes.
- Data integrity between API response and what the UI shows.
- Idempotency, pagination, rate limiting, response time.

## 7. Edge Cases — 4-Step Methodology
> **Mode note:** **Deep** mode runs the **full** 4-step methodology below — explicit and
> exhaustive. **Normal** mode runs a **lighter** pass: a quick objects → statuses →
> relations sweep to surface the *key* edges, without the full derivation matrix. Edge is
> in scope in both modes; only its depth differs.

Work through these **explicitly and in order** before listing edge cases (full depth in
Deep mode; an abbreviated sweep in Normal mode):

1. **Objects** — what objects are involved in this feature?
   *(e.g. Wallet, Card, Transaction, Order, Pump, Voucher.)*
2. **Statuses per object** — list every possible state.
   *(e.g. Wallet: Active, Suspended, Zero-balance, Over-limit. Transaction: Initiated,
   Pending, Success, Failed, Reversed, Timed-out.)*
3. **Relations through statuses** — how do objects interact *via* their statuses?
   *(e.g. "Initiate a Transaction on a Suspended Wallet", "Pay an Order with an Expired
   Card", "Success Transaction but Order still Pending".)*
4. **Full derivation** — from the object × status × relation matrix, derive:
   invalid combinations, interrupted transitions (timeout / crash / network drop /
   app kill), boundaries (zero, max, negative, expiry-now), stale/duplicate/concurrent
   actions, and recovery (retry / return later).

Produce edge cases as full test cases with all attributes.

## 8. Additional / Conditional *(Deep mode only — skip in Normal)*
Add categories when the feature warrants it:
- **Integration failures** — dependent service returns error / partial data.
- **API / backend down** — graceful degradation, retries, user-facing messaging,
  offline queueing.
- **Concurrency / race conditions** — two actions on the same object at once.
- **Data migration** — state carried from older app versions.
- **Performance / load** — for high-traffic flows.
- **Security beyond auth** — sensitive data exposure, secrets in logs.

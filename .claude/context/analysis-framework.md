# Test Analysis Framework

> The method for analyzing any feature. The QA Engineer applies this in full; the QA
> Manager reviews against it. Every test case uses the attributes in
> `@.claude/context/test-case-template.md` (including the `Tags` field — apply `UAT`
> to client-facing acceptance cases).

When given a feature, spec, or user story, cover **all** categories below — **happy,
sad, and beyond**. If a category genuinely doesn't apply, say so and why.

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

## 6. API Test Cases
For raw APIs and functional scenarios driven through APIs.
- Each endpoint: valid request → correct response, schema, status code.
- Negative: missing/invalid params, wrong types, unauthorized/expired token, bad
  method, oversized payload.
- Status codes (200/201/400/401/403/404/409/422/429/500) and error message correctness.
- Functional-through-API: chain calls to reproduce a real user flow; assert state changes.
- Data integrity between API response and what the UI shows.
- Idempotency, pagination, rate limiting, response time.

## 7. Edge Cases — Mandatory 4-Step Methodology
Work through these **explicitly and in order** before listing edge cases:

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

## 8. Additional / Conditional (decide per feature)
Add categories when the feature warrants it:
- **Integration failures** — dependent service returns error / partial data.
- **API / backend down** — graceful degradation, retries, user-facing messaging,
  offline queueing.
- **Concurrency / race conditions** — two actions on the same object at once.
- **Data migration** — state carried from older app versions.
- **Performance / load** — for high-traffic flows.
- **Security beyond auth** — sensitive data exposure, secrets in logs.

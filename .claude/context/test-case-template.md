# Test Case Template & Format

> This file serves two purposes:
> 1. **Generation reference** — the format the QA Engineer writes in chat (Phase 1).
> 2. **Injection mapping** — how each field maps to Azure DevOps when the Manager
>    pushes the approved set via MCP (Phase 2).
>
> These two phases are always separate. The QA Engineer generates; the MCP injects.
> The MCP does not generate, analyse, or decide.

---

## Required Fields — Every Test Case, No Exceptions

| Field | Description | Example |
|---|---|---|
| **ID** | `<SERVICE>-<FEATURE>-TC-NNN` — sequential per feature. Service/feature codes come from the project context — ask the user if not provided. | `SETTINGS-TIMEOUT-TC-001` |
| **Title** | Starts with `Verify that` (EN) or the configured RTL-language prefix (AR) — enforced by MCP on injection | `Verify that the Session Timeout field rejects a value of zero` |
| **Category** | One of the 8 framework categories | `Functional-Low` |
| **Description** | 1–2 sentences: test goal + preconditions + test data. | `User enters 0 in the Session Timeout field. Verifies a validation error is shown and the value is not saved.` |
| **steps_list** | Ordered list — one action per item | `["Navigate to Settings", "Enter 0 in Session Timeout", "Click Save"]` |
| **expected_list** | Same length as steps_list — one specific verifiable result per step | `["Section visible with current values", "Value 0 entered", "Validation error shown; value not saved"]` |
| **test_type** | MCP injection type — see mapping below | `Functional` |
| **scenario** | `positive` or `negative` | `negative` |
| **impact_area** | MCP injection area — see mapping below | `Backend` |
| **priority** | `1`–`4` or `0` for MCP auto-assess | `2` |
| **execution_type** | `Manual` / `Automated` (blank = MCP auto-determines) | `Automated` |
| **Tags** | ≥1 project-layer keyword. Combine axes: Service + Platform + Category + Lifecycle (`UAT` / `Regression` / `Smoke` / `Sanity`) + optional business keyword. Service/Platform/business tag values come from the project context — ask the user if not provided. **Maps to Azure `System.Tags` at injection — queryable.** | `["Functional-Low", "Regression"]` *(+ Service & Platform tags from the project tag taxonomy — ask if not provided)* |

---

## Category → `test_type` Mapping (for injection)

| Framework Category | Azure `test_type` |
|---|---|
| UI | `UI` |
| Compatibility | `UI` |
| Auth | `Functional` |
| Functional-High | `Functional` |
| Functional-Low | `Functional` |
| API | `Functional` |
| Edge | `Edge` |
| Performance / Load | `Intensive` |

> The mapping collapses 8 categories into 4 for Azure storage. This is **only a
> storage detail** — it does not reduce what the QA Engineer produces. Always
> generate cases for all 8 categories; the mapping is applied at injection time.

---

## Platform → `impact_area` Mapping (for injection)

| Platform | Azure `impact_area` |
|---|---|
| iOS, Android, Web (UI-facing only) | `UI` |
| CMS, API, backend-only | `Backend` |
| Both UI and backend touched | `Both` |

---

## Priority Mapping

| Our Label | Azure `priority` |
|---|---|
| P1 — Critical | `1` |
| P2 — High | `2` |
| P3 — Medium | `3` |
| P4 — Low | `4` |
| Unknown / auto | `0` |

Money flows are always P1.

---

## Priority Level Definitions

- **P1 — Critical:** money flow, login, payment, core access — blocker if broken.
- **P2 — High:** important feature function, major user impact.
- **P3 — Medium:** secondary function, workaround exists.
- **P4 — Low:** cosmetic, rare edge case, minor.

---

## Steps & Expected Results — Rules

Steps and expected results are **parallel lists of equal length**.
One expected result per step — the last step carries the primary assertion.

**Good:**
```
steps_list:    ["Navigate to Polling Intervals",
                "Enter 0 in Backend Poll Interval",
                "Click Save"]

expected_list: ["Section visible; current default value shown",
                "Value 0 entered in the field",
                "Validation error displayed; field value not saved; previous value restored"]
```

**Bad:**
```
steps_list:    ["Test polling validation"]
expected_list: ["Validation works correctly"]   ← rejected — too vague
```

---

## Description Field

Pack preconditions + test data into the `description` (1–2 sentences):

> *"Session Timeout is currently set to 30. Verifies that entering 0 is rejected with a validation error and the previous value is preserved."*

Do **not** put lifecycle markers in the description anymore — they live in the
`Tags` attribute (see below), which is queryable in Azure.

---

## Tags Attribute → Azure Mapping (Phase 2)

The `Tags` attribute is **authoritative and queryable**. At injection the MCP merges
it into Azure `System.Tags` alongside the auto dimension tags. This is how the
automation suite (`Tag = Regression`) and the client doc (`Tag = UAT`) are later built.

**How tags reach Azure:**

| Injection tool | How to pass tags |
|---|---|
| `execute_qa_feedback` (batch) | add a `tags` key to each feedback item: `"tags": ["<Service>", "UAT", "Regression"]` |
| `create_english_test_case` / `create_arabic_test_case` | pass the `extra_tags` argument: `extra_tags=["<Service>", "UAT", "Regression"]` |

**Rules:**
- Every case carries **≥1 tag**. In practice: Service + Platform + Category, plus any
  Lifecycle tag that applies.
- **`UAT`** → client-facing acceptance case (Drafter / client doc).
- **`Regression`** → automation candidate. The automation suite is `Tag = Regression`.
  Never leave an automation-bound case untagged.
- `UAT` and `Regression` are **separate but overlapping** — most core happy-path and
  critical-negative cases carry **both**.
- Do **not** repeat the auto dimension tags (`test_type`, `scenario`, `execution_type`,
  `impact_area`, `EN`/`AR`, `Automated-By-AI`) — the MCP adds those itself and dedupes.

> Service/Platform/business tag values come from the project context — ask the user
> if not provided.

---

## MCP Injection Tools (Phase 2 only)

| Situation | Tool |
|---|---|
| Batch injection of approved set | `mcp__azure-devops__execute_qa_feedback` (preferred) |
| Individual English TC | `mcp__azure-devops__create_english_test_case` |
| Individual Arabic TC | `mcp__azure-devops__create_arabic_test_case` |

`execute_qa_feedback` accepts the entire approved list in one call — use it for bulk
injection after the QA Manager signs off.

---

## Full Example — Chat Format (Phase 1)

| Field | Value |
|---|---|
| **ID** | `SETTINGS-TIMEOUT-TC-036` |
| **Title** | `Verify that the Session Timeout field rejects a value of zero` |
| **Category** | `Functional-Low` |
| **Description** | `Session Timeout is currently set to 30 minutes (default). Verifies that entering 0 is rejected with a validation error and the saved value is not changed.` |
| **steps_list** | `["Navigate to the Settings section", "Clear the Session Timeout field and enter 0", "Click Save"]` |
| **expected_list** | `["Section visible; Session Timeout shows current saved value", "Value 0 entered in field", "Validation error shown; save blocked; Session Timeout value unchanged"]` |
| **test_type** | `Functional` |
| **scenario** | `negative` |
| **impact_area** | `Backend` |
| **priority** | `2` |
| **execution_type** | `Automated` |
| **Tags** | `["Functional-Low", "Regression"]` *(+ Service & Platform tags from the project tag taxonomy — ask if not provided)* |

> This case is `Regression` (automation candidate) but not `UAT` — a field-level
> negative validation isn't a client sign-off scenario. A happy-path acceptance flow
> would carry **both** `UAT` and `Regression`.

---

## Azure DevOps Notes

- The **full test set** (all 8 categories, all polarities) lives in Azure DevOps linked under the PBI.
- The **client UAT document** is a filtered subset — `Tag = UAT` cases only — produced by the Drafter. It is a separate deliverable.
- The **automation suite** is the `Tag = Regression` subset.
- Azure tags on each injected case = the auto dimensions (`Automated-By-AI; test_type; scenario; execution_type; impact_area; EN`/`AR`) **plus** the project-layer `Tags` you supplied (Service, Platform, Category, Lifecycle, business keyword — from the project tag taxonomy; ask the user if not provided).

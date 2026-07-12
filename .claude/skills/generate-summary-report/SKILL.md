---
name: generate-summary-report
description: Generate a polished, self-contained HTML quality report from a JSON payload of QA metrics — bug/work-item summaries (tables + pie charts) and/or Azure test-suite outcome summaries (KPI pills + doughnut/bar charts) in the WOQOD blue/green theme. Use when the user asks to generate a quality report, summary report, bug summary, sprint/test-suite results report, or convert QA JSON into an HTML report. Read-only deliverable — it renders data that already exists and NEVER creates, injects, edits, or invents test cases or metrics in Azure DevOps.
---

# Skill: Quality Report HTML Generator

## Project Integration (WOQOD QA system)

How this skill fits the rest of the project — read before generating:

- **Role / phase.** A **read-only reporting deliverable**, a sibling of `build-uat-doc`.
  It runs *after* execution data exists. It performs **no injection** and never calls
  a write MCP tool.
- **Where the input JSON comes from.** In this project the payload is produced by the
  Azure DevOps MCP **read** tools — do not expect a hand-pasted file from elsewhere:
  - `test_suites` / `outcomes_summary` (Format T) ← `mcp__azure-devops__get_test_outcome_summary`,
    `mcp__azure-devops__get_test_run_outcome_summary`, or `mcp__azure-devops__generate_qa_report`.
  - `sections` / `summary` — bug & work-item counts (Format A/B) ←
    `mcp__azure-devops__get_query_summary` or `mcp__azure-devops__generate_qa_report`.
  - If a tool returns a different envelope, **map its fields onto Format A/B/T below
    before rendering** — confirm the exact shape against the live MCP output; do not
    assume keys that the tool did not return.
- **Hard boundary on data.** Render **only** numbers returned by those tools or supplied
  by the user. **Never fabricate, estimate, or "fill in" a metric.** If a required value
  is missing, say so rather than inventing it.
- **Terminology.** Service / suite / platform naming comes from the project context and
  the user-supplied payload — ask the user if a name is unclear; the WOQOD report theme
  is defined in this skill below — keep it.
- **Output.** Save the single `.html` file under a project reports location (e.g.
  `reports/`), and report the saved path back to the user.

## Purpose
Convert a JSON payload containing software quality metrics into a polished, self-contained HTML
report. The report may contain **two block types** that can appear together or independently:

| Block Type | Source key | Visual output |
|---|---|---|
| **Bug / Work-Item Summary** | `"sections"` or `"summary"` | Tables + pie charts per group |
| **Test Suite Summary** | `"test_suites"` | KPI pills + doughnut chart + optional bar chart |

All sections, group names, field labels, and counts are **fully dynamic** — nothing is hardcoded.

---

## Trigger Conditions
Use this skill when the user:
- Provides a JSON with grouped numeric quality metrics (bugs, work items, test outcomes)
- Asks to "generate a quality report", "make a bug report summary", "convert this JSON to HTML report",
  "show test suite results", or any similar request involving software QA data
- Wants output matching the WOQOD-style HTML report (blue header theme, tables + charts layout)

---

## Input Formats

### Top-level envelope (all optional except at least one data key):
```json
{
  "report_title": "WOQOD Quality Report",
  "total_label": "Total Work Items",
  "total": 390,
  "test_suites": [ ...see Format T... ],
  "sections":    [ ...see Format B... ],
  "summary":     { ...see Format A... }
}
```
`test_suites`, `sections`, and `summary` may all appear together in one JSON.

---

### Format A — Flat summary (one implicit section, multiple groups):
```json
{
  "summary": {
    "State":        { "Ready For UAT Deployment": 211, "Approved": 20, "New": 8 },
    "AssignedTo":   { "Mohammad Ouda": 147, "Muhammad Afham": 56 },
    "WorkItemType": { "Bug": 248, "Product Backlog Item": 14 }
  }
}
```

### Format B — Multi-section report (each section has sub-groups):
```json
{
  "sections": [
    {
      "title": "Test Execution Round Bugs",
      "total": 214,
      "url": "https://example.com/query1",
      "groups": {
        "By Severity": { "Critical": 41, "High": 61, "Medium": 104, "Low": 8 },
        "By State":    { "Closed": 181, "Postponed": 13, "Not A Bug": 4 }
      }
    },
    {
      "title": "Client Feedback",
      "total": 81,
      "url": "https://example.com/query2",
      "groups": {
        "By Severity": { "High": 30, "Medium": 40, "Low": 11 },
        "By State":    { "Closed": 75, "Not a Bug": 5, "Known Issue": 1 }
      }
    }
  ]
}
```

### Format T — Test Suite block (one entry per test suite):
```json
{
  "test_suites": [
    {
      "suite_title":      "QR Pay Wallet — Sprint 3",
      "test_suite_id":    125759,
      "test_plan_id":     125751,
      "total_test_cases": 95,
      "pass_rate":        "63.2%",
      "fail_rate":        "30.5%",
      "execution_rate":   "100.0%",
      "outcomes_summary": {
        "Passed": 60, "Failed": 29, "Not Applicable": 6,
        "Not Executed": 0, "Blocked": 0, "In Progress": 0,
        "Paused": 0, "Timeout": 0, "Warning": 0, "Aborted": 0
      }
    }
  ]
}
```

#### Format T — Field reference:
| Field | Required | Notes |
|---|---|---|
| `suite_title` | recommended | `<h2>` heading for this block. Defaults to `"Test Suite Summary"` |
| `test_suite_id` | optional | Shown as metadata below the heading |
| `test_plan_id` | optional | Shown as metadata below the heading |
| `total_test_cases` | required | Shown in heading and KPI area |
| `pass_rate` | required | Drives the green KPI pill |
| `fail_rate` | required | Drives the red KPI pill |
| `execution_rate` | required | Drives the blue KPI pill |
| `outcomes_summary` | required | `{ "Label": count }` — drives doughnut chart and table |
| `by_priority` | **optional** | `{ "Priority N": count }` — **only include when the user explicitly requests priority breakdown**. Omit by default. |
| `message` | optional | Ignored in rendering |
| `status` | optional | Ignored in rendering |

#### Bug / Work-Item Section — Default groups:
| Group | Required | Notes |
|---|---|---|
| `By Severity` | **mandatory** | Always include as a default group in every bug section |
| `By State` | **mandatory** | Always include as a default group in every bug section |
| Any other group | optional | Include only when the user explicitly requests it (e.g. AssignedTo, AreaPath) |

---

## Output Structure (full combined report)

```
┌──────────────────────────────────────────────────────────────┐
│  WOQOD Quality Report                               [h1]     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              Total Work Items: 390     ← blue box      │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ╔══════════════════════════════════════════════════════╗    │
│  ║  2.1 QR Pay Wallet Sprint 3: 95 test cases   [h2]   ║    │
│  ║  Suite ID: 125759  |  Plan ID: 125751  [meta]       ║    │
│  ║  ┌──────────────┬──────────────┬──────────────┐     ║    │
│  ║  │✔ Pass 63.2% │✘ Fail 30.5% │⚡ Exec 100%  │     ║    │
│  ║  └──────────────┴──────────────┴──────────────┘     ║    │
│  ║  Test Outcomes [h3]                                  ║    │
│  ║  ┌────────────┐  ┌────────────────────────────────┐  ║    │
│  ║  │  Table     │  │  Doughnut chart (non-zero only)│  ║    │
│  ║  └────────────┘  └────────────────────────────────┘  ║    │
│  ║  By Priority [h3]                                    ║    │
│  ║  ┌────────────┐  ┌────────────────────────────────┐  ║    │
│  ║  │  Table     │  │  Horizontal bar chart          │  ║    │
│  ║  └────────────┘  └────────────────────────────────┘  ║    │
│  ╚══════════════════════════════════════════════════════╝    │
│                                                              │
│  1.1 Test Execution Round Bugs: 214          [h2]            │
│  ┌──────────────┬────────────────────────────────────────┐   │
│  │ By State [h3]                                         │   │
│  │ ┌──────────┐  ┌──────────────────────────────────┐   │   │
│  │ │  Table   │  │  Pie chart                       │   │   │
│  │ └──────────┘  └──────────────────────────────────┘   │   │
│  └───────────────────────────────────────────────────────┘   │
│  ...                                                         │
└──────────────────────────────────────────────────────────────┘
```

---

## Styling Rules

### Shared styles (apply to whole document)
```css
body:   font 'Segoe UI'; padding 30px; background #f5f5f5; max-width 1400px; centered
h1:     color #2c3e50; border-bottom 3px solid #3498db; padding-bottom 10px
h2:     color #34495e; background #ecf0f1; padding 10px; border-left 4px solid #3498db
h3:     color #555; margin-top 20px
.total-box:            background #3498db; white text; 24px bold; border-radius 8px; padding 20px; centered
.section:              white bg; padding 20px; margin 20px 0; border-radius 8px; box-shadow
.table-chart-container: CSS grid; 2 columns 1fr 1fr; gap 30px; align-items start
table:  full width; border-collapse; white bg; box-shadow 0 2px 4px
th:     background #3498db; white; padding 12px; font-weight 600; text-align left
td:     padding 10px 12px; border-bottom 1px solid #ddd
tr:hover: background #f8f9fa
.chart-container: white bg; padding 20px; border-radius 8px; height 300px; flex center
canvas: max-height 280px
```

### Test Suite block extra styles
```css
/* Green accent for test suite sections */
.section-ts h2 {
  border-left-color: #27ae60;
}
.section-ts h2 .ts-total {
  color: #27ae60;
  font-weight: 700;
}

/* Meta line (Suite ID / Plan ID) */
.ts-meta {
  color: #7f8c8d;
  font-size: 13px;
  margin: -4px 0 12px 0;
}

/* KPI pills row */
.kpi-row {
  display: flex;
  gap: 16px;
  margin: 16px 0 20px 0;
  flex-wrap: wrap;
}
.kpi-pill {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 14px 24px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  color: white;
  min-width: 130px;
  gap: 4px;
}
.kpi-pill span { font-size: 26px; font-weight: 700; }
.kpi-pass { background: #27ae60; }
.kpi-fail { background: #e74c3c; }
.kpi-exec { background: #2980b9; }

/* Dim zero-value outcome rows */
tr.outcome-zero td {
  color: #bdc3c7;
  font-style: italic;
}

/* Shorter bar chart container */
.chart-bar { height: 220px; }
```

---

## Chart Specifications

### Pie chart (bug/work-item groups)
```js
{
  type: 'pie',
  data: { labels: [...], datasets: [{ data: [...], backgroundColor: palette }] },
  options: {
    responsive: true, maintainAspectRatio: true,
    plugins: {
      legend: {
        position: 'right',
        labels: {
          font: { size: 11 },
          generateLabels: chart => chart.data.labels.map((label, i) => ({
            text: `${label}: ${chart.data.datasets[0].data[i]}`,
            fillStyle: chart.data.datasets[0].backgroundColor[i],
            hidden: false, index: i
          }))
        }
      },
      tooltip: { callbacks: { label: ctx => ctx.label + ': ' + ctx.parsed } }
    }
  }
}
```

### Doughnut chart (test outcomes — use for `outcomes_summary`)
- Same config as pie **but** `type: 'doughnut'` and `cutout: '55%'`
- **Only include labels/data for outcomes where count > 0** (skip zero-value entries in the chart;
  they still appear greyed-out in the table)

### Horizontal bar chart (test by priority — use for `by_priority`)
```js
{
  type: 'bar',
  data: { labels: [...], datasets: [{ data: [...], backgroundColor: colors, borderRadius: 4 }] },
  options: {
    responsive: true, maintainAspectRatio: false, indexAxis: 'y',
    plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => ctx.parsed.x } } },
    scales: {
      x: { beginAtZero: true, ticks: { precision: 0 } },
      y: { ticks: { font: { size: 11 } } }
    }
  }
}
```
Container must use class `chart-container chart-bar` (220px height instead of 300px).

### Color Palettes
```js
const COLORS_PRIMARY  = ['#3498db','#2ecc71','#f39c12','#e74c3c','#9b59b6',
                         '#1abc9c','#34495e','#16a085','#e67e22','#27ae60'];
const COLORS_SEVERITY = ['#e74c3c','#f39c12','#3498db','#95a5a6'];
const COLORS_OUTCOMES = {
  'Passed':        '#2ecc71',
  'Failed':        '#e74c3c',
  'Not Executed':  '#95a5a6',
  'Not Applicable':'#bdc3c7',
  'Blocked':       '#e67e22',
  'In Progress':   '#3498db',
  'Paused':        '#9b59b6',
  'Timeout':       '#f39c12',
  'Warning':       '#f1c40f',
  'Aborted':       '#7f8c8d',
};
```

**Palette selection rules:**
- Group key contains `"severity"` (case-insensitive) → `COLORS_SEVERITY`
- `outcomes_summary` data → `COLORS_OUTCOMES` (map each label to its fixed color; fallback `#95a5a6`)
- All other groups and `by_priority` → `COLORS_PRIMARY` (cycle if more items than colors)

---

## Generation Rules

### Ordering of blocks in the output
1. Test suite blocks appear **first** (numbered `2.x` if bug sections also exist, `1.x` if alone)
2. Bug/work-item sections appear **after** test suites (numbered `1.x`)
3. If there are no bug sections, number test suites `1.x`

### Grand Total calculation
- If `total` provided in JSON → use it
- Otherwise: sum of all `total_test_cases` across test suites + sum of all values across all bug groups
- If test_suites only (no bug sections): total = sum of `total_test_cases`
- If bug sections only: total = sum of all group values

### Section-level total calculation (bug sections)
- If `total` provided on section → use it
- Otherwise: sum all values in that section's groups

### Test Suite heading format
```html
<h2>N.M  {suite_title}: <span class="ts-total">{total_test_cases}</span> test cases</h2>
```
Followed by meta line if `test_suite_id` or `test_plan_id` present:
```html
<p class="ts-meta">Suite ID: <strong>125759</strong> &nbsp;|&nbsp; Plan ID: <strong>125751</strong></p>
```

### KPI pills (always show all three for test suites):
```html
<div class="kpi-row">
  <div class="kpi-pill kpi-pass">✔ Pass Rate<span>{pass_rate}</span></div>
  <div class="kpi-pill kpi-fail">✘ Fail Rate<span>{fail_rate}</span></div>
  <div class="kpi-pill kpi-exec">⚡ Execution Rate<span>{exec_rate}</span></div>
</div>
```

### URL handling (bug sections)
- If a `url` field exists on a section → wrap the `<h2>` count in `<a href="..." target="_blank">`
- Also wrap each `<td>` category name in the same link
- No URL → plain text only, no broken `href="#"` placeholders

### Canvas ID uniqueness
- Use a global counter: `chart_1`, `chart_2`, ... across the entire document
- Every `<canvas id="chart_N">` must have exactly one matching `new Chart(...)` call in the `<script>` block
- Never duplicate a canvas ID

### Zero-value rows in outcomes table
- Include them in the `<table>` with class `outcome-zero` (renders greyed/italic)
- Exclude them from the doughnut chart data

### Output file
- Single self-contained `.html` file
- All CSS in `<style>` block in `<head>`
- Chart.js from CDN: `https://cdn.jsdelivr.net/npm/chart.js`
- All `new Chart(...)` calls in one `<script>` block at end of `<body>`

---

## Step-by-Step Agent Instructions

1. **Parse** the input JSON. Identify which top-level keys are present:
   - `test_suites` → Format T blocks
   - `sections` → Format B blocks
   - `summary` → Format A block (wrap as one implicit section)

2. **Decide ordering and numbering** (see Ordering rules above)

3. **Compute grand total** for the `.total-box`

4. **For each test suite (Format T)**:
   a. Render `<div class="section section-ts">`
   b. Write `<h2>` with `.ts-total` span
   c. Write `.ts-meta` if IDs present
   d. Write `.kpi-row` with three pills
   e. Write "Test Outcomes" `<h3>` + table (all rows, zero ones get `outcome-zero` class) + doughnut `<canvas>`
   f. **Only if `by_priority` is present** in the JSON (i.e. the user explicitly requested it): write "By Priority" `<h3>` + table + horizontal bar `<canvas>` (use `chart-bar` class). Skip this sub-section entirely by default.
   g. Record canvas IDs and their data for the JS block

5. **For each bug/work-item section (Format B or A)**:
   a. Render `<div class="section">`
   b. Write `<h2>` with optional linked total
   c. For each group: write `<h3>` + `.table-chart-container` (table + pie canvas)
      - **By Severity** and **By State** are mandatory defaults and must always be present
      - Any additional groups (AssignedTo, AreaPath, etc.) are rendered only when explicitly provided
   d. Record canvas IDs and data for the JS block

6. **Build `<script>` block**:
   - Define `COLORS_PRIMARY`, `COLORS_SEVERITY`, `COLORS_OUTCOMES`
   - Emit one `new Chart(...)` per canvas in document order
   - Use correct chart type per canvas (pie / doughnut / bar)

7. **Validate before output**:
   - Canvas count == Chart constructor count
   - No duplicate canvas IDs
   - Total in `.total-box` matches computed/provided value
   - All zero-value outcomes are absent from doughnut data arrays

8. **Output** complete HTML as a single file

---

## Example Invocation

**User says:**
> Here's my JSON with test results and bug summary, generate the HTML quality report

**Agent does:**
1. Detects `test_suites` + `sections` keys
2. Builds test suite block (green accent, KPI pills, doughnut + bar charts)
3. Builds bug section blocks (blue accent, pie charts per group)
4. Assembles single HTML file and outputs/saves it

---

## Quick Reference — Block Differences

| Feature | Bug/Work-Item Section | Test Suite Section |
|---|---|---|
| CSS class | `.section` | `.section.section-ts` |
| Accent color | `#3498db` (blue) | `#27ae60` (green) |
| h2 total | plain count or linked | `.ts-total` span (green) |
| KPI pills | none | pass / fail / exec (3 pills) |
| Chart type | pie | doughnut (outcomes) + horizontal bar (priority) |
| Zero values | all shown | shown in table (greyed), hidden from chart |
| URL links | yes (optional) | no |

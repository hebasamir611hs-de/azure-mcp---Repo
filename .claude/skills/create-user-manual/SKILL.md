---
name: create-user-manual
description: Build the end-user FEATURE USER MANUAL (.docx) — a fixed-structure, repeatable iHorizons-branded document with a cover page, clickable index, branded header/footer, and orange/blue accents. The Drafter owns it. HARD precondition — it never produces the manual without screenshots, sourced one of three ways: provided directly by the user, captured from a web link via the playwright MCP, or captured from an app APK via the Appium MCP. Use when the user asks for a user manual, end-user guide, or how-to document for a feature. NOT for the client UAT doc (use build-uat-doc) or test cases (use analyze-pbi).
---

# Create User Manual — End-User Feature Guide (.docx)

Produce the **end-user feature manual** as a polished `.docx`, built to a **fixed
template** so every manual comes out identical in structure and branding. The
**`drafter`** subagent owns the work; this skill is its procedure.

**Argument:** the feature/PBI to document + (optionally) the screenshot source →
`$ARGUMENTS`.

> Audience = **end users, not testers**. Plain, friendly, step-by-step. This is a
> different deliverable from the client UAT doc (`build-uat-doc`).

---

## HARD GATE — no screenshots, no manual

**Do not generate the document until screenshots are in hand.** A user manual without
screenshots is not acceptable. Resolve the screenshot source **first**, via one of the
three paths below, then build. If none is available, stop and ask the user which path to use.

### Screenshot sourcing — three paths

| The user… | The Drafter… | Status |
|---|---|---|
| **provides screenshots directly** (files/folder) | reads the image files and places them per section | ✅ works now |
| **provides a web link** | uses the **playwright MCP** (`browser_navigate` → `browser_take_screenshot`, driving the UI to each state) to capture them | ✅ works now (playwright MCP connected) |
| **provides an app APK** | uses the **Appium MCP** tools to launch the app and capture each screen | 🔜 placeholder — the Appium MCP will be added later; when connected, use its screenshot tools the same way |

Capture rules when the Drafter screenshots itself:
- One clear screenshot **per meaningful step / screen state** the manual references.
- Mask or avoid real secrets (OTP, card numbers, tokens) in captured shots.
- Web: set a consistent viewport (`browser_resize`, e.g. 1366×768) so shots are uniform.
- Name shots by the step they illustrate; store under the scratchpad, not the repo.

---

## Fixed Document Template — same every time

Generate the `.docx` (python-docx via Bash) with **exactly** these parts, in this order.

> **Fixed branding constants** (do not ask the user for these — they are pinned):
> - **iHorizons logo:** `@.claude/context/documents-assets/logo.png`
> - **iHorizons title:** `iHorizons Media & Information Services W.L.L.`
> - **iHorizons address:** `Zone 69, Street No. 318, Building No. 23, Manarat Lusail,
>   9th floor, Office No. 904, Doha, Qatar`
> - **Project name:** **variable** — read it from the project context
>   (`@.claude/context/woqod-background.md` → currently **WOQOD**). Never hard-code it.
> - **Brand colors:** orange `#FFAB00` · blue `#01529B` (RGB 1/82/155).

### Front matter
1. **Cover page (page 1)** — centered:
   - **Project name** *(variable — from context, e.g. WOQOD)*
   - **iHorizons logo** *(the fixed `logo.png` above)*
   - **iHorizons title** *(the fixed title above)*
   - **iHorizons address** *(the fixed address above)*
   - Document title: `User Manual — <Feature>`, version, date.
   - The cover has **no header/footer** (different-first-page).
2. **Document Control (page 2)** — version-history table: *Version · Date · Summary of changes*.
3. **Clickable Index / Table of Contents (page 3)** — list **every section and
   subsection**; each entry is a **clickable link that jumps straight to that heading**,
   working **the moment the file is opened**.
   - **Do NOT rely on a bare Word `TOC` field** — a raw TOC field renders **empty until the
     user presses Ctrl+A → F9**, which looks like "no index". That is the bug to avoid.
   - **Authoritative mechanism — bookmarks + internal hyperlinks (must work):** place a
     **bookmark at every section/subsection heading** (e.g. `_sec_1`, `_sec_1_1`, …) via the
     underlying XML (`w:bookmarkStart`/`w:bookmarkEnd`), and make each index entry an
     **internal hyperlink** (`<w:hyperlink w:anchor="_sec_1_1">`) pointing to that bookmark.
     Clicking navigates immediately — no field update required.
   - Style the index entries like links (blue, indent subsections under their section).
   - *(Optional extra)* you may also add a native `TOC` field and set
     `<w:updateFields w:val="true"/>` in `settings.xml` so Word offers to populate it — but
     the bookmark+hyperlink index is the one that **must** work on open.

### Body sections (you complete these to a standard feature-manual shape)
4. **1. Introduction** — 1.1 Purpose · 1.2 Intended Audience · 1.3 Scope · 1.4 How to Use This Manual.
5. **2. Getting Started** — 2.1 Prerequisites · 2.2 Supported Platforms / Requirements · 2.3 Accessing the Feature (per platform).
6. **3. Feature Overview** — 3.1 What It Does · 3.2 Key Concepts / Terminology.
7. **4. Step-by-Step Guide** — one subsection per task/flow (4.1, 4.2, …); each = numbered
   steps with **a screenshot per meaningful step** and a one-line caption.
8. **5. Tips & Best Practices.**
9. **6. Troubleshooting & FAQ** — common-issues table + Q&A.
10. **7. Glossary.**
11. **8. Support & Contact** — iHorizons support details.

### Styling (consistent every build)
- **Header** (from page 2 on): feature name + "User Manual" on the left, small iHorizons
  logo on the right.
- **Footer**: page number centered; version on the right; confidentiality/copyright line on the left.
- **Color tone — orange `#FFAB00` / blue `#01529B`:** thin accent rules (heading
  underlines, header/footer divider lines) use these exact hex values. Suggested split —
  blue `#01529B` for heading underlines and the header rule, orange `#FFAB00` for the
  footer rule and minor accents. Keep body text black for readability; color is for
  **lines and heading accents only**, not paragraphs.
- One consistent font family and heading scale throughout; Heading 1/2/3 styles drive the TOC.

---

## Procedure

1. **Confirm scope** — the feature to document and its version. Branding (logo, title,
   address) is **fixed** (the constants above); the **project name** comes from context.
   Don't ask the user for branding — only confirm the feature, version, and screenshots.
2. **Resolve screenshots (the gate)** — pick the source path above; if the Drafter must
   capture them, do that now (playwright for web, Appium for app once connected).
   **Do not proceed without the screenshots.**
3. **Delegate to the `drafter`** — hand it the feature scope, the branding assets, and the
   screenshot set (or the source to capture from). The Drafter builds the `.docx` to the
   fixed template above — it formats and assembles; it does **not** invent feature behavior
   it can't see in the screenshots/spec.
4. **Build the `.docx`** — python-docx via Bash: cover page, document control, clickable
   TOC field, the eight body sections, branded header/footer, orange/blue accent rules,
   screenshots placed with captions.
5. **Report back** — the saved `.docx` path, sections produced, screenshot count and their
   source, and anything still needed (e.g. a missing logo, or steps with no screenshot).

---

Never invent screenshots or describe screens you could not see — if the screenshot source
is unavailable, stop and ask; do not fabricate a manual.

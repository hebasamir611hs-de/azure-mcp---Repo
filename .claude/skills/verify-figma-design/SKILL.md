---
name: verify-figma-design
description: Open a PBI's Figma design link via the Figma MCP, verify the linked frame actually matches the PBI before trusting it (never assume a name match means a content match), then extract exact design tokens — fonts, colors, spacing, exact copy — into detailed, assertable UI test cases. Triggered by analyze-pbi / quick-test-cases during Phase-1 analysis, before any test case is derived, listed, or injected. Not invoked directly by the user under normal flow. Do NOT use this for a PBI's embedded/attached images — that is the separate has_images / get_story_for_analysis_with_images gate. A Figma link, when present, takes priority over images as the design source.
---

# Verify Figma Design — Open, Verify, Extract, Before Any Case Exists

Turn a Figma link into **verified, exact** UI test-case input. A frame *named* after
the PBI is not proof it *is* the PBI's design — this skill's whole point is to check
content, not just labels, before a single test case is written.

> **Runs inside Phase 1, before derivation.** `analyze-pbi` / `quick-test-cases` call
> this skill as part of reading the PBI — its output (verified tokens, or an explicit
> "not verified" outcome) is an input to case derivation, never a follow-up correction
> after cases already exist.

**Argument:** the Figma URL (found by scanning the PBI's Description/AC, or supplied by
the user when asked) **plus** the PBI's title/description to check it against →
`$ARGUMENTS`

## Procedure

1. **Parse the URL** into a `fileKey` and, if present, a `nodeId`:
   - Pattern: `figma.com/(file|design)/<fileKey>/...` and `?node-id=<id>` (the URL's
     `node-id` uses a dash, e.g. `1-8970`; the API wants a colon, e.g. `1:8970` —
     convert it).
   - If the link has no `node-id`, note that the fetch will cover the whole file
     (more expensive, less scoped) — prefer asking the user for the specific
     frame's link if the PBI only needs one screen.

2. **Fetch the node** — call `mcp__figma__get_figma_data(fileKey, nodeId)`. Always
   pass `nodeId` when you have one; never fetch a whole file "just in case."

3. **Verify relevance — do not skip this, do not rubber-stamp a name match.**
   Compare the fetched node's actual content against the PBI's title/description.
   Work from concrete evidence, not vibes:
   - **Look for the PBI's specific expected content** — the real field labels,
     headings, or copy the PBI describes. If the PBI says the page has a "Name" and
     "Email" field, do literal strings resembling those appear anywhere in the
     node's text values?
   - **Red flags that the frame is a template / wrong / not-yet-designed**, any of
     which should make you slow down and dig further:
     - Lorem-ipsum or other placeholder body text
     - Generic breadcrumb/label placeholders (e.g. "First page" / "Second page")
     - Generically-numbered component names (e.g. "Component 17 – 58")
     - The same content block repeated under different variant labels (a
       style-guide / component-showcase pattern, not a finished screen)
     - Placeholder contact/business data (e.g. phone `(+000) 000 00000`)
   - **If the PBI-specific content is absent, or red flags dominate** — **STOP.**
     Report plainly what you expected to find vs. what's actually in the frame
     (quote the mismatch — e.g. "expected a Name/Email/Submit form; found Lorem
     ipsum body text and a placeholder breadcrumb"), then **ask the human once**:
     *"This Figma frame doesn't look like the [PBI title] design — [short evidence].
     Is this the right frame, is there a different node in this file, or should I
     proceed without a verified design?"* Act on the answer. Never extract tokens
     from a frame you haven't verified, and never silently substitute a guess.
   - **If confirmed relevant** — proceed to extraction.

4. **Extract exact design tokens** from the verified node's tree:
   - **Copy** — exact text content per element (headings, labels, placeholders,
     button text, helper/error text).
   - **Typography** — font-family, size, weight, line-height (resolve the node's
     `textStyle` reference against the response's style definitions).
   - **Color** — resolved hex/rgba per element (resolve `fills`/`strokes` references
     against the response's color/style definitions).
   - **Spacing & layout** — padding, gaps, dimensions, corner radius from each
     node's `layout` data.
   Scope this to elements the PBI's feature actually touches — do not transcribe an
   entire design system's worth of unrelated tokens.

5. **(Optional) Visual cross-check** — call `mcp__figma__download_figma_images` for
   the node when a rendered view would help confirm a layout/spacing reading that's
   ambiguous from the tree data alone. Not required when the token data is already
   unambiguous.

6. **Produce detailed UI test cases from the tokens** — one case per meaningful
   design detail, written as a concrete, checkable expected result, e.g.:
   *"Verify that the Submit button matches the approved Figma design"* → expected:
   *"background `#01529B`, label 'Submit' in Inter 600 16px, 12px corner radius,
   24px vertical padding."* Tag these cases so it's clear they're Figma-verified
   (not a standard/assumed render) — this is what lets `automate-test-case` later
   assert the exact values instead of just presence/visibility.

7. **Report back** to the calling skill: the relevance verdict + the evidence for
   it, which file/node was used, the full token set, and the generated UI cases —
   delivered **before** the overall Phase-1 set is finalized, so these cases merge
   into the same review gate and sign-off as everything else.

## Hard boundary

- **Never extracts tokens from an unverified frame.** Step 3 is mandatory, every
  time — a matching name or title is not sufficient evidence on its own.
- **Never injects, never calls any Azure DevOps tool.** This skill only reads Figma
  and writes cases to chat, same as the rest of Phase 1.
- **Never runs after cases already exist for this PBI.** If new Figma input shows up
  after sign-off, that's a fresh Phase-1 pass, not a patch onto an approved set.
- **Not a substitute for the image gate.** A PBI's embedded/attached images are a
  separate source (`has_images` → `get_story_for_analysis_with_images`). If a PBI
  has both a Figma link and images, the Figma link is the design source — the skills
  that call this one do not also trigger the image gate for the same PBI.

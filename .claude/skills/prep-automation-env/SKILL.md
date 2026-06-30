---
name: prep-automation-env
description: Verify and prepare the automation environment for a chosen surface (web / mobile / both) — checks the appropriate MCP is registered (Playwright MCP for web, Appium MCP for mobile), the runtime is present (Node, Python, Appium drivers, host SDKs), and ./automation/ is scaffolded for that surface. Auto-runs scaffold-automation-framework when the framework is missing; surfaces a confirmation prompt only if scaffolding errors. Returns a clear status report with checkmark/cross items and explicit next commands. iOS on a non-macOS host is reported as ACTIONABLE (find a macOS host), not silently skipped. Use after Phase-1 surface detection (offered in analyze-pbi sign-off) or from inside route-automation, before any automate-test-case run. Does NOT install heavyweight SDKs (Android SDK / Xcode / Java) automatically — reports and directs.
---

# Prep Automation Environment — Surface-Targeted Readiness Check

Verify the automation environment is ready for the requested surface, scaffold the
framework if missing, and produce a tight readiness report. This is the **gate** the
Development Manager hat runs before any `automate-test-case` call.

**Argument:** the surface → `$ARGUMENTS` (`web` | `mobile` | `both`).
If not provided, ask. If Phase-1 surface detection already named it, pass it through
unchanged.

> Standards (stack, structure, locator strategy) live in
> `@.claude/context/automation-standards.md`. This skill does NOT restate them — it
> verifies the host can satisfy them.

## Procedure

1. **Resolve the surface plan.**
   - `web`    → check web path only.
   - `mobile` → check mobile path (Android + iOS separately).
   - `both`   → check both paths.
   For mobile, treat **Android** and **iOS** as two independent sub-targets — one
   can be ready while the other is blocked.

2. **MCP registration check** (read `.mcp.json` at project root).

   | Surface  | Expected MCP entry |
   |---|---|
   | `web`    | `playwright` (or compatible Playwright MCP) — **treat as present even if not yet registered**, the registration PR is in flight; report as provisional ready. |
   | `mobile` | `appium` — required. Fail-actionable if missing. |

   Do NOT modify `.mcp.json` from this skill.

3. **Host capability check** (read-only — use Bash to probe versions).
   - **Web:** `node --version` ≥ 18; `python --version` ≥ 3.11; `pip show playwright` (the Python pkg) present, browsers installed (`playwright install --dry-run` is fine).
   - **Mobile / Android:** Node ≥ 18; `appium --version` ≥ 2; `appium driver list --installed` contains `uiautomator2`; `adb version` on PATH; `ANDROID_HOME` env var set OR Android Studio default location populated.
   - **Mobile / iOS:** the host **must be macOS**. On Windows / Linux → mark **ACTIONABLE**: *"iOS automation requires a macOS host. Either run this skill on a Mac, or remove `IOS` from the case Platform tags for this batch."* Do not skip silently.

4. **Framework scaffold check.**
   - Look for `./automation/` at the project root.
   - For `web`: check `./automation/web/` and `./automation/core/web/` exist.
   - For `mobile`: check `./automation/mobile/` and `./automation/core/mobile/` exist.
   - **If anything required is missing → invoke the `scaffold-automation-framework`
     skill with the surface argument automatically.** Do not ask first.
   - **If scaffolding errors** (e.g. write-permission failure, missing deps it cannot
     install) → stop, surface the error verbatim, and ask the user how to proceed.

5. **Compose the readiness report** in this exact format:

   ```
   === Automation Environment: <surface> ===
   MCP:
     [ok]   azure-devops
     [ok]   appium             (or [ACTIONABLE] if missing)
     [ok*]  playwright         (* provisional — registration PR in flight)
   Host:
     [ok]   Node v<version>
     [ok]   Python v<version>
     [ok]   Appium v<version>
     [ok]   uiautomator2 driver v<version>
     [ACTIONABLE]  Android SDK / ADB → install Android Studio + add platform-tools to PATH
     [ACTIONABLE]  iOS automation requires a macOS host
   Framework (./automation/):
     [ok]   core/<surface>
     [ok]   <surface>/tests/  scaffolded
   Readiness: <N/M> items ready. The [ACTIONABLE] items below block automate-test-case for <surface>:
     - <each actionable item with its explicit fix command>
   ```

6. **Hand back to the caller.**
   - If the surface is **green across the board** → say so and point the user (or
     `route-automation`) at `automate-test-case` next.
   - If any [ACTIONABLE] remains → return the report and **stop**. Do not invoke
     `automate-test-case` against a non-ready surface.
   - For `both`: if one side is green and the other is blocked, say which sub-surface
     can proceed and which is blocked — don't fail the whole call.

## Hard boundaries

- **Read + scaffold only.** Never modifies `.mcp.json`, never installs Android SDK /
  Xcode / Java / system tools, never writes to Azure DevOps, never authors test code
  (that is `automate-test-case`).
- **No silent skips.** Anything that blocks the surface gets an explicit [ACTIONABLE]
  line with a concrete next command — never a quiet pass.
- **Scaffolding is the only write** — and only via the `scaffold-automation-framework`
  skill, which owns the structure contract.

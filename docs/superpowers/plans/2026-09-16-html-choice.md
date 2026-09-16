# HTML Choice Implementation Plan

> Execute inline with test-driven development; independently forward-test the Skill before handoff.

**Goal:** Shared click-based HTML interaction for Codex, Claude Desktop, WorkBuddy and Doubao Work. Claude Code keeps native controls.

**Architecture:** Reuse the existing Question and WorkflowEngine contracts. Add an HTML presentation, a loopback browser transport and an optional MCP Apps transport sharing the same controller. The controller accepts question-bound callbacks and never executes ADB or downloads. Agent tools consume the resulting pending action and supply evidence as before.

**Tech Stack:** Python standard library for the local browser; optional official Python MCP SDK 1.26.0 for stdio MCP Apps; dependency-free HTML/CSS/JavaScript.

**Spec:** The user expanded the approved scope during implementation: WorkBuddy/Doubao must also avoid overflowing native menus. Four desktops share HTML with a full app list and a viewport-fixed confirmation footer. Embedded MCP App where actually rendered; otherwise authenticated browser, never numbered-text fallback. Claude Code remains native.

## Global constraints

- Only loopback bind, random bearer token, Host/Origin checks, no arbitrary HTTP file or command endpoints.
- All submitted answers bind the current question instance/presentation, reject stale/duplicate or missing choices.
- UI performs no downloads, installs, ADB operations or fabricated evidence.
- HTML host support must be tested, not inferred from unit tests. Browser fallback remains point-and-click.
- Keep host installation and real-host rendering acceptance separate from protocol/browser checks.

## Tasks

- [x] 1. Tests first: HTML platform gating, multi-choice, short-input gating, stale/duplicate callbacks and pending-action lock. Implement `html_ui.py` with the existing workflow.
- [x] 2. Tests first: authenticated loopback routes, non-local Host/Origin rejection and wait/result return. Implement `html_server.py` and `serve-ui` / `wait-ui` / `resume-html` CLI.
- [x] 3. Add accessible `choice.html` rendering summary tables, short radio/checkbox questions, explicit submit and supplemental input. Browser E2E covers two rounds, invalid input, named confirmation, reload and fixed-button viewport bounds.
- [x] 4. Add optional `mcp_ui.py` using official SDK. Verify stdio initialize/tools/resources plus simulated iframe bridge; these do not equal real-host acceptance.
- [x] 5. Update Skill routing, references, packaging and README; test extracted ZIPs and independently forward-test instructions. Record actual acceptance gaps; publish only a prerelease while client UI control is blocked.
- [ ] 6. Real Codex/WorkBuddy/Doubao installation, embedded rendering and multi-round callback acceptance: blocked by computer-use connection failure. Claude client acceptance deferred by user.

## Baseline

Main b7c1c8d; 147 unit tests passed. Existing Skill stops when neither Codex native input tool is exposed; it has no HTML transport. User supplied real blocked session is additional baseline evidence.

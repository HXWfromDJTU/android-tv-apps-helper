# Four-Platform Skill Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and document one behaviorally equivalent Android TV Apps Helper workflow for Claude, Codex, WorkBuddy, and Doubao Work.

**Architecture:** Keep the Codex Skill as the canonical source and generate self-contained host packages using declarative profiles. Enforce shared-core parity with behavioral package tests and record live-host evidence separately from automated compatibility.

**Tech Stack:** Python 3.10+ standard library, unittest, Markdown, JSON, GitHub Releases.

**Spec:** `docs/superpowers/specs/2026-09-15-four-platform-parity-design.md`

## Global Constraints

- Version is `0.3.0`.
- S0-S11, `pending_question`, immutable approval, ADB serial binding, evidence levels, and APK source policy must be equivalent on all platforms.
- Doubao Work must use local-computer execution for LAN ADB.
- Claude live-host validation is out of scope for this release.
- No APK may be embedded in any Skill ZIP.

---

### Task 1: Deterministic Platform Packages

**Files:**
- Create: `tests/test_platform_packages.py`
- Create: `scripts/build_platform_packages.py`
- Modify: `scripts/build_workbuddy_package.py`
- Modify: `plugins/android-tv-apps-helper/plugin.json`

**Interfaces:**
- Consumes: canonical plugin Skill, references, harness, catalog, notices.
- Produces: `build(platform: str, output: Path, version: str | None) -> dict[str, object]`.

- [ ] Write package tests that request all three profiles, inspect real ZIP files, execute the extracted harness, and assert shared-core hashes and the absence of APKs.
- [ ] Run `python3 -m unittest tests.test_platform_packages -v`; expect failure because the platform builder does not exist.
- [ ] Implement the profile-based builder and retain the old WorkBuddy command as a compatibility wrapper.
- [ ] Bump the plugin version to `0.3.0` and add platform keywords.
- [ ] Run the package tests and the full test suite.
- [ ] Commit the package implementation.

### Task 2: Host Preflight and Platform Guidance

**Files:**
- Modify: `plugins/android-tv-apps-helper/skills/android-tv-apps-helper/SKILL.md`
- Modify: `plugins/android-tv-apps-helper/skills/android-tv-apps-helper/references/interaction-contract.md`
- Create: `plugins/android-tv-apps-helper/skills/android-tv-apps-helper/references/platforms.md`
- Modify: `tests/test_skill_contract.py`

**Interfaces:**
- Consumes: platform identity and host tool availability.
- Produces: one persisted local-execution preflight before S0, then the unchanged workflow.

- [ ] Add a behavioral contract test that simulates a packaged Skill and proves all host profiles route through the same harness/question state.
- [ ] Run the contract test; expect failure because host preflight guidance is absent.
- [ ] Add concise platform routing and local-versus-cloud boundaries.
- [ ] Run contract and full tests.
- [ ] Commit the platform guidance.

### Task 3: Four-Platform Documentation and Release Evidence

**Files:**
- Modify: `README.md`
- Create: `docs/platform-compatibility.json`
- Create: `docs/platform-validation.md`
- Modify: `THIRD_PARTY_NOTICES.md` only if a new third-party component is added.

**Interfaces:**
- Consumes: package metadata and live-host results.
- Produces: installation prompts, fallback instructions, invocation steps, and evidence status for all four platforms.

- [ ] Document exact installation and first-run instructions for all hosts.
- [ ] Record Claude as automated-only, not live verified.
- [ ] Validate JSON and Markdown links locally.
- [ ] Commit the documentation.

### Task 4: Live Host Validation

**Files:**
- Modify: `docs/platform-compatibility.json`
- Modify: `docs/platform-validation.md`

**Interfaces:**
- Consumes: built release candidates and host UI observations.
- Produces: per-platform installation, invocation, first-response, and invalid-answer evidence.

- [ ] Install the candidate in Codex, WorkBuddy, and Doubao Work using their supported UI.
- [ ] Start a new conversation and explicitly invoke the Skill.
- [ ] Verify the first response is S0 with one question and `1/2/0` options.
- [ ] Submit an ambiguous answer and verify the same question is redisplayed without ADB execution.
- [ ] Record exact pass, fail, or blocked evidence without upgrading claims.
- [ ] Commit the validation report.

### Task 5: Release

**Files:**
- Modify: `README.md` if candidate links become final release links.
- Generate: `dist/*.zip`, `dist/SHA256SUMS`, `dist/platform-compatibility.json`.

**Interfaces:**
- Consumes: the verified commit and version `0.3.0`.
- Produces: public GitHub tag and release assets.

- [ ] Run all tests, skill validation, plugin validation, compile checks, JSON checks, and reproducible package builds.
- [ ] Merge the feature branch to `main` without discarding unrelated work.
- [ ] Tag and publish `v0.3.0` with all release assets.
- [ ] Download the public assets and compare SHA-256 with the local build.
- [ ] Verify the GitHub README and release URLs.

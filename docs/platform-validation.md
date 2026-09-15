# Platform Validation — v0.3.0

## Evidence rules

The platform matrix separates five results: artifact build, installation visibility, explicit Skill invocation, dialogue-contract behavior, and physical-TV acceptance. A later level never backfills an earlier missing level, and a textual “installed” response is not equivalent to seeing the Skill in the host.

Dialogue-contract validation uses the same two probes on every available host:

1. Start a new conversation and explicitly invoke Android TV Apps Helper. The first reply must identify the read-only/mutation boundary and show exactly one `S0-Q1` question with `1`, `2`, and `0` choices. It must execute no ADB command.
2. Reply `继续`. The host must explain that the answer is invalid, redisplay the same `S0-Q1` and options, and still execute no ADB command.

## Current results

| Platform | Artifact | Installed and visible | Explicit invocation | S0 + invalid-answer lock | Physical TV |
|---|---|---|---|---|---|
| Codex | Passed | Pending live validation | Pending | Pending | Not run in this release |
| WorkBuddy | Passed | Pending live validation | Pending | Pending | Not run in this release |
| 豆包工作 | Passed | Pending live validation | Pending | Pending | Not run in this release |
| Claude Desktop/Code | Passed automated package checks | Not run by user request | Not run | Not run | Not run |

## Automated evidence

- All WorkBuddy, Doubao Work, and Claude packages contain identical shared references, catalog, notices, and harness hashes.
- Each extracted package runs its real `tv-helper init-session` command and enters S0.
- Doubao Work `cloud_computer` session creation fails before a session file is created; `local_computer` succeeds.
- No platform package contains an APK.

Live evidence will be appended after the clients are exercised. Failures remain failures or blockers; they are not converted into compatibility claims.

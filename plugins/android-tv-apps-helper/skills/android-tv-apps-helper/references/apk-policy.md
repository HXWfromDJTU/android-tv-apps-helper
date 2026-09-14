# APK Catalog and Distribution Policy

The source of truth is `../../catalog/apps.json` relative to the plugin root.

## Distribution modes

- `upstream_release`: download from the named publisher's HTTPS release URL.
- `project_release`: download from this project's GitHub Release only when license and redistribution evidence are recorded.
- `pending_rights`: a file may exist, but public redistribution permission is not verified. No URL is allowed.
- `pending_file`: the expected binary is missing. No URL is allowed.

Never silently turn a pending entry into a downloadable one. Show the status and ask the user to skip, submit an authorized local file, or return.

## Clash Meta invariant

Every Clash Meta asset URL must start with:

```text
https://github.com/MetaCubeX/ClashMetaForAndroid/releases/download/
```

Do not mirror it in this repository or replace the official URL with a third-party download.

## Local and downloaded APK validation

Before planning an install:

1. Confirm the file exists and is a readable ZIP with `AndroidManifest.xml`.
2. Record the absolute path, byte size, and SHA-256.
3. Compare size and SHA-256 with the catalog when available.
4. Inspect package, version, minimum SDK, and ABI using available Android build tools; mark unavailable metadata honestly when tools are absent.
5. Compare with the locked TV's SDK, ABI, free storage, and installed version/signature.
6. Create an immutable plan ID from target serial, file digest, and action.

Recompute the digest immediately before execution. A changed file, serial, command, or risk invalidates approval.

## Project release eligibility

A project-hosted APK needs all of:

- a local file matching the recorded SHA-256 and size;
- a known upstream repository or publisher;
- a license or explicit permission allowing redistribution;
- a notice linking the exact upstream source/release;
- a GitHub Release asset URL under this project.

Store APK binaries in GitHub Releases, not Git history. Keep proprietary, unclear, or missing apps visible in the catalog with their blocking reason.

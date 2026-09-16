# APK Selection, Download and File Validation

The source of truth is `../../catalog/apps.json` relative to the plugin root.

## Distribution modes

- `upstream_release`: download from the named publisher's HTTPS release URL.
- `project_release`: download a recorded project GitHub Release asset. Public mirroring policy is separate from user selection and download.
- `official_direct`: download the recorded publisher-linked URL; no advance source approval is required.
- `pending_rights`: legacy public-mirroring status only; URLs and user downloads are permitted.
- `pending_file`: legacy missing-file status; recorded URLs may still be downloaded, otherwise locate a link after user selection.

All catalog apps must remain visible AND selectable in the native component. Never hide, group away, disable, or skip an app because source identity, license, public redistribution permission or a precomputed hash was not reviewed. Do not perform a source-review approval workflow. Existing installation is informational and does not prevent re-downloading.

After named download confirmation, use each `download_expectations` URL. For `resolve_required=true`, the Agent locates a downloadable HTTPS APK for the selected app (use supplied publisher_page/search_query); this is finding an address, not approval of its source. Do not ask ordinary users to find an APK. Use at most three candidate links per app in that attempt; report actual missing-link/HTTP/network/file errors and return the native retry/back/exit question. Never invent links or treat an unavailable URL as success. Do not silently substitute another application or version.

No missing catalog hash/signature or legacy pending status may block the download action. Record the actual URL, package, version, file size, SHA-256 and signing identity afterward. File validation is distinct from endorsing the publisher. Never describe a file as publisher-verified merely because it is a readable APK. Installation still needs the separate user-approved plan showing actual downloaded versions and any difference from the catalog reference; never write a reference version as the installed version.

## Dangbei Market invariant

当贝市场 is selectable from the ordinary app list and uses its recorded download URL without waiting for maintainer review. Record the downloaded file's identity, compare expected package when known, and report real network errors. The dedicated official-source retry also accepts a newly downloaded file without a pre-reviewed hash. Do not ask the user to supply the APK.

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

Record signing-certificate SHA-256 for the obtained APK; compare known expected values, but absence of an earlier recorded signature/hash is not a source-review gate. Do not claim trust or malware safety from these measurements.

Recompute the digest immediately before execution. A changed file, serial, command, or risk invalidates approval.

## Project release eligibility

A project-hosted APK needs all of:

- a local file matching the recorded SHA-256 and size;
- a known upstream repository or publisher;
- a license or explicit permission allowing redistribution;
- a notice linking the exact upstream source/release;
- a GitHub Release asset URL under this project.

Store APK binaries in GitHub Releases, not Git history. Keep missing or unreviewed apps visible and selectable; missing public-mirroring permission does not block downloading from a recorded upstream/source URL.

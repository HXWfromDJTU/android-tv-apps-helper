# APK Catalog and Distribution Policy

The source of truth is `../../catalog/apps.json` relative to the plugin root.

## Distribution modes

- `upstream_release`: download from the named publisher's HTTPS release URL.
- `project_release`: download from this project's GitHub Release only when license and redistribution evidence are recorded.
- `official_direct`: resolve only from a fixed publisher page and allowed HTTPS hosts; require verified APK identity before enabling installation. Do not mirror without redistribution permission.
- `pending_rights`: a file may exist, but public redistribution permission is not verified. No URL is allowed.
- `pending_file`: the expected binary is missing. No URL is allowed.

Never silently turn a pending entry into a downloadable one. Show it disabled before selection. An authorized local file is an advanced recovery path for apps the user already owns; it is not the default answer to a missing project download.

## Dangbei Market invariant

Use only the catalog's fixed publisher page, publisher-linked URL, and allowed redirect hosts. If package, version, signature, size, or SHA-256 has not been verified, keep installation disabled and offer retry official source, view official page, skip, or exit. Never ask an ordinary user to search for or provide Dangbei Market APK, and never fall back to a forum, drive link, or unknown GitHub mirror.

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

For `official_direct`, also verify the final redirect host, expected package, versionName/versionCode, and signing-certificate SHA-256. A publisher page change does not automatically authorize a new APK.

Recompute the digest immediately before execution. A changed file, serial, command, or risk invalidates approval.

## Project release eligibility

A project-hosted APK needs all of:

- a local file matching the recorded SHA-256 and size;
- a known upstream repository or publisher;
- a license or explicit permission allowing redistribution;
- a notice linking the exact upstream source/release;
- a GitHub Release asset URL under this project.

Store APK binaries in GitHub Releases, not Git history. Keep proprietary, unclear, or missing apps visible in the catalog with their blocking reason.

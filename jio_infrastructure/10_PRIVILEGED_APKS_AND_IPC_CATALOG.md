# 10. Privileged System Applications & Android IPC Action Catalog

> **Parent Topic:** [`jio_infrastructure/README.md`](README.md)  
> **Source Directory:** [`ota_packages/extracted/apks/`](../ota_packages/extracted/apks/)  
> **Total Packages Analyzed:** 88 Applications (Privileged System, System Ext, Product, and Vendor partitions)

---

## 1. Functional System Classification

The extracted application suite is divided into 10 operational tiers:

```
                                  Jio System Application Suite
                                                │
         ┌──────────────────┬───────────────────┼───────────────────┬──────────────────┐
         ▼                  ▼                   ▼                   ▼                  ▼
   Provisioning/TR069    UI & Launcher      Auth & SSO          Media & IPTV        Telemetry/ADC
   ──────────────────    ─────────────      ──────────          ────────────        ─────────────
   • TR069.apk           • JioLauncher.apk  • JioStbSsoService  • JioLiveTV.apk     • JioAdc.apk
   • JioHttpUpdate.apk   • JioHotelLauncher • PADI.apk          • JioInputSource    • AKA.apk
   • JioUsbUpdate.apk    • JioSettings.apk  • JioProfileUtility • Bioscope.apk      • PODLogService
   • JioRcuUpdate.apk    • ControlCenter.apk                    • AndroidMediaShell • JioSmartStats
```

---

## 2. Privileged Application Catalog Matrix

Below is the verified matrix of all proprietary Jio privileged packages extracted from the Android 11 OS payload:

The permissions column lists manifest declarations. A permission declaration alone does not prove that Android granted a signature or privileged permission at runtime. The Factory Setup signer check and the distinct Jio Store install path are documented in [the mask-ROM analysis, §1.2](../AML_MASKROM_SECURITY_ANALYSIS.md#12-factory-setup-usb-apk-path-the-signer-check).

| Package File | Android Package Name | Version | Critical Permissions Declared | Primary Architectural Role |
| :--- | :--- | :--- | :--- | :--- |
| **`TR069.apk`** | `com.jio.tr069client` | `4.2.3` | `WRITE_SECURE_SETTINGS`, `MANAGE_DEVICE_POLICY_DEBUGGING_FEATURES`, `REBOOT`, `RECOVERY` | CWMP carrier management, remote ADB control, policy enforcement. |
| **`JioHttpUpdate.apk`** | `com.jio.stb.httpupdate` | `1.0.8` | `REBOOT`, `RECOVERY`, `WRITE_EXTERNAL_STORAGE` | NanoHTTPD web update daemon (port 54321), A/B update engine binding. |
| **`JioStbSsoService.apk`** | `com.jio.stb.sso` | `2.1.4` | `INTERACT_ACROSS_USERS`, `GET_ACCOUNTS` | Single Sign-On broker, line binding validation, token broadcast. |
| **`PADI.apk`** | `com.jio.padi` | `1.0.2` | `INTERNET`, `ACCESS_NETWORK_STATE` | Netflix & OTT partner token generation (`partnerapi.jio.com`). |
| **`JioLiveTV.apk`** | `com.jio.stb.catv` | `3.4.12` | `SYSTEM_ALERT_WINDOW`, `MODIFY_AUDIO_SETTINGS` | Linear IPTV & DVB-IP stream decoder, channel tuning, cloud DVR. |
| **`JioInputSource.apk`** | `com.jio.stb.inputsource` | `1.0.5` | `TV_INPUT_HARDWARE` | Tuner HAL binding, unicast DRM key coordination (`ucast-key.iptv.jio.com`). |
| **`JioLauncher.apk`** | `com.iwedia.ui.rjio.launcher.reliance` | `3.0.72` | `WRITE_SETTINGS`, `PACKAGE_USAGE_STATS` | Default Android TV Leanback launcher, dynamic category rendering. |
| **`JioHotelLauncher.apk`** | `com.jio.stb.hotellauncher` | `2.0.18` | `WRITE_SETTINGS`, `REBOOT` | Hospitality firmware launcher, dynamic room signage, guest token reset. |
| **`JioSettings.apk`** | `com.rjil.jiostbsetting` | `15.1.5` | `INSTALL_PACKAGES`, `DELETE_PACKAGES`, `REQUEST_DELETE_PACKAGES`, `WRITE_SECURE_SETTINGS`, `CHANGE_WIFI_STATE` | Custom system settings UI, diagnostics, and Factory Setup USB APK signer-check/installer. |
| **`JioAdc.apk`** | `com.jio.adc.embedded` | `1.5.0` | `READ_PRIVILEGED_PHONE_STATE` | Automated Data Collector (ADC), event batching, Magnum ingest. |
| **`AKA.apk`** | `com.jio.adc.aka` | `1.0.3` | `DUMP`, `BATTERY_STATS` | Hardware sensor monitoring, thermal tracking, memory footprint analytics. |
| **`PODLogService.apk`** | `com.jio.podlogservice` | `1.0.1` | `READ_LOGS`, `DUMP` | Automated logcat, tombstone, and dmesg log compression and upload. |
| **`JioSmartStats.apk`** | `com.jio.smartstats` | `1.1.2` | `ACCESS_NETWORK_STATE` | Video QoE (Quality of Experience) packet loss and buffer metrics. |
| **`JioVoice.apk`** | `com.jio.voiceassist` | `3.0.52` | `RECORD_AUDIO`, `CAPTURE_AUDIO_OUTPUT` | HelloJio voice assistant, Reverie offline edge ASR engine, Azure speech synthesis. |
| **`BTRemoteServer.apk`** | `com.jio.remote.btserver` | `2.1.0` | `BLUETOOTH_PRIVILEGED`, `BLUETOOTH_ADMIN` | Bluetooth Low Energy voice remote GATT pairing and audio pipeline. |
| **`JioStore.apk`** | `com.jio.store` | `1.5.8.7` | `INSTALL_PACKAGES`, `REQUEST_INSTALL_PACKAGES`, `DELETE_PACKAGES`, `REQUEST_DELETE_PACKAGES` | Proprietary app store and PackageInstaller client, cleartext PHP proxy integration (`49.40.64.244`). |
| **`JioAdsPushService.apk`** | `com.jio.adspush` | `2.0.4` | `RECEIVE_BOOT_COMPLETED` | Mercury push ad campaign synchronization and image caching. |
| **`JioScreensaver.apk`** | `com.jio.screensaver` | `2.3.7` | `WAKE_LOCK` | Sponsored screensaver display, Mercury attribution click tracking. |
| **`JioAppOptimizer.apk`** | `com.jio.appoptimizer` | `1.2.0` | `FORCE_STOP_PACKAGES`, `KILL_BACKGROUND_PROCESSES` | App whitelisting and background process killer for memory management. |
| **`JioSDKService.apk`** | `com.jio.sdk` | `1.0.4` | `INTERACT_ACROSS_USERS` | Java framework wrapper interfacing with native root `/system/bin/sdknativeservice`. |

---

## 3. Internal Android Broadcast Intent Bus Catalog

Cross-package communication is handled via a private broadcast intent bus. Below is the reverse-engineered registry:

### 3.1 TR-069 & Carrier Policy Broadcasts
* **`com.tr069.action.Create_New_Session`**: Forces `TR069.apk` to immediately wake up and open a CWMP session to `acs.oss.jio.com`.
* **`com.tr069.action.VendorConfigurationFileDownloaded`**: Delivered when the ACS pushes an updated vendor XML/JSON file. Handled by `TR069.apk`, `ChatBot.apk`, and `JioSettings.apk`.
* **`com.tr069.action.BLOCKED_DC_EVENT_LIST`**: Instructs `JioLauncher.apk` and `JioSettings.apk` to block user access to blacklisted applications.
* **`com.tr069.action.PACKAGE_REMOVED_DC_EVENTS`**: Instructs the launcher to unregister and purge removed deployment units.
* **`com.tr069.action.PRODUCT_TYPE_CHANGED`**: Broadcast when provisioning re-classifies device operating mode.
* **`com.tr069.action.HOTSPOT_STATUS_CHANGED`**: Synchronizes local Wi-Fi hotspot states with cloud policies.
* **`com.jio.tr069.action.reboot_notify`**: Signals `JioService.apk` to perform graceful cleanup prior to ACS reboot.

### 3.2 Television & Channel Tuning Broadcasts
* **`com.jio.catv.intent.action.TUNE_CHANNEL`**: Signals `JioLiveTV.apk` to switch tuner input to a designated channel.
* **`com.jio.catv.intent.action.DVBIP_MODE_BOUQUET_CHANGE`**: Switches active DVB-IP bouquet identifiers.

### 3.3 Single Sign-On & Identity Broadcasts
* **`com.jio.action.SSO_LOGIN_SUCCESS`**: Broadcast by `JioStbSsoService.apk` to distribute fresh authentication bearer tokens to `JioStore.apk`, `JioLiveTV.apk`, and `JioVoice.apk`.

### 3.4 Hardware Remote Control & Bluetooth Broadcasts
* **`com.tr069.action.RCU_CLEAR_CACHE`**: Purges cached Bluetooth remote pairing descriptors.
* **`com.tr069.action.RCU_PAIR_BLOCK`**: Prevents unauthorized third-party Bluetooth input peripherals from pairing.
* **`com.jio.tr069.action.GET_RCU_DATA`**: Requests battery level, firmware version, and signal telemetry from `BTRemoteServer.apk`.

### 3.5 App Optimization & Process Control Broadcasts
* **`com.jio.action.GET_FG_PACKAGE`**: Polled by `JioAppOptimizer.apk` to identify the current foreground application.
* **`com.jio.action.POST_FG_PACKAGE`**: Signals foreground transition events.
* **`com.jio.action.SET_WHITE_PACKAGE`**: Dynamically whitelists critical system packages to protect them from memory reclamation kills.

---
## 🔗 Related Documents

| Related Document | Relationship |
| :--- | :--- |
| [`../OTA_ANALYSIS.md`](../OTA_ANALYSIS.md) | §7 — Extracted applications, launcher & overlays table (source APKs for this catalog). |
| [`../JDWP_SYSTEM_ESCALATION_FINDINGS.md`](../JDWP_SYSTEM_ESCALATION_FINDINGS.md) | `JioCommandReceiver.apk` (`com.rjil.jio.stb.commandreceiver`) debuggable system-UID (UID 1000) JDWP escalation findings. |
| [`11_SECURITY_AUDIT_AND_ATTACK_SURFACE.md`](11_SECURITY_AUDIT_AND_ATTACK_SURFACE.md) | §2.6 — Privileged activity-launch trampoline in `JioCommandReceiver.apk` and other privileged-app attack surface. |

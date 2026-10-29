# 06. Telemetry, Device Analytics & Push Notification Infrastructure

> **Parent Topic:** [`jio_infrastructure/README.md`](README.md)  
> **Source Packages:** [`JioAdc.apk`](../ota_packages/extracted/apks/jio_system_priv_app/JioAdc.apk), [`AKA.apk`](../ota_packages/extracted/apks/jio_system_priv_app/AKA.apk), [`PODLogService.apk`](../ota_packages/extracted/apks/jio_system_priv_app/PODLogService.apk), [`JioSmartStats.apk`](../ota_packages/extracted/apks/jio_system_priv_app/JioSmartStats.apk)

---

## 1. Executive Summary & Topology

Reliance Jio gathers hardware telemetry, network quality metrics, application engagement logs, and crash dumps through a proprietary analytics ecosystem known as **Magnum**. Device-level collection is orchestrated by privileged background daemons implementing the **Automated Data Collector (ADC)** framework:

```
                      ┌──────────────────────────────────────────────┐
                      │          On-Device Telemetry Daemons         │
                      │  (JioAdc.apk / AKA.apk / PODLogService.apk)  │
                      └──────────────────────┬───────────────────────┘
                                             │
             ┌───────────────────────────────┴───────────────────────────────┐
             │                                                               │
             ▼                                                               ▼
 ┌───────────────────────────────────────┐       ┌───────────────────────────────────────┐
 │       Magnum Analytics Platform       │       │    Push Notification Delivery Fleet   │
 ├───────────────────────────────────────┤       ├───────────────────────────────────────┤
 │ • devents.magnum.jio.com              │       │ • auth.push.jio.com                   │
 │ • fcmr.magnum.jio.com                 │       │ • ndelivery.push.jio.com              │
 │ • stg-devents.magnum.jio.com          │       │ • fcmr.magnum.jio.com (FCM Router)    │
 └───────────────────────────────────────┘       └───────────────────────────────────────┘
```

---

## 2. Magnum Telemetry & Event Ingestion Endpoints

The primary telemetry gateway is `devents.magnum.jio.com`:

| Environment | Endpoint URL | Protocol | Role |
| :--- | :--- | :--- | :--- |
| **Production Ingest** | `https://devents.magnum.jio.com/v1/device/analytics` | HTTPS (TCP 443) | Receives compressed batches of user events, UI interactions, and system metrics. |
| **Staging Ingest** | `https://stg-devents.magnum.jio.com/v1/device/analytics` | HTTPS (TCP 443) | Pre-production testing environment. |
| **SIT Ingest** | `http://sit-devents.magnum.jio.com/v1/device/analytics` | HTTP (TCP 80) | Unencrypted test ingest endpoint discovered in `JioLauncher.apk`. |
| **FCM Router (Prod)** | `https://fcmr.magnum.jio.com` | HTTPS (TCP 443) | Magnum push message router interfacing with Google FCM. |
| **FCM Router (Staging)**| `https://stg-fcmr.magnum.jio.com` | HTTPS (TCP 443) | Staging FCM notification routing node. |

---

## 3. Jio Push Notification Delivery Fleet

Push notifications destined for system apps (such as urgent OTA alerts, promotional popups, or configuration resets) route through Jio’s specialized push broker:
* **Authentication Endpoint:** `https://auth.push.jio.com`
* **Notification Delivery Node:** `https://ndelivery.push.jio.com`
* **Workflow:**
  1. The client registers its FCM token with `auth.push.jio.com`.
  2. Inbound wake-up payloads are signaled via `fcmr.magnum.jio.com`.
  3. Full notification contents and rich media banners are fetched from `ndelivery.push.jio.com`.

---

## 4. On-Device ADC (Automated Data Collection) Pipeline

Decompilation of `JioAdc.apk` (`com.jio.adc`), `AKA.apk` (`com.jio.adc.aka`), and `PODLogService.apk` exposes the internal pipeline:

### 4.1 Component Roles
* **`JioAdc.apk` (com.jio.adc.embedded):** The primary data collector library running as a persistent system service. Exposes internal AIDL interfaces for other Jio apps to log events.
* **`AKA.apk` (com.jio.adc.aka):** Analytics Collector Agent. Monitors low-level system states, device memory, CPU utilization, and thermal events.
* **`PODLogService.apk`:** Privileged system daemon that captures `logcat` dumps, kernel `dmesg` outputs, and crash tombstone files from `/data/tombstones/`, packaging them for diagnostics upload.
* **`JioSmartStats.apk`:** Gathers Wi-Fi signal quality (RSSI, BSSID), packet error rates, and buffer underrun telemetry during video playback.

### 4.2 Lifecycle & Upload Management
The ADC engine buffers events locally in an encrypted SQLite database and schedules batched uploads to minimize network wake-ups:
* `getLastUploadBatchInfo`
* `getNextUploadTime`
* `getLastUploadResult`
* `mUploadDisabled` (Dynamic flag toggled by carrier policy)

### 4.3 IPC Broadcast Triggers
`JioAdc.apk` and `JioSettings.apk` communicate telemetry states via intent actions:
```text
com.jio.adc.embedded.adc.action.AR
com.jio.adc.embedded.adc.action.F
com.rjil.jiostbsetting.ACTION_STB_EVENT
com.rjil.jiostbsetting.ACTION_STB_RESULT
```

---

## 5. Voice AI Interaction Telemetry & Web Beacon Tracking (JAMP / `pl.gif`)

In addition to Magnum and ADC batch analytics, the HelloJio Voice Assistant ([`JioVoice.apk`](../ota_packages/extracted/apks/jio_system_priv_app/JioVoice.apk)) operates a real-time web beacon telemetry exfiltration channel:

### 5.1 The Akamai Tracking Beacon (`pl.gif`)
* **Endpoint:** `https://jiova.akamaized.net/jiova/usagedump/pl.gif?`
* **Trigger Component:** [`com.android.app.jio.voiceassist.voice.b.a`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_voice/sources/com/android/app/jio/voiceassist/voice/b/a.java#L100-L213) (tagged internally as `"JAMP get call"` via Android Volley).
* **Delivery Mechanism:** Dispatches an HTTP GET request to retrieve a 43-byte transparent 1x1 GIF (`image/gif`), embedding sensitive voice query analytics directly into the URL query parameters.

### 5.2 Exfiltrated Voice Interaction Fields
Every voice command spoken into the remote transmits the following telemetry payload:

| Query Parameter Key | Collected Data Element |
| :--- | :--- |
| **`finalStt`** | **Speech-To-Text Transcript:** Exact full transcription of the customer's spoken words. |
| **`userInput` / `content`** | Raw speech query input string. |
| **`subscriberId`** | The customer's JioFiber FTTH subscriber account identifier. |
| **`topScoringIntent`** | NLU classified intent (`PlayMedia`, `ChangeChannel`, `WeatherQuery`, etc.). |
| **`sttConfidenceScore`** | Acoustic recognition confidence percentage. |
| **`voiceInvokingApp` / `appname`** | Foreground application package name running when mic was activated (e.g. JioCinema, YouTube). |
| **`profile_id` / `user_type`** | Active household user profile identifier and subscriber classification. |
| **`inAppSTTDuration`** | Local on-device STT latency in milliseconds. |
| **`gbResponseDuration`** | Gateway Backend cloud response latency in milliseconds. |
| **`timeStamp`** | Epoch millisecond timestamp of the voice event. |
| **`launchScreen` / `launchPositionRow`** | Exact UI coordinates and screen state from which voice search was triggered. |

### 5.3 Secondary JITA Event Beacon
Dynamic configuration ([`va-stb-config.json`](http://jiova.akamaized.net/static/config/va-stb-config.json)) provisions a secondary event beacon under the `jita_server` configuration block:
```text
https://quantum-sit-lc.jio.com/va/poc/ev.gif?
```
Used for proof-of-concept event dumping and analytics verification on staging and test STB hardware.

---
## 🔗 Related Documents

| Related Document | Relationship |
| :--- | :--- |
| [`../NETWORK_ANALYSIS.md`](../NETWORK_ANALYSIS.md) | Telemetry traffic capture and endpoint categorization (Magnum, FCM). |
| [`08_VOICE_AI_AND_HELLOMODELS.md`](08_VOICE_AI_AND_HELLOMODELS.md) | Voice interaction telemetry web beacon (`pl.gif` / `jita_server`) and real-time usage tracking (§5). |
| [`07_ADTECH_MERCURY_AND_MONETIZATION.md`](07_ADTECH_MERCURY_AND_MONETIZATION.md) | Ad impression/click attribution telemetry (`mercury-ck.jio.com`). |

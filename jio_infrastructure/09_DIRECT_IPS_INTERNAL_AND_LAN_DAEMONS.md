# 09. Direct AS55836 IP Backends, Local Daemons & LAN Subnet Ports

> **Parent Topic:** [`jio_infrastructure/README.md`](README.md)  
> **Source Packages:** [`JioStore.apk`](../ota_packages/extracted/apks/jio_system_priv_app/JioStore.apk), [`JioVoice.apk`](../ota_packages/extracted/apks/jio_system_priv_app/JioVoice.apk), [`JioHttpUpdate.apk`](../ota_packages/extracted/apks/jio_system_priv_app/JioHttpUpdate.apk), `/system/bin/sdknativeservice`  
> **Related Research:** [`Housekeeping-SDK.md`](../Housekeeping-PoC/Housekeeping-SDK.md), [`NETWORK_ANALYSIS.md`](../NETWORK_ANALYSIS.md)

---

## 1. Direct AS55836 IP Gateways & Cleartext PHP Proxies

In addition to DNS-resolved endpoints, static analysis of `JioStore.apk` and `JioVoice.apk` revealed direct hardcoded IP connections inside Jio's Autonomous System (`AS55836`):

### 1.1 The Cleartext PHP Proxy Gateway (`49.40.64.244:6080`)
A cluster of internal PHP proxy scripts listens on non-standard TCP port **6080 over unencrypted cleartext HTTP**:

```http
http://49.40.64.244:6080/proxy.api.php
http://49.40.64.244:6080/proxy.mads.php
http://49.40.64.244:6080/proxy.vapi.php
http://49.40.64.244:6080/sit.api.php
http://49.40.64.244:6080/sit.mads.php
http://49.40.64.244:6080/sit.vapi.php
http://49.40.64.244:6080/sit.goapi.php
http://49.40.64.244:6080/sit.gomapi.php
```

#### Purpose & Architecture:
* Acts as an internal proxy and routing bridge between the Set-Top Box app suite and Jio's internal microservice backplanes.
* Endpoints prefixed with `proxy.*` handle production traffic, while `sit.*` routes to System Integration Testing environments.
* The lack of transport encryption (HTTP port 6080) permits full inspection and interception when monitored within the carrier network.

---

### 1.2 Direct Core IP Infrastructure Matrix

| Direct IP Address | Domain / PTR | Port & Protocol | Role in Ecosystem |
| :--- | :--- | :--- | :--- |
| **`49.40.8.93`** | `acs.oss.jio.com` | TCP `8443`, `9443` (TLS) | Primary TR-069 Auto-Configuration Server (WildFly 10 / JBoss). |
| **`49.40.48.28`** | `sftp.telematics.jio.com` | TCP `22` (SSH / SFTP) | Internal carrier telematics and diagnostic logcat ingestion repository (`va` / `V@13ji@o`). |
| **`49.40.48.224`** | `bs.jio.com` | TCP `443` (TLS) | Bootstrap Services (service discovery and registration policies). |
| **`49.40.64.194`** | *(No PTR Record)* | TCP `8124` (**Cleartext HTTP**) | Direct Datacenter Speech Output Engine (SOE) hosting `/soe/api/tts/v1` and `/soe/activity/srsdeletepid` (see Section 1.3). |
| **`49.40.21.37`<br>`49.40.21.52`<br>`49.40.21.202`** | `fota.mst.kai.jiophone.net`<br>`api.kai.jiophone.net` | TCP `80`, `443` | Master FOTA Origin tier synchronizing firmware packages to Akamai NetStorage. |
| **`103.63.129.21`** | `api.jio.com` | TCP `443` (TLS) | Primary Subscriber Authentication & Entitlement API (F5 BigIP ADC). |
| **`[2405:200:1602:1174::8]`** | *(Jio IPv6 Subnet)* | TCP `443` (TLS) | Direct IPv6 core sync node referenced in `JioService.apk`. |

---

### 1.3 Direct Cleartext Speech Output Engine & Biometric Reset (`49.40.64.194:8124`)

Reverse engineering of [`JioVoice.apk`](../ota_packages/extracted/apks/jio_system_priv_app/JioVoice.apk) uncovered a direct IP datacenter binding to **`49.40.64.194`** running an Apache HTTP server on cleartext TCP port **`8124`**:

* **Network Location:** AS55836 (Reliance Jio Infocomm Limited, Ghansoli Datacenter, Navi Mumbai).
* **Hosted Services:**
  * `http://49.40.64.194:8124/soe/api/tts/v1` — Native Speech Output Engine (SOE) REST API. Dispatched by [`CustomTextToSpeechService.java`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_voice/sources/com/android/app/jio/voiceassist/voice/customtts/CustomTextToSpeechService.java) to synthesize speech responses.
  * `http://49.40.64.194:8124/soe/activity/srsdeletepid` — Speaker Recognition System (SRS) voice biometric profile purging API.
  * `ws://49.40.64.194:8124/soe/v1/echo` — Unencrypted WebSocket audio stream.
* **Production Routing Flaw:** In [`com.android.app.jio.voiceassist.b.a.t()`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_voice/sources/com/android/app/jio/voiceassist/b/a.java#L152-L154), the application evaluates `if (JioGlobalSearchApplication.c != 1)` to select the SRS deletion endpoint. Because production devices run with environment code `c == 0` (where `1` denotes staging), **all production STB profile resets bypass domain TLS and route unencrypted payloads containing subscriber SSO tokens and voice profile IDs directly to `49.40.64.194:8124`**.

---

## 2. On-Device Native Services & Background Daemons

### 2.1 The Native Root Daemon (`/system/bin/sdknativeservice`)
* **Process Identity:** Runs under user **`root` (`uid 0`)**, group `root shell bluetooth system`.
* **Init Definition:**
  ```ini
  service sdknativeservice /system/bin/sdknativeservice
      class main
      user root
      group root shell bluetooth system
  ```
* **SELinux Domain:** `sdknativeservice` (granted `dac_override`, `dac_read_search`, `net_admin`, `net_raw`, `setuid`, `sys_module`, `sys_ptrace`, and `execute_no_trans` on `/system/bin/sh`).
* **Binder Registration:** Exposes binder service `com.jio.sdk.sdknativeservice`.
* **Execution Vulnerability:** Dispatches requests to internal modules (e.g., Module 4, OS). The `get-cpu-temperature` command reads a `zone:` string parameter and passes it directly to `popen(zone_string, "r")` with zero sanitization, providing a local root shell primitive from ADB.

---

### 2.2 Local NanoHTTPD Portal (`JioHttpUpdate.apk` on Port 54321)
* **Binding:** TCP `0.0.0.0:54321` (accessible over local Wi-Fi / Ethernet).
* **Software:** Embedded Java NanoHTTPD.
* **Functionality:** Provides local web browser flashing of OTA packages (`/updateme`) guarded by an 8-digit randomized on-screen security PIN.

---

### 2.3 Network ADB Daemon (`adbd` on Port 5555)
* **Configuration:** Hardcoded in `/vendor/build.prop`:
  ```ini
  service.adb.tcp.port=5555
  ```
* **Behavior:** The moment `Settings.Global.adb_enabled` transitions to `1` (either via TR-069 `Device.JioSTB.USB.USBDebugging` or local toggling), `adbd` binds directly to `0.0.0.0:5555`, opening a wireless debugging console accessible across the local subnet.

---

### 2.4 Local Subnet Pairing Beacon (`5775/UDP`)
* **Transport:** UDP Broadcast to subnet broadcast (`192.168.x.255:5775`).
* **Purpose:** Emitted by the STB during boot and idle states to enable the **JioHome** smartphone companion app and local home control systems (e.g. RTI smart remote integrations) to discover and pair with the STB without transiting cloud servers.

---
## 🔗 Related Documents

| Related Document | Relationship |
| :--- | :--- |
| [`../VOICE_DYNAMIC_CONFIG_RESEARCH.md`](../VOICE_DYNAMIC_CONFIG_RESEARCH.md) | SOE TTS endpoint (`49.40.64.194:8124`) and diagnostic PIN `777333` research (§4). |
| [`08_VOICE_AI_AND_HELLOMODELS.md`](08_VOICE_AI_AND_HELLOMODELS.md) | Datacenter Speech Output Engine backends and WebSocket audio echo (`ws://49.40.64.194:8124/soe/v1/echo`) (§5.1). |
| [`Housekeeping-PoC/Housekeeping-SDK.md`](../Housekeeping-PoC/Housekeeping-SDK.md) | `sdknativeservice` root shell exploit — the native root daemon documented in §2.1. |
| [`../NETWORK_ANALYSIS.md`](../NETWORK_ANALYSIS.md) | Local UDP discovery beacon (5775/UDP) and LAN daemon traffic. |

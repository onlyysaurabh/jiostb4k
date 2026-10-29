# 02. Device Management, TR-069 CWMP & Dual-Stack Heartbeat Infrastructure

> **Parent Topic:** [`jio_infrastructure/README.md`](README.md)  
> **Target Package:** `com.jio.tr069client` ([`TR069.apk`](../ota_packages/extracted/apks/jio_system_priv_app/TR069.apk), Version 4.2.3, build 423)  
> **Related Research:** [`TR069_ACS_RESEARCH.md`](../TR069_ACS_RESEARCH.md), [`TR069_REMOTE_ADB_ANALYSIS.md`](../TR069_REMOTE_ADB_ANALYSIS.md)

---

## 1. Overview & Architectural Fleet Partitioning

Reliance Jio enforces centralized device lifecycle management, remote diagnostics, dynamic policy application, and remote recovery through the Broadband Forum **CPE WAN Management Protocol (CWMP / TR-069)** and TR-181/TR-135 device data models.

Reverse engineering of extracted system configuration assets in `TR069.apk` reveals that Jio operates **three dedicated Auto-Configuration Server (ACS) clusters** partitioned by device class:

```
                                  Jio CWMP Management Fleet
                                               │
         ┌────────────────────────┬────────────┴───────────┬────────────────────────┐
         ▼                        ▼                        ▼                        ▼
     STB ACS                 JioBook ACS                IoT ACS             Dual-Stack Heartbeats
  ───────────────          ───────────────           ─────────────          ─────────────────────
  acs.oss.jio.com          macs.oss.jio.com          iotacs.jioconnect.com  jiodeviceheartbeat-v4.jio.com
  Port: 8443 / 9443        Port: 8443                Port: 8080 / 8001      jiodeviceheartbeat-v6.jio.com
  Fleet: Set-Top Boxes     Fleet: JioBook Laptops    Fleet: ONTs / Gateways Fleet: All Connected CPEs
```

### 1.1 Hardcoded Configuration Profiles (`assets/*.config`)
Directly inside `TR069.apk`:

```properties
# assets/stb_config.config
acsurl=https://acs.oss.jio.com:8443/ftacs-digest/ACS

# assets/jiobook_config.config
acsurl=https://macs.oss.jio.com:8443/ftacs-digest/ACS

# assets/iotacs.config
acsurl=http://iotacs.jioconnect.com:8080/ftacs-digest/ACS
```

---

## 2. Server Cluster Topology & Cryptographic Identity

### 2.1 The STB ACS Cluster (`acs.oss.jio.com`)
* **IP Address:** `49.40.8.93` (AS55836, Reliance Jio Infocomm Ltd)
* **Listening Ports:** TCP `8443` (primary management flow), TCP `9443` (secondary / batch telemetry flow)
* **Software Stack:** Red Hat WildFly Enterprise Application Server 10.x (JBoss), Java EE runtime.
* **TLS Identity:**
  * Subject: `CN=acs.oss.jio.com`, `O=Jio Platforms Ltd`, `OU=RJIL`
  * Issuer: `CN=RILSUBCA01` (Internal Reliance Subordinate CA)

### 2.2 The Laptop ACS Cluster (`macs.oss.jio.com`)
* **FQDN:** `macs.oss.jio.com`
* **Port:** TCP `8443`
* **Target:** JioBook Arm-based laptops running JioOS. Enables corporate and educational remote administration, package enrollment, and operating system recovery.

### 2.3 The IoT & Residential Gateway ACS (`iotacs.jioconnect.com`)
* **FQDN:** `iotacs.jioconnect.com`
* **Ports:** TCP `8080` (CWMP RPC endpoint), TCP `8001` (Firmware download portal)
* **Target:** JioFiber GPON ONTs (Arcadyan, Sercomm, Skyworth), smart home gateways, and fixed wireless CPEs.
* **Firmware URL Example:**
  ```text
  http://iotacs.jioconnect.com:8001/Arcadyan-OTA-01.25.12-2024-06-17_userdebug.zip
  ```

---

## 3. Dual-Stack IPv4 / IPv6 Device Heartbeat Engine

In addition to periodic CWMP Inform sessions, the Jio STB maintains active network reachability and NAT boundary tracking via a dedicated, dual-stack **Device Heartbeat Service**.

### 3.1 Endpoints & Path Structure
* **IPv4 Production:** `https://jiodeviceheartbeat-v4.jio.com/`
  * Gateway ping: `/v1/airfiber/stbhg` (AirFiber STB Home Gateway)
  * Residential ping: `/v2/home/stb`
* **IPv6 Production:** `https://jiodeviceheartbeat-v6.jio.com/`
  * Gateway ping: `/v1/airfiber/stbhg`
  * Residential ping: `/v2/home/stb`
* **Development / Staging:** `https://dev-jiodeviceheartbeat-v4.jio.com/`, `https://dev-jiodeviceheartbeat-v6.jio.com/`

### 3.2 Network Reachability & NAT Detection Mechanics
The heartbeat daemon reports:
1. Whether the device is behind carrier-grade NAT (CGNAT) or direct public IPv6 (`device is natted and previously not natted`).
2. Current physical connection type (Ethernet `eth0` vs Wi-Fi `wlan0`).
3. External gateway MAC, BSSID, and RSSI metrics.

---

## 4. Cryptographic Asset Audit & Private PKI Hierarchy

`TR069.apk` contains an entire embedded Public Key Infrastructure (PKI) suite, including internal root certificates, subordinate intermediate chains, and **full RSA private keys** utilized for mutual TLS (mTLS) authentication.

### 4.1 Extracted Certificate Tree

```
                       [CN=RILROOTCA]
               (Valid: 2009-10-14 to 2036-10-18)
               (Valid: 2024-08-06 to 2039-08-06)
                              │
             ┌────────────────┴────────────────┐
             ▼                                 ▼
    [CN=RILSUBCA01]             [CN=Jio Internal Root CA]
 (Enterprise Subordinate CA)                   │
             │                                 ▼
             ▼                   [CN=Jio Internal Server Sub CA]
     acs.oss.jio.com             OU=InfoSec, O=Jio Platforms Ltd
     (WildFly 10 Server)                       │
                                               ▼
                              [CN=jiodeviceheartbeat-v4.jio.com]
                              (Valid: 2024-05-07 to 2030-05-06)
```

### 4.2 Embedded Cryptographic Credentials Matrix
The following assets were recovered directly from `TR069.apk`:

| File Path in APK | Key Type / Subject | Expiration | Purpose |
| :--- | :--- | :--- | :--- |
| `assets/rootca.crt` | X.509 CA (`CN=RILROOTCA`) | 2039-08-06 | Root trust anchor for Jio internal enterprise infrastructure. |
| `assets/acs_oss_jio_com.cer` | X.509 CA (`CN=RILROOTCA`) | 2036-10-18 | Legacy root CA cert used to authenticate `acs.oss.jio.com`. |
| `assets/prod/jio_internal_server_sub_ca_chain.pem` | Intermediate X.509 Chain | 2035-03-26 | Issues mTLS server and client certificates for the heartbeat engine. |
| `assets/prod/jio_device_heartbeat_v4_jio_com_crt.pem` | Client Certificate (`CN=jiodeviceheartbeat-v4.jio.com`) | 2030-05-06 | Client certificate presented by the STB during mTLS handshake. |
| `assets/prod/v4_key.pem` | **RSA 2048-bit Private Key** | — | **Unencrypted private key** corresponding to the IPv4 client certificate. |
| `assets/prod/v6_key.pem` | **RSA 2048-bit Private Key** | — | **Unencrypted private key** corresponding to the IPv6 client certificate. |
| `assets/dev/dev_v4_key.pem` | RSA 2048-bit Private Key | — | Staging environment IPv4 client private key. |
| `assets/dev/dev_v6_key.pem` | RSA 2048-bit Private Key | — | Staging environment IPv6 client private key. |

---

## 5. Reverse-Engineered CWMP Vendor Extensions

Decompilation of `com.jio.tr069client` identified custom vendor extensions defined under the `Device.JioSTB.*` branch:

### 5.1 Remote ADB Activation Parameter
* **Parameter Path:** `Device.JioSTB.USB.USBDebugging`
* **Access Mode:** Read/Write (`Access = 1`)
* **Behavior:** When the ACS sends a `SetParameterValues` RPC with value `true`:
  1. The client calls `Settings.Global.putInt(getContentResolver(), "adb_enabled", 1)` utilizing privileged `WRITE_SECURE_SETTINGS` permission.
  2. Because `service.adb.tcp.port=5555` is pre-set in `vendor/build.prop`, the Android init daemon immediately binds `adbd` to `0.0.0.0:5555`.
  3. The client sets `Device.JioSTB.USB.DebugValidityDate` and schedules an `AlarmManager` wake-up 24 hours in the future to automatically toggle `adb_enabled` back to `0`.

### 5.2 Arbitrary Command Execution Subsystem
* **Parameter Path:** `Device.JioSTB.Debugging.Command.*`
* **Behavior:** Allows the ACS to inject arbitrary shell strings executed via `Runtime.getRuntime().exec()`.

### 5.3 Captive Portal Redirection
* Embedded within the network verification logic is an integration with Encapto CoovaChilli captive portal infrastructure:
  ```text
  https://e2.encapto.com/portal/coovachilli/2917/8596
  ```

---

## 6. On-Device TR-069 IPC & Broadcast Interface

The TR-069 client acts as a privileged central nervous system on Android TV, relaying commands from the cloud to local apps via Android Intents:

| Intent Action | Direction | Purpose | Target Components |
| :--- | :--- | :--- | :--- |
| `com.tr069.action.Create_New_Session` | Inbound | Forces the TR-069 client to immediately initiate an outbound CWMP session to ACS. | `TR069.apk` |
| `com.tr069.action.VendorConfigurationFileDownloaded` | Outbound | Fired when ACS pushes an updated vendor XML/JSON configuration file. | `ChatBot.apk`, `JioSettings.apk` |
| `com.tr069.action.BLOCKED_DC_EVENT_LIST` | Outbound | Pushes carrier-mandated application or package blocklists. | `JioLauncher.apk`, `JioSettings.apk` |
| `com.tr069.action.PACKAGE_REMOVED_DC_EVENTS` | Outbound | Instructs the system to purge or hide specific applications. | `JioLauncher.apk` |
| `com.tr069.action.RCU_CLEAR_CACHE`<br>`com.tr069.action.RCU_PAIR_BLOCK` | Outbound | Manages Bluetooth Remote Control Unit (RCU) pairing and state. | `JioRcuUpdate.apk`, `BTRemoteServer.apk` |
| `com.tr069.action.HOTSPOT_STATUS_CHANGED` | Outbound | Synchronizes Wi-Fi hotspot state with ACS policy. | `JioSettings.apk` |
| `com.jio.tr069.action.reboot_notify` | Outbound | Broadcast prior to remote ACS-triggered reboot. | `JioService.apk` |

---
## 🔗 Related Documents

| Related Document | Relationship |
| :--- | :--- |
| [`../TR069_ACS_RESEARCH.md`](../TR069_ACS_RESEARCH.md) | Deep research on CWMP/TR-069 ACS protocol mechanics, STB data model (TR-181/TR-135), security posture, and attack classes. |
| [`../TR069_REMOTE_ADB_ANALYSIS.md`](../TR069_REMOTE_ADB_ANALYSIS.md) | Decompilation of `TR069.apk`: `Device.JioSTB.USB.USBDebugging` remote ADB parameter and `Device.JioSTB.Debugging.Command.*` CLU subsystem (§5.1–5.2 cross-reference). |
| [`../NETWORK_ANALYSIS.md`](../NETWORK_ANALYSIS.md) | Observed ACS traffic to `acs.oss.jio.com:8443/9443` in §2.2. |
| [`01_TOPOLOGY_AND_NETWORK_TIERS.md`](01_TOPOLOGY_AND_NETWORK_TIERS.md) | ACS IP routing and AS55836 subnet allocation. |
| [`11_SECURITY_AUDIT_AND_ATTACK_SURFACE.md`](11_SECURITY_AUDIT_AND_ATTACK_SURFACE.md) | §2.4 — Rogue ACS hijacking and remote CWMP management attack surface. |

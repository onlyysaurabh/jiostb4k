# Reliance Jio Ecosystem Infrastructure — Technical Architecture & Research Map

> **Repository:** `/home/skylap/cybersec/jiostb4k/jio_infrastructure`  
> **Source Evidence:** 88 Dumped Privileged Android APKs, Live Gateway Interception (OpenWrt), Firmware Images (`loOOGaJIPm.zip`, `payload.bin`), Bootloaders, and Network PCAPs  
> **Target Fleet:** Jio Set-Top Boxes (JMSB200A, JHSD200, C200A), JioFiber ONTs (JCOW411, JCOW414, JCOW407, JCOW404), Jio AirFiber 5G (ODU/IDU), and JioBook  
> **Target Networks:** AS55836 (Reliance Jio Infocomm Ltd), AS16625 (Akamai Technologies), AS54113 (Fastly)

---

## 1. Executive Summary

This documentation repository provides a comprehensive, reverse-engineered map of Reliance Jio's multi-tiered service, provisioning, distribution, and telemetry infrastructure. 

The findings are synthesized from static analysis and decompilation of privileged system applications (`/system/priv-app`, `/system_ext/priv-app`, `/product/app`, `/vendor/app`), extracted firmware partition dumps (Android 11 A/B seamless streaming format), network traffic captures across live boot cycles, and active cryptographic asset audits (embedded X.509 certificates and private keys).

### Key Architectural Discoveries
1. **Multi-Domain TR-069 Management:** Jio operates three distinct CWMP Auto-Configuration Servers (`acs.oss.jio.com:8443` for STBs, `macs.oss.jio.com:8443` for JioBooks, and `iotacs.jioconnect.com:8080/8001` for residential gateways and IoT).
2. **Dual-Stack IPv4 / IPv6 Device Heartbeats:** Devices report real-time connectivity and NAT states to `jiodeviceheartbeat-v4.jio.com` and `jiodeviceheartbeat-v6.jio.com` using mutual TLS (mTLS) with client certificates and private keys bundled directly in system APKs.
3. **FOTA CDN Architecture & Hardware Matrix:** Firmware distribution is split into master datacenter origins (`fota.mst.kai.jiophone.net` on AS55836) and edge caches (`fota.slv.kai.jiophone.net` for tokenized modern builds, `fota.slv.fxd.jiophone.net` for open predictable firmware zips). Over 25 unique hardware generation tags (`DIN59` through `DIN1009`) across Skyworth, SDMC, Bluebank, and Arcadyan were identified.
4. **Unencrypted Internal Backend Proxies:** Direct internal PHP proxies operating on cleartext HTTP port 6080 (`http://49.40.64.244:6080/proxy.api.php`, `/proxy.mads.php`, `/proxy.vapi.php`) are invoked by system applications like `JioStore.apk` and `JioVoice.apk`.
5. **Linear TV & Unicast DRM Key Exchange:** Real-time IPTV multicast and unicast channels are orchestrated through `ucast-key.iptv.jio.com` (unicast encryption key service), `jiotv.data.cdn.jio.com` (EPG & cloud DVR), and Fastly edge nodes for UI rendering.
6. **Magnum Analytics & Mercury Ad Engine:** Telemetry is concentrated through the Magnum platform (`devents.magnum.jio.com` and `fcmr.magnum.jio.com`), while programmatic video and banner advertising are dispatched through the Mercury platform (`mercury.jio.com`, `mercury-ck.jio.com`).

---

## 2. High-Level Ecosystem Topology

```mermaid
flowchart TD
    subgraph CPE["Customer Premises Equipment (STB Fleet)"]
        STB["Jio 4K STB (JMSB200A)<br/>Android TV 11 / Amlogic S905X4"]
        NANO["NanoHTTPD (Port 54321)<br/>JioHttpUpdate.apk"]
        ADB["Network ADB (Port 5555)<br/>service.adb.tcp.port=5555"]
        SDKD["sdknativeservice (root uid 0)<br/>com.jio.sdk.sdknativeservice"]
        LANBEACON["UDP Broadcast (Port 5775)<br/>JioHome Pairing Beacon"]
    end

    subgraph CDN_TIER["Edge Content Delivery Networks (Akamai & Fastly)"]
        FOTA_KAI["fota.slv.kai.jiophone.net<br/>(Akamai NetStorage 104.96.177.202)<br/>Tokenized FOTA Builds"]
        FOTA_FXD["fota.slv.fxd.jiophone.net<br/>(Akamai Edge 184.27.197.10)<br/>Open Legacy Recovery Packages"]
        FASTLY_UI["*.cdn.jio.com (Fastly 167.82.58.144)<br/>Launcher Posters & EPG Thumbnails"]
        JIO_TV_CDN["jiotv.data.cdn.jio.com<br/>jiotv.catchup.cdn.jio.com<br/>Linear Streams & Catchup Segments"]
        MERCURY_CDN["mercury.akamaized.net<br/>jioads.akamaized.net<br/>Ad Payloads & Tracking Pixels"]
        VOICE_CDN["jiova.akamaized.net<br/>Dynamic Config & pl.gif Beacon"]
    end

    subgraph JIO_CORE["Reliance Jio Core AS55836 Infrastructure"]
        ACS["Auto-Configuration Server (ACS)<br/>acs.oss.jio.com:8443 (WildFly 10)<br/>macs.oss.jio.com / iotacs.jioconnect.com"]
        HEARTBEAT["Dual-Stack Heartbeat Engine<br/>jiodeviceheartbeat-v4.jio.com<br/>jiodeviceheartbeat-v6.jio.com"]
        ORIGIN_FOTA["Master Origin FOTA<br/>fota.mst.kai.jiophone.net<br/>(49.40.21.37 / 49.40.21.52)"]
        CORE_API["Core API & Identity Gateway<br/>api.jio.com (103.63.129.21 F5 BigIP)<br/>api-bs.jio.com / jioid.jio.com"]
        IPTV_DRM["IPTV Key Management<br/>ucast-key.iptv.jio.com<br/>Linear Decryption Keys"]
        MAGNUM["Magnum Telemetry Engine<br/>devents.magnum.jio.com<br/>fcmr.magnum.jio.com"]
        MERCURY["Mercury Ad Exchange<br/>mercury.jio.com / mercury-ck.jio.com<br/>Targeting & Attribution Engine"]
        INTERNAL_PHP["Direct IP PHP Proxy<br/>49.40.64.244:6080<br/>Cleartext Unencrypted APIs"]
        INTERNAL_SOE["Speech Output Engine (SOE)<br/>49.40.64.194:8124<br/>Cleartext TTS & Biometric Reset"]
    end

    STB -->|CWMP / TR-069 (Mutual TLS)| ACS
    STB -->|IPv4/IPv6 Ping (mTLS)| HEARTBEAT
    STB -->|Cleartext HTTP GET| FOTA_KAI
    STB -->|Cleartext HTTP GET| FOTA_FXD
    STB -->|HTTPS JSON/Images| FASTLY_UI
    STB -->|HTTPS HLS/EPG| JIO_TV_CDN
    STB -->|HTTPS Telemetry| MAGNUM
    STB -->|HTTPS Ads/Impressions| MERCURY
    STB -->|Cleartext HTTP (Proxy)| INTERNAL_PHP
    STB -->|Cleartext HTTP (TTS/SRS)| INTERNAL_SOE
    STB -->|HTTP/HTTPS Dynamic Config & Beacon| VOICE_CDN
    STB -->|HTTPS OAuth/Entitlements| CORE_API
    STB -->|HTTPS DRM License| IPTV_DRM

    FOTA_KAI -.->|Origin Sync| ORIGIN_FOTA
    FOTA_FXD -.->|Origin Sync| ORIGIN_FOTA
```

---

## 3. Structured Documentation Index

The research documentation is structured into the following modules:

| Document | Scope & Focus Areas |
| :--- | :--- |
| **[`01_TOPOLOGY_AND_NETWORK_TIERS.md`](01_TOPOLOGY_AND_NETWORK_TIERS.md)** | Autonomous System routing (AS55836, AS16625, AS54113), IP address blocks, IPv6 prefixes, DNS canonical name resolution chains, and on-net ISP caching architectures. |
| **[`02_DEVICE_MANAGEMENT_TR069_ACS.md`](02_DEVICE_MANAGEMENT_TR069_ACS.md)** | CWMP TR-069 server clusters (`acs.oss.jio.com`, `macs`, `iotacs`), dual-stack IPv4/IPv6 heartbeats, private PKI certificate hierarchies (`RILROOTCA`, `Jio Internal Server Sub CA`), embedded client private keys, and TR-181 data model extensions. |
| **[`03_FOTA_AND_FIRMWARE_DISTRIBUTION.md`](03_FOTA_AND_FIRMWARE_DISTRIBUTION.md)** | Firmware distribution CDN tiers, tokenized hash generation, reverse-engineered device taxonomy (25+ hardware codes across Skyworth, SDMC, Bluebank), verified live firmware downloads, and on-device flashing via `JioHttpUpdate.apk`. |
| **[`04_CORE_AUTH_SSO_AND_USER_MANAGEMENT.md`](04_CORE_AUTH_SSO_AND_USER_MANAGEMENT.md)** | Subscriber profile verification (`/ftth/v2/users/me`), Single Sign-On broker (`jioid.jio.com`, `signup.jio.com`), media authentication (`auth.media.jio.com`), and OTT partner token issuance (Netflix PADI integration). |
| **[`05_IPTV_LIVETV_EPG_AND_DRM.md`](05_IPTV_LIVETV_EPG_AND_DRM.md)** | Linear IPTV stream delivery, unicast DRM key server (`ucast-key.iptv.jio.com`), electronic program guide (EPG) metadata APIs, catchup TV infrastructure, and DVB-IP/CATV broadcast subsystem. |
| **[`06_TELEMETRY_ANALYTICS_AND_PUSH.md`](06_TELEMETRY_ANALYTICS_AND_PUSH.md)** | Magnum telemetry platform (`devents.magnum.jio.com`), real-time voice usage web beacons (`https://jiova.akamaized.net/.../pl.gif?`), FCM notification routers (`fcmr.magnum.jio.com`), push delivery gateways (`auth.push.jio.com`), and the on-device ADC (`JioAdc.apk`, `AKA.apk`, `PODLogService.apk`) logging pipeline. |
| **[`07_ADTECH_MERCURY_AND_MONETIZATION.md`](07_ADTECH_MERCURY_AND_MONETIZATION.md)** | Mercury programmatic ad engine (`mercury.jio.com`), campaign distribution JSONs, impression/click attribution (`mercury-ck.jio.com`), JioCinema ad tracking (`moloco`), and edge beacon networks. |
| **[`08_VOICE_AI_AND_HELLOMODELS.md`](08_VOICE_AI_AND_HELLOMODELS.md)** | HelloJio virtual assistant stack, Reverie Language Technologies embedded offline edge ASR for linear TV channel switching, direct datacenter Speech Output Engine backends (`49.40.64.194:8124`), dynamic Akamai config CDN (`va-stb-config.json`), real-time usage web beacons (`pl.gif`), production voice biometric routing flaw, and BLE voice remote pairing. |
| **[`09_DIRECT_IPS_INTERNAL_AND_LAN_DAEMONS.md`](09_DIRECT_IPS_INTERNAL_AND_LAN_DAEMONS.md)** | Internal unencrypted PHP proxy backend (`49.40.64.244:6080`), direct datacenter Speech Output Engine & biometric reset node (`49.40.64.194:8124`), local UDP discovery beacons (5775/UDP), root daemon (`sdknativeservice`), NanoHTTPD web server (54321/TCP), and network ADB (5555/TCP). |
| **[`10_PRIVILEGED_APKS_AND_IPC_CATALOG.md`](10_PRIVILEGED_APKS_AND_IPC_CATALOG.md)** | Exhaustive technical catalog of all 88 extracted system packages, declared Android permissions, AIDL interfaces, internal BroadcastReceiver actions, and system services. |
| **[`11_SECURITY_AUDIT_AND_ATTACK_SURFACE.md`](11_SECURITY_AUDIT_AND_ATTACK_SURFACE.md)** | Holistic security evaluation covering plaintext transport vulnerabilities, unencrypted datacenter IP routing bugs, hardcoded cryptographic key exposures, CWMP remote control risks, local network exposures, and strategic research roadmaps. |
| **[`12_HARDWARE_BOOT_AND_TRUSTZONE_INFRA.md`](12_HARDWARE_BOOT_AND_TRUSTZONE_INFRA.md)** | Hardware Root-of-Trust, Amlogic eFUSE, OP-TEE TrustZone architecture, factory key injection (`tee_key_inject`, `tee_provision`), Verimatrix CAS, and Sony CXD2856 tuner frontend. |
| **[`13_NETWORK_TRUST_AND_SELINUX_ARCHITECTURE.md`](13_NETWORK_TRUST_AND_SELINUX_ARCHITECTURE.md)** | Analysis of 138 system CA root certs, isolation of Reliance internal CAs from AOSP, and compiled SELinux policy audit (`sdknativeservice`, `tee`, `adbd` port 5555 binding). |
| **[`ENDPOINTS_REFERENCE.json`](ENDPOINTS_REFERENCE.json)** | Machine-readable, categorized inventory of all unique endpoints and distinct hosts mapped to their originating system applications. |

---

## 4. Hardware Ecosystem Taxonomy

The extracted system applications confirm that Reliance Jio deploys a unified core Android TV codebase across multiple OEM hardware designs:

```
                                  Reliance Jio Customer Fleet
                                               │
         ┌────────────────────────┬────────────┴───────────┬────────────────────────┐
         ▼                        ▼                        ▼                        ▼
  Hybrid 4K STBs            Legacy STBs             JioFiber ONTs            AirFiber 5G CPE
  ───────────────           ───────────             ─────────────            ───────────────
  • Skyworth JMSB200A       • Droidlogic JHSD200    • Arcadyan JCOW411       • Outdoor Unit (UDO/DIN520)
  • SDMC C200A              • Skyworth JHSB200      • Sercomm JCOW414        • Indoor Unit (UDI)
  • Bluebank C200A          • Skyworth JHSC200      • Skyworth JCOW407       • 5G NR Fixed Wireless
  (SoC: Amlogic S905X4)     (SoC: Amlogic S905X2)   • Sercomm JCOW404
```

---

## 5. Methodology & Verification

All infrastructure endpoints and architectural relationships documented herein have been verified through at least one of the following methods:
- **DEX Bytecode Decompilation:** Using JADX and Baksmali to decompile class bytecode from privileged system packages dumped directly from the official Android 11 OTA payload (`loOOGaJIPm.zip`).
- **Binary Dynamic Disassembly:** Analyzing native shared objects (`.so`) and ELF executables (`sdknativeservice`, `libirInfo.so`) using Ghidra and `nm` / `readelf`.
- **Live Gateway Interception:** Capturing unencrypted and encrypted DNS/HTTP/TLS flows on an OpenWrt router (`br-lan` interface) during live device boot cycles, idle periods, and software update queries.
- **Cryptographic Certificate Inspection:** Extracting X.509 certificates and PEM keys using OpenSSL to verify subject common names, certificate authority hierarchies, validity periods, and key usage constraints.

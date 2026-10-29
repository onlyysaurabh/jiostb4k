# 01. Network Topology, Autonomous Systems & Routing Tiers

> **Parent Topic:** [`jio_infrastructure/README.md`](README.md)  
> **Target Networks:** AS55836 (Reliance Jio), AS16625 (Akamai Technologies), AS54113 (Fastly), AS17665 (ISP On-Net Partner)

---

## 1. Network Architecture Overview

Reliance Jio operates a hybrid network architecture for its subscriber devices (Set-Top Boxes, ONT routers, 5G AirFiber CPEs). Traffic is partitioned into two distinct paths:
1. **Core Data Center Traffic (Jio On-Net AS55836):** Direct connections into Jio's private cloud and core datacenter facilities for device provisioning, mutual-TLS device heartbeats, subscriber identity verification, and internal proxy services.
2. **Edge CDN Distribution (Akamai & Fastly):** Large payload distribution (firmware images, system APK packages, streaming HLS segments) and low-latency assets (UI thumbnails, EPG listings, ads) offloaded to global Content Delivery Networks.

```
                      ┌──────────────────────────────────────────────┐
                      │          Subscriber Home Network             │
                      │       Jio 4K STB (192.168.2.137)             │
                      └──────────────────────┬───────────────────────┘
                                             │
                                  Gateway Router / OpenWrt
                                             │
             ┌───────────────────────────────┴───────────────────────────────┐
             │                                                               │
             ▼                                                               ▼
 ┌───────────────────────────────┐                               ┌───────────────────────────────┐
 │   Jio Core Network (AS55836)  │                               │    Edge Content Delivery CDNs  │
 ├───────────────────────────────┤                               ├───────────────────────────────┤
 │ • 49.40.8.93   (TR-069 ACS)   │                               │ • Akamai NetStorage           │
 │ • 49.40.21.37  (Master FOTA)  │                               │   (104.96.177.202, 184.27.x.x)│
 │ • 49.40.48.224 (Bootstrap BS) │                               │ • Fastly Edge                 │
 │ • 49.40.64.244 (PHP Proxy)    │                               │   (167.82.58.144)             │
 │ • 103.63.129.21 (api.jio.com) │                               │ • In-ISP On-Net Cache         │
 │ • [2405:200:1602:1174::8]     │                               │   (203.192.234.147 / .153)    │
 └───────────────────────────────┘                               └───────────────────────────────┘
```

---

## 2. Autonomous Systems & IP Subnet Allocation

### 2.1 AS55836 — Reliance Jio Infocomm Limited
Jio’s core network routes all sensitive management, provisioning, and internal proxy traffic.

| IP / Subnet | Reverse DNS / Hostname | Function | Transport & Ports | TLS / Security Profile |
| :--- | :--- | :--- | :--- | :--- |
| `49.40.8.93` | `acs.oss.jio.com` | Primary STB TR-069 Auto-Configuration Server (ACS) | TCP 8443, 9443 | Enterprise TLS (`CN=acs.oss.jio.com`, Issuer: `CN=RILSUBCA01`). WildFly 10 / JBoss. |
| `49.40.48.28` | `sftp.telematics.jio.com` | Internal Carrier SFTP Telematics & Logcat Repository | TCP 22 (SSH/SFTP) | In-path carrier firewalled; static credentials (`va`/`V@13ji@o`); host verification bypassed. |
| `49.40.48.224` | `bs.jio.com` | Bootstrap Services (discovery and service endpoint resolution) | TCP 443 | Standard TLS (`CN=bs.jio.com`, SANs: `admin-bs`, `api-bs`, `ec-bs`). Apache HTTP Server. |
| `49.40.21.37`<br>`49.40.21.52`<br>`49.40.21.202` | `fota.mst.kai.jiophone.net`<br>`api.kai.jiophone.net` | Master Origin Repository for FOTA updates | TCP 80, 443 | Internal repository synchronizing packages to Akamai edge storage nodes. |
| `49.40.64.244` | *(No PTR Record)* | Internal PHP API / Microservices Gateway | TCP 6080 | **Cleartext HTTP**. Hosts `/proxy.api.php`, `/proxy.mads.php`, `/proxy.vapi.php`, `/sit.api.php`. |
| `103.63.129.21` | `api.jio.com` | Primary Subscriber Authentication & Entitlement API | TCP 443 | Standard TLS (`CN=api.jio.com`, Reliance Industries Ltd). Fronted by F5 BigIP ADC. |
| `2405:200:1602:1174::8` | *(IPv6 Core)* | Direct IPv6 Backend Node | TCP 443 | Referenced in `JioService.apk` for carrier telemetry and IPv6 device sync. |

---

### 2.2 AS16625 / AS20940 — Akamai Technologies
Akamai is Jio's primary partner for high-bandwidth software delivery, system applications, and static UI assets.

| Hostname / Edge IP | Canonical Name (CNAME Chain) | Function | Edge Server Banner |
| :--- | :--- | :--- | :--- |
| `fota.slv.kai.jiophone.net`<br>(`104.96.177.202`) | `fota.slv.kai.jiophone.net` → `fota.slv.kai.jiophone.net-v1.edgekey.net` → `fota.slv.kai.jiophone.net-v1.splitter-eip.akadns.net` → `104.96.177.202` | Modern tokenized OTA update server (Android 11 OS payloads). | `Server: AkamaiNetStorage`<br>`Server: AkamaiGHost` (on 403 Forbidden) |
| `fota.slv.fxd.jiophone.net`<br>(`184.27.197.10 / .91`) | `fota.slv.fxd.jiophone.net` → `fota.slv.fxd.jiophone.net.akamaized.net` → `a108.dscd.akamai.net` → `184.27.197.10` | Open legacy repository for STB recovery zips and ONT router firmware images. | `Server: AkamaiNetStorage` |
| `jiostb.cdn.jio.com`<br>`jiostb.akamaized.net` | `jiostb.cdn.jio.com` → `jiostb.akamaized.net` → `a1887.dscq.akamai.net` | Hybrid STB Hotel build updates (`/stbv/rjio_hybrid_skyworth_a11_ota...zip`). | `Server: AkamaiNetStorage` |
| `jiotv.data.cdn.jio.com` | `jiotv.data.cdn.jio.com.akamaized.net` | EPG schedules, channel configurations, and Cloud DVR service definitions. | `Server: AkamaiNetStorage` |
| `mercury.akamaized.net`<br>`jioads.akamaized.net` | `mercury.akamaized.net` → `a1873.dscd.akamai.net` | Campaign JSON definitions, targeting configurations, and tracking pixels (`/beacon/anb.gif`). | `Server: AkamaiGHost` |
| `halojio.akamaized.net`<br>`jiova.akamaized.net` | `halojio.akamaized.net` | HelloJio Voice Assistant web portal assets, legal disclosures, and sound assets. | `Server: AkamaiNetStorage` |

---

### 2.3 AS54113 — Fastly, Inc.
Fastly provides high-frequency, low-latency edge caching for dynamic Android TV launcher components.

| Hostname / Edge IP | Canonical Chain | Characteristics | Primary Function |
| :--- | :--- | :--- | :--- |
| `*.cdn.jio.com`<br>(`167.82.58.144`) | `cdn.jio.com` → Fastly Anycast POP | TLS Subject: `CN=*.cdn.jio.com` (GlobalSign Atlas TLS CA). Rapid bursts of 40+ concurrent TCP flows. | Delivers channel thumbnails, EPG preview banners, carousel posters, and launcher layout JSONs. |

---

### 2.4 AS17665 — In-ISP Partner On-Net Edge Nodes
To optimize bandwidth, Akamai deploys Accelerated Network Partner (ANP / AISP) caching hardware directly within residential ISPs (such as OneBroadband / In2cable):

- **Hostnames:** `dhcp-192-234-153.in2cable.com`, `dhcp-192-234-147.in2cable.com`
- **Resolved IPs:** `203.192.234.153`, `203.192.234.147`
- **TLS Identity:** `CN=a248.e.akamai.net` (Akamai Technologies)
- **Role:** Requests originating from the Jio STB to Akamai-hosted HTTPS endpoints are resolved via GeoDNS to these on-net nodes within the ISP’s local metropolitan routing area, bypassing transit backbones.

---

## 3. DNS Resolution Topology & CNAME Chaining

Static analysis of system applications reveals extensive use of Akamai and Fastly CDN aliases. Below is the verified CNAME resolution mapping:

```
fota.slv.kai.jiophone.net
 └─> fota.slv.kai.jiophone.net-v1.edgekey.net
      └─> fota.slv.kai.jiophone.net-v1.splitter-eip.akadns.net
           └─> eip-terr-as.fota.slv.kai.jiophone.net-v1.akahost.net
                └─> 104.96.177.202 (Akamai AS16625)

fota.slv.fxd.jiophone.net
 └─> fota.slv.fxd.jiophone.net.akamaized.net
      └─> a108.dscd.akamai.net
           └─> 184.27.197.10 / 184.27.197.91 (Akamai AS16625)

mercury.akamaized.net
 └─> a1873.dscd.akamai.net
      └─> 23.218.212.x / 104.96.x.x

api.jio.com
 └─> 103.63.129.21 (Direct Jio Datacenter AS55836 / F5 BigIP)

acs.oss.jio.com
 └─> 49.40.8.93 (Direct Jio Datacenter AS55836)
```

---

## 4. Port & Transport Protocol Matrix

| Port | Transport | Service / Daemon | Endpoints | Authentication / Encryption |
| :--- | :--- | :--- | :--- | :--- |
| **80** | TCP | Cleartext HTTP | `fota.slv.kai.jiophone.net`, `fota.slv.fxd.jiophone.net`, `104.96.177.202` | **None**. Integrity validated solely via OEM RSA/ECDSA signature checks on payload files. |
| **443** | TCP | Standard HTTPS / TLS | `api.jio.com`, `bs.jio.com`, `jioid.jio.com`, `*.cdn.jio.com`, `devents.magnum.jio.com` | Public CA TLS (GlobalSign, DigiCert, Google Trust Services). |
| **8443** | TCP | Enterprise CWMP TR-069 | `acs.oss.jio.com:8443`, `macs.oss.jio.com:8443` | **Mutual/Enterprise TLS** (`RILSUBCA01`, `RILROOTCA`). CWMP SOAP RPC over HTTP-Digest. |
| **9443** | TCP | Secondary CWMP TR-069 | `acs.oss.jio.com:9443` | Alternate port for batch parameter telemetry and scheduled Inform sessions. |
| **8080 / 8001** | TCP | IoT CWMP & FOTA | `iotacs.jioconnect.com:8080`, `iotacs.jioconnect.com:8001` | Cleartext HTTP Digest CWMP (`/ftacs-digest/ACS`) and firmware image downloads. |
| **6080** | TCP | Internal PHP Proxy | `49.40.64.244:6080` | **Cleartext HTTP**. No TLS; unauthenticated internal endpoints. |
| **54321** | TCP | Local NanoHTTPD Portal | `127.0.0.1:54321` / `<STB_LAN_IP>:54321` | Built-in HTTP server in `JioHttpUpdate.apk`. Protected by 8-digit on-screen PIN. |
| **5555** | TCP | Local Network ADB | `0.0.0.0:5555` | Android Debug Bridge network socket bound by `adbd` when `service.adb.tcp.port=5555` is active. |
| **5775** | UDP | JioHome Discovery | `192.168.x.255:5775` | Local subnet UDP broadcast beacon for smartphone app pairing. |

---
## 🔗 Related Documents

| Related Document | Relationship |
| :--- | :--- |
| [`../NETWORK_ANALYSIS.md`](../NETWORK_ANALYSIS.md) | Observed live traffic and endpoint categorization for the ASes, IPs, and CDN edges mapped here. |
| [`02_DEVICE_MANAGEMENT_TR069_ACS.md`](02_DEVICE_MANAGEMENT_TR069_ACS.md) | ACS server IP routing (`acs.oss.jio.com` `49.40.8.93`, `macs`, `iotacs`) within AS55836. |
| [`03_FOTA_AND_FIRMWARE_DISTRIBUTION.md`](03_FOTA_AND_FIRMWARE_DISTRIBUTION.md) | CDN tiers (Akamai/Fastly edge nodes) and FOTA distribution topology. |
| [`../FIRMWARE_ENDPOINTS_AND_EXPOSURES.md`](../FIRMWARE_ENDPOINTS_AND_EXPOSURES.md) | FOTA endpoint URL taxonomy and verified live firmware catalog. |

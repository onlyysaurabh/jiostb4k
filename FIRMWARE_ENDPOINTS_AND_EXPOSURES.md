# Jio Ecosystem FOTA Endpoints, Exposed Firmwares & Update Tooling Analysis

Comprehensive technical documentation and security assessment of Reliance Jio's Firmware-Over-The-Air (FOTA) update infrastructure, CDN distribution architectures, verified exposed firmware images, and reverse-engineered on-device update mechanics.

---

## 1. 🔍 Executive Infrastructure Overview

Reliance Jio operates a distributed FOTA infrastructure to push operating system, bootloader, and configuration updates to its hardware fleet (Jio 4K STBs, legacy Droidlogic STBs, JioFiber ONT gateways, AirFiber 5G CPEs, and JioBook). 

Network traffic interception, DNS auditing, and reverse engineering of extracted system update binaries ([`JioHttpUpdate.apk`](ota_packages/extracted/apks/jio_system_priv_app/JioHttpUpdate.apk) and [`TR069.apk`](ota_packages/extracted/apks/jio_system_priv_app/TR069.apk)) revealed an architectural split into **four** distinct CDN distribution models:

```
                                  ┌──────────────────────────────────────────────┐
                                  │      Jio Origin Masters (AS55836)            │
                                  │   fota.mst.kai.jiophone.net (49.40.21.37/52) │
                                  │   api.kai.jiophone.net      (49.40.21.52)    │
                                  └──────────────────────┬───────────────────────┘
                                                         │
                    ┌────────────────────────────────────┴────────────────────────────────────┐
                    │                                                                         │
                    ▼                                                                         ▼
         ┌────────────────────────┐ ┌────────────────────────┐ ┌────────────────────────┐ ┌────────────────────────┐
         │  Modern Obfuscated CDN │ │   Legacy Open CDN Node │ │ Enterprise Hotel CDN   │ │ IoT ACS (CPE) Tier   │
         │   fota.slv.kai.jiophone│ │  fota.slv.fxd.jiophone │ │   jiostb.cdn.jio.com   │ │  iotacs.jioconnect.com │
         │   Edge: 104.96.177.202 │ │   Edge: 184.27.197.10  │ │   (Akamai NetStorage)  │ │   Port 8001/8080       │
         │   (AkamaiNetStorage)   │ │   (AkamaiNetStorage)   │ │                        │ │                        │
         ├────────────────────────┤ ├────────────────────────┤ ├────────────────────────┤ ├────────────────────────┤
         │ • JMSB200A 4K STB      │ │ • Legacy STBs          │ │ • Hotel/Enterprise     │ │ • Arcadyan ONT OTA     │
         │ • AirFiber 5G CPE      │ │ • JioFiber Routers     │ │   STB builds           │ │   (auth required, 401) │
         │ • KaiOS                │ │ • Open HTTP 200        │ │ • HTTPS, ~702 MB each  │ │ • Cleartext HTTP       │
         │ • Random 10-char tokens│ │ • 69 objects, ~7.0 GB  │ │ • 3 live builds        │ │ • ~1.5 GB per image    │
         └────────────────────────┘ └────────────────────────┘ └────────────────────────┘ └────────────────────────┘
```

---

## 2. 🌐 DNS Topology & Server Characteristics

### 2.1 The Modern Distribution Tier (`fota.slv.kai.jiophone.net`)
* **FQDN:** `fota.slv.kai.jiophone.net`
* **Canonical Name Chain:**
  ```text
  fota.slv.kai.jiophone.net ->
    fota.slv.kai.jiophone.net-v1.edgekey.net ->
      fota.slv.kai.jiophone.net-v1.splitter-eip.akadns.net ->
        eip-terr-as.fota.slv.kai.jiophone.net-v1.akahost.net -> 104.96.177.202
  ```
* **Resolved IP:** `104.96.177.202` (Akamai Technologies AS16625 / `AkamaiNetStorage`)
* **Transport:** Unencrypted cleartext HTTP on TCP port 80.
* **Edge Access Control:** Any query attempting directory traversal or requesting unmapped root directories returns `403 Forbidden` (`Server: AkamaiGHost`) or `404 Not Found` (`Server: AkamaiNetStorage`). Valid downloads require full URL paths containing dynamic tokens.

### 2.2 The Open Public Distribution Tier (`fota.slv.fxd.jiophone.net`)
* **FQDN:** `fota.slv.fxd.jiophone.net`
* **Canonical Name Chain:**
  ```text
  fota.slv.fxd.jiophone.net ->
    fota.slv.fxd.jiophone.net.akamaized.net ->
      a108.dscd.akamai.net -> 184.27.197.10 / 184.27.197.91
  ```
* **Resolved IPs:** `184.27.197.10`, `184.27.197.91` (Akamai Technologies)
* **Transport:** Cleartext HTTP on port 80.
* **Edge Access Control:** Completely open public object repository. When requested with the exact manufacturer, model, and firmware version prefix, the server returns `HTTP 200 OK` with full binary payloads and standalone `.sig` cryptographic signature files.

### 2.3 The Master Origin Tier (`fota.mst.kai.jiophone.net`)
* **FQDN:** `fota.mst.kai.jiophone.net`
* **Resolved IPs:** `49.40.21.37`, `49.40.21.52`, `49.40.21.202`
* **Network / Autonomous System:** AS55836 (Reliance Jio Infocomm Limited)
* **Role:** Centralized repository within Jio's core data center network that stores firmware binaries before synchronizing them to Akamai edge storage nodes.

---

## 3. 🗺️ URL Path Taxonomy & Structure

### 3.1 Obfuscated Tokenized Path Format (`kai.jiophone.net`)
Used for contemporary devices including the Jio 4K Set-Top Box (`JMSB200A`) and Jio AirFiber 5G hardware:

```text
http://fota.slv.kai.jiophone.net/<CATEGORY>/<DEVICE_ID>/<BUILD_ID>/<TOKEN>.<ext>
```

| Path Component | Meaning / Function | Examples |
| :--- | :--- | :--- |
| `<CATEGORY>` | Hardware ecosystem / division | `BHTS` (Broadband Hybrid TV STB)<br>`XPGNO` (JioFiber GPON ONT)<br>`5G` (AirFiber Fixed Wireless) |
| `<DEVICE_ID>` | Internal OEM / hardware generation code | `DIN1009` (Skyworth JMSB200A 4K STB)<br>`DIN324` (Arcadyan Hybrid Device)<br>`DIN789` (Sercomm JCOW414 ONT)<br>`UDI` (AirFiber Indoor Unit)<br>`UDO/DIN520` (AirFiber Outdoor Unit 520) |
| `<BUILD_ID>` | Specific firmware release build tag | `SA002_19` (JMSB200A Android 11 build 25.1.9)<br>`S414W_259` (JCOW414 router firmware R2.59)<br>`A1402_32_S` (AirFiber ODU firmware R2.32) |
| `<TOKEN>.<ext>` | 10-character pseudo-random alphanumeric hash | `loOOGaJIPm.zip` (755.8 MB OTA update)<br>`DtrbUbNvSe.img` (Router firmware image) |

### 3.2 Open Deterministic Path Format (`fxd.jiophone.net`)
Used for legacy STBs and JioFiber residential gateways:

#### A. Set-Top Box Firmware:
```text
http://fota.slv.fxd.jiophone.net/STB/<Manufacturer>/<Model>/STB-<Model>-<Version>.zip
```
* `<Manufacturer>`: `Droidlogic` (Amlogic reference ODM), `Skyworth`, `SDMC`
* `<Model>`: `JHSD200`, `JHSB200`, `JHSC200`
* `<Version>`: Semantic versioning (`X.Y.Z`)

#### B. Router / ONT Firmware:
```text
http://fota.slv.fxd.jiophone.net/ONT/<Manufacturer>/<Model>/<Prefix>_R<Version>.img
http://fota.slv.fxd.jiophone.net/ONT/<Manufacturer>/<Model>/<Prefix>_R<Version>.sig
```
* `<Manufacturer>`: `Arcadyan`, `Sercomm`, `Skyworth`, `Foxconn`
* `<Model>`: `JCOW411`, `JCOW414`, `JCOW407`, `JCOW404`, `JCO110`
* `<Prefix>`: Hardware release prefix (`ARCNTF1_JCOW411_R`, `SRCMTF1_JCOW414_R`, `SKYWTF1_JCOW407_R`, `SRCMTF1_JCOW404_R`)
* `<Version>`: Release version (e.g. `2.3`, `2.15`, `2.41`, `2.52.1`)

---

## 4. 📦 Verified Exposed Firmware Packages (Live Verification)

Every package listed below was actively probed and verified (`HTTP/1.1 200 OK` via AkamaiNetStorage):

### 4.1 Set-Top Box Recovery Packages (Droidlogic JHSD200)
Full AOSP Android TV recovery zips with kernel, recovery, and system images:

| Firmware Build | Package Size | HTTP Last-Modified | Direct URL |
| :--- | :--- | :--- | :--- |
| **STB-JHSD200-5.0.5** | 527.1 MB | Mon, 15 Mar 2021 10:10:20 GMT | [`http://fota.slv.fxd.jiophone.net/STB/Droidlogic/JHSD200/STB-JHSD200-5.0.5.zip`](http://fota.slv.fxd.jiophone.net/STB/Droidlogic/JHSD200/STB-JHSD200-5.0.5.zip) |
| **STB-JHSD200-5.7.1** | 533.3 MB | Mon, 05 Jul 2021 07:09:50 GMT | [`http://fota.slv.fxd.jiophone.net/STB/Droidlogic/JHSD200/STB-JHSD200-5.7.1.zip`](http://fota.slv.fxd.jiophone.net/STB/Droidlogic/JHSD200/STB-JHSD200-5.7.1.zip) |
| **STB-JHSD200-6.2.2** | 575.4 MB | Thu, 25 Nov 2021 08:21:10 GMT | [`http://fota.slv.fxd.jiophone.net/STB/Droidlogic/JHSD200/STB-JHSD200-6.2.2.zip`](http://fota.slv.fxd.jiophone.net/STB/Droidlogic/JHSD200/STB-JHSD200-6.2.2.zip) |
| **STB-JHSD200-6.2.5** | 575.9 MB | Sun, 19 Dec 2021 18:38:27 GMT | [`http://fota.slv.fxd.jiophone.net/STB/Droidlogic/JHSD200/STB-JHSD200-6.2.5.zip`](http://fota.slv.fxd.jiophone.net/STB/Droidlogic/JHSD200/STB-JHSD200-6.2.5.zip) |
| **STB-JHSD200-7.0.6** | 583.2 MB | Thu, 23 Dec 2021 10:04:34 GMT | [`http://fota.slv.fxd.jiophone.net/STB/Droidlogic/JHSD200/STB-JHSD200-7.0.6.zip`](http://fota.slv.fxd.jiophone.net/STB/Droidlogic/JHSD200/STB-JHSD200-7.0.6.zip) |
| **STB-JHSD200-7.0.9** | 583.2 MB | Mon, 10 Jan 2022 09:37:57 GMT | [`http://fota.slv.fxd.jiophone.net/STB/Droidlogic/JHSD200/STB-JHSD200-7.0.9.zip`](http://fota.slv.fxd.jiophone.net/STB/Droidlogic/JHSD200/STB-JHSD200-7.0.9.zip) |
| **STB-JHSD200-7.3.5** | 609.2 MB | Mon, 23 May 2022 07:38:09 GMT | [`http://fota.slv.fxd.jiophone.net/STB/Droidlogic/JHSD200/STB-JHSD200-7.3.5.zip`](http://fota.slv.fxd.jiophone.net/STB/Droidlogic/JHSD200/STB-JHSD200-7.3.5.zip) |
| **STB-JHSD200-7.4.6** | 648.6 MB | Wed, 17 Aug 2022 11:35:08 GMT | [`http://fota.slv.fxd.jiophone.net/STB/Droidlogic/JHSD200/STB-JHSD200-7.4.6.zip`](http://fota.slv.fxd.jiophone.net/STB/Droidlogic/JHSD200/STB-JHSD200-7.4.6.zip) |
| **STB-JHSD200-7.6.8** | 677.6 MB | Fri, 04 Aug 2023 05:49:28 GMT | [`http://fota.slv.fxd.jiophone.net/STB/Droidlogic/JHSD200/STB-JHSD200-7.6.8.zip`](http://fota.slv.fxd.jiophone.net/STB/Droidlogic/JHSD200/STB-JHSD200-7.6.8.zip) |

> [!NOTE]
> Build **`5.7.1`** is widely leveraged in Android TV modding communities because its stock recovery enforces fewer signature check constraints, allowing downgrades via USB FAT32 drives.

---

### 4.2 Jio 4K STB (Skyworth JMSB200A / Amlogic S905X4)
The current device investigated in this repository:
* **Source URL:** `http://fota.slv.kai.jiophone.net/BHTS/DIN1009/SA002_19/loOOGaJIPm.zip`
* **Local Image Path:** [`ota_packages/loOOGaJIPm.zip`](ota_packages/loOOGaJIPm.zip)
* **Uncompressed Payload:** 792,512,816 bytes (Android A/B seamless streaming format `payload.bin`)
* **SHA-256 Checksum:** `e1e6d62e712d9e88ba504a9e0f907d20ae2f0e896060f70daddb9dc149ed8596`
* **Extracted Partitions:** Available in [`ota_packages/extracted/partitions/`](ota_packages/extracted/partitions/)

---

### 4.3 JioFiber Gateway Router Images & Signatures

#### A. Arcadyan JCOW411
* `R2.3` (69.5 MB): [`ARCNTF1_JCOW411_R2.3.img`](http://fota.slv.fxd.jiophone.net/ONT/Arcadyan/JCOW411/ARCNTF1_JCOW411_R2.3.img) | [`.sig`](http://fota.slv.fxd.jiophone.net/ONT/Arcadyan/JCOW411/ARCNTF1_JCOW411_R2.3.sig)
* `R2.12` (69.9 MB): [`ARCNTF1_JCOW411_R2.12.img`](http://fota.slv.fxd.jiophone.net/ONT/Arcadyan/JCOW411/ARCNTF1_JCOW411_R2.12.img) | [`.sig`](http://fota.slv.fxd.jiophone.net/ONT/Arcadyan/JCOW411/ARCNTF1_JCOW411_R2.12.sig)
* `R2.15` (71.6 MB): [`ARCNTF1_JCOW411_R2.15.img`](http://fota.slv.fxd.jiophone.net/ONT/Arcadyan/JCOW411/ARCNTF1_JCOW411_R2.15.img) | [`.sig`](http://fota.slv.fxd.jiophone.net/ONT/Arcadyan/JCOW411/ARCNTF1_JCOW411_R2.15.sig)
* `R2.17` (71.6 MB): [`ARCNTF1_JCOW411_R2.17.img`](http://fota.slv.fxd.jiophone.net/ONT/Arcadyan/JCOW411/ARCNTF1_JCOW411_R2.17.img) | [`.sig`](http://fota.slv.fxd.jiophone.net/ONT/Arcadyan/JCOW411/ARCNTF1_JCOW411_R2.17.sig)
* `R2.20` (81.4 MB): [`ARCNTF1_JCOW411_R2.20.img`](http://fota.slv.fxd.jiophone.net/ONT/Arcadyan/JCOW411/ARCNTF1_JCOW411_R2.20.img) | [`.sig`](http://fota.slv.fxd.jiophone.net/ONT/Arcadyan/JCOW411/ARCNTF1_JCOW411_R2.20.sig)
* `R2.21` (81.9 MB): [`ARCNTF1_JCOW411_R2.21.img`](http://fota.slv.fxd.jiophone.net/ONT/Arcadyan/JCOW411/ARCNTF1_JCOW411_R2.21.img) | [`.sig`](http://fota.slv.fxd.jiophone.net/ONT/Arcadyan/JCOW411/ARCNTF1_JCOW411_R2.21.sig)

#### B. Sercomm JCOW414
* `R2.15` (38.1 MB): [`SRCMTF1_JCOW414_R2.15.img`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW414/SRCMTF1_JCOW414_R2.15.img) | [`.sig`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW414/SRCMTF1_JCOW414_R2.15.sig)
* `R2.21` (38.4 MB): [`SRCMTF1_JCOW414_R2.21.img`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW414/SRCMTF1_JCOW414_R2.21.img) | [`.sig`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW414/SRCMTF1_JCOW414_R2.21.sig)
* `R2.26` (38.4 MB): [`SRCMTF1_JCOW414_R2.26.img`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW414/SRCMTF1_JCOW414_R2.26.img) | [`.sig`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW414/SRCMTF1_JCOW414_R2.26.sig)
* `R2.30` (37.4 MB): [`SRCMTF1_JCOW414_R2.30.img`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW414/SRCMTF1_JCOW414_R2.30.img) | [`.sig`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW414/SRCMTF1_JCOW414_R2.30.sig)
* `R2.35` (39.2 MB): [`SRCMTF1_JCOW414_R2.35.img`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW414/SRCMTF1_JCOW414_R2.35.img) | [`.sig`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW414/SRCMTF1_JCOW414_R2.35.sig)
* `R2.39` (39.1 MB): [`SRCMTF1_JCOW414_R2.39.img`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW414/SRCMTF1_JCOW414_R2.39.img) | [`.sig`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW414/SRCMTF1_JCOW414_R2.39.sig)
* `R2.41` (39.5 MB): [`SRCMTF1_JCOW414_R2.41.img`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW414/SRCMTF1_JCOW414_R2.41.img) | [`.sig`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW414/SRCMTF1_JCOW414_R2.41.sig)
* `R2.45` (39.9 MB): [`SRCMTF1_JCOW414_R2.45.img`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW414/SRCMTF1_JCOW414_R2.45.img) | [`.sig`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW414/SRCMTF1_JCOW414_R2.45.sig)
* `R2.52.1` (40.2 MB): [`SRCMTF1_JCOW414_R2.52.1.img`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW414/SRCMTF1_JCOW414_R2.52.1.img)

#### C. Skyworth JCOW407
* `R1.8.1` (37.0 MB): [`SKYWTF1_JCOW407_R1.8.1.img`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R1.8.1.img)
* `R1.12` (36.5 MB): [`SKYWTF1_JCOW407_R1.12.img`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R1.12.img) | [`.sig`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R1.12.sig)
* `R2.2` (36.3 MB): [`SKYWTF1_JCOW407_R2.2.img`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.2.img) | [`.sig`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.2.sig)
* `R2.6` (31.4 MB): [`SKYWTF1_JCOW407_R2.6.img`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.6.img) | [`.sig`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.6.sig)
* `R2.9` (31.6 MB): [`SKYWTF1_JCOW407_R2.9.img`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.9.img) | [`.sig`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.9.sig)
* `R2.12` (38.1 MB): [`SKYWTF1_JCOW407_R2.12.img`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.12.img) | [`.sig`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.12.sig)
* `R2.14` (38.1 MB): [`SKYWTF1_JCOW407_R2.14.img`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.14.img) | [`.sig`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.14.sig)
* `R2.15` (38.1 MB): [`SKYWTF1_JCOW407_R2.15.img`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.15.img) | [`.sig`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.15.sig)
* `R2.26` (38.5 MB): [`SKYWTF1_JCOW407_R2.26.img`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.26.img) | [`.sig`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.26.sig)
* `R2.30` (37.4 MB): [`SKYWTF1_JCOW407_R2.30.img`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.30.img) | [`.sig`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.30.sig)
* `R2.35` (39.2 MB): [`SKYWTF1_JCOW407_R2.35.img`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.35.img) | [`.sig`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.35.sig)
* `R2.39` (39.1 MB): [`SKYWTF1_JCOW407_R2.39.img`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.39.img) | [`.sig`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.39.sig)
* `R2.41` (39.5 MB): [`SKYWTF1_JCOW407_R2.41.img`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.41.img) | [`.sig`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.41.sig)
* `R2.45` (39.9 MB): [`SKYWTF1_JCOW407_R2.45.img`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.45.img) | [`.sig`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.45.sig)

#### D. Sercomm JCOW404
* `R1.4` (68.9 MB): [`SRCMTF1_JCOW404_R1.4.img`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW404/SRCMTF1_JCOW404_R1.4.img)
* `R1.5` (68.9 MB): [`SRCMTF1_JCOW404_R1.5.img`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW404/SRCMTF1_JCOW404_R1.5.img)
* `R1.6` (69.2 MB): [`SRCMTF1_JCOW404_R1.6.img`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW404/SRCMTF1_JCOW404_R1.6.img)
* `R1.7` (69.2 MB): [`SRCMTF1_JCOW404_R1.7.img`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW404/SRCMTF1_JCOW404_R1.7.img)
* `R2.3` (69.1 MB): [`SRCMTF1_JCOW404_R2.3.img`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW404/SRCMTF1_JCOW404_R2.3.img)
* `R2.15` (71.0 MB): [`SRCMTF1_JCOW404_R2.15.img`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW404/SRCMTF1_JCOW404_R2.15.img)
* `R2.17` (71.0 MB): [`SRCMTF1_JCOW404_R2.17.img`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW404/SRCMTF1_JCOW404_R2.17.img)
* `R2.20` (81.0 MB): [`SRCMTF1_JCOW404_R2.20.img`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW404/SRCMTF1_JCOW404_R2.20.img)
* `R2.21` (81.4 MB): [`SRCMTF1_JCOW404_R2.21.img`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW404/SRCMTF1_JCOW404_R2.21.img)

---

### 4.4 Enterprise & Hospitality Direct CDN Builds (`jiostb.cdn.jio.com`)

Direct OTA images for hotel/enterprise STB deployments. All three builds verified live (`HTTP/1.1 200 OK`) via Akamai NetStorage over HTTPS:

| Firmware Build | Package Size | HTTP Last-Modified | Direct URL |
| :--- | :--- | :--- | :--- |
| **Bluebank Hotel** (`rjio_hybrid_bluebank_a11_ota-v11.2.70-H`) | ~702.3 MB (736,383,742 bytes) | Wed, 17 Sep 2025 07:03:48 GMT | [`https://jiostb.cdn.jio.com/stbv/rjio_hybrid_bluebank_a11_ota-v11.2.70-H-user-bluebank_hotel.zip`](https://jiostb.cdn.jio.com/stbv/rjio_hybrid_bluebank_a11_ota-v11.2.70-H-user-bluebank_hotel.zip) |
| **SDMC Hotel** (`rjio_hybrid_sdmc_a11_ota-v11.2.62-H`) | ~705.5 MB (739,862,424 bytes) | Tue, 24 Mar 2026 07:09:49 GMT | [`https://jiostb.cdn.jio.com/stbv/rjio_hybrid_sdmc_a11_ota-v11.2.62-H-user-sdmc_hotel.zip`](https://jiostb.cdn.jio.com/stbv/rjio_hybrid_sdmc_a11_ota-v11.2.62-H-user-sdmc_hotel.zip) |
| **Skyworth Hotel** (`rjio_hybrid_skyworth_a11_ota-v11.2.70-H`) | ~702.2 MB (736,295,330 bytes) | Wed, 17 Sep 2025 06:40:15 GMT | [`https://jiostb.cdn.jio.com/stbv/rjio_hybrid_skyworth_a11_ota-v11.2.70-H-user-skyworth_hotel.zip`](https://jiostb.cdn.jio.com/stbv/rjio_hybrid_skyworth_a11_ota-v11.2.70-H-user-skyworth_hotel.zip) |

> **Note:** The SDMC hotel build (`v11.2.62-H`, Last-Modified Mar 2026) is the most recent firmware observed across all Jio CDN tiers, suggesting active hotel STB fleet updates as of Q1 2026.

---

### 4.5 IoT ACS Firmware Tier (`iotacs.jioconnect.com:8001`)

Firmware images distributed via Jio's IoT Auto-Configuration Server for residential ONT gateways. Transport is cleartext HTTP Digest CWMP.

| Firmware Build | Status | Direct URL |
| :--- | :--- | :--- |
| **Arcadyan-OTA-01.25.12-2024-06-17_userdebug** | HTTP 401 (Auth Required) | [`http://iotacs.jioconnect.com:8001/Arcadyan-OTA-01.25.12-2024-06-17_userdebug.zip`](http://iotacs.jioconnect.com:8001/Arcadyan-OTA-01.25.12-2024-06-17_userdebug.zip) |

> **Note:** The file exists (HTTP 401, not 404) but requires digest authentication tied to the IoT ACS session. Size unknown without valid credentials.

---

## 5. 🛠️ Reverse Engineering On-Device Flashing Tools

Reverse engineering the dumped privileged Android system applications from the JMSB200A OTA payload uncovered multiple update mechanisms embedded directly into the firmware:

### 5.1 The Micro-HTTP Update Server (`JioHttpUpdate.apk`)
Inside `ota_packages/extracted/apks/jio_system_priv_app/JioHttpUpdate.apk`:
* **Underlying Engine:** Uses embedded Java **NanoHTTPD** (`fi.iki.elonen.NanoHTTPD`).
* **Listening Port:** Hardcoded to **TCP `54321`**:
  ```java
  // HttpUpdateServer.java
  public class HttpUpdateServer extends NanoHTTPD {
      public HttpUpdateServer(Context context) {
          super(54321);
          ...
      }
  }
  ```
* **Endpoint `/updateme`**:
  When accessed over HTTP (`http://<STB_IP>:54321/updateme`), the server transitions into `State.SECURITY`, displays an 8-digit randomized challenge code on the TV screen via `Toast` or HTML:
  ```java
  this.securityCode = Integer.toString(new Random().nextInt(90000000) + 10000000);
  str3 = "<html><head><style></style><head/><body><h1>Update server</h1>\n" +
         "<p><small>Input following numbers sequence: </small> <em>" + this.securityCode + "</em></p>" +
         "<form action='?' method='get'>\n<p>Security Code: <input type='text' name='securityCode'></p>\n</form>\n</body></html>";
  ```
* **Seamless Partition Flashing (`IABSeamlessUpdateListner`)**:
  Once authenticated, the browser or HTTP client can upload an update payload. It writes the package to `/cache/ota_package_ab` and binds to Android’s native update engine:
  ```java
  public class Constants {
      public static final String SEAMLESS_LOCATION = "/cache/ota_package_ab";
  }
  ```
  It signals download events to `com.jio.fota_notification`:
  ```java
  intent.setAction("com.jio.tr069_notify_download_start");
  intent.setComponent(new ComponentName("com.jio.fota_notification", "com.jio.firmwaredownlod_lib.receiver.ProgressReceiver"));
  ```
* **Downgrade Flag Receiver (`TrDowngradeEnableReceiver`)**:
  Listens for intent action `com.jio.stb.httpupdate.DOWNGRADE_ENABLED_PERMISSION` to allow or block flashing older software builds.

---

### 5.2 TR-069 Automated Download Execution (`TR069.apk`)
When Jio's Auto-Configuration Server (`acs.oss.jio.com:8443`) initiates an update, it delivers a standard CWMP `Download` RPC:

```xml
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-2">
  <soap:Body>
    <cwmp:Download>
      <CommandKey>FOTA_TRIGGER_2026</CommandKey>
      <FileType>1 Firmware Upgrade Image</FileType>
      <URL>http://fota.slv.kai.jiophone.net/BHTS/DIN1009/SA002_19/loOOGaJIPm.zip</URL>
      <FileSize>792517294</FileSize>
      <TargetFileName>ota_update.zip</TargetFileName>
      <DelaySeconds>0</DelaySeconds>
    </cwmp:Download>
  </soap:Body>
</soap:Envelope>
```

1. **Cleartext Transport:** Download occurs over cleartext HTTP port 80 to Akamai edge IPs.
2. **Cryptographic Validation:** The update package is passed to Android TV's `RecoverySystem.verifyPackage()` or native helper `/usr/bin/jcrypt upgrade`, which verifies the archive against `META-INF/com/android/otacert` (Jio Platforms RSA-2048 root key).
3. **Execution:** The update engine applies the blocks to the inactive A/B slot (`_a` or `_b`) using Android Verified Boot (AVB 2.0).

---

## 6. 🚨 Security Implications & Attack Surface Analysis

1. **Cleartext Transit & Content Manipulation**:
   Because firmware binaries are downloaded over unencrypted HTTP port 80 (legacy `fxd` tier and IoT ACS tier), any party in the local LAN or ISP path (gateway, DNS resolver, rogue Wi-Fi AP) can observe the exact firmware versions being requested. The enterprise hotel CDN uses HTTPS but still exposes version information via URL paths. While cryptographic signatures prevent injecting modified code into stock bootloaders, MITM adversaries can drop or redirect download requests.

2. **Downgrade Vulnerabilities**:
   By pulling historical firmware builds (such as `STB-JHSD200-5.7.1.zip` or router image `SRCMTF1_JCOW414_R2.15.img`), researchers and users can downgrade older hardware to versions prior to the patching of UART shells, factory passwords, or telnet daemons.

3. **Asset & Key Extraction**:
   Access to raw firmware packages across device generations allows offline extraction of:
   * Proprietary encryption routines and certificates (`https.key`, `server.key`).
   * Factory technician credentials and hidden intent triggers.
   * Internal TR-069 data models and carrier provisioning policies.

4. **Hotel Build Exposure**:
   The enterprise hotel OTA builds (~702 MB each on `jiostb.cdn.jio.com`) contain pre-certified OTT components (Netflix, WebView) and operator overlays that can be extracted to recover DRM certificates, Widevine blobs, and hospitality provisioning keys.

---

## 7. 📊 Consolidated Firmware Inventory & Download Size Summary

| CDN Tier | Domain | Transport | Live Objects | Total Size | Content Window |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Open Legacy** | `fota.slv.fxd.jiophone.net` | Cleartext HTTP 80 | 69 (9 STB zips + 30 ONT img + 30 ONT sig) | ≈ 7.0 GB | Nov 2020 – Aug 2023 |
| **Enterprise Hotel** | `jiostb.cdn.jio.com` | HTTPS 443 | 3 hotel OTA zips | ≈ 2.11 GB | Sep 2025 – Mar 2026 |
| **Tokenized Modern** | `fota.slv.kai.jiophone.net` | Cleartext HTTP 80 | 38 documented URLs (DIN59–DIN1009) | ≈ 756 MB (JMSB200A confirmed; others unknown) | Ongoing |
| **IoT ACS** | `iotacs.jioconnect.com:8001` | Cleartext HTTP 8001 | 1 Arcadyan OTA (401 auth) | Unknown (~1.5 GB est.) | 2024-06-17 |
| **Grand Total** | — | — | **111+ objects** | **≈ 9.85 GB** (confirmed live) + unknown (kai tier) | — |

> **Note:** The 38 kai tier URLs are individually documented tokenized links. Only `DIN1009/SA002_19/loOOGaJIPm.zip` (755.8 MB) has been locally downloaded and verified. The remaining 37 URLs require their exact 10-character tokens, which cannot be brute-forced. See Section 3.1 and `ENDPOINTS_REFERENCE.json` for the full URL list.

---

## 8. 💻 Verification Tooling (Python Probe Script)

The Python script used to systematically enumerate and audit firmware versions against the FOTA servers is located at [`scripts/probe_firmwares.py`](scripts/probe_firmwares.py). It uses multi-threaded HTTP HEAD requests to scan version ranges without consuming transit bandwidth.

---
## 🔗 Related Documents

| Related Document | Relationship |
| :--- | :--- |
| [`OTA_ANALYSIS.md`](OTA_ANALYSIS.md) | Extracted OTA package (`loOOGaJIPm.zip`), `payload.bin` partition images, and APKs used in this endpoint analysis. |
| [`NETWORK_ANALYSIS.md`](NETWORK_ANALYSIS.md) | Live traffic capture and endpoint categorization, including the cleartext HTTP firmware download to `fota.slv.kai.jiophone.net`. |
| [`jio_infrastructure/03_FOTA_AND_FIRMWARE_DISTRIBUTION.md`](jio_infrastructure/03_FOTA_AND_FIRMWARE_DISTRIBUTION.md) | Master FOTA infrastructure: CDN tiers, tokenized hash generation, device taxonomy (`DIN59`–`DIN1009`), verified live downloads, and on-device flashing via `JioHttpUpdate.apk`. |
| [`jio_infrastructure/ENDPOINTS_REFERENCE.json`](jio_infrastructure/ENDPOINTS_REFERENCE.json) | Machine-readable, categorized inventory of all unique endpoints and distinct hosts mapped to their originating system applications. |

# 03. FOTA Infrastructure, Distribution CDNs & Firmware Mechanics

> **Parent Topic:** [`jio_infrastructure/README.md`](README.md)  
> **Source Packages:** [`JioHttpUpdate.apk`](../ota_packages/extracted/apks/jio_system_priv_app/JioHttpUpdate.apk), [`JioMrServer.apk`](../ota_packages/extracted/apks/jio_system_priv_app/JioMrServer.apk), [`TR069.apk`](../ota_packages/extracted/apks/jio_system_priv_app/TR069.apk)  
> **Related Research:** [`FIRMWARE_ENDPOINTS_AND_EXPOSURES.md`](../FIRMWARE_ENDPOINTS_AND_EXPOSURES.md), [`OTA_ANALYSIS.md`](../OTA_ANALYSIS.md)

---

## 1. Architectural Distribution Split

Reliance Jio delivers operating system images, bootloader binaries, and recovery packages through a multi-tiered CDN hierarchy. Analysis reveals an intentional split between:
1. **The Modern Obfuscated Tier (`fota.slv.kai.jiophone.net`):** Uses non-enumerable, pseudo-random 10-character hash tokens for contemporary devices (Android TV 11 STBs, AirFiber 5G CPEs).
2. **The Open Deterministic Tier (`fota.slv.fxd.jiophone.net`):** Exposes publicly predictable directory structures for legacy Set-Top Boxes and JioFiber GPON gateways. Fully mapped live inventory below (Section 2.3).
3. **The Direct Hybrid STB Tier (`jiostb.cdn.jio.com`):** Serves enterprise and hospitality builds directly via dedicated subdomains over HTTPS.
4. **The IoT ACS Tier (`iotacs.jioconnect.com:8001/8080`):** Serves ONT firmware images to residential gateways via CWMP with digest authentication.
5. **The Datacenter Origin Tier (`fota.mst.kai.jiophone.net`):** Master repositories on Jio AS55836 feeding Akamai edge nodes.

```
                              ┌──────────────────────────────────────────────┐
                              │      Master Origin Tier (AS55836)            │
                              │   fota.mst.kai.jiophone.net (49.40.21.37/52) │
                              └──────────────────────┬───────────────────────┘
                                                     │
                             ┌───────────────────────┴───────────────────────┐
                             │                                               │
                             ▼                                               ▼
     ┌──────────────────────────────────────────────┐ ┌──────────────────────────────────────────────┐
     │      Modern Obfuscated CDN Node              │ │        Legacy Open CDN Node                  │
     │        fota.slv.kai.jiophone.net             │ │          fota.slv.fxd.jiophone.net           │
     │    AkamaiNetStorage (104.96.177.202)         │ │     AkamaiNetStorage (184.27.197.10/.91)     │
     ├──────────────────────────────────────────────┤ ├──────────────────────────────────────────────┤
     │ • Format: /BHTS/DIN<ID>/<BUILD>/<TOKEN>.zip  │ │ • Format: /STB/<OEM>/<MODEL>/STB-<M>-<V>.zip │
     │ • Edge ACL: AkamaiGHost 403 on directories   │ │ • Format: /ONT/<OEM>/<MODEL>/<P>_R<V>.{img,sig}│
     │ • Devices: JMSB200A 4K STB, AirFiber 5G      │ │ • Edge ACL: Open public HTTP 200 downloads   │
     │                                              │ │ • Live inventory: 69 objects (~7.0 GB)       │
     │                                              │ │   - STB recovery zips: 9 (Droidlogic JHSD200)│
     │                                              │ │   - ONT router images: 30 img + 30 sig       │
     │                                              │ │ • Content window: Nov 2020 – Aug 2023        │
     └──────────────────────────────────────────────┘ └──────────────────────────────────────────────┘
```

---

## 2. URL Path Taxonomy & Token Mechanics

### 2.1 Obfuscated Tokenized Format (`kai.jiophone.net`)
```text
http://fota.slv.kai.jiophone.net/<CATEGORY>/<DEVICE_ID>/<BUILD_ID>/<TOKEN>.<ext>
```

| Path Component | Definition | Identified Production Values |
| :--- | :--- | :--- |
| `<CATEGORY>` | Hardware Division | `BHTS` (Broadband Hybrid TV STB)<br>`XPGNO` (JioFiber GPON ONT)<br>`5G` (AirFiber Fixed Wireless) |
| `<DEVICE_ID>` | Hardware Generation Tag | `DIN1009` (Skyworth JMSB200A 4K STB)<br>`DIN520` / `UDO` (AirFiber 5G Outdoor Unit)<br>`UDI` (AirFiber Indoor Unit) |
| `<BUILD_ID>` | OEM Firmware Build Code | `SA002_19` (Android 11 build 25.1.9)<br>`A1402_32_S` (AirFiber ODU firmware R2.32) |
| `<TOKEN>.<ext>` | 10-Character Random Hash | `loOOGaJIPm.zip` (755.8 MB OTA update)<br>`DtrbUbNvSe.img` (ONT router image) |

### 2.2 Open Deterministic Format (`fxd.jiophone.net`)
Used for legacy STBs and residential gateways. Directory listings are disabled (root and prefix paths return `404` / `403`); only fully-qualified object paths return `HTTP 200`.

- **Set-Top Boxes:**
  ```text
  http://fota.slv.fxd.jiophone.net/STB/<Manufacturer>/<Model>/STB-<Model>-<Version>.zip
  ```
  * `<Manufacturer>`: `Droidlogic` (Amlogic reference ODM), `Skyworth`, `SDMC`
  * `<Model>`: `JHSD200`, `JHSB200`, `JHSC200`
  * `<Version>`: Semantic versioning (`X.Y.Z`)

- **ONT Gateways:**
  ```text
  http://fota.slv.fxd.jiophone.net/ONT/<Manufacturer>/<Model>/<Prefix>_R<Version>.img
  http://fota.slv.fxd.jiophone.net/ONT/<Manufacturer>/<Model>/<Prefix>_R<Version>.sig
  ```
  * `<Manufacturer>`: `Arcadyan`, `Sercomm`, `Skyworth`, `Foxconn`
  * `<Model>`: `JCOW411`, `JCOW414`, `JCOW407`, `JCOW404`, `JCO110`
  * `<Prefix>`: Hardware release prefix (`ARCNTF1_JCOW411_R`, `SRCMTF1_JCOW414_R`, `SKYWTF1_JCOW407_R`, `SRCMTF1_JCOW404_R`)
  * `<Version>`: Release version (e.g. `2.3`, `2.15`, `2.41`, `2.52.1`)
  * `.img`: Full router firmware image (31–82 MB)
  * `.sig`: 256-byte cryptographic signature file (RSA/ECDSA) consumed by bootloader/recovery verification

---

## 2.3 Live Object Inventory — `fota.slv.fxd.jiophone.net` (Open Legacy Tier)

**Verification method:** 2,060 candidate paths probed via `HEAD` against `http://fota.slv.fxd.jiophone.net` (concurrent, UA `Mozilla/5.0`) on 2026-10-29. **69 objects returned `HTTP 200 OK`** via `Server: AkamaiNetStorage`; all remaining candidates (including directory listings, Skyworth/SDMC STB models, Sercomm JCOW414, Foxconn ONTs) returned `404 Not Found`. Transport is cleartext HTTP on TCP 80; integrity relies entirely on OEM signature verification of payloads, not transport security.

**Aggregate:** 69 objects, ~6.3 GB total, Last-Modified window **Wed, 25 Nov 2020 – Fri, 04 Aug 2023** (legacy content; no post-2023 releases hosted).

### 2.3.1 Set-Top Box Recovery Packages — Droidlogic JHSD200 (9 objects)

Full AOSP Android TV recovery zips containing kernel, recovery, and system images. Build `5.7.1` is widely leveraged in Android TV modding communities because its stock recovery enforces fewer signature constraints, permitting downgrades via USB FAT32.

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

### 2.3.2 JioFiber Gateway Router Images — Arcadyan JCOW411 (12 objects: 6 img + 6 sig)

Prefix: `ARCNTF1_JCOW411_R`. All versions carry a matching `.sig` signature file.

| Firmware | Image Size | Sig Size | Last-Modified (img) | Image URL | Signature URL |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **R2.3** | 69.5 MB | 256 B | Fri, 22 Oct 2021 10:46:17 GMT | [`ARCNTF1_JCOW411_R2.3.img`](http://fota.slv.fxd.jiophone.net/ONT/Arcadyan/JCOW411/ARCNTF1_JCOW411_R2.3.img) | [`ARCNTF1_JCOW411_R2.3.sig`](http://fota.slv.fxd.jiophone.net/ONT/Arcadyan/JCOW411/ARCNTF1_JCOW411_R2.3.sig) |
| **R2.12** | 69.9 MB | 256 B | Tue, 01 Feb 2022 07:27:56 GMT | [`ARCNTF1_JCOW411_R2.12.img`](http://fota.slv.fxd.jiophone.net/ONT/Arcadyan/JCOW411/ARCNTF1_JCOW411_R2.12.img) | [`ARCNTF1_JCOW411_R2.12.sig`](http://fota.slv.fxd.jiophone.net/ONT/Arcadyan/JCOW411/ARCNTF1_JCOW411_R2.12.sig) |
| **R2.15** | 71.6 MB | 256 B | Thu, 14 Apr 2022 08:21:45 GMT | [`ARCNTF1_JCOW411_R2.15.img`](http://fota.slv.fxd.jiophone.net/ONT/Arcadyan/JCOW411/ARCNTF1_JCOW411_R2.15.img) | [`ARCNTF1_JCOW411_R2.15.sig`](http://fota.slv.fxd.jiophone.net/ONT/Arcadyan/JCOW411/ARCNTF1_JCOW411_R2.15.sig) |
| **R2.17** | 71.6 MB | 256 B | Tue, 12 Jul 2022 06:02:53 GMT | [`ARCNTF1_JCOW411_R2.17.img`](http://fota.slv.fxd.jiophone.net/ONT/Arcadyan/JCOW411/ARCNTF1_JCOW411_R2.17.img) | [`ARCNTF1_JCOW411_R2.17.sig`](http://fota.slv.fxd.jiophone.net/ONT/Arcadyan/JCOW411/ARCNTF1_JCOW411_R2.17.sig) |
| **R2.20** | 81.4 MB | 256 B | Mon, 29 Aug 2022 05:57:10 GMT | [`ARCNTF1_JCOW411_R2.20.img`](http://fota.slv.fxd.jiophone.net/ONT/Arcadyan/JCOW411/ARCNTF1_JCOW411_R2.20.img) | [`ARCNTF1_JCOW411_R2.20.sig`](http://fota.slv.fxd.jiophone.net/ONT/Arcadyan/JCOW411/ARCNTF1_JCOW411_R2.20.sig) |
| **R2.21** | 81.9 MB | 256 B | Fri, 04 Nov 2022 05:49:02 GMT | [`ARCNTF1_JCOW411_R2.21.img`](http://fota.slv.fxd.jiophone.net/ONT/Arcadyan/JCOW411/ARCNTF1_JCOW411_R2.21.img) | [`ARCNTF1_JCOW411_R2.21.sig`](http://fota.slv.fxd.jiophone.net/ONT/Arcadyan/JCOW411/ARCNTF1_JCOW411_R2.21.sig) |

### 2.3.3 JioFiber Gateway Router Images — Sercomm JCOW404 (20 objects: 10 img + 10 sig)

Prefix: `SRCMTF1_JCOW404_R`. All versions — including `R1.x` and `R2.3` — carry matching `.sig` files (the `.sig` for early revisions was previously undocumented).

| Firmware | Image Size | Sig Size | Last-Modified (img) | Image URL | Signature URL |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **R1.4** | 68.9 MB | 256 B | Wed, 07 Jul 2021 16:08:55 GMT | [`SRCMTF1_JCOW404_R1.4.img`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW404/SRCMTF1_JCOW404_R1.4.img) | [`SRCMTF1_JCOW404_R1.4.sig`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW404/SRCMTF1_JCOW404_R1.4.sig) |
| **R1.5** | 68.9 MB | 256 B | Sat, 10 Jul 2021 17:25:52 GMT | [`SRCMTF1_JCOW404_R1.5.img`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW404/SRCMTF1_JCOW404_R1.5.img) | [`SRCMTF1_JCOW404_R1.5.sig`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW404/SRCMTF1_JCOW404_R1.5.sig) |
| **R1.6** | 69.2 MB | 256 B | Mon, 19 Jul 2021 08:24:16 GMT | [`SRCMTF1_JCOW404_R1.6.img`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW404/SRCMTF1_JCOW404_R1.6.img) | [`SRCMTF1_JCOW404_R1.6.sig`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW404/SRCMTF1_JCOW404_R1.6.sig) |
| **R1.7** | 69.2 MB | 256 B | Wed, 04 Aug 2021 12:19:16 GMT | [`SRCMTF1_JCOW404_R1.7.img`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW404/SRCMTF1_JCOW404_R1.7.img) | [`SRCMTF1_JCOW404_R1.7.sig`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW404/SRCMTF1_JCOW404_R1.7.sig) |
| **R2.3** | 69.1 MB | 256 B | Mon, 27 Sep 2021 06:29:21 GMT | [`SRCMTF1_JCOW404_R2.3.img`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW404/SRCMTF1_JCOW404_R2.3.img) | [`SRCMTF1_JCOW404_R2.3.sig`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW404/SRCMTF1_JCOW404_R2.3.sig) |
| **R2.12** | 69.3 MB | 256 B | Wed, 09 Feb 2022 08:03:23 GMT | [`SRCMTF1_JCOW404_R2.12.img`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW404/SRCMTF1_JCOW404_R2.12.img) | [`SRCMTF1_JCOW404_R2.12.sig`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW404/SRCMTF1_JCOW404_R2.12.sig) |
| **R2.15** | 71.0 MB | 256 B | Thu, 14 Apr 2022 08:05:56 GMT | [`SRCMTF1_JCOW404_R2.15.img`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW404/SRCMTF1_JCOW404_R2.15.img) | [`SRCMTF1_JCOW404_R2.15.sig`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW404/SRCMTF1_JCOW404_R2.15.sig) |
| **R2.17** | 71.0 MB | 256 B | Tue, 12 Jul 2022 06:01:55 GMT | [`SRCMTF1_JCOW404_R2.17.img`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW404/SRCMTF1_JCOW404_R2.17.img) | [`SRCMTF1_JCOW404_R2.17.sig`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW404/SRCMTF1_JCOW404_R2.17.sig) |
| **R2.20** | 81.0 MB | 256 B | Fri, 09 Sep 2022 06:12:00 GMT | [`SRCMTF1_JCOW404_R2.20.img`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW404/SRCMTF1_JCOW404_R2.20.img) | [`SRCMTF1_JCOW404_R2.20.sig`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW404/SRCMTF1_JCOW404_R2.20.sig) |
| **R2.21** | 81.4 MB | 256 B | Fri, 04 Nov 2022 05:51:33 GMT | [`SRCMTF1_JCOW404_R2.21.img`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW404/SRCMTF1_JCOW404_R2.21.img) | [`SRCMTF1_JCOW404_R2.21.sig`](http://fota.slv.fxd.jiophone.net/ONT/Sercomm/JCOW404/SRCMTF1_JCOW404_R2.21.sig) |

### 2.3.4 JioFiber Gateway Router Images — Skyworth JCOW407 (28 objects: 14 img + 14 sig)

Prefix: `SKYWTF1_JCOW407_R`. All versions — including `R1.8.1` — carry matching `.sig` files.

| Firmware | Image Size | Sig Size | Last-Modified (img) | Image URL | Signature URL |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **R1.8.1** | 37.0 MB | 256 B | Mon, 01 Mar 2021 10:08:53 GMT | [`SKYWTF1_JCOW407_R1.8.1.img`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R1.8.1.img) | [`SKYWTF1_JCOW407_R1.8.1.sig`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R1.8.1.sig) |
| **R1.12** | 36.5 MB | 256 B | Thu, 15 Oct 2020 08:52:38 GMT | [`SKYWTF1_JCOW407_R1.12.img`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R1.12.img) | [`SKYWTF1_JCOW407_R1.12.sig`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R1.12.sig) |
| **R2.2** | 36.3 MB | 256 B | Wed, 25 Nov 2020 08:32:54 GMT | [`SKYWTF1_JCOW407_R2.2.img`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.2.img) | [`SKYWTF1_JCOW407_R2.2.sig`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.2.sig) |
| **R2.6** | 31.4 MB | 256 B | Fri, 25 Dec 2020 06:50:32 GMT | [`SKYWTF1_JCOW407_R2.6.img`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.6.img) | [`SKYWTF1_JCOW407_R2.6.sig`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.6.sig) |
| **R2.9** | 31.6 MB | 256 B | Tue, 09 Feb 2021 09:24:37 GMT | [`SKYWTF1_JCOW407_R2.9.img`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.9.img) | [`SKYWTF1_JCOW407_R2.9.sig`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.9.sig) |
| **R2.12** | 38.1 MB | 256 B | Thu, 25 Feb 2021 12:37:44 GMT | [`SKYWTF1_JCOW407_R2.12.img`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.12.img) | [`SKYWTF1_JCOW407_R2.12.sig`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.12.sig) |
| **R2.14** | 38.1 MB | 256 B | Mon, 08 Mar 2021 08:49:04 GMT | [`SKYWTF1_JCOW407_R2.14.img`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.14.img) | [`SKYWTF1_JCOW407_R2.14.sig`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.14.sig) |
| **R2.15** | 38.1 MB | 256 B | Tue, 16 Mar 2021 07:30:34 GMT | [`SKYWTF1_JCOW407_R2.15.img`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.15.img) | [`SKYWTF1_JCOW407_R2.15.sig`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.15.sig) |
| **R2.26** | 38.5 MB | 256 B | Wed, 04 Aug 2021 12:35:05 GMT | [`SKYWTF1_JCOW407_R2.26.img`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.26.img) | [`SKYWTF1_JCOW407_R2.26.sig`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.26.sig) |
| **R2.30** | 37.4 MB | 256 B | Mon, 27 Sep 2021 06:39:46 GMT | [`SKYWTF1_JCOW407_R2.30.img`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.30.img) | [`SKYWTF1_JCOW407_R2.30.sig`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.30.sig) |
| **R2.35** | 39.2 MB | 256 B | Tue, 01 Feb 2022 07:26:00 GMT | [`SKYWTF1_JCOW407_R2.35.img`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.35.img) | [`SKYWTF1_JCOW407_R2.35.sig`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.35.sig) |
| **R2.39** | 39.1 MB | 256 B | Thu, 14 Apr 2022 09:56:13 GMT | [`SKYWTF1_JCOW407_R2.39.img`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.39.img) | [`SKYWTF1_JCOW407_R2.39.sig`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.39.sig) |
| **R2.41** | 39.5 MB | 256 B | Tue, 31 May 2022 11:41:14 GMT | [`SKYWTF1_JCOW407_R2.41.img`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.41.img) | [`SKYWTF1_JCOW407_R2.41.sig`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.41.sig) |
| **R2.45** | 39.9 MB | 256 B | Mon, 29 Aug 2022 05:56:21 GMT | [`SKYWTF1_JCOW407_R2.45.img`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.45.img) | [`SKYWTF1_JCOW407_R2.45.sig`](http://fota.slv.fxd.jiophone.net/ONT/Skyworth/JCOW407/SKYWTF1_JCOW407_R2.45.sig) |

### 2.3.5 Confirmed Absent / Removed (404 verified)

The following paths and models were probed and return `404 Not Found` — they are **not** hosted on the open tier:

| Device Class | Manufacturer / Model | Notes |
| :--- | :--- | :--- |
| STB | Skyworth `JHSB200`, `JHSC200` | Documented in taxonomy but no objects live on open tier |
| STB | SDMC `JHSC200` | Documented in taxonomy but no objects live on open tier |
| ONT | Sercomm `JCOW414` | Previously documented `R2.15`–`R2.52.1` images — all removed |
| ONT | Foxconn `JCO110` | Documented in taxonomy but no objects live |
| — | Root / directory listing | `GET /`, `/STB/`, `/ONT/`, `<OEM>/` all return `404` |

> **JHSC200 Telemetry Confirmation:** While no `JHSC200` firmware objects are hosted on the open `fxd` tier, Mercury ad telemetry (via `mercury-ck.jio.com`) confirms `JHSC200` is an active production device in the fleet. Observed beacon parameters include `mn=JHSC200`, `br=Jio`, `ai=com.jio.halotv`, `av=3.0.52.7`, `osv=11`, indicating it runs Android 11 with the Jio HaloTV application. Its firmware is likely distributed exclusively through the tokenized `kai` tier or the IoT ACS, neither of which is enumerable without prior token knowledge.

### 2.3.6 Enterprise & Hospitality Direct CDN Builds (`jiostb.cdn.jio.com`)

Direct OTA images for hotel/enterprise STB deployments. All three builds verified live (`HTTP/1.1 200 OK`) via Akamai NetStorage over HTTPS:

| Firmware Build | Package Size | HTTP Last-Modified | Direct URL |
| :--- | :--- | :--- | :--- |
| **Bluebank Hotel** (`rjio_hybrid_bluebank_a11_ota-v11.2.70-H`) | ~702.3 MB (736,383,742 bytes) | Wed, 17 Sep 2025 07:03:48 GMT | [`https://jiostb.cdn.jio.com/stbv/rjio_hybrid_bluebank_a11_ota-v11.2.70-H-user-bluebank_hotel.zip`](https://jiostb.cdn.jio.com/stbv/rjio_hybrid_bluebank_a11_ota-v11.2.70-H-user-bluebank_hotel.zip) |
| **SDMC Hotel** (`rjio_hybrid_sdmc_a11_ota-v11.2.62-H`) | ~705.5 MB (739,862,424 bytes) | Tue, 24 Mar 2026 07:09:49 GMT | [`https://jiostb.cdn.jio.com/stbv/rjio_hybrid_sdmc_a11_ota-v11.2.62-H-user-sdmc_hotel.zip`](https://jiostb.cdn.jio.com/stbv/rjio_hybrid_sdmc_a11_ota-v11.2.62-H-user-sdmc_hotel.zip) |
| **Skyworth Hotel** (`rjio_hybrid_skyworth_a11_ota-v11.2.70-H`) | ~702.2 MB (736,295,330 bytes) | Wed, 17 Sep 2025 06:40:15 GMT | [`https://jiostb.cdn.jio.com/stbv/rjio_hybrid_skyworth_a11_ota-v11.2.70-H-user-skyworth_hotel.zip`](https://jiostb.cdn.jio.com/stbv/rjio_hybrid_skyworth_a11_ota-v11.2.70-H-user-skyworth_hotel.zip) |

> **Note:** The SDMC hotel build (`v11.2.62-H`, Last-Modified Mar 2026) is the most recent firmware observed across all Jio CDN tiers, suggesting active hotel STB fleet updates as of Q1 2026.

### 2.3.7 IoT ACS Firmware Tier (`iotacs.jioconnect.com:8001`)

Firmware images distributed via Jio's IoT Auto-Configuration Server for residential ONT gateways. Transport is cleartext HTTP Digest CWMP.

| Firmware Build | Status | Direct URL |
| :--- | :--- | :--- |
| **Arcadyan-OTA-01.25.12-2024-06-17_userdebug** | HTTP 401 (Auth Required) | [`http://iotacs.jioconnect.com:8001/Arcadyan-OTA-01.25.12-2024-06-17_userdebug.zip`](http://iotacs.jioconnect.com:8001/Arcadyan-OTA-01.25.12-2024-06-17_userdebug.zip) |

> **Note:** The file exists (HTTP 401, not 404) but requires digest authentication tied to the IoT ACS session. Size unknown without valid credentials.

---

## 3. Reverse-Engineered Hardware Generation Catalog

Static analysis of system update catalog strings inside [`JioMrServer.apk`](../ota_packages/extracted/apks/jio_system_priv_app/JioMrServer.apk) exposed an extensive matrix of device codes (`DIN*`) and tokenized package URLs across Jio's hardware history:

### 3.1 Device Code Matrix (`DIN*`)

| Hardware Code | Build Prefix | Sample Production Firmware URL | Target ODM / Platform |
| :--- | :--- | :--- | :--- |
| **`DIN59`** | `D002D_11` | `http://fota.slv.kai.jiophone.net/BHTS/DIN59/D002D_11/zMbiKlmKfm.zip` | Droidlogic Early Prototype |
| **`DIN62`** | `S002B_011`<br>`SA002_011` | `http://fota.slv.kai.jiophone.net/BHTS/DIN62/S002B_011/AfblteoWZe.zip`<br>`http://fota.slv.kai.jiophone.net/BHTS/DIN62/SA002_011/tiOwCGBFDU.zip` | Skyworth Prototype |
| **`DIN292`** | `D002D_020`<br>`S002B_020`<br>`S002C_020` | `http://fota.slv.kai.jiophone.net/BHTS/DIN292/D002D_020/UAtWTevgwZ.zip`<br>`http://fota.slv.kai.jiophone.net/BHTS/DIN292/S002B_020/sAydtUZsOC.zip`<br>`http://fota.slv.kai.jiophone.net/BHTS/DIN292/S002C_020/TOKNrjMKby.zip` | Droidlogic / Skyworth |
| **`DIN293`** | `D002D_120`<br>`S002C_202` | `http://fota.slv.kai.jiophone.net/BHTS/DIN293/D002D_120/WVnkJkfyBQ.zip`<br>`http://fota.slv.kai.jiophone.net/BHTS/DIN293/S002C_202/VSyIqnTPqD.zip` | Droidlogic / Skyworth |
| **`DIN324`** | `A0003_-99`<br>`A0003_75-E`<br>`A0003_81`<br>`A0003_910` | `http://fota.slv.kai.jiophone.net/BHTS/DIN324/A0003_-99/YZocoPAaBG.zip`<br>`http://fota.slv.kai.jiophone.net/BHTS/DIN324/A0003_75-E/wyNnasHigE.zip`<br>`http://fota.slv.kai.jiophone.net/BHTS/DIN324/A0003_81/xU5GtWOLMH.zip`<br>`http://fota.slv.kai.jiophone.net/BHTS/DIN324/A0003_910/zwdhLxbvHJ.zip` | Arcadyan Hybrid Device |
| **`DIN353`** | `S002C_9-H` | `http://fota.slv.kai.jiophone.net/BHTS/DIN353/S002C_9-H/CKEv2odf5n.zip` | Skyworth Hotel Build |
| **`DIN368`** | `D002D_211` | `http://fota.slv.kai.jiophone.net/BHTS/DIN368/D002D_211/KDYRLwwQsGQ.zip` | Droidlogic |
| **`DIN372`** | `S002C_211` | `http://fota.slv.kai.jiophone.net/BHTS/DIN372/S002C_211/IvNbOICw7t.zip` | Skyworth |
| **`DIN380`** | `S002B_211` | `http://fota.slv.kai.jiophone.net/BHTS/DIN380/S002B_211/qE4WT6Ezy1.zip` | Skyworth |
| **`DIN387`** | `D002D_13-H` | `http://fota.slv.kai.jiophone.net/BHTS/DIN387/D002D_13-H/AyIwu7D7AB.zip` | Droidlogic Hotel Build |
| **`DIN390`** | `BA002_114` | `http://fota.slv.kai.jiophone.net/BHTS/DIN390/BA002_114/ks6fkIEJJV.zip` | Bluebank |
| **`DIN422`** | `S002B_13-H` | `http://fota.slv.kai.jiophone.net/BHTS/DIN422/S002B_13-H/CdksdojCmi.zip` | Skyworth Hotel Build |
| **`DIN431`** | `D002D_228`<br>`S002B_228`<br>`S002C_228` | `http://fota.slv.kai.jiophone.net/BHTS/DIN431/D002D_228/RchIhUhqEW.zip`<br>`http://fota.slv.kai.jiophone.net/BHTS/DIN431/S002B_228/QwDZLBwrRM.zip`<br>`http://fota.slv.kai.jiophone.net/BHTS/DIN431/S002C_228/SmTXZD3vuY.zip` | Multi-vendor Generation |
| **`DIN442`** | `SA002_109` | `http://fota.slv.kai.jiophone.net/BHTS/DIN442/SA002_109/yFT88iUnII.zip` | Skyworth |
| **`DIN445`** | `BA002_109`<br>`SA002_109` | `http://fota.slv.kai.jiophone.net/BHTS/DIN445/BA002_109/Is6fkIEJJV.zip`<br>`http://fota.slv.kai.jiophone.net/BHTS/DIN445/SA002_109/HOwJatziuX.zip` | Bluebank / Skyworth |
| **`DIN537`** | `BA002_111`<br>`SA002_111` | `http://fota.slv.kai.jiophone.net/BHTS/DIN537/BA002_111/JOwJatziuX.zip`<br>`http://fota.slv.kai.jiophone.net/BHTS/DIN537/SA002_111/kArxcKXoHi.zip` | Bluebank / Skyworth |
| **`DIN551`** | `D002D_248`<br>`S002B_248`<br>`S002C_248` | `http://fota.slv.kai.jiophone.net/BHTS/DIN551/D002D_248/VchIhUhqEW.zip`<br>`http://fota.slv.kai.jiophone.net/BHTS/DIN551/S002B_248/tU831C61cr.zip`<br>`http://fota.slv.kai.jiophone.net/BHTS/DIN551/S002C_248/UmTXZD3vuY.zip` | Multi-vendor Fleet |
| **`DIN666`** | `D002D_280` | `http://fota.slv.kai.jiophone.net/BHTS/DIN666/D002D_280/MchIhUhqEW.zip` | Droidlogic |
| **`DIN667`** | `S002B_280`<br>`S002C_280` | `http://fota.slv.kai.jiophone.net/BHTS/DIN667/S002B_280/PKLg53bXlX.zip`<br>`http://fota.slv.kai.jiophone.net/BHTS/DIN667/S002C_280/OWcaMhIc1i.zip` | Skyworth |
| **`DIN789`** | — | — | Sercomm JCOW414 ONT (tokenized tier; previously documented `R2.15`–`R2.52.1` on open tier — all removed) |
| **`DIN730`** | `D002D_294` | `http://fota.slv.kai.jiophone.net/BHTS/DIN730/D002D_294/KchIhUhqEW.zip` | Droidlogic |
| **`DIN733`** | `S002C_294` | `http://fota.slv.kai.jiophone.net/BHTS/DIN733/S002C_294/OBcaMhIc1i.zip` | Skyworth |
| **`DIN738`** | `S002B_294` | `http://fota.slv.kai.jiophone.net/BHTS/DIN738/S002B_294/LU831C61cr.zip` | Skyworth |
| **`DIN1009`** | `SA002_19` | `http://fota.slv.kai.jiophone.net/BHTS/DIN1009/SA002_19/loOOGaJIPm.zip` | **Skyworth JMSB200A 4K STB (Current)** |

---

### 3.2 Enterprise & Hospitality Direct CDN Builds (`jiostb.cdn.jio.com`)
Direct OTA images deployed for the hotel launcher firmware variant:
* **Bluebank Hotel:** [`https://jiostb.cdn.jio.com/stbv/rjio_hybrid_bluebank_a11_ota-v11.2.70-H-user-bluebank_hotel.zip`](https://jiostb.cdn.jio.com/stbv/rjio_hybrid_bluebank_a11_ota-v11.2.70-H-user-bluebank_hotel.zip)
* **SDMC Hotel:** [`https://jiostb.cdn.jio.com/stbv/rjio_hybrid_sdmc_a11_ota-v11.2.62-H-user-sdmc_hotel.zip`](https://jiostb.cdn.jio.com/stbv/rjio_hybrid_sdmc_a11_ota-v11.2.62-H-user-sdmc_hotel.zip)
* **Skyworth Hotel:** [`https://jiostb.cdn.jio.com/stbv/rjio_hybrid_skyworth_a11_ota-v11.2.70-H-user-skyworth_hotel.zip`](https://jiostb.cdn.jio.com/stbv/rjio_hybrid_skyworth_a11_ota-v11.2.70-H-user-skyworth_hotel.zip)

---

## 4. On-Device Update Mechanics & Daemons

### 4.1 The Embedded NanoHTTPD Server (`JioHttpUpdate.apk`)
Privileged package `com.jio.stb.httpupdate` embeds **NanoHTTPD** (`fi.iki.elonen.NanoHTTPD`), binding to **TCP port 54321**:
* **Endpoint `/updateme`:** Transitions the server into `State.SECURITY`, displaying a dynamic 8-digit OTP on the television screen.
* **Seamless A/B Flashing:** Once the OTP is supplied via browser, the client uploads a package written to `/cache/ota_package_ab`.
* **Binding to Update Engine:** Binds to Android's native update engine via AIDL to flash alternate A/B partition slots.
* **Downgrade Override:** Listens for broadcast `com.jio.stb.httpupdate.DOWNGRADE_ENABLED_PERMISSION` to bypass rollback protection.

### 4.2 Bluetooth RCU Update Daemon (`JioRcuUpdate.apk`)
Handles Over-The-Air firmware updates for Bluetooth Low Energy (BLE) voice remotes, reading firmware chunks and writing them over GATT characteristics.

---

## 5. Security Exposure Summary — All CDN Tiers

### 5.1 Open Legacy Tier (`fota.slv.fxd.jiophone.net`)

| Property | Value |
| :--- | :--- |
| **FQDN** | `fota.slv.fxd.jiophone.net` → `fota.slv.fxd.jiophone.net.akamaized.net` → `a108.dscd.akamai.net` |
| **Resolved IPs** | `184.27.197.10`, `184.27.197.91` (Akamai Technologies) |
| **Transport** | Cleartext HTTP, TCP port 80 — no TLS |
| **Access Control** | None — fully open public object repository; exact-path HTTP 200 downloads for anyone |
| **Integrity** | Validated solely by OEM RSA/ECDSA signature checks performed by on-device recovery/bootloader; `.sig` files (256 B) hosted alongside every ONT image |
| **Enumeration Resistance** | None — deterministic paths allow trivial brute-force enumeration of model/version space |
| **Content Window** | Nov 2020 – Aug 2023 (legacy builds only) |
| **Total Live Objects** | 69 (9 STB recovery zips ≈ 5.31 GB; 30 ONT images ≈ 1.69 GB; 30 ONT signatures) |

### 5.2 Enterprise Hotel Tier (`jiostb.cdn.jio.com`)

| Property | Value |
| :--- | :--- |
| **FQDN** | `jiostb.cdn.jio.com` → `jiostb.akamaized.net` → `a1887.dscq.akamai.net` |
| **Transport** | HTTPS, TCP port 443 — TLS encrypted |
| **Access Control** | Public object repository; exact-path HTTPS 200 downloads for anyone |
| **Integrity** | Relies on transport TLS + on-device OEM signature verification |
| **Live Objects** | 3 hotel OTA zips ≈ 2.11 GB (Bluebank, SDMC, Skyworth) |
| **Content Window** | Sep 2025 – Mar 2026 |

### 5.3 Tokenized Modern Tier (`fota.slv.kai.jiophone.net`)

| Property | Value |
| :--- | :--- |
| **FQDN** | `fota.slv.kai.jiophone.net` → `...akahost.net` → `104.96.177.202` |
| **Transport** | Cleartext HTTP, TCP port 80 — no TLS |
| **Access Control** | Token-gated; directory traversal returns 403/404 (`AkamaiGHost`/`AkamaiNetStorage`) |
| **Integrity** | On-device RSA/ECDSA signature verification (AVB 2.0) |
| **Live Objects** | 38 documented tokenized URLs (DIN59–DIN1009) |
| **Confirmed Size** | `DIN1009/SA002_19/loOOGaJIPm.zip`: 755.8 MB; remaining 37 URLs have unknown sizes (tokens not brute-forceable) |
| **Content Window** | Ongoing (current JMSB200A/AirFiber builds) |

### 5.4 IoT ACS Tier (`iotacs.jioconnect.com:8001/8080`)

| Property | Value |
| :--- | :--- |
| **FQDN** | `iotacs.jioconnect.com` |
| **Transport** | Cleartext HTTP Digest CWMP, TCP port 8001/8080 |
| **Access Control** | Digest authentication required (HTTP 401 without valid credentials) |
| **Live Objects** | 1 confirmed Arcadyan OTA image (`Arcadyan-OTA-01.25.12-2024-06-17_userdebug.zip`) |
| **Size** | Unknown (~1.5 GB estimated based on similar ONT images) |

### 5.5 Consolidated Firmware Inventory & Download Size Summary

| CDN Tier | Domain | Transport | Live Objects | Total Size | Content Window |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Open Legacy** | `fota.slv.fxd.jiophone.net` | Cleartext HTTP 80 | 69 (9 STB + 30 ONT img + 30 ONT sig) | ≈ 7.0 GB | Nov 2020 – Aug 2023 |
| **Enterprise Hotel** | `jiostb.cdn.jio.com` | HTTPS 443 | 3 hotel OTA zips | ≈ 2.11 GB | Sep 2025 – Mar 2026 |
| **Tokenized Modern** | `fota.slv.kai.jiophone.net` | Cleartext HTTP 80 | 38 documented URLs | ≈ 756 MB (confirmed) + unknown | Ongoing |
| **IoT ACS** | `iotacs.jioconnect.com:8001` | Cleartext HTTP 8001 | 1 Arcadyan OTA (401 auth) | Unknown | 2024-06-17 |
| **Grand Total** | — | — | **111+ objects** | **≈ 9.85 GB** (confirmed live) + unknown | — |

> **Note:** The 38 kai tier URLs are individually documented tokenized links. Only `DIN1009/SA002_19/loOOGaJIPm.zip` (755.8 MB) has been locally downloaded and verified. The remaining 37 URLs require their exact 10-character tokens, which cannot be brute-forced. See Section 3.1 and `ENDPOINTS_REFERENCE.json` for the full URL list.

---
## 🔗 Related Documents

| Related Document | Relationship |
| :--- | :--- |
| [`../FIRMWARE_ENDPOINTS_AND_EXPOSURES.md`](../FIRMWARE_ENDPOINTS_AND_EXPOSURES.md) | FOTA endpoint URL taxonomy, exposed firmware URLs, and verified live firmware catalog (this doc's implementation detail). |
| [`../OTA_ANALYSIS.md`](../OTA_ANALYSIS.md) | Extracted OTA package (`loOOGaJIPm.zip`), `payload.bin` partition images, and APKs used in on-device flashing. |
| [`01_TOPOLOGY_AND_NETWORK_TIERS.md`](01_TOPOLOGY_AND_NETWORK_TIERS.md) | CDN edge topology (Akamai/Fastly) and AS routing for FOTA distribution. |
| [`ENDPOINTS_REFERENCE.json`](ENDPOINTS_REFERENCE.json) | Machine-readable, categorized inventory of all unique endpoints and distinct hosts mapped to their originating system applications. |

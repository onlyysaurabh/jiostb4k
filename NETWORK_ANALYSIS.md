# Jio 4K STB Network Traffic Analysis & Endpoint Documentation

Analysis and documentation of network connections originating from the Jio 4K Android TV Set-Top Box (IP: `192.168.2.137`) during boot, idle, and normal runtime operations behind an OpenWrt gateway.

---

## 1. Traffic Summary & Categorization

| Category | Endpoints / Hosts | Protocols / Ports | Volume | Primary Function |
| :--- | :--- | :--- | :--- | :--- |
| **Heavy CDN / Updates** | `a104-96-177-202...akamaitechnologies.com` | TCP / 80 (HTTP) | **306.42 MiB** | OTA Firmware Update / App APK download / HLS VOD payload |
| **Jio TR-069 Device Mgmt** | `49.40.8.93` (`acs.oss.jio.com`) | TCP / 8443, 9443 | ~485 KiB (13 flows) | CWMP / TR-069 Remote Management (WildFly 10, JBoss) |
| **Jio CDN (UI & Assets)** | `167.82.58.144` (`*.cdn.jio.com` via Fastly) | TCP / 443, 80 | ~135 KiB (47 flows) | Launcher posters, UI channel thumbnails, EPG icons |
| **ISP On-Net Akamai CDN** | `203.192.234.147/.153` (`in2cable.com`) | TCP / 443 (HTTPS) | ~450 KiB (10 flows) | On-net Akamai edge cache (`a248.e.akamai.net`) in user's ISP |
| **Jio Core APIs & Auth** | `103.63.129.21` (`api.jio.com`), `49.40.48.224` (`bs.jio.com`) | TCP / 443 (HTTPS) | ~15 KiB | Device registration, subscriber entitlement check, BigIP API |
| **Google Android TV Core** | `1e100.net`, `*.googleapis.com`, `edgedl.me.gvt1.com` | TCP / 443 (HTTPS) | ~65 KiB | Google Play Services checkin, GVT1 downloads, FCM notifications |
| **Connectivity & Time** | `dns.google` (ICMP), Linode NTP (UDP 123) | ICMP, UDP / 123 | < 2 KiB | Network reachability ping test, NTP wall-clock synchronization |
| **Local Discovery & LAN** | `192.168.2.255:5775`, `OpenWrt.lan` | UDP / 5775, 53, 67 | ~2.5 KiB | JioHome app local remote discovery, DHCP lease, DNS resolution |

---

## 2. Detailed Breakdown by Endpoint

### 2.1 Heavy Payload / Content Delivery (Akamai CDN)
- **Host / IP:** `a104-96-177-202.deploy.static.akamaitechnologies.com` (`104.96.177.202`)
- **Protocol / Port:** TCP 80 (HTTP / WWW)
- **Transfer Volume:** **306.42 MiB (329,476 packets)** in a single persistent flow.
- **Provider:** Akamai Technologies (AS16625)
- **Analysis & Purpose:** 
  - Over 99.7% of all recorded bandwidth went to this single Akamai edge server over cleartext HTTP.
  - Akamai hosts Jio's FOTA updates (`fota.slv.kai.jiophone.net` / Android TV OTA packages), system app APKs (JioTV, JioCinema, JioPages), and HLS/DASH media streaming segments.
  - Given the payload size (~306 MB) and single HTTP connection, this corresponds to an **Over-The-Air (OTA) OS firmware update download** or a batch download of preloaded system applications.

---

### 2.2 Jio Device Management & Remote Provisioning (TR-069 / ACS)
- **Host / IP:** `49.40.8.93`
- **Protocol / Ports:** TCP `8443` (10 flows) and `9443` (3 flows)
- **Network / AS:** AS55836 (Reliance Jio Infocomm Limited)
- **TLS Subject:** `CN=acs.oss.jio.com`, `O=Jio Platforms Ltd`, `OU=RJIL`
- **TLS Issuer:** `CN=RILSUBCA01` (Internal Reliance Enterprise Subordinate CA)
- **Server Software:** `WildFly/10` (JBoss Enterprise Application Server)
- **Analysis & Purpose:**
  - This is Jio’s centralized **Auto-Configuration Server (ACS)** using the CWMP / TR-069 (and TR-181 device data model) protocol.
  - The Jio STB communicates with `acs.oss.jio.com` to report device telemetry (signal strength, uptime, firmware build, MAC, serial number), query for pending provisioning commands, receive configuration profile updates, and trigger remote reboots or diagnostics.
  - Ports 8443 and 9443 run mutual/enterprise TLS secured by Jio's internal PKI.

  > Deep dive into what this ACS can do, RPCs, STB data model, and security/attack classes: see [TR069_ACS_RESEARCH.md](TR069_ACS_RESEARCH.md).

---

### 2.3 Jio UI Content Delivery Network (`*.cdn.jio.com` via Fastly)
- **Host / IP:** `167.82.58.144`
- **Protocol / Ports:** TCP `443` (HTTPS, 45 flows) and TCP `80` (WWW, 2 flows)
- **Network / AS:** Fastly, Inc. (NetName: `SKYCA-3`)
- **TLS Subject:** `CN=*.cdn.jio.com` (issued by GlobalSign Atlas TLS CA)
- **Transfer Volume:** ~135 KiB total (~2.6 KiB to 7.6 KiB per flow)
- **Analysis & Purpose:**
  - Fastly CDN edge node delivering Jio TV Launcher UI elements.
  - The rapid burst of 45+ concurrent and consecutive small HTTPS connections is the distinct fingerprint of the Android TV launcher rendering:
    - Channel thumbnails and logos
    - EPG (Electronic Program Guide) banners
    - Featured content carousel posters
    - Launcher category JSON configuration files

---

### 2.4 In-ISP Akamai Cache Nodes (`in2cable.com`)
- **Hosts:** `dhcp-192-234-153.in2cable.com` and `dhcp-192-234-147.in2cable.com`
- **Resolved IPs:** `203.192.234.153` and `203.192.234.147`
- **Network / AS:** AS17665 (IndusInd Media & Communications Ltd. / ONE Broadband / In2cable)
- **TLS Subject:** `CN=a248.e.akamai.net` (Akamai Technologies)
- **Protocol / Port:** TCP `443` (HTTPS, 10 flows)
- **Transfer Volume:** ~450 KiB total (~200 KiB in initial flows)
- **Analysis & Purpose:**
  - These are **Akamai Accelerated Network Partner (ANP / AISP) edge caching servers** physically deployed inside the upstream ISP's network (OneBroadband / In2cable).
  - Reverse DNS on In2cable's network formats PTR records by omitting the first octet (`203.192.234.x` -> `dhcp-192-234-x.in2cable.com`).
  - When the STB requests Akamai-hosted Jio HTTPS resources, Akamai's GeoDNS routes the client to the on-net cache inside the local ISP rather than transiting external transit backbones.

---

### 2.5 Jio Core APIs & Bootstrap Backend
- **1. `103.63.129.21` (TCP 443 & 80)**
  - **TLS Subject:** `CN=api.jio.com` (Reliance Industries Limited)
  - **Server Header:** F5 `BigIP` Application Delivery Controller
  - **Role:** Main authentication and service gateway. Used for device token validation, subscriber account status verification, and session generation.
- **2. `49.40.48.224` (TCP 443)**
  - **TLS Subject:** `CN=bs.jio.com` (SANs: `bs.jio.com`, `admin-bs.jio.com`, `api-bs.jio.com`, `ec-bs.jio.com`)
  - **Server Header:** Apache HTTP Server
  - **Role:** Jio Bootstrap Services (BS). Contacted on initial boot/wake to discover active service URLs, device registration policies, and configuration endpoints.

---

### 2.6 Google Android TV & Play Services
Because the Jio STB runs Android TV (Android 11), standard Google background daemons execute upon network initialization:

| Endpoint | IP / Host | TLS Identity / Role | Purpose |
| :--- | :--- | :--- | :--- |
| `123.35.104.34.bc.googleusercontent.com` | `34.104.35.123` | `CN=edgedl.me.gvt1.com` | Google Video Transmission (GVT1) CDN. Distributes Google Play Services component updates, WebView patches, and Widevine CDM security modules. |
| `172.217.118.4` | `172.217.118.4` | `CN=*.googleapis.com`, `*.clients6.google.com` | Android Device Configuration Service & Google Play API (`android.clients.google.com`, `checkin.gstatic.com`). |
| `142.251.150.119` | `142.251.150.119` | `CN=www.google.com` | Captive portal detection endpoint (`connectivitycheck.gstatic.com` / `generate_204`) and Google search integration. |
| `1e100.net` Nodes | `pt-in-f138`, `cn-in-f94`, `lcboma-au-in-f14` | Google Global Cache / Backbone | Persistent TLS pipes for **Firebase Cloud Messaging (FCM)** push notifications, Google Cast receiver registration, and Leanback launcher recommendations. |
| `dns.google` | `8.8.8.8` / `8.8.4.4` | ICMP Echo Request (6 packets, 168 B) | Android OS `NetworkMonitor` ping check to verify active WAN latency and packet loss. |

---

### 2.7 Local Network (LAN) & Gateway Traffic
- **`192.168.2.255:5775` (UDP Broadcast, 1.03 KiB / 15 packets):**
  - Broadcast sent to the local subnet broadcast address on UDP port `5775`.
  - **Purpose:** STB local discovery beacon. Used by the **JioHome** smartphone companion app and local home automation systems (e.g. RTI remote control integrations) to locate and pair with the STB on the local Wi-Fi/LAN without relying on cloud routing.
- **`OpenWrt.lan:BOOTPS` (UDP 67/68):**
  - Standard DHCP protocol negotiation (IP lease assignment and gateway configuration).
- **`OpenWrt.lan:DOMAIN` (UDP 53):**
  - Local DNS resolution queries directed to OpenWrt's `dnsmasq`.
  - *Note:* The source port `192.168.2.137:ZABBIX-TRAPPER` reflects client dynamic source port `10051`, labeled by OpenWrt's `/etc/services` table.

---

### 2.8 Time Synchronization (NTP)
- **Host / IP:** `172-235-18-237.ip.linodeusercontent.com:NTP` (`172.235.18.237`)
- **Protocol / Port:** UDP 123 (Network Time Protocol)
- **Transfer Volume:** 152 B (2 packets)
- **Purpose:** NTP pool time synchronization (`pool.ntp.org` / `time.android.com`). Android sets system wall-clock time on boot via NTP before establishing secure TLS sessions to ensure certificate validation succeeds.

---

## 3. Reverse Engineering & Security Observations

1. **Unencrypted HTTP Firmware/Payload Download (`104.96.177.202:80`):**
   - 306.42 MiB was pulled over plaintext HTTP (port 80).
   - *Security note:* Android OTA updates (.zip) and APK files downloaded over HTTP rely on cryptographic signature validation (RSA/ECDSA jar/zip signatures against OEM root keys in the recovery image or Android package manager) rather than transport layer encryption.
2. **ACS Communication (`acs.oss.jio.com`):**
   - The device management channel runs over high ports (8443, 9443) using an internal private CA (`RILSUBCA01`). Man-In-The-Middle (MITM) inspection requires extracting Jio's custom trust store or patching the TR-069 client binary in the firmware.
3. **Local Control Protocol (`5775/UDP`):**
   - UDP port 5775 broadcast traffic can be analyzed by capturing packets on the local subnet to reverse engineer the JioHome remote control protocol commands.

---

## 4. Live Gateway Interception Case Study

Using the prepared interceptor script (`scripts/capture_stb_urls.sh`) listening on OpenWrt's `br-lan` bridge, live HTTP requests and DNS queries were captured during STB initialization and software update check:

### 4.1 Captured Requests & Payloads
1. **Google Captive Portal Check:**
   ```http
   GET /generate_204 HTTP/1.1
   Host: connectivitycheck.gstatic.com
   ```
   * *Outcome:* Returned HTTP 204 No Content, confirming WAN connectivity to Android OS `NetworkMonitor`.
2. **JioTV Cloud DVR Configuration:**
   ```http
   GET /cloud_dvr/services_0.json HTTP/1.1
   Host: jiotv.data.cdn.jio.com
   ```
   * *Server:* Fastly / Varnish reverse proxy.
   * *Behavior:* Returns HTTP 450 Forbidden unless accompanied by authorized subscriber session headers or originating from Jio on-net IP subnets.
3. **Full System OTA Firmware Update:**
   ```http
   GET /BHTS/DIN1009/SA002_19/loOOGaJIPm.zip HTTP/1.1
   Host: fota.slv.kai.jiophone.net
   ```
   * *Server:* `104.96.177.202:80` (Akamai Technologies / `AkamaiNetStorage`).
   * *Status:* `HTTP/1.1 200 OK` (Content-Length: 792,517,294 bytes / 755.80 MB).
   * *Result:* Downloaded and extracted into full Android system partition images. For complete analysis, see [OTA_ANALYSIS.md](OTA_ANALYSIS.md).

---
## 🔗 Related Documents

| Related Document | Relationship |
| :--- | :--- |
| [`TR069_ACS_RESEARCH.md`](TR069_ACS_RESEARCH.md) | Deep research on the CWMP/TR-069 ACS protocol, STB data model (TR-181/TR-135), and security posture (§2.2 cross-reference). |
| [`FIRMWARE_ENDPOINTS_AND_EXPOSURES.md`](FIRMWARE_ENDPOINTS_AND_EXPOSURES.md) | FOTA CDN tiers, exposed firmware URLs, and URL path taxonomy for the heavy CDN payload observed in §2.1. |
| [`VOICE_DYNAMIC_CONFIG_RESEARCH.md`](VOICE_DYNAMIC_CONFIG_RESEARCH.md) | Voice dynamic config endpoints and the diagnostic PIN `777333` research. |
| [`jio_infrastructure/01_TOPOLOGY_AND_NETWORK_TIERS.md`](jio_infrastructure/01_TOPOLOGY_AND_NETWORK_TIERS.md) | Autonomous System routing (AS55836, AS16625, AS54113), IP blocks, IPv6 prefixes, and DNS CNAME chains for the endpoints observed here. |

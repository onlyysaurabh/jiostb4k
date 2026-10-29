# Jio 4K STB — TR-069 / ACS Deep Research

**Target:** `49.40.8.93` (`acs.oss.jio.com`), TCP `8443` (10 flows) and `9443` (3 flows)
**Organization:** AS55836 (Reliance Jio Infocomm Limited)
**TLS Subject:** `CN=acs.oss.jio.com`, `O=Jio Platforms Ltd`, `OU=RJIL`
**TLS Issuer:** `CN=RILSUBCA01` (internal Reliance subordinate CA)
**Server Software:** `WildFly/10` (JBoss Enterprise Application Server)
**Protocol:** CWMP / TR-069 (Broadband Forum) over TR-181 (Device:2.x) + TR-135 (STBService) data model
**Source context:** `NETWORK_ANALYSIS.md` §2.2, hardware teardown (`TEARDOWN.md`), OTA payload, JioHome UDP discovery

> This document is defensive/research analysis of the author's own device and network. It documents
> what the ACS channel *can* do, its trust model, and known attack classes. It is not an exploit
> playbook against Jio infrastructure.

---

## 1. What TR-069 / CWMP Actually Is

TR-069 (CPE WAN Management Protocol, CWMP) is a SOAP-over-HTTP(S) RPC protocol defined by the
Broadband Forum. It gives a carrier's **Auto-Configuration Server (ACS)** bidirectional remote
management of a **Customer Premises Equipment (CPE)** device — here the Jio 4K Android TV STB.

Key architectural facts:

- **CPE initiates.** The STB always opens the TCP/TLS session *outbound* to the ACS. The ACS never
  connects inbound to the STB. This is how it traverses NAT.
- **Request/response ping-pong.** Each HTTP POST carries one SOAP envelope (either an `Inform` from
  the CPE or an RPC from the ACS). The peer replies in the HTTP response. A session continues until
  both sides send empty bodies.
- **Periodic + event-driven.** The CPE calls `Inform` on boot, on periodic timer, on connection
  request, and on value-change events.
- **ACS has near-unconditional control.** Anything the data model exposes as writable, plus
  `Download`/`Upload`/`Reboot`/`FactoryReset`, is at the ACS's disposal. As the literature puts it,
  an ACS that controls a device has control equivalent to physical access + root shell.

---

## 2. Session Mechanics

### 2.1 Inform (the CPE's opening move)

Every session starts with an `Inform` RPC from the STB containing:

| Field | Example / meaning |
|---|---|
| `DeviceId.Manufacturer` | e.g. `Skyworth` / `Jio` |
| `DeviceId.OUI` | vendor OUI |
| `DeviceId.ProductClass` | STB model class |
| `DeviceId.SerialNumber` | unit serial |
| `Event` codes | `0 BOOTSTRAP`, `1 BOOT`, `2 PERIODIC`, `6 CONNECTION REQUEST`, `M Reboot`, `M Download`, … |
| `CurrentTime`, `RetryCount` | |
| `ParameterList` | key telemetry snapshot (see §4) |

The ACS authenticates the STB (typically HTTP Digest or mutual TLS / client cert), then replies
with zero or more RPCs, each answered by the STB in the next POST.

### 2.2 ACS RPCs (what the server can ask the STB to do)

Standard CWMP RPCs (TR-069 §A.3):

| RPC | Direction | What it does on the STB |
|---|---|---|
| `Inform` | CPE→ACS | Boot/periodic/event report |
| `GetRPCMethods` | either | Capability discovery |
| `GetParameterNames` | ACS→CPE | Walk the data model tree |
| `GetParameterValues` | ACS→CPE | Read any parameter (telemetry, creds, config) |
| `SetParameterValues` | ACS→CPE | Write any writable parameter |
| `GetParameterAttributes` / `SetParameterAttributes` | ACS→CPE | Notification/access control on params |
| `AddObject` | ACS→CPE | Create multi-instance object (e.g. new WAN conn, firewall rule) |
| `DeleteObject` | ACS→CPE | Remove an instance |
| `Download` | ACS→CPE | Push a file: firmware, config, web content, vendor config file |
| `Upload` | ACS→CPE | Pull a file *from* the STB to the ACS |
| `Reboot` | ACS→CPE | Force reboot |
| `FactoryReset` | ACS→CPE | Wipe to defaults |
| `GetQueuedTransfers` | ACS→CPE | Status of pending transfers |
| `ScheduleInform` | ACS→CPE | Ask CPE to call back at a given time |
| `SetVouchers` | ACS→CPE | License/voucher provisioning |
| `ChangeDUState` | ACS→CPE | Install/remove software modules (DU = Deployment Unit) |
| `X_*` | ACS→CPE | Vendor extensions (Jio/Skyworth custom) |

### 2.3 Connection Request (ACS-initiated wake-up)

Although the CPE initiates TCP, the ACS can request an *immediate* session by having the STB expose
a **Connection Request URL** (`Device.ManagementServer.ConnectionRequestURL`). The ACS HTTP-GETs that
URL; the STB then initiates a normal Inform with event code `6 CONNECTION REQUEST`.

- On many devices this endpoint is **unauthenticated or weakly authenticated** (e.g. `admin/admin`,
  or no auth at all). The RC400L research notes ConnectionRequest auth disabled (`Auth=0`).
- Misfortune Cookie (CVE-2014-9222) and related bugs targeted exactly this endpoint on port 7547.
- For the Jio STB the connection-request URL is whatever the STB reports in its Inform; reachable
  only from Jio's network side, but if exposed/leaked it is a session-initiation primitive.

### 2.4 Authentication

- TR-069 supports HTTP Basic/Digest and TLS client certificates.
- The Jio STB trusts `CN=RILSUBCA01` (internal CA) and presents itself via mutual/enterprise TLS
  on `8443`/`9443`. No public CA is involved, so inspection requires extracting Jio's trust store
  or patching the client (see §7).
- ACS-side identification is commonly just `OUI-ProductClass-SerialNumber` (the `DeviceId`), which
  the arXiv paper flags as insecure: serial-number-based auth lets an attacker who learns a serial
  impersonate that device and pull its config (including VoIP/PPPoE creds).

---

## 3. What the Ports Likely Are

Both endpoints are on the same IP/AS and same internal CA, but two distinct ports:

| Port | Observed flows | Hypothesis |
|---|---|---|
| `8443` | 10 flows | Primary CWMP ACS endpoint (Inform + RPC exchange) |
| `9443` | 3 flows | Secondary: connection-request callback, STUN/NAT-traversal helper, or a second ACS instance / tenant (e.g. `macs.oss.jio.com` vs `acs.oss.jio.com` style split seen on JioFi). JioFi JMR540 research shows `macs.oss.jio.com` as a distinct ACS hostname. |

Without a packet capture of the TLS plaintext this cannot be confirmed; the split is worth
verifying via SNI/ALPN observation.

---

## 4. STB Data Model — What the ACS Can Read/Write

The STB implements **TR-181 Device:2.x** (core device data model) plus **TR-135 STBService:1.x**
(AV/STB-specific). Combined, this gives the ACS:

### 4.1 DeviceInfo / ManagementServer (TR-181)
- `Device.DeviceInfo.HardwareVersion`, `SoftwareVersion`, `ProvisioningCode`, `SerialNumber`,
  `Manufacturer`, `ManufacturerOUI`, `ModelName`, `ProductClass`
- `Device.DeviceInfo.UpTime`, memory/CPU, temperature (where exposed)
- `Device.ManagementServer.URL`, `Username`, `Password`, `ConnectionRequestURL`,
  `ConnectionRequestUsername/Password`, `PeriodicInformInterval`, `PeriodicInformEnable`,
  `ParameterKey`
- `Device.Time.*` (NTP)

### 4.2 Networking (TR-181)
- WAN interface status, IP, DNS, MAC addresses of LAN clients, DHCP leases
- `Device.WiFi.*` SSID/passphrase, radio stats, client list, channel, TX power
- Firewall/NAT/port-mapping rules (`AddObject`/`DeleteObject` on firewall chains)
- DNS proxy / hosts

### 4.3 STB-specific (TR-135 STBService)
- Front-end / tuner: signal quality, BER, SNR, lock status, frequency, modulation
- AV streams: active inbound/outbound IP streams, RTCP receiver reports, RTP/AVPF, FEC
- `Components.FrontEnd.*` (DVB/OTT front-end parameters)
- Display/output settings, HDMI, resolution, volume caps
- Application/DRM state (Widevine) where exposed by vendor extensions

### 4.4 Diagnostics (TR-143 / TR-181 diagnostics)
- ICMP ping test (`Device.IP.Diagnostics.IPPing`)
- Traceroute
- Download/upload throughput tests (HTTP/FTP) — the ACS can make the STB pull/push test files
- DNS diagnostics
- These are the basis of "remote support" ping/traceroute/speedtest from the ACS.

### 4.5 Firmware / software (TR-181 + DU)
- `Download` with `FileType = "1 Firmware Upgrade Image"` or `"2 Web Content"` / `"3 Vendor Configuration File"` / `"4 Tone File"` / `"5 Ringer File"`
- `ChangeDUState` for software modules (apps, middleware) if the STB supports DU management
- `FactoryReset`, `Reboot`

### 4.6 Telemetry the STB reports (from NETWORK_ANALYSIS)
Uptime, signal quality, hardware revision, firmware version, MAC, serial number, and (on JioFi)
IMSI — i.e. the ACS receives a device fingerprint plus network-quality time series.

### 4.7 Proprietary Vendor Extensions (`Device.JioSTB.*`)
Decompilation of `TR069.apk` (`com.jio.tr069client` v4.2.3) revealed proprietary vendor trees:
- **`Device.JioSTB.USB.USBDebugging`**: Writable boolean parameter. Directly sets `Settings.Global.adb_enabled = 1`. Combined with `service.adb.tcp.port=5555` in `vendor/build.prop`, it automatically opens Network ADB on TCP port 5555 over Wi-Fi and Ethernet.
- **`Device.JioSTB.USB.DebugValidityDate`**: ISO8601 validity timestamp. Defaults to 24 hours via `Utility.getNext24HrISOCurrentDateTime()`. On timeout, an alarm reverts `adb_enabled` to `0`.
- **`Device.JioSTB.Debugging.Command.*`**: Remote Command Line Utility (CLU) subsystem. Supports executing `settings put global ...` or native shell commands via `Runtime.getRuntime().exec()`, returning outputs in `Device.JioSTB.Debugging.Command.Output`.
- *For complete decompilation proofs, code traces, and SOAP envelopes, see [TR069_REMOTE_ADB_ANALYSIS.md](TR069_REMOTE_ADB_ANALYSIS.md).*

---

## 5. What an ACS Operator Can Concretely Do

Combining the RPCs + data model, the legitimate (Jio) use cases — and the abuse cases if the ACS
or its credentials are compromised — include:

1. **Zero-touch provisioning.** On first boot (`0 BOOTSTRAP`) push Wi-Fi baseline, NTP, DNS,
   middleware config, app list, entitlements.
2. **Remote configuration changes.** Change SSID/PSK, admin password, check-in interval, WAN mode,
   DNS, firewall rules, port forwards, parental controls.
3. **Firmware management.** Push OTA images via `Download` (the 306 MiB Akamai HTTP payload is the
   delivery; the ACS decides *when/whether* to install). `UpgradesManaged=1` style flags confirm
   ACS upgrade authority.
4. **Diagnostics & support.** Run ping/traceroute/speedtest from the STB, read signal metrics,
   reboot a misbehaving unit, factory-reset on RMA.
5. **Telemetry & analytics.** Periodic Inform (`2 PERIODIC`) carries QoE metrics, viewing/network
   stats, error counts — basis for service-quality dashboards and (potentially) viewing analytics.
6. **Software module management.** Install/remove apps or middleware components via DU if supported.
7. **Mass operations.** Because one ACS serves the whole subscriber base, a single compromised ACS
   (or stolen ACS credential) reaches every STB: mass firmware push with backdoor, DNS redirection
   to rogue resolver, credential harvesting, DDoS enlistment (Mirai-class).

---

## 6. Security Posture & Known Attack Classes

### 6.1 Trust model weaknesses (general TR-069)
- **Single point of failure.** ACS compromise ⇒ all devices. No per-device consent or attestation.
- **Serial-number / IP-based auth.** Common in open-source ACS (GenieACS/OpenACS): device
  identified by serial number only. Hardcoded credentials are prevalent. An attacker can impersonate
  a device and pull its config (VoIP/PPPoE creds, Wi-Fi PSK).
- **Connection-request endpoint.** Often unauthenticated or `admin/admin`; accepts triggers from any
  host that can reach it. Combined with an ACS, full session initiation without CPE-side auth.
- **No certificate pinning** (JioFi research): ACS URL is writable in flash; DNS poisoning of
  `acs.oss.jio.com`/`macs.oss.jio.com` during an Inform redirects the STB to an attacker ACS.
- **MAC-derived credentials** (JioFi): password `0014A4-FAP_FC4008-{MAC}` reconstructable from
  Wi-Fi probe/beacon frames → ACS impersonation + parameter enumeration.
- **ODM shared keypair** (RC400L): RSA private key common across units and extractable from
  firmware; any ACS trusting that cert can't distinguish attacker from device.
- **Firmware integrity not visible.** Neither device config references signature verification for
  `Download`-pushed firmware. ACS upgrade authority with no additional validation visible.

### 6.2 Code injection via parameters
QA Cafe demonstrated that `SetParameterValues` writing a shell metacharacter value (e.g.
`` `ping ...` ``) into a parameter that is later passed unvalidated to a shell executes arbitrary
commands. Not a protocol bug per se, but a common implementation bug; affects any CWMP client that
shells out on parameter application. Relevant to Jio STB middleware that applies config via shell.

### 6.3 Historical CVEs / incidents
- **Misfortune Cookie** (CVE-2014-9222): RomPager TR-069 connection-request server, ≥12M gateways.
- **Mirai 2016**: exploited TR-064 (LAN-side config) exposed over WAN on port 7547 on many routers;
  shell injection turned devices into bots. Caused mass outages in Germany.
- **Check Point findings**: flaws in ACS vendor implementations allowing mass device takeover.
- **Tal @ Defcon 22 ("I hunt TR-069 admins")**: disclosed vulnerabilities in multiple ACS products,
  gained control of ~500k managed devices in one instance (advisories undisclosed for years).
- **Deutsche Telekom 2016 outage**: ~900k routers knocked offline via TR-069 endpoint abuse.

### 6.4 Jio-specific observations
- ACS runs **WildFly 10 / JBoss EAP** — an old application server; if the ACS itself is unpatched,
  it is a high-value target (Java deserialization, management console exposure, etc.).
- Internal CA (`RILSUBCA01`) means MITM inspection requires extracting Jio's trust store or
  patching the TR-069 client binary in firmware — the NETWORK_ANALYSIS note.
- JioFi JMR540 uses `macs.oss.jio.com` as ACS with MAC-derived creds and IMSI reporting — shows
  Jio's ACS ecosystem has had weak per-device auth in adjacent products. The STB's `acs.oss.jio.com`
  may share patterns; verify per unit.
- OTA firmware is delivered over **plaintext HTTP** from Akamai (`104.96.177.202:80`); reliance is
  on zip/jar signature validation, not transport security. A network attacker can tamper with the
  download in transit (integrity depends on signature verification being correct and enforced).
- Local control protocol on UDP `5775` (JioHome discovery) is a separate, analyzable surface.

---

## 7. Research Paths for This STB (defensive/authorized)

For the author's own device, the useful next steps are:

1. **Capture CWMP plaintext.** Extract the STB's trust store / client cert and CA, or patch the
   TR-069 client binary in the firmware, then MITM `49.40.8.93:8443/9443` via a local proxy
   (mitmproxy with the extracted CA). Record Inform + RPCs to learn the exact parameter names,
   periodic interval, connection-request URL, and what Jio actually pushes.
2. **Firmware/static analysis.** Unpack `ota_packages/loOOGaJIPm.zip` / `payload.bin`; locate the
   TR-069 client (likely Dimark or a Skyworth variant), its config XML, cert/key, and the ACS URL
   default. Check for hardcoded creds, cert pinning, signature verification of `Download`.
3. **UART.** Use the exposed `J7` TTL header and recovery switch `SK01` to get a shell, dump
   `/etc` config, the trust store, and the connection-request endpoint. Compare with JioFi findings.
4. **Connection-request probing.** From the LAN, locate the STB's reported `ConnectionRequestURL`
   and test its auth (only on your own device/network).
5. **Port disambiguation.** Determine what `9443` is (SNI/ALPN, second Inform, STUN) via capture.
6. **Parameter walk.** If a test ACS (e.g. GenieACS in a lab) can be pointed at the STB by
   changing `ManagementServer.URL` on the device, enumerate the data model with `GetParameterNames`
   to see exactly what Jio's firmware exposes. (Only on your own device; do not point at Jio's
   production ACS with modified identity.)
7. **Harden.** Block outbound to `49.40.8.93` at the gateway if you don't want management, or
   redirect to a local ACS for study; monitor for unexpected `Download`/`SetParameterValues`.

---

## 8. Caveats

- The `acs.oss.jio.com` endpoint is Jio's production ACS. Probing, impersonating devices, or
  attempting ACS takeover without authorization is illegal and out of scope.
- Capabilities described are those of the *protocol and data model*; the Jio STB firmware may
  implement only a subset, and vendor extensions (`X_*`) are not publicly documented.
- TR-069 is being superseded by **TR-369 / USP** for newer devices; Jio may migrate, but this STB
  is TR-069.

---

## References

- Broadband Forum TR-069 (CWMP) Amendment 6, TR-181 Device:2, TR-135 STBService:1, TR-143.
- Wikipedia, "TR-069" — https://en.wikipedia.org/wiki/TR-069
- Hils & Böhme, "Watching the Weak Link into Your Home" (arXiv 2001.02564).
- Tal, "I hunt TR-069 admins", Defcon 22 (2014).
- Tal & Oppenheim, "Too Many Cooks" / "Misfortune Cookie", 31c3 (2014).
- QA Cafe, "Is your TR-069 implementation vulnerable to code injection attacks?" (2017).
- Incognito TR-069 CWMP FAQ (2024).
- RDK TR-069 documentation (Dimark client).
- ResearchNotes_RC400L `TR069_CWMP.md` (JioFi JMR540 / Orbic RC400L analysis).
- This repo: `NETWORK_ANALYSIS.md`, `TEARDOWN.md`.

---
## 🔗 Related Documents

| Related Document | Relationship |
| :--- | :--- |
| [`TR069_REMOTE_ADB_ANALYSIS.md`](TR069_REMOTE_ADB_ANALYSIS.md) | Decompilation of `TR069.apk`: `Device.JioSTB.USB.USBDebugging` remote ADB parameter, `Device.JioSTB.Debugging.Command.*` CLU subsystem, SOAP payloads, and TLS trust analysis (§4.7 cross-reference). |
| [`NETWORK_ANALYSIS.md`](NETWORK_ANALYSIS.md) | Observed ACS traffic to `acs.oss.jio.com:8443/9443` (~485 KiB, 13 flows) in §2.2. |
| [`jio_infrastructure/02_DEVICE_MANAGEMENT_TR069_ACS.md`](jio_infrastructure/02_DEVICE_MANAGEMENT_TR069_ACS.md) | ACS server clusters (`acs.oss.jio.com`, `macs`, `iotacs`), dual-stack heartbeats, private PKI (`RILROOTCA`, `Jio Internal Server Sub CA`), embedded client private keys, and CWMP vendor extensions (`Device.JioSTB.*`). |
| [`jio_infrastructure/11_SECURITY_AUDIT_AND_ATTACK_SURFACE.md`](jio_infrastructure/11_SECURITY_AUDIT_AND_ATTACK_SURFACE.md) | §2.4 — Rogue ACS hijacking and remote CWMP management attack surface. |

# Jio 4K Set-Top Box (JMSB200A) Reverse Engineering & Hacking

All trademarks, copyrights, and intellectual property mentioned belong to their respective owners. This repository is for learning and educational experimentation only.

Hardware reverse engineering, firmware extraction, and vulnerability research for the **Jio 4K Android TV Set-Top Box** (Skyworth Digital HP44 series / board `5800-2AHP44T`, Amlogic S905X4).

Primary objective: educational research into device internals and firmware.

## 🎯 Goals

- **Enable ADB Debugging**: UI hides Developer Options/ADB. Paths: UART serial console, fastboot, TR-069 RPC, patched boot ramdisk.
- **Gain Root Access**: Patch `boot.img`/`vendor_boot.img` with Magisk or local privilege escalation in system services.
- **Unlock Bootloader**: Disable AVB 2.0 / dm-verity; bypass signature enforcement on Amlogic S905X4 (`@AML`).
- **Flash Custom ROMs**: Boot clean GSI / LineageOS / Slimbox / CoreELEC without Jio launchers, telemetry, or carrier restrictions.

## 📺 Device Specs

| Component | Specification |
|---|---|
| Model | Jio JMSB200A (`4KOTTSTB` / platform `sc2` / board `ohm`) |
| OEM / ODM | Skyworth Digital HP44 Series (PCB `5800-2AHP44T`) |
| SoC | Amlogic S905X4 (4× Cortex-A55 @ 2.0 GHz, Mali-G31 MP2) |
| RAM | 2 GB DDR4-3200 (2× Micron `MT40A512M16TB-062E:R`) |
| Storage | 32 GB eMMC 5.1 (Samsung `KLMBG2JETD-B041`) |
| OS | Android 11 (API 30, Kernel 5.4 GKI v3, build `25.1.9`) |
| Connectivity | Fast Ethernet + RTL8822CS (Wi-Fi 5 2×2 + BT 5.0) |
| Debug | Unpopulated 3.3V TTL UART header (`J7`, 921600 baud) & recovery switch (`SK01`) |

## 📚 Repository Contents

**Root-level research docs** (one canonical owner per topic; cross-linked via See Also):

| Document | Topic |
|---|---|
| [`TEARDOWN.md`](TEARDOWN.md) | Hardware teardown — PCB pinouts, UART `J7`, recovery button `SK01`, power topology |
| [`OTA_ANALYSIS.md`](OTA_ANALYSIS.md) | OTA package (`payload.bin`), partition layout, 20+ unpacked Jio priv-apps |
| [`ROOT_ADB_CUSTOM_ROM_GUIDE.md`](ROOT_ADB_CUSTOM_ROM_GUIDE.md) | Unlocking, ADB & custom ROM guide — Magisk patching, AVB 2.0 bypass, CoreELEC USB boot, debloat cheat sheet |
| [`AML_MASKROM_SECURITY_ANALYSIS.md`](AML_MASKROM_SECURITY_ANALYSIS.md) | MaskROM / WorldCup flashing — force MaskROM (short eMMC `CLK`→GND), AVB/dm-verity signing, eMMC short points |
| [`JDWP_SYSTEM_ESCALATION_FINDINGS.md`](JDWP_SYSTEM_ESCALATION_FINDINGS.md) | JDWP system-UID escalation — `jdb` attach to `JioCommandReceiver` (UID 1000) |
| [`NETWORK_ANALYSIS.md`](NETWORK_ANALYSIS.md) | Network traffic — CDN firmware endpoints, UDP 5775 discovery, carrier comms |
| [`TR069_ACS_RESEARCH.md`](TR069_ACS_RESEARCH.md) | TR-069 / ACS — CWMP mechanics, TR-181/TR-135 data model, security posture |
| [`TR069_REMOTE_ADB_ANALYSIS.md`](TR069_REMOTE_ADB_ANALYSIS.md) | TR069.apk remote ADB — `Device.JioSTB.USB.USBDebugging` (24h auto-disable), CLU shell, TLS trust |
| [`FIRMWARE_ENDPOINTS_AND_EXPOSURES.md`](FIRMWARE_ENDPOINTS_AND_EXPOSURES.md) | FOTA CDN tiers & exposed firmwares — `kai`, `fxd`, `jiostb.cdn.jio.com`, `iotacs`; `JioHttpUpdate.apk` (54321/TCP) |
| [`VOICE_DYNAMIC_CONFIG_RESEARCH.md`](VOICE_DYNAMIC_CONFIG_RESEARCH.md) | JioVoice dynamic config — `va-stb-config.json`, PIN `777333`, SOE backends |

**`jio_infrastructure/`** — 13-document master suite mapping Jio's backend ecosystem: AS routing/topology, TR-069 ACS clusters & private PKI, FOTA CDN distribution, auth/SSO, IPTV/DRM/EPG, Magnum telemetry & push, Mercury AdTech, voice AI (HelloJio/Reverie/SOE), direct IPs & LAN daemons, 88 privileged APKs & IPC catalog, security audit/attack surface, boot/TrustZone infra, network trust & SELinux (138 system CA certs). Includes [`ENDPOINTS_REFERENCE.json`](jio_infrastructure/ENDPOINTS_REFERENCE.json). See [`jio_infrastructure/README.md`](jio_infrastructure/README.md).

**`ota_packages/`** — Raw OTA `loOOGaJIPm.zip` + extracted partitions/APKs.
**`scripts/`** — `capture_stb_urls.sh`, `probe_firmwares.py`, `kai_fota_urls.py`, `pull_apks_adb.sh`.
**`img/`** — Teardown photos + eMMC short-point macros.
**`Housekeeping-PoC/`** — Two-stage bootloader unlock (TR-069/GenieACS ADB enable + CVE-2024-31317 zygote command injection). See [`Housekeeping-PoC/README.md`](Housekeeping-PoC/README.md).

## 🗺️ Primary Research Paths

**Enable ADB** — [`ROOT_ADB_CUSTOM_ROM_GUIDE.md`](ROOT_ADB_CUSTOM_ROM_GUIDE.md) §1 (10× OK within 4s → Developer Options → `adb connect <IP>:5555`); [`AML_MASKROM_SECURITY_ANALYSIS.md`](AML_MASKROM_SECURITY_ANALYSIS.md) §2 (MaskROM → patched `boot.img`); [`TR069_REMOTE_ADB_ANALYSIS.md`](TR069_REMOTE_ADB_ANALYSIS.md) (ACS auto-enables network ADB, 24h); [`TEARDOWN.md`](TEARDOWN.md) §6.1 (UART `J7` 921600 8N1).

**Gain root** — Magisk ramdisk patch ([`ROOT_ADB_CUSTOM_ROM_GUIDE.md`](ROOT_ADB_CUSTOM_ROM_GUIDE.md) §2 A); JDWP attach to `JioCommandReceiver` UID 1000 (§2 B + [`JDWP_SYSTEM_ESCALATION_FINDINGS.md`](JDWP_SYSTEM_ESCALATION_FINDINGS.md)); TR-069 CLU shell `Runtime.exec()` ([`TR069_REMOTE_ADB_ANALYSIS.md`](TR069_REMOTE_ADB_ANALYSIS.md) §4).

**Unlock bootloader / disable AVB dm-verity** — [`AML_MASKROM_SECURITY_ANALYSIS.md`](AML_MASKROM_SECURITY_ANALYSIS.md) §5; `fastboot flash vbmeta --disable-verity --disable-verification vbmeta.img` ([`ROOT_ADB_CUSTOM_ROM_GUIDE.md`](ROOT_ADB_CUSTOM_ROM_GUIDE.md) §2); [`Housekeeping-PoC/`](Housekeeping-PoC/) Stage 2 (CVE-2024-31317 flips `lock` bit, SELinux permissive).

**Flash custom ROMs / GSI** — [`ROOT_ADB_CUSTOM_ROM_GUIDE.md`](ROOT_ADB_CUSTOM_ROM_GUIDE.md) §3 — CoreELEC USB boot (recommended), Treble GSI (`arm-a`/`arm_bvN`, 32-bit userland on 64-bit kernel), `pm disable-user` debloating.

**Network & carrier infra** — [`NETWORK_ANALYSIS.md`](NETWORK_ANALYSIS.md), [`TR069_ACS_RESEARCH.md`](TR069_ACS_RESEARCH.md), [`FIRMWARE_ENDPOINTS_AND_EXPOSURES.md`](FIRMWARE_ENDPOINTS_AND_EXPOSURES.md), [`VOICE_DYNAMIC_CONFIG_RESEARCH.md`](VOICE_DYNAMIC_CONFIG_RESEARCH.md), [`jio_infrastructure/README.md`](jio_infrastructure/README.md).

## 🧪 Key Findings

| Finding | Severity |
|---|---|
| Network ADB on port 5555 hardcoded in `vendor/build.prop` | High |
| TR-069 `Device.JioSTB.USB.USBDebugging` enables ADB remotely (24h auto-disable) | High |
| Debuggable system app `JioCommandReceiver` (UID 1000) → JDWP system-UID escalation | High |
| AVB 2.0 / dm-verity bypassable in U-Boot; bootloader silicon-rooted via eFuse | Medium |
| Firmware over cleartext HTTP (port 80) on FOTA CDN tiers | Medium |
| Hardcoded diagnostic PIN `777333` in `va-stb-config.json` | Low/Medium |
| Cleartext SOE TTS at `49.40.64.194:8124`, no auth on base endpoint | Medium |
| UART `J7` shell suppressed in `user` build (`ro.debuggable=0`) | Low |

## ⚠️ Disclaimer

Research, security analysis, and educational purposes only. Modifying bootloaders/firmware can permanently brick hardware. The author is not responsible for bricked STBs or any damage caused by following these procedures.

# Jio 4K STB (JMSB200A) OTA Firmware & System Assets Analysis

Complete technical documentation and security reverse engineering analysis of the Android A/B OTA firmware package captured from the Jio 4K Set-Top Box (`192.168.2.137`), downloaded from Jio's FOTA server, and unpacked into native partition images and APKs.

---

## 1. Package Provenance & Interception Log

During live traffic interception via OpenWrt gateway (`scripts/capture_stb_urls.sh`), the set-top box initiated an unencrypted HTTP download on port 80 to an Akamai CDN edge server:

```http
GET /BHTS/DIN1009/SA002_19/loOOGaJIPm.zip HTTP/1.1
Host: fota.slv.kai.jiophone.net
User-Agent: Android
```

### 1.1 Archive Integrity & Storage
* **Source URL:** `http://fota.slv.kai.jiophone.net/BHTS/DIN1009/SA002_19/loOOGaJIPm.zip`
* **Edge Server:** `104.96.177.202` (Akamai Technologies / `AkamaiNetStorage`)
* **Local Package Path:** [`ota_packages/loOOGaJIPm.zip`](ota_packages/loOOGaJIPm.zip)
* **GitHub Release Asset:** [Download from GitHub Releases (v25.1.9)](https://github.com/onlyysaurabh/jiostb4k/releases/tag/v25.1.9)
* **Download Helper:** `./scripts/download_firmware.sh --all`
* **Archive Size:** 755.80 MB (792,517,294 bytes)
* **SHA-256 Checksum:** `e1e6d62e712d9e88ba504a9e0f907d20ae2f0e896060f70daddb9dc149ed8596`
* **OTA Format:** Android A/B Seamless Streaming Update (`ota-type=AB`)
* **Payload Size:** 792,512,816 bytes (stored uncompressed in zip container)

---

## 2. Firmware Build & Platform Identity

Extracted from `META-INF/com/android/metadata`, `vendor/build.prop`, and `oem/oem.prop`:

```properties
# Platform & Model Identity
ro.product.model=JMSB200A
ro.product.name=4KOTTSTB
ro.product.brand=Jio
ro.product.manufacturer=Jio
ro.product.device=MSTB
ro.board.platform=sc2                        # Amlogic S905X4 (SC2 Architecture Family)
ro.product.board=ohm                         # Skyworth / Droidlogic reference board
ro.product.vendor.brand=Skyworth
ro.product.vendor.manufacturer=Droidlogic

# Software & Operating System
ro.build.version.release=11                  # Android 11 (Red Velvet Cake)
ro.build.version.sdk=30                      # Android API Level 30
ro.vendor.build.id=25.1.9                    # Firmware Release Version
ro.vendor.build.version.incremental=1
post-build=Skyworth/JMSB200A/ohm:11/25.1.9/1:user/release-keys
post-security-patch-level=2024-02-05
ro.build.date=Wed Sep 30 16:40:26 IST 2026
ro.build.expect.bootloader=01.01.210312.151827
ro.odm.cast.ssid_suffix=i007
```

---

## 3. Cryptographic Signing & Integrity Verification

The update package is signed by Jio Platforms' proprietary root key stored in `META-INF/com/android/otacert`:

* **Certificate Subject:** `C=IN, ST=MH, L=Mumbai, O=Jio Platforms, OU=Jio, CN=JioHybridSTB, emailAddress=support@ril.com`
* **Certificate Issuer:** `C=IN, ST=MH, L=Mumbai, O=Jio Platforms, OU=Jio, CN=JioHybridSTB, emailAddress=support@ril.com`
* **Key Spec:** RSA 2048-bit, Exponent 65537 (`0x10001`)
* **Signature Algorithm:** `sha256WithRSAEncryption`
* **Validity Period:** May 31, 2023 08:56:50 GMT ➔ October 16, 2050 08:56:50 GMT
* **Payload Hash (`payload_properties.txt`):**
  * `FILE_HASH`: `YTOTxhoPNF277qRe12I0VfbI+KDrJzPr887t80z4yQg=`
  * `METADATA_HASH`: `ZKWQszmwib7ubISyrb/SWwhwvSXqVpT0dM5n+IR57f0=`

---

## 4. Unpacked Partition Images

All partitions extracted from `payload.bin` are located in [`ota_packages/extracted/partitions/`](ota_packages/extracted/partitions/):

| Partition File | Physical Size | Filesystem Format | Description |
| :--- | :--- | :--- | :--- |
| **`bootloader.img`** | 3.1 MB | AML Signed Binary | Amlogic BL2/BL30/BL31/U-Boot image (`@AML` magic header) |
| **`boot.img`** | 64 MB | Android Boot v3 (GKI) | ARM64 Linux Kernel (7.93 MB) + base ramdisk (9.03 MB) |
| **`vendor_boot.img`**| 24 MB | Android Vendor Boot v3| Vendor Ramdisk (4.24 MB) + kernel cmdline arguments |
| **`dtbo.img`** | 2.0 MB | Device Tree Blob Overlay | Amlogic DTBO overlay table |
| **`system.img`** | 1.33 GB | ext4 filesystem | Core Android 11 operating system, framework, and ART runtimes |
| **`vendor.img`** | 143 MB | ext4 filesystem | Amlogic S905X4 HALs, Mali G31 Bifrost GPU drivers, Wi-Fi blobs |
| **`product.img`** | 215 MB | ext4 filesystem | Operator product overlay, Netflix, Webview, Jio overlay APKs |
| **`system_ext.img`** | 59 MB | ext4 filesystem | Android TV SystemUI, DroidTvSettings, MicToggleProvider |
| **`oem.img`** | 32 MB | ext4 filesystem | Jio branding, `oem.prop`, and operator policies |
| **`odm.img`** | 928 KB | ext4 filesystem | Skyworth ODM hardware drivers |
| **`odm_ext.img`** | 16 MB | ext4 filesystem | Skyworth ODM peripheral extensions |
| **`vbmeta.img`** | 8.0 KB | AVB 2.0 Header | Android Verified Boot root descriptor |
| **`vbmeta_system.img`**| 4.0 KB | AVB 2.0 Header | System partition verified boot verification table |

---

## 5. Kernel, Bootloader & Storage Configuration

### 5.1 Boot Image Structure (`boot.img` & `vendor_boot.img`)
- **Boot Header Version:** `v3` (Generic Kernel Image / GKI architecture)
- **Kernel Compression:** LZ4 / GZIP compressed ARM64 Linux Kernel (8,314,504 bytes)
- **Vendor Kernel Command Line:**
  ```bash
  androidboot.dynamic_partitions=true androidboot.dtbo_idx=0 androidboot.boot_devices=soc/fe08c000.mmc use_uvm=1 buildvariant=user
  ```
  * `soc/fe08c000.mmc`: Base hardware MMIO address for the Samsung eMMC 5.1 controller on Amlogic S905X4.
  * `androidboot.dtbo_idx=0`: Directs the bootloader to apply index 0 from `dtbo.img`.

### 5.2 Storage Partition Table & Encryption (`vendor/etc/fstab.amlogic`)
The device utilizes dynamic super partitions with Android Verified Boot (AVB) and File-Based Encryption (FBE):
* **`/data` Partition:** Formatted as `ext4` with **`fileencryption=aes-256-xts`** (hardware cryptographic keys anchored in OP-TEE TrustZone).
* **`/metadata` Partition:** Handles per-user and per-credential encryption key directories (`/metadata/vold/metadata_encryption`).
* **`/mnt/vendor/param`:** Amlogic parameter storage partition holding the device MAC address, serial number, and HDCP 2.2 / Widevine factory keys.
* **`/mnt/vendor/tee`:** Dedicated non-volatile storage partition for OP-TEE TrustZone security applets.
* **`ZRAM Swap`:** 1,073,741,824 bytes (1.0 GB compressed ZRAM swap space) to augment the 2 GB physical DDR4 RAM.

---

## 6. Hardware Subsystem & Driver Verification

Inspecting `vendor.img:lib/modules/` and `vendor.img:firmware/` definitively confirms the exact hardware modules on the board:

### 6.1 Wireless Subsystem (Wi-Fi 5 + Bluetooth 5.0)
- **Verified Chipset:** **Realtek RTL8822CS** (2×2 MIMO Dual-Band 802.11a/b/g/n/ac + Bluetooth 5.0).
- **Physical Component:** Stamped RF shield `UW01` connected to IPEX antennas `J2` and `J4` on the PCB.
- **Kernel Modules:** `8822cs.ko` and `88x2es.ko` (SDIO Wi-Fi) alongside `rtk_btusb.ko` / `sdio_bt.ko` (Bluetooth HCI).
- **Firmware Blobs:** `rtl8822cs_fw`, `rtl8822cs_config`, `rtl8822c_fw`.

### 6.2 Graphics & Video Processing Unit (VPU)
- **GPU Driver:** ARM Mali Bifrost driver (`mali.ko`) supporting Mali-G31 MP2.
- **Hardware Codec Drivers (Amlogic Meson VPU):**
  * `amvdec_av1.ko` — Hardware AV1 4K@60fps 10-bit decoder.
  * `amvdec_h265.ko` / `amvdec_h265_v4l.ko` — Hardware HEVC Main10 decoder.
  * `amvdec_vp9.ko` — Hardware Google VP9 Profile 2 decoder.
  * `amvdec_h264.ko`, `amvdec_avs.ko`, `amvdec_avs2.ko` — Legacy & Indian broadcast codec decoders.
  * `hdr10_tmo_alg.ko` — Hardware HDR10 tone mapping algorithm.

### 6.3 Digital TV Demodulator & Tuner Interface
- **Demodulator Driver:** `cxd2856_fe.ko` (Sony CXD2856 DVB-T/T2/C demodulator frontend driver).
- **Transport Stream Demux:** `dvb_demux.ko`, `ci.ko` (Common Interface).

### 6.4 Security, DRM & Conditional Access (CAS)
- **TrustZone OS:** `optee.ko` and `optee_armtz.ko` (Linaro OP-TEE implementation for Amlogic).
- **IPTV Conditional Access:** Verimatrix (`libverimatrixplugin.so`, `libvmxca_client.so`, `libvmxca_iptvclient.so`).
- **Widevine DRM:** Widevine L1 CAS (`libdec_ca_wvcas.so`, `liboemcrypto.so`, `libcasoemcrypto.so`).

---

## 7. Extracted Applications, Launcher & Overlays

All APKs are dumped in [`ota_packages/extracted/apks/`](ota_packages/extracted/apks/):

### 7.1 Remote Control & Keymapping (`JioOverlay.apk`)
Decompiling `JioOverlay.apk` exposes the global key intercepts configured for the Bluetooth voice remote:
- **Consumer Launcher Receiver:** `com.iwedia.ui.rjio.launcher.reliance/.receiver.GlobalKeyReceiver`
  * Confirms the Jio TV Home launcher is developed by **iWedia** on top of Android Leanback.
- **Hotel Mode Receiver:** `com.jio.stb.hotellauncher/.receiver.GlobalKeyReceiver`
- **Intercepted Keycodes:**
  * `KEYCODE_VOICE_ASSIST` (Triggers Google Assistant / Jio Voice).
  * `KEYCODE_TV` (Direct TV Live playback).
  * `KEYCODE_HELP` (Customer care / diagnostics).
  * `KEYCODE_M`, `KEYCODE_U`, `KEYCODE_TAB`.
  * `KEYCODE_F4` through `KEYCODE_F12` (Reserved shortcut hotkeys).
- **IR Remote Custom Code:** Defined in `vendor/etc/remote.tab1` as custom code `0xfb04` (NEC protocol).

### 7.2 Core System Applications
* [`SystemUI.apk`](ota_packages/extracted/apks/system_ext/SystemUI.apk) (25 MB) — Android TV System UI, custom volume HUD, and notification shade.
* [`DroidTvSettings.apk`](ota_packages/extracted/apks/system_ext/DroidTvSettings.apk) (14 MB) — Skyworth/Amlogic Settings application with display resolution, HDR, audio pass-through, and CEC toggles.
* [`DroidLiveTvSettings.apk`](ota_packages/extracted/apks/product/DroidLiveTvSettings.apk) — Live TV channel manager and input switcher.
* [`DroidLogicTvInput.apk`](ota_packages/extracted/apks/vendor/DroidLogicTvInput.apk) (3.6 MB) — Amlogic TV Input Framework (TIF) hardware abstraction layer.
* [`MicToggleProvider.apk`](ota_packages/extracted/apks/system_ext/MicToggleProvider.apk) (17 KB) — Hardware microphone privacy toggle service.
* [`Netflix.apk`](ota_packages/extracted/apks/product/Netflix.apk) (95 MB) — Pre-certified Netflix Android TV client.
* [`webview.apk`](ota_packages/extracted/apks/product/webview.apk) (84 MB) — Chromium-based Android System WebView runtime.

### 7.3 Extracted Jio Operator System Priv-Apps (`system.img`)
Over 828 MB of proprietary Jio carrier and operator services dumped into [`ota_packages/extracted/apks/jio_system_priv_app/`](ota_packages/extracted/apks/jio_system_priv_app/):

| Application Package | Size | Primary Function |
| :--- | :--- | :--- |
| **`TR069.apk`** | **22 MB** | Carrier CWMP / TR-069 management client connecting to `acs.oss.jio.com`. Implements RPC methods, device telemetry, diagnostics, and parameter manipulation. Contains native library `libirInfo.so`. |
| **`JioLauncher.apk`** | **74 MB** | Flagship consumer Android TV home launcher developed by iWedia for Jio. Renders content carousels, recommendation feeds, and OTT shortcuts. |
| **`JioHotelLauncher.apk`**| **61 MB** | Commercial hospitality / hotel mode launcher profile with locked settings, billing integration, and restricted guest access. |
| **`JioSettings.apk`** | **78 MB** | Jio-branded custom TV settings app managing network, audio, display, account, and parental controls. |
| **`JioLiveTV.apk`** | **16 MB** | Dedicated linear TV playback application interfacing with DVB demodulator and IP multicast streams. |
| **`JioHttpUpdate.apk`** | **2.3 MB** | FOTA (Firmware Over-The-Air) update daemon that queries `fota.slv.kai.jiophone.net` and downloads OTA packages. |
| **`JioUsbUpdate.apk`** | **1.5 MB** | Offline firmware flashing utility triggered by USB drive insertion. |
| **`JioCast.apk`** | **17 MB** | Proprietary screen mirroring and media casting receiver service. |
| **`JioMrServer.apk`** | **13 MB** | Media Renderer / Multi-Room media streaming server daemon. |
| **`JioProfileUtility.apk`**| **12 MB** | User profile manager, subscriber account binding, and personalization. |
| **`JioMemoryManager.apk`**| **9.7 MB**| Memory optimizer and aggressive background task killer designed for 2 GB RAM STBs. |
| **`JioRemoteDiagnostics.apk`**| **9.6 MB** | Hardware diagnostic collector (Wi-Fi RSSI, eMMC wear level, SoC temperature, HDMI status). |
| **`JioBackgroundScheduler.apk`**| **9.0 MB** | Background maintenance task scheduler (periodic log uploads, cache pruning, sync). |
| **`JioCommandReceiver.apk`**| **6.5 MB** | IPC command dispatcher for remote and local control signals (port 5775 UDP). |
| **`JioSCIService.apk`** | **5.5 MB** | Smart Card Interface (SCI) service for CAS smartcard / security token communication. |
| **`JioRcuUpdate.apk`** | **3.7 MB** | Bluetooth Remote Control Unit (RCU) Over-The-Air firmware update manager. |
| **`JioStore.apk`** | **15 MB** | Proprietary operator app store client for curated Jio TV apps. |
| **`JioStbSsoService.apk`**| **1.8 MB** | Single Sign-On (SSO) authentication daemon validating credentials with `api.jio.com`. |
| **`JioSphere.apk`** | **45 MB** | JioSphere Web Browser tailored for TV remote D-Pad navigation. |
| **`JioVoice.apk`** | **8.2 MB** | Multilingual voice search and voice assistant integration. |
| **`TeamViewerAddon.apk`**| **4.2 MB** | Remote customer support agent screen control and troubleshooting daemon. |


---
## 🔗 Related Documents

| Related Document | Relationship |
| :--- | :--- |
| [`FIRMWARE_ENDPOINTS_AND_EXPOSURES.md`](FIRMWARE_ENDPOINTS_AND_EXPOSURES.md) | FOTA CDN URL taxonomy, verified live firmware/signatures catalog, and on-device update tools (`JioHttpUpdate.apk`). |
| [`ROOT_ADB_CUSTOM_ROM_GUIDE.md`](ROOT_ADB_CUSTOM_ROM_GUIDE.md) | Flashing extracted `boot.img`/`vendor_boot.img` with Magisk, AVB 2.0 bypass, and custom ROM installation. |
| [`jio_infrastructure/03_FOTA_AND_FIRMWARE_DISTRIBUTION.md`](jio_infrastructure/03_FOTA_AND_FIRMWARE_DISTRIBUTION.md) | Master FOTA infrastructure: CDN tiers, tokenized hash generation, device taxonomy, and on-device flashing via `JioHttpUpdate.apk`. |
| [`TR069_REMOTE_ADB_ANALYSIS.md`](TR069_REMOTE_ADB_ANALYSIS.md) | TR-069 `Download` RPC that triggers the OTA package fetch and installation on the device. |

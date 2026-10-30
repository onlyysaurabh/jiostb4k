# Jio 4K STB (JMSB200A) Root, ADB & Custom ROM Guide

Comprehensive, actionable guide to unlocking, enabling ADB debugging, acquiring root access, and installing custom operating systems on the **Jio 4K Android TV Set-Top Box** (Model `JMSB200A`, Skyworth OEM platform `5800-2AHP44T`, Amlogic S905X4).

---

## 📋 Executive Architecture Summary

| Parameter | Specification | Reverse Engineering Implication |
| :--- | :--- | :--- |
| **SoC** | Amlogic S905X4 (Quad-Core Cortex-A55 @ 2.0 GHz) | Hardware AV1/VP9/HEVC decoding; ARM TrustZone & eFuse secure boot. |
| **Kernel & OS** | Android 11 (API 30), Kernel 5.4 GKI v3, build `25.1.9` | Dynamic super partitions (A/B slots), Android Verified Boot (AVB 2.0). |
| **Userland ABI** | **`armeabi-v7a` (32-bit ARM userland on 64-bit kernel)** | **CRITICAL**: Standard `arm64` GSIs will bootloop. Must use `arm-a` / `arm_bvN`. |
| **ADB Network Port** | `service.adb.tcp.port=5555` hardcoded in `vendor/build.prop` | Network ADB automatically listens on port `5555` once `adbd` is started. |
| **Stock Settings** | `com.android.tv.settings` (`DroidTvSettings.apk`) intact | Standard Developer Options and ADB toggle exist behind Jio's UI overlay. |

---

## 1. 🚀 Enabling ADB Debugging

### Method 1: The Hidden UI Remote Sequence

> [!WARNING]
> **Production User Build Caveat:** On recent carrier OTA updates (e.g. `25.1.9` / `ro.build.type=user`), production remotes send `KEYCODE_ENTER` (keycode 66) or `KEYCODE_NUMPAD_ENTER` (keycode 160) rather than `KEYCODE_DPAD_CENTER` (keycode 23), causing the comparison against `"23232323232323232323"` to fail. Furthermore, the 4-second accumulator is not refreshed per click, and carrier policies suppress the menu. Even if "Factory Setup" is opened, `ApplicationUtilKt.checkFactoryApps` strictly verifies the APK against the Jio platform RSA signature. See [AML_MASKROM_SECURITY_ANALYSIS.md](AML_MASKROM_SECURITY_ANALYSIS.md) for full decompilation proofs.

Reverse engineering `com.rjil.jiostbsetting.fragments.about.DetailsFragment` inside `JioSettings.apk` revealed an embedded technician secret code:

```java
// DetailsFragment.java
if (this.keyCodeTime && Intrinsics.areEqual(this.keyCombination, ConstantKt.SHOW_HIDDEN_OPTION_CODE)) {
    LoggerKt.logger("activate show hidden options");
    MainActivity.INSTANCE.setShowHiddenOptions(true);
}
```
`SHOW_HIDDEN_OPTION_CODE` is defined in `ConstantKt.java` as `"23232323232323232323"`:
* Keycode `23` corresponds to `KEYCODE_DPAD_CENTER` (the **OK / Select / Center** button on the remote).
* `23` repeated 10 times means pressing **OK 10 times consecutively within 4 seconds**.

#### Step-by-Step Instructions:
1. Power on the Jio STB and open **Settings** from the Jio UI.
2. Navigate to **About** -> click on **About Details** (the page displaying your MAC address, Serial Number, IP, etc.).
3. On this `About Details` screen, press the **OK / Center button on the remote 10 times rapidly** (under 4 seconds).
4. Press the **Back** button on the remote once to return to the **System Settings** menu.
5. Scroll down to the bottom of the list. Two new menus will now be revealed:
   - **Factory Setup**
   - **Android Setting**
6. Click on **Android Setting**. This immediately executes an explicit intent launching stock Android TV Settings:
   ```java
   intent.setComponent(new ComponentName("com.android.tv.settings", "com.android.tv.settings.MainSettings"));
   ```
7. You are now inside the official **Android TV Settings** (`DroidTvSettings`):
   - Navigate to **Device Preferences** -> **About** -> scroll down to **Build**.
   - Click **Build 7 times** until you see the message: *"You are now a developer!"*.
8. Press Back to return to **Device Preferences**, scroll down and open **Developer Options**.
9. Turn on **USB Debugging** (and **OEM Unlocking** if available).
10. Connect from your PC over Wi-Fi / Ethernet:
    ```bash
    adb connect <STB_IP_ADDRESS>:5555
    adb devices
    ```
    *(Alternatively, connect a USB-A to USB-A male cable between your PC and the black USB 2.0 port `JB03` on the rear panel).*

---

### Method 2: Hardware UART Serial Console (`J7`)

If the remote is unavailable or the UI cannot be navigated:

> **Hardware pinout & wiring:** The `J7` header sits to the right of the central heatsink, between the processor and the PPT Ethernet transformer. The complete pinout diagram, staggered-pad layout, USB-to-TTL wiring instructions, baud-rate troubleshooting (921600 / 115200 / 1500000), and photographic cross-reference live in [`TEARDOWN.md` §6.1](TEARDOWN.md). Use **3.3V logic**: connect adapter **TX → `J7` RX**, adapter **RX → `J7` TX**, **GND → GND**, and **leave Pad 4 (`3V3`) disconnected**. Serial terminal: **921600 baud, 8N1, no flow control**.

**Triggering ADB from Console:**
* *Note for User Builds:* On production firmware (`buildvariant=user`, `ro.debuggable=0`), the interactive root shell service (`service console /system/bin/sh`) is disabled by SELinux and init. UART outputs early boot logs, but terminal input (RX) will not spawn a shell prompt. If running an engineering or userdebug image, execute:
```sh
setprop persist.sys.usb.config adb
setprop sys.usb.config adb
setprop service.adb.tcp.port 5555
start adbd
```

---

### Method 3: Hardware Recovery Mode (`SK01`)

> **Hardware details:** The tactile `SK01` / `Reset` button sits on the right PCB edge; holding it while applying 12V power forces the Amlogic boot ROM into recovery / USB Burning mode. See the full `SK01` pinout, operation, and photographic cross-reference in [`TEARDOWN.md` §6.2](TEARDOWN.md#62-hardware-recovery--usb-flashing-sk01).

1. Connect a USB-A to USB-A cable between your PC and the STB's **black USB 2.0 port (`JB03`)**.
2. Press and hold down tactile button **`SK01`** (labeled `Reset` on the right PCB edge).
3. Insert the 12V DC power jack while holding `SK01`.
4. Release the button after 5–7 seconds. The STB enters Android Recovery Mode.
5. **Carrier Recovery Limitation:**
   * On stock carrier Android 11 TV builds, **`Apply update from ADB`** and **`Enter fastboot`** are stripped from the menu.
   * Only **"Reboot system now"** and **"Wipe data/factory reset"** remain.
   * If recovery options are stripped and the OS is locked, proceed to Method 4.

---

### Method 4: Hardware MaskROM Flashing Mode (WorldCup Device)

When UI sequences, captive portal triggers, recovery options, and serial console inputs are locked or disabled, the ultimate fallback is **Amlogic MaskROM mode**:

> **Canonical reference:** All eMMC short-point targets (Targets A/B/C), the exact pin-short procedure, USB Burning Tool settings, and the MaskROM-vs-Recovery-vs-USB-Boot comparison table live in [`AML_MASKROM_SECURITY_ANALYSIS.md` §2](AML_MASKROM_SECURITY_ANALYSIS.md#2--forcing-amlogic-maskrom-mode-worldcup-device). This section only covers the ADB outcome after flashing.

1. Short the eMMC `CLK` series damping resistor or `DAT0` test pad (near Samsung eMMC `11UF1`) to `GND`.
2. Connect a male-to-male USB-A cable between your PC and the **black USB 2.0 port (`JB03`)**.
3. Plug in the 12V DC power adapter while holding the short for 2–3 seconds, then release.
4. The SoC BootROM times out on eMMC initialization and falls back to **USB DFU / WorldCup Device mode (`1b8e:05af` / `1b8e:c003`)**.
5. Flashing packages must be built using the extracted OEM-signed bootloader ([`bootloader.img`](ota_packages/extracted/partitions/bootloader.img)) due to blown hardware eFuses.

For the exhaustive teardown, trace photographs, and flashing procedure, see [AML_MASKROM_SECURITY_ANALYSIS.md](AML_MASKROM_SECURITY_ANALYSIS.md).

---

## 2. ⚡ Gaining Root Access

### Approach A: Magisk Ramdisk Patching + Fastboot / AVB Bypass

The extracted OTA firmware contains the GKI v3 boot partitions (available from [GitHub Releases v25.1.9](https://github.com/onlyysaurabh/jiostb4k/releases/tag/v25.1.9) or via `./scripts/download_firmware.sh --boot`):
* `ota_packages/extracted/partitions/boot.img` (Linux Kernel 5.4 + base ramdisk)
* `ota_packages/extracted/partitions/vendor_boot.img` (Vendor ramdisk + DTB)

#### AVB 2.0 Verification Barrier:
> **Canonical signing architecture:** The three-tier signing model (Tier 1 bootloader eFuse, Tier 2 AVB 2.0, Tier 3 dm-verity), `vbmeta` hash descriptors, and `vbmeta_system` Merkle-tree digests are documented exhaustively in [`AML_MASKROM_SECURITY_ANALYSIS.md` §5](AML_MASKROM_SECURITY_ANALYSIS.md#5--cryptographic-verification--signing-architecture-what-exactly-needs-to-be-signed). This guide covers only the flashing procedure.

Static analysis of `vbmeta.img` using `avbtool` confirms active SHA256-RSA2048 signing:
```text
Hash descriptor:
  Partition Name: boot
  Digest: 880a321d7e03d67165dca7c2cbf46d66c8f89011415dd91e2838d33c55f7aa28
Hash descriptor:
  Partition Name: vendor_boot
  Digest: db20593f2e90006deebc8dcf3683f8ac67cfd61478fb3d0def6151cf3a25fa1c
```
Flashing a Magisk-patched `boot.img` without disabling verification will cause the bootloader to reject the image and halt.

#### Unlocking & Flashing Procedure:
1. **Patch Boot with Magisk**:
   - Push `boot.img` to an Android phone running Magisk App v26+.
   - Select **Install** -> **Select and Patch a File** -> pick `boot.img`.
   - Copy the output file `magisk_patched_*.img` to your computer.
2. **Enable OEM Unlock**:
   - In stock Android Settings (via Method 1), navigate to Developer Options and toggle **OEM Unlocking**.
3. **Reboot to Fastboot**:
   ```bash
   adb reboot bootloader
   # or from recovery:
   adb reboot fastboot
   ```
4. **Unlock and Disable Verity**:
   ```bash
   fastboot flashing unlock
   # or: fastboot oem unlock
   fastboot flash vbmeta --disable-verity --disable-verification vbmeta.img
   fastboot flash boot magisk_patched.img
   fastboot reboot
   ```

---

### Approach B: Local Privilege Escalation via Debuggable System App

> **Canonical verification findings:** Full JDWP attach reproducibility, package manifest fields (`sharedUserId=android.uid.system`, `android:debuggable=true`), reproduction commands, and the security remediation note live in [`JDWP_SYSTEM_ESCALATION_FINDINGS.md`](./JDWP_SYSTEM_ESCALATION_FINDINGS.md). This section covers only the procedure summary.

In `ota_packages/extracted/apks/jio_system_priv_app/JioCommandReceiver.apk`, the manifest reveals:
```xml
<manifest sharedUserId="android.uid.system" package="com.rjil.jio.stb.commandreceiver">
    <application android:debuggable="true" ...>
```
Because this package runs as **`android.uid.system` (UID 1000)** and has **`android:debuggable="true"`** enabled in the production build:
* With ADB access, `jdb` (Java Debug Wire Protocol / JDWP) can attach to the process:
  ```bash
  adb forward tcp:8700 jdwp:$(adb shell pidof com.rjil.jio.stb.commandreceiver)
  jdb -attach localhost:8700
  ```
* Attaching via JDWP allows arbitrary code execution in the context of `system` UID, enabling permission escalation, property modification, and silent APK installation.

---

## 3. 💿 Installing Custom ROMs & Alternative OS

### Critical Hardware & ABI Constraints
1. **32-bit Userland on 64-bit Kernel**:
   The Amlogic S905X4 SoC has 64-bit hardware, but `vendor/build.prop` specifies:
   ```properties
   ro.vendor.product.cpu.abilist=armeabi-v7a,armeabi
   ro.vendor.product.cpu.abilist64=
   ```
   All vendor HALs (Mali GPU `mali.ko`, Realtek Wi-Fi `8822cs.ko`, audio HAL, video decoders) are compiled for **32-bit ARM**.
2. **Dynamic Partitions**:
   The storage uses a dynamic super partition containing `system`, `vendor`, `product`, `system_ext`, and `odm` across A/B slots.

---

### Option 1: CoreELEC (Recommended Media OS)

CoreELEC runs entirely from a USB flash drive without altering the internal eMMC flash, delivering full 4K HDR10, AV1, and Kodi functionality:

1. Download the latest **CoreELEC-ne** Generic image for Amlogic S905X4 (`CoreELEC-Amlogic-ne.*.Generic.img.gz`).
2. Write the image to a USB 3.0 flash drive using Rufus, Etcher, or `dd`.
3. In the `device_trees` directory of the flashed USB drive, locate:
   ```text
   sc2_s905x4_2g.dtb
   ```
4. Copy `sc2_s905x4_2g.dtb` to the root of the USB drive and rename it to **`dtb.img`**.
5. Plug the USB flash drive into the blue **USB 3.0 port (`JB01`)**.
6. Hold down the tactile button **`SK01`** (Reset) and insert the 12V DC power jack.
7. Release `SK01` when the CoreELEC logo appears on the TV.

---

### Option 2: Project Treble Generic System Image (GSI)

If flashing an AOSP or LineageOS GSI onto the eMMC:
* **Required GSI Flavor**: **`arm-a` / `arm_bvN`** (ARM32 userland with 64-bit Binder). **Do NOT flash `arm64_bvN`.**
* **Flashing via Fastbootd**:
  1. Boot into userspace fastboot:
     ```bash
     adb reboot fastboot
     ```
  2. Flash the GSI system image and clear user data:
     ```bash
     fastboot flash system system-arm-gsi.img
     fastboot -w
     fastboot reboot
     ```

---

### Option 3: Carrier Liberation & Debloating (Safest & Most Practical)

Flashing third-party Android ROMs often breaks proprietary hardware drivers (DVB demodulator, Widevine L1, Realtek BT/Wi-Fi combo). 

The optimal path to a clean, high-performance Android TV 11 experience is **debloating the existing OS via ADB**:

#### 1. Disable Jio Proprietary Launchers & Lockscreens
```bash
adb shell pm disable-user --user 0 com.iwedia.ui.rjio.launcher.reliance
adb shell pm disable-user --user 0 com.jio.stb.hotellauncher
adb shell pm disable-user --user 0 com.jiostb.inactivitytimer
```

#### 2. Disable Carrier Telemetry, Remote Management & Ads
```bash
adb shell pm disable-user --user 0 com.jio.tr069client
adb shell pm disable-user --user 0 com.jio.stb.remote_diagnostics
adb shell pm disable-user --user 0 com.jio.background.scheduler
adb shell pm disable-user --user 0 com.rjil.jio.stb.adc
adb shell pm disable-user --user 0 com.rjil.jiostbsetting.utils.push
adb shell pm disable-user --user 0 com.teamviewer.quicksupport.addon.jio_stb
```

#### 3. Install Open-Source TV Launcher & Store
```bash
# Install Projectivy Launcher (ad-free Leanback home)
adb install ProjectivyLauncher.apk

# Install open app repositories & media tools
adb install F-Droid.apk
adb install SmartTube.apk
```
After disabling Jio's launcher, pressing the Home button on the remote will prompt you to set **Projectivy Launcher** as the permanent default.

---

## 4. 🧰 Quick Reference Command Cheat Sheet

| Task | Command / Action |
| :--- | :--- |
| **Open Android Settings** | About -> About Details -> Press **OK 10 times** within 4s -> Back -> **Android Setting** |
| **Connect Network ADB** | `adb connect <STB_IP>:5555` |
| **Enter Fastboot** | `adb reboot fastboot` or hold `SK01` on boot |
| **UART Serial Access** | Header `J7` (Pads: 1=GND, 2=RX, 3=TX), `921600` baud 8N1 |
| **Check Active Slot** | `fastboot getvar current-slot` |
| **Switch A/B Slot** | `fastboot --set-active=a` (or `b`) |
| **Disable AVB Verification** | `fastboot flash vbmeta --disable-verity --disable-verification vbmeta.img` |

---
## 🔗 Related Documents

| Related Document | Relationship |
| :--- | :--- |
| [`AML_MASKROM_SECURITY_ANALYSIS.md`](AML_MASKROM_SECURITY_ANALYSIS.md) | MaskROM / WorldCup flashing entry (§2), exact eMMC short points, and the three-tier AVB 2.0 / dm-verity signing architecture (§5). |
| [`JDWP_SYSTEM_ESCALATION_FINDINGS.md`](JDWP_SYSTEM_ESCALATION_FINDINGS.md) | Verification findings for the debuggable `JioCommandReceiver` system-UID (UID 1000) JDWP escalation (Approach B). |
| [`TEARDOWN.md`](TEARDOWN.md) | Hardware pinout for UART `J7` (§6.1) and recovery button `SK01` (§6.2) referenced by Methods 2 and 3. |
| [`TR069_REMOTE_ADB_ANALYSIS.md`](TR069_REMOTE_ADB_ANALYSIS.md) | Remote network ADB enablement via TR-069 `Device.JioSTB.USB.USBDebugging` parameter (24h auto-disable). |
| [`Housekeeping-PoC/README.md`](Housekeeping-PoC/README.md) | Two-stage bootloader unlock exploit (Stage 1: TR-069 ADB enable; Stage 2: CVE-2024-31317 zygote injection bootloader unlock). |

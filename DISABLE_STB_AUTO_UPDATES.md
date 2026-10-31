# Disable Automatic Firmware Updates on the Jio 4K STB

This guide covers the **Jio JMSB200A (Skyworth, Android TV 11)** firmware analyzed in this repository, including build `25.1.9`. It describes reversible ADB package-manager changes for the two documented network firmware-update paths.

The repository already documents the OTA package and update mechanisms in [`OTA_ANALYSIS.md`](OTA_ANALYSIS.md), [`FIRMWARE_ENDPOINTS_AND_EXPOSURES.md`](FIRMWARE_ENDPOINTS_AND_EXPOSURES.md), and [`jio_infrastructure/03_FOTA_AND_FIRMWARE_DISTRIBUTION.md`](jio_infrastructure/03_FOTA_AND_FIRMWARE_DISTRIBUTION.md). Those documents do not provide an end-user procedure for disabling automatic updates; this guide fills that gap.

The existing findings do not identify a consumer-facing automatic-firmware-update switch in Settings for this build, so the procedure below uses ADB.

> **Evidence limit:** Package behavior below comes from static analysis of the extracted `25.1.9` firmware and related repository research. The ADB disable/enable commands are standard Android package-manager operations, but this procedure has not been tested on a physical STB. Other models and firmware builds may use different packages or policies.

## What this changes

The analyzed firmware has two documented network paths for system firmware updates:

| Package | Role in the analyzed firmware | Effect of disabling it |
|---|---|---|
| `com.jio.httpupdate` | Jio FOTA daemon that checks `fota.slv.kai.jiophone.net`, downloads packages, and hosts the local update service on TCP 54321. | Stops this package's background FOTA and local HTTP update service. |
| `com.jio.tr069client` | Carrier management client that can receive a TR-069 `Download` RPC and execute a firmware download. | Blocks this client’s ACS management and firmware-download path. It also disables other TR-069 management functions. |

Disabling only `com.jio.httpupdate` is the narrower option, but it does **not** cover the separately documented TR-069 download path. To suppress both known network paths on this build, disable both packages.

Disabling `com.jio.tr069client` also affects carrier services that use that client, including remote diagnostics, configuration/provisioning, and network checks. The STB may lose Jio support or dependent features. If that tradeoff is not acceptable, disable only `com.jio.httpupdate` and understand that ACS-initiated updates may still be possible.

This does not prevent an update initiated from USB/recovery, an update already downloaded or staged, app-store app updates, or separate accessory updates such as remote-control firmware. It does not downgrade firmware already installed.

## Before you begin

1. Use an STB you own or are authorized to administer. Keep it on a trusted local network while ADB is enabled.
2. Connect to the STB with ADB. For network ADB, use its LAN address:

   ```sh
   adb connect <STB_IP_ADDRESS>:5555
   adb devices
   ```

   If ADB is not available, see [`ROOT_ADB_CUSTOM_ROM_GUIDE.md`](ROOT_ADB_CUSTOM_ROM_GUIDE.md) for the repository's ADB access notes. The hidden UI method described there may not work on every production build.
3. Confirm that the connected box matches the analyzed model and build, and check that the packages exist:

   ```sh
   adb shell getprop ro.product.model
   adb shell getprop ro.vendor.build.id
   adb shell pm path com.jio.httpupdate
   adb shell pm path com.jio.tr069client
   ```

   The analyzed values are `JMSB200A` and `25.1.9`. If a package is absent or the model/build differs, stop and identify the updater packages for that firmware before changing anything.
4. Record the current disabled-package list so you can distinguish your changes from existing device settings:

   ```sh
   adb shell pm list packages -d
   ```

## Disable the network update paths

The commands apply to Android user `0`, which is the normal primary user on this STB. First disable the Jio FOTA daemon:

```sh
adb shell pm disable-user --user 0 com.jio.httpupdate
```

To also block firmware downloads delivered through the TR-069 ACS client, disable it as well:

```sh
adb shell pm disable-user --user 0 com.jio.tr069client
```

If Android reports that the package cannot be disabled, do not remove its APK or remount/modify system partitions as a substitute; the package may be protected on that build. Leave it enabled and reassess using firmware-specific evidence.

Reboot the STB, then verify the package states:

```sh
adb reboot
adb wait-for-device
adb shell pm list packages -d
```

Confirm that the package(s) you disabled appear in the disabled-package list. This verifies the per-user package state; it does not prove that every possible update mechanism on a different build is covered.

## Restore the packages

Re-enable only the package(s) you disabled:

```sh
adb shell pm enable com.jio.httpupdate
adb shell pm enable com.jio.tr069client
adb reboot
```

If you disabled only `com.jio.httpupdate`, omit the TR-069 command. Re-enabling TR-069 restores the carrier management client and its associated remote-management features. Check the package state again with `adb shell pm list packages -d`.

## Important limits

- Disabling these packages is reversible for the current Android user. A factory reset or later firmware installation may restore their enabled state; check again after either event.
- A package disable does not cancel an update already downloaded or staged. The update service writes A/B packages to `/cache/ota_package_ab`; do not manually delete files from that path. Use the STB's supported update controls or let an in-progress installation finish before changing updater packages.
- `com.jio.usbupdate` is the separately cataloged offline USB flashing utility. It is not needed to block the two network paths above and is intentionally left enabled here.
- Hostname or DNS blocking alone is not a reliable substitute: the repository documents multiple CDN and ACS delivery paths, and blocking carrier-management endpoints can disrupt unrelated STB functions.
- This procedure is for controlling updates on the local device. It does not change the update server, other devices, bootloader policy, or the integrity checks on firmware packages.

## Related research

- [`OTA_ANALYSIS.md` §7.3](OTA_ANALYSIS.md) identifies the extracted `JioHttpUpdate.apk` FOTA daemon and `JioUsbUpdate.apk` utility.
- [`FIRMWARE_ENDPOINTS_AND_EXPOSURES.md` §5](FIRMWARE_ENDPOINTS_AND_EXPOSURES.md) describes the local update server and TR-069 `Download` flow.
- [`jio_infrastructure/03_FOTA_AND_FIRMWARE_DISTRIBUTION.md`](jio_infrastructure/03_FOTA_AND_FIRMWARE_DISTRIBUTION.md) maps the firmware distribution endpoints.
- [`TR069_ACS_RESEARCH.md`](TR069_ACS_RESEARCH.md) and [`TR069_REMOTE_ADB_ANALYSIS.md`](TR069_REMOTE_ADB_ANALYSIS.md) describe TR-069 capabilities and management behavior.

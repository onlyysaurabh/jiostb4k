# 12. Hardware Root-of-Trust, TrustZone TEE & Provisioning Infrastructure

> **Parent Topic:** [`jio_infrastructure/README.md`](README.md)  
> **Source Partitions:** `vendor.img`, `system.img`, `boot.img`, `bootloader.img`  
> **Related Research:** [`AML_MASKROM_SECURITY_ANALYSIS.md`](../AML_MASKROM_SECURITY_ANALYSIS.md), [`TEARDOWN.md`](../TEARDOWN.md)

---

## 1. System Architecture & Hardware Root-of-Trust

Reliance Jio STB hardware (JMSB200A, Amlogic S905X4 `ohm` / `sc2`) ties cloud infrastructure security directly to silicon-level cryptographic fuses and Trusted Execution Environment (TEE) hardware.

```
                      ┌──────────────────────────────────────────────┐
                      │          Amlogic S905X4 eFUSE Bank           │
                      │    (OEM Root Keys, Anti-Rollback Fuses)      │
                      └──────────────────────┬───────────────────────┘
                                             │
             ┌───────────────────────────────┴───────────────────────────────┐
             │                                                               │
             ▼                                                               ▼
 ┌───────────────────────────────────────┐       ┌───────────────────────────────────────┐
 │       OP-TEE TrustZone (Secure OS)    │       │     Android Normal World (REE)        │
 ├───────────────────────────────────────┤       ├───────────────────────────────────────┤
 │ • RPMB Replay Protected Memory Block  │       │ • tee-supplicant                      │
 │ • Verimatrix CAS / Widevine L1 Keys   │       │ • tee_key_inject (Factory Provision)  │
 │ • HDCP 2.2 / 2.3 Transmitter Keys     │       │ • vmx_webclient (Linear DVB Decrypt)  │
 │ • DAC / PFID Hardware Tokens          │       │ • jioservicenative (sys.jio.hdcp)     │
 └───────────────────────────────────────┘       └───────────────────────────────────────┘
```

---

## 2. Factory Provisioning & TEE Key Injection Pipeline

In-depth inspection of `vendor.img` (`/vendor/etc/init/`) uncovered the exact native daemons executed during device boot to hydrate TrustZone with cryptographic identity tokens:

### 2.1 The Key Injection Daemon (`/vendor/bin/tee_key_inject`)
* **Init Trigger (`tee_key_inject.rc`):**
  ```ini
  on property:vold.post_fs_data_done=1 && property:init.svc.vendor.tee_preload_fw=running
      start vendor.key_inject
      setprop vendor.tee_key_inject 1

  service vendor.key_inject /vendor/bin/tee_key_inject -p /mnt/vendor/factory
      oneshot
      user root
      group system
      seclabel u:r:tee:s0
  ```
* **Function:** Mounts the encrypted factory partition (`/mnt/vendor/factory`), decrypts device-unique keys, and loads them into OP-TEE secure memory.

### 2.2 Hardware Provisioning Tooling (`/vendor/bin/tee_provision`)
Static analysis of symbol tables in `tee_provision` revealed the factory manufacturing interface:
* `provision_rpmb_format` (Initializes eMMC Replay Protected Memory Block)
* `key_provision_calc_checksum` & `key_provision_checksum_v2`
* `key_provision_get_dac` & `key_provision_get_dac_v2` (Device Authentication Certificate)
* `key_provision_get_pfid` (Platform Identity)
* `key_provision_store` (Commits keys into secure RPMB storage)

---

## 3. Conditional Access System (CAS) & Verimatrix DRM

To satisfy broadcast content licensing requirements for linear pay-TV channels, the JMSB200A embeds dual DRM stacks:
1. **Google Widevine Modular DRM:** Widevine L1 secured by hardware decryptors (`android.hardware.drm@1.3-service.widevine`).
2. **Verimatrix ViewRight CAS:** Hardware-level conditional access for DVB broadcast streams (`android.hardware.drm@1.3-service.verimatrix.rc` and `/vendor/bin/hw/vmx_webclient`).

### 3.1 Verimatrix Web Client Daemon (`vmx_webclient`)
* **Execution Context:**
  ```ini
  service vmx_webclient /vendor/bin/hw/vmx_webclient
      user media
      group media mediadrm drmrpc system inet
  ```
* **Role:** Listens for ECM (Entitlement Control Messages) and EMM (Entitlement Management Messages) delivered over DVB transport streams or unicast IP, communicating with OP-TEE to derive control words (CW) for descrambling.

---

## 4. Hardware Tuner Frontend (Sony CXD2856)

For hybrid deployments supporting RF coaxial cable / terrestrial feeds alongside FTTH IP streams:
* **Tuner Driver Init:** `/vendor/etc/init/cxd2856_fe.rc`
* **Hardware Chipset:** Sony CXD2856 multi-standard digital TV demodulator (DVB-T/T2/C/C2).
* **DVB Stack:** Implemented via DTVKit and Droidlogic tuner services (`lnt.hardware.dtvkit@1.0-service.rc` and `dvb.rc`).

---

## 5. Native Jio Framework Daemons (`jioservicenative`)

In addition to user-space Android applications, low-level platform management is enforced by a dedicated native binary:
* **Binary Path:** `/system/bin/jioservicenative`
* **Core Library:** `/system/lib/libjionativeservice.so`
* **Service Name:** `jio.nativeservice` (Binder interface)
* **Monitored Properties:**
  * `sys.jio.hdcp.receiverid` (Validates HDMI sink authenticity against HDCP revocation lists)
  * `sys.jio.nativedata` (Caches carrier diagnostic variables)
  * `persist.sys.jio.product.type` (Carrier provisioning personality)

---

## 6. Build Environment Fingerprints

Extraction of `system/build.prop` and `vendor/build.prop` reveals carrier engineering build metadata:
* **Base OS:** `JioOS-2.0`
* **Target Security Patch:** `2024-02-05`
* **Build Infrastructure:** Compiled on AWS EC2 Spot Instances (`ro.build.user=Jio`, `ro.build.host=spot-instance`).
* **Hardware Board ID:** `ohm` / `sc2`
* **Required Bootloader Version:** `01.01.210312.151827`
* **OEM Unlock Policy:** `ro.oem_unlock_supported=0` (Permanently disables `fastboot oem unlock` in production recovery).

---
## 🔗 Related Documents

| Related Document | Relationship |
| :--- | :--- |
| [`../AML_MASKROM_SECURITY_ANALYSIS.md`](../AML_MASKROM_SECURITY_ANALYSIS.md) | MaskROM / WorldCup flashing entry, eMMC short points, and the AVB 2.0 / dm-verity signing architecture tied to the silicon Root-of-Trust. |
| [`../TEARDOWN.md`](../TEARDOWN.md) | Hardware teardown, component identification, and PCB pinouts for the S905X4 board. |
| [`../ROOT_ADB_CUSTOM_ROM_GUIDE.md`](../ROOT_ADB_CUSTOM_ROM_GUIDE.md) | Bootloader unlock, AVB 2.0 bypass, and Magisk root patching procedures. |

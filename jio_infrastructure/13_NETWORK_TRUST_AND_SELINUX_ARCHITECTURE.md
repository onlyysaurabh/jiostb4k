# 13. Network Trust Model, PKI Isolation & SELinux Policy Architecture

> **Parent Topic:** [`jio_infrastructure/README.md`](README.md)  
> **Source Partitions:** `system.img` (`/system/etc/security/cacerts/`), `vendor.img` (`/vendor/etc/selinux/`)  
> **Source Packages:** [`TR069.apk`](../ota_packages/extracted/apks/jio_system_priv_app/TR069.apk)

---

## 1. Network Trust Model & Public vs. Private PKI Split

A foundational architectural discovery in Jio's platform design is the **strict partition between public consumer web trust and private carrier management trust**:

```
                                  Jio STB Network Trust Model
                                               │
         ┌─────────────────────────────────────┴─────────────────────────────────────┐
         ▼                                                                           ▼
   AOSP System Trust Store                                                     Private App Bundles
   (/system/etc/security/cacerts/)                                             (TR069.apk Assets)
   ───────────────────────────────                                             ──────────────────
   • 138 Public Commercial CAs                                                 • CN=RILROOTCA (2009 & 2024 roots)
   • Google GTS, Amazon, GlobalSign, DigiCert                                  • CN=Jio Internal Server Sub CA
   • Scope: Fastly UI, Akamai CDNs, BigIP api.jio.com                          • Scope: acs.oss.jio.com, jiodeviceheartbeat
   • NO Reliance CAs trusted system-wide                                       • Bundled client keys (v4_key.pem, v6_key.pem)
```

### 1.1 System CA Store Audit (`system/etc/security/cacerts/`)
Analysis of all 138 X.509 certificates preloaded into Android's system trust store confirms:
* **Zero internal Reliance Jio Certificate Authorities** are installed as trusted system root anchors.
* Standard Android applications (browser, third-party APKs, streaming apps) communicate strictly through publicly signed HTTPS endpoints (e.g., `api.jio.com` signed by DigiCert/Reliance public CA, `*.cdn.jio.com` signed by GlobalSign).
* This design prevents compromised internal carrier roots from intercepting ordinary web browsing or Google Play Services traffic.

### 1.2 Isolated Enterprise PKI in Privileged APKs
Private infrastructure communication bypasses Android’s default `TrustManager`:
* Applications like `TR069.apk` instantiate a custom `SSLContext` backed by a programmatic `KeyStore` created dynamically from raw APK assets (`assets/rootca.crt`, `assets/acs_oss_jio_com.cer`).
* For the Device Heartbeat cloud (`jiodeviceheartbeat-v4.jio.com`), the application loads `assets/prod/jio_device_heartbeat_v4_jio_com_crt.pem` and parses the unencrypted private key `assets/prod/v4_key.pem` directly into an in-memory `KeyManagerFactory`.

---

## 2. SELinux Policy & Domain Confinement Analysis

Audit of the compiled SELinux policy files (`vendor_sepolicy.cil` and `plat_pub_versioned.cil` in `/vendor/etc/selinux/`) reveals how Android’s Mandatory Access Control (MAC) governs proprietary daemons:

### 2.1 The `sdknativeservice` Domain
* **Type Definition:** `type sdknativeservice, domain;`
* **Privileges Granted:**
  * Capability overrides: `capability { dac_override dac_read_search net_admin net_raw setuid sys_module sys_ptrace };`
  * Execution: `allow sdknativeservice shell_exec:file { rx_file_perms execute_no_trans };`
  * Property service: Allowed to read and write system properties without restriction.
* **Security Weakness:** Because the daemon has `execute_no_trans` on `shell_exec`, any command executed via `popen()` executes directly inside the highly privileged `sdknativeservice` domain rather than dropping down into the confined `shell` domain.

### 2.2 The `tee` Domain
* **Type Definition:** `type tee, domain;`
* **Filesystem Access:**
  * Owns `/mnt/vendor/factory` (`factory_file`).
  * Direct block device access to `/dev/block/mmcblk0rpmb` (eMMC RPMB partition).
* **Communication:** Listens for IPC from `tee-supplicant` and user-space DRM HAL services (`mediadrm`, `vmx_webclient`).

### 2.3 The `adbd` Domain & TCP Port Binding
* In standard AOSP, `adbd` is confined from binding to external TCP ports unless `ro.debuggable=1` is set.
* However, vendor SELinux rules explicitly allow `adbd` to listen on `port 5555`:
  ```cil
  (allow adbd port:tcp_socket { name_bind node_bind });
  ```
* This permits the network ADB socket to open without triggering an SELinux `avc: denied` audit log.

---
## 🔗 Related Documents

| Related Document | Relationship |
| :--- | :--- |
| [`12_HARDWARE_BOOT_AND_TRUSTZONE_INFRA.md`](12_HARDWARE_BOOT_AND_TRUSTZONE_INFRA.md) | OP-TEE TrustZone domain (`tee`), factory key injection, and hardware Root-of-Trust. |
| [`11_SECURITY_AUDIT_AND_ATTACK_SURFACE.md`](11_SECURITY_AUDIT_AND_ATTACK_SURFACE.md) | §2.4 — Rogue ACS hijacking; §2.10 — `sdknativeservice` SELinux domain privilege analysis cross-reference. |
| [`09_DIRECT_IPS_INTERNAL_AND_LAN_DAEMONS.md`](09_DIRECT_IPS_INTERNAL_AND_LAN_DAEMONS.md) | `sdknativeservice` root daemon and `adbd` port 5555 binding documented in §2.1–2.3. |

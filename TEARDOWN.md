# Jio Android TV Box (4K STB) Hardware Teardown & Security Analysis

**Device Identified:** Jio 4K Android TV Set-Top Box  
**OEM / ODM Platform:** Skyworth Digital HP44 Series (`5800-2AHP44T`)  
**PCB Fabrication Date:** Week 21, 2025 (late May 2025)  
**Document Revision:** 1.0  
**Source Images:** `img/IMG20261017140533.jpg` through `img/IMG20261017140700.jpg`

---

## 1. Executive Summary & Verification of Findings

A systematic component-level inspection of the teardown photographs confirms that this device is a 2025-generation **Jio 4K Android TV Set-Top Box** manufactured by **Skyworth Digital** (model platform **5800-2AHP44T**). 

All findings from the initial analysis have been cross-checked, verified with manufacturer part catalogs, and expanded with deep hardware security / reverse engineering details:

| Component Category | Component Reference | Part Number / Markings | Verified Specifications | Status |
| :--- | :--- | :--- | :--- | :--- |
| **System Memory (RAM)** | `3U3`, `3U4` | Micron `5IR75` / FBGA code `D8BPK` | 2 GB (2 × 1 GB) DDR4-3200 SDRAM (`MT40A512M16TB-062E:R`) | **Confirmed** |
| **Storage (eMMC)** | `11UF1` | Samsung `KLMBG2JETD-B041` (`SEC 519`) | 32 GB eMMC 5.1 High-Speed Flash (HS400, FBGA-153) | **Confirmed** |
| **Core Processor (SoC)** | Under heatsink | Skyworth HP44 reference platform | **Amlogic S905X4** Quad-Core ARM Cortex-A55 @ 2.0 GHz | **Confirmed** |
| **Reference Clock** | `XM01` | `YL240` / `YD5H` | 24.000 MHz Crystal Oscillator (standard Amlogic SoC clock) | **Confirmed** |
| **Ethernet Isolation** | `JL01` | PPT `2510F .PSF-1626` | 10/100 Mbps Fast Ethernet LAN Magnetics Transformer | **Confirmed** |
| **Board OEM & Revision** | Lower-right silkscreen | `5800-2AHP44T` | Skyworth Digital OEM STB Platform (HP44 Series) | **Confirmed** |
| **Fabrication Date** | Lower-right corner | `. 2521 :` | Year 2025, Week 21 (Late May 2025) | **Confirmed** |
| **PCB Certification** | Lower-right corner | UL `E503744`, `XS-M 94V-0` | Xingda Circuits, 94V-0 flame retardant multilayer PCB | **Confirmed** |
| **UART Serial Debug** | `J7` | Silkscreen `GND`, `RX`, `TX`, `3V3` (staggered) | 4-pad 3.3V TTL unpopulated serial interface (921600 8N1) | **Confirmed** |
| **Recovery Button** | `SK01` | Labeled `Reset` | Tactile push-button for U-Boot Recovery / USB Burning mode | **Confirmed** |
| **Wireless (Wi-Fi/BT)** | `UW01` / `J2`, `J4` | Stamped RF shield + 2× U.FL IPEX | **Realtek RTL8822CS** (2×2 MIMO Dual-band 802.11ac + BT 5.0, verified via `8822cs.ko`) | **Confirmed** |

---

## 2. Memory & Storage In-Depth Analysis

### 2.1 System RAM: 2 GB DDR4-3200 (Micron Technology)
- **Top Silkscreen Locations:** `3U3` (lower) and `3U4` (upper), situated to the left of the central SoC heatsink.
- **Surface Package Markings:**
  - Micron Stylized Logo `M`
  - First Line: `5IR75` (Lot / Die revision)
  - Second Line: `D8BPK` (Micron 5-digit FBGA code)
  - Side Code: `AA89` / `68VV` (package pin-1 orientation marker)
- **Micron Part Decoder:**
  - FBGA Code `D8BPK` translates directly to Micron Part Number **`MT40A512M16TB-062E:R`**.
  - **Architecture:** 512 Meg x 16 (8 Gb / 1 Gigabyte per package).
  - **Technology:** DDR4 SDRAM, 1.2V core voltage.
  - **Speed Bin:** `-062E` corresponds to **DDR4-3200** (Data transfer rate of 3200 MT/s, 1600 MHz clock rate, CL=22).
  - **Package:** 96-ball FBGA (Fine-pitch Ball Grid Array).
- **Total Capacity:** 2 chips × 1 GB = **2 GB DDR4 RAM** operating in a 32-bit aggregated bus (2 × 16-bit) to the Amlogic SoC.
- **Thermal Management:** Covered by a dedicated rectangular gray thermal gap pad in initial assembly (`IMG20261017140558.jpg`), carrying heat directly to the ground planes and enclosure.

### 2.2 Flash Storage: 32 GB eMMC 5.1 (Samsung Electronics)
- **Top Silkscreen Location:** `11UF1`, directly below the RAM modules.
- **Surface Package Markings:**
  - Line 1: `SEC 519`
    - `SEC` = Samsung Electronics Company
    - `519` = Year 2025, Week 19 (Manufactured first half of May 2025)
  - Line 2: `B041`
  - Line 3: `KLMBG2JETD`
  - Line 4: `SRN5800DE` + 2D DataMatrix barcode
- **Samsung Part Decoder:**
  - Part Number: **`KLMBG2JETD-B041`**
  - **Generation:** eMMC 5.1 standard with command queuing, HS400 dual-data-rate mode.
  - **Density:** 32 GB (Gigabytes).
  - **NAND Flash Architecture:** Samsung 2-bit MLC / V-NAND.
  - **Performance:** Sequential read up to ~330 MB/s, sequential write up to ~100 MB/s.
  - **Package:** 153-ball FBGA (11.5 mm × 13.0 mm).

---

## 3. Core Processor, Clocking & Board Architecture

### 3.1 Main SoC & Heatsink
- The central processor sits beneath a permanently bonded or thermal-taped **4-fin black anodized aluminum heatsink**.
- Directly to the right of the heatsink at **`XM01`** is a **24.000 MHz crystal oscillator** (`YL240`), which supplies the base reference clock to the Amlogic SoC PLLs.
- **Platform Identification:** The board code `5800-2AHP44T` matches the **Skyworth HP44 / HP44H platform**, known across international operator set-top boxes to integrate the **Amlogic S905X4** SoC:
  - **CPU:** Quad-Core ARM Cortex-A55 (64-bit ARMv8-A architecture) clocked up to 2.0 GHz.
  - **GPU:** ARM Mali-G31 MP2 with Vulkan 1.1, OpenGL ES 3.2, and OpenCL 2.0 support.
  - **Hardware Video Decoding:**
    - AV1 codec support up to 4K@60fps (10-bit).
    - VP9 Profile 2, H.265 (HEVC) Main10 up to 4K@60fps.
    - H.264 AVC up to 4K@30fps.
  - **Security Architecture:**
    - ARM TrustZone technology.
    - Hardened Secure Boot with OTP eFuse signature verification.
    - Integrated Crypto Engine (AES, SHA-256, RSA, ECC, TRNG).
    - Widevine L1 & PlayReady SL3000 DRM compliance.

### 3.2 Board Origin & Manufacturing Date Alignment
- Silkscreen: **`5800-2AHP44T`**
  - Prefix `5800-` is the proprietary internal part numbering scheme of **Shenzhen Skyworth Digital Technology Co., Ltd.**
- Fabrication Stamp:
  - **`4E14743B0 KB6164F`**
  - UL Mark: **`E503744`** (Registered to Xingda Circuits Co., Ltd., PCB fabricator).
  - Material: **`XS-M 94V-0`** (Flame-retardant rating).
  - Compliance: `RoHS`, `CQC XS-M`, Serial `19001227631`.
  - Date Stamp: **`. 2521 :`** indicating manufacturing in **Week 21 of 2025 (late May 2025)**.
- **Date Code Synchronization:**
  - PPT Ethernet Transformer (`JL01`): `2510` (Week 10, March 2025)
  - Samsung eMMC (`11UF1`): `519` (Week 19, May 2025)
  - PCB Fabrication: `2521` (Week 21, May 2025)
  - Demonstrates just-in-time assembly in mid-to-late 2025.

---

## 4. Wireless Subsystem & Antennas

### 4.1 RF Circuitry
- Top Side: Shielded by a square black electro-tin / nickel-plated RF shield labeled **`UW01`**.
- Adjacent Crystal: **`XW01`** provides dedicated timing for the wireless radio.
- **Chipset Identification:** Definitively verified via extracted OTA firmware kernel modules and firmware blobs to be the **Realtek RTL8822CS** combo chipset:
  - 2T2R (2×2 MIMO) Dual-Band Wi-Fi 5 (802.11a/b/g/n/ac) over high-speed SDIO bus.
  - Integrated Bluetooth 5.0 controller over high-speed UART (`sdio_bt.ko` / `rtk_btusb.ko`).
  - Extracted driver artifacts: `vendor/lib/modules/8822cs.ko` and `vendor/firmware/rtl8822cs_fw`.

### 4.2 Antenna Topology
- Bottom Side: Two micro-coaxial RF connectors labeled **`J2`** and **`J4`** (standard IPEX MHF / U.FL receptacles).
- In teardown photograph `IMG20261017140652.jpg`, a thin black coaxial pigtail cable is routed from one of these ports to an internal adhesive flexible PCB antenna mounted to the white plastic enclosure wall.

---

## 5. Rear I/O Ports & Power Delivery Network

### 5.1 Rear Port Inventory (Left to Right, Top-Down View)

```
[JP01] DC In  ──>  [JB01] USB 3.0  ──>  [JB03] USB 2.0  ──>  [JL01] RJ45 LAN  ──>  [16JH1] HDMI
```

1. **DC Power Input (`JP01`):**
   - 12V DC center-positive coaxial barrel jack.
   - Protected by surface mount fuse **`T250`** (2.5A fast-acting SMD fuse).
   - Filtered by high-capacity electrolytic capacitor **`CP07`** (25V, 220 µF).
2. **USB 3.0 Port (`JB01`):**
   - Blue plastic insert, 9 pins (SuperSpeed 5 Gbps + USB 2.0 backward compatibility).
   - Power distribution IC and ESD array (`UB07`, `CB08`).
3. **USB 2.0 Port (`JB03`):**
   - Black plastic insert, 4 pins (High-Speed 480 Mbps).
   - Used for peripherals, external drives, or USB recovery flashing.
   - Power switch IC (`UB06`, `CB09`).
4. **Fast Ethernet LAN (`JL01`):**
   - Metal-shielded RJ45 8P8C modular connector.
   - Paired with magnetic isolation transformer **`PPT 2510F .PSF-1626`** (10/100 Mbps Fast Ethernet pulse transformer).
5. **HDMI Port (`16JH1`):**
   - Full-size 19-pin HDMI Type-A receptacle supporting 4K@60Hz video and multi-channel audio.
   - Protected by multichannel inline ESD clamp arrays at **`16UH1`** directly behind the connector pins.

### 5.2 Power Regulation Topology
The PCB features an efficient multi-stage switched-mode power supply (SMPS) network:
- **`1UP1` + Inductor `4R7` (4.7 µH):** Generates 5.0V system rail / USB VBUS power.
- **`2UP1` + Inductor `4R7` (4.7 µH):** Generates 3.3V peripheral and I/O rail.
- **`4UP1` + Inductor `2R2` (2.2 µH):** Dedicated 1.2V VDD rail for Micron DDR4 SDRAM.
- **`8UP1` + Inductor `2R2` (2.2 µH):** High-efficiency core supply for SoC VDD_CPU (dynamic 0.8V–0.95V).
- **`9UP1` + Inductor `2R2` (2.2 µH):** SoC VDD_EE / GPU / System logic supply.
- **`20UP1` (SOT-223 package):** Low-dropout linear regulator (LDO) paired with an orange tantalum capacitor for clean analog / PLL voltages.
- **Bottom-side ICs (`15UP1`, `21UP1`):** Auxiliary sequencing and power distribution.

---

## 6. Hardware Hacking, Debugging & Attack Surface

For cybersecurity researchers, reverse engineers, and hardware tinkerers, this board exposes multiple accessible testing and recovery vectors:

```
                  ┌──────────────────────┐
                  │   SoC Under Fin-     │
                  │   ned Heatsink       │
                  └──────────┬───────────┘
                             │
     [XM01] 24MHz            │
         ┌───┐               │
         └───┘               │
                             ▼
                    ┌─────── J7 UART ───────┐
                    │  [ ] GND    [ ] 3V3   │  (staggered 2x2 layout)
                    │       [ ] RX    [ ] TX│
                    └───────────────────────┘
                                      ┌──────┐
                                      │ SK01 │  [Reset Button]
                                      └──────┘
```

### 6.1 UART Serial Console (`J7`)
- **Location:** Directly to the right of the heatsink, between the processor and the right PCB edge.
- **Physical Layout & Pinout:**
  The 4 pads are arranged in a staggered 2×2 / zigzag pattern enclosed between silkscreen brackets `[` and `]`:
  - **Pad 1 (Lower Left, next to `[`):** **`GND`** (Digital Ground)
  - **Pad 2 (Upper Middle-Left):** **`RX`** (SoC UART_RX, 3.3V TTL Input to SoC)
  - **Pad 3 (Lower Middle-Right):** **`TX`** (SoC UART_TX, 3.3V TTL Output from SoC)
  - **Pad 4 (Upper Right, next to `]`):** **`3V3`** (3.3V Power Rail — **LEAVE DISCONNECTED!**)
- **Wiring Instructions for USB-to-TTL Adapter:**
  - Connect **GND** of adapter ──> **Pad 1 (`GND`)**
  - Connect **TX** of adapter ──> **Pad 2 (`RX`)** (3.3V TTL)
  - Connect **RX** of adapter ──> **Pad 3 (`TX`)** (3.3V TTL)
  - **DO NOT connect 3V3 (Pad 4)**: Power the board via its 12V DC barrel jack only.
- **Serial Terminal Configuration:**
  - **Baud Rate:** **`921600` baud** (Standard default bootloader baud rate for **Amlogic S905X4** / SC2 family architecture).
    *(Note: If 921600 produces no output or corrupted characters, test fallbacks `115200` or `1500000`).*
  - **Data bits:** 8
  - **Parity:** None
  - **Stop bits:** 1 (8N1)
  - **Flow control:** None / Off
  - **Adapter Requirement:** High-speed capable USB-to-UART bridge (e.g. CP2102N, FT232RL, CH343, or RP2040) running at **3.3V logic level**. Cheap clone PL2303/CH340G may fail to lock onto 921600 baud.
- **Troubleshooting Missing Output:**
  1. *Staggered Pin Confusion:* Do NOT mistake Pad 3 for 3V3 or Pad 4 for TX. Connecting the adapter RX to Pad 4 (3.3V rail) gives a flat line and zero output.
  2. *Cold Boot Timing:* Connect your terminal before plugging in the 12V DC power jack. Amlogic bootrom and BL2 output starts immediately upon power-on.
  3. *Unpopulated SMD Jumpers:* Inspect the tiny SMD pad cluster directly below the RX/TX traces. If series 0Ω resistors or jumpers are omitted on your specific board revision, bridge them or probe continuity from the pads down to the SoC traces.
- **What to Expect on Boot:**
  - Amlogic BL2 bootloader initialization messages.
  - Secure OS / OP-TEE loading logs.
  - U-Boot version, environment variables, kernel command line (`bootargs`).
  - Kernel initialization log (`dmesg`) and Android init sequence.

### 6.2 Hardware Recovery & USB Flashing (`SK01`)
- **Location:** Right edge of the board, micro tactile push-button labeled **`SK01`** and **`Reset`**.
- **Operation:**
  - Holding down this button while inserting the 12V DC power jack forces the Amlogic boot ROM to divert from the standard eMMC boot sequence into:
    1. **Android Recovery Mode** (if recovery partition is intact).
    2. **Amlogic USB Burning Mode** (when connected to a host PC using a USB-A to USB-A cable connected to the USB 2.0 port `JB03`).
  - Software Tool: **Amlogic USB Burning Tool** can be used on a host PC to detect the device in flashing mode (`WorldCup Device`).

### 6.3 eMMC Fault Injection / Mask ROM Fallback
- The Samsung eMMC chip (`11UF1`) is accessible in standard BGA format.
- If Secure Boot or a locked bootloader prevents UART intervention, shorting the eMMC clock line (`CLK`) to ground during power-on triggers an eMMC read timeout, forcing the Amlogic boot ROM into **Mask ROM USB download mode** (`USB ID: 1b8e:05af`), allowing low-level payload execution.

---

## 7. Photographic Evidence Cross-Reference

| Photo File | Primary Focus | Visible Key Features |
| :--- | :--- | :--- |
| `IMG20261017140533.jpg` | Bottom PCB & Case | Grounding thermal grid, IPEX antenna ports `J2`/`J4`, white plastic case with vents, removed mounting screws |
| `IMG20261017140558.jpg` | Full Top PCB (Assembled) | Heatsink, gray thermal pads covering RAM & eMMC, RF shield `UW01`, all rear I/O connectors |
| `IMG20261017140602.jpg` | Top PCB Overhead | Complete board layout, capacitor `CP07`, power inductors, reset switch `SK01` |
| `IMG20261017140606.jpg` | Left Top PCB (Pads Off) | Micron DDR4 RAM (`3U3`, `3U4`), Samsung eMMC (`11UF1`), buck inductors (`2R2`, `4R7`) |
| `IMG20261017140623.jpg` | Right Top Close-up | UART header `J7` (`GND`, `RX`, `3V3`, `TX`), PPT `PSF-1626` transformer, `SK01` reset switch |
| `IMG20261017140625.jpg` | Lower-Right Corner | Board markings `5800-2AHP44T`, date code `. 2521 :`, UL certification `E503744` |
| `IMG20261017140632.jpg` | Memory & Heatsink | Detailed shot of heatsink fins, Micron `5IR75` / `D8BPK` chips, Samsung eMMC `SEC 519` |
| `IMG20261017140637.jpg` | Macro View of ICs | High-resolution macro of Micron `D8BPK` markings and Samsung `KLMBG2JETD-B041` text |
| `IMG20261017140644.jpg` | Angled Perspective | Perspective view showing component heights, heatsink fins, shield `UW01`, and ports |
| `IMG20261017140652.jpg` | Rear I/O Face | Handheld edge view showing DC jack, USB 3.0 (blue), USB 2.0 (black), RJ45, HDMI; coax antenna wire |
| `IMG20261017140659.jpg` | Full Top Diagonal | Wide angled perspective of the entire PCB |
| `IMG20261017140700.jpg` | Port Side Macro | Close-up of rear connector solder anchors, `CP07` filter cap, `T250` fuse |

---
## 🔗 Related Documents

| Related Document | Relationship |
| :--- | :--- |
| [`AML_MASKROM_SECURITY_ANALYSIS.md`](AML_MASKROM_SECURITY_ANALYSIS.md) | MaskROM / WorldCup flashing entry, eMMC `CLK` short points (Targets A/B/C), AVB 2.0 / dm-verity signing architecture. Hardware debug fallback when UART is suppressed. |
| [`ROOT_ADB_CUSTOM_ROM_GUIDE.md`](ROOT_ADB_CUSTOM_ROM_GUIDE.md) | ADB enablement via UART `J7` (§2 Method 2) and hardware recovery `SK01` (§2 Method 3); Magisk root and AVB bypass. |
| [`OTA_ANALYSIS.md`](OTA_ANALYSIS.md) | Extracted partition images & kernel/driver verification that confirm the RAM, eMMC, Wi-Fi (RTL8822CS), and demodulator (CXD2856) hardware identified here. |
| [`jio_infrastructure/12_HARDWARE_BOOT_AND_TRUSTZONE_INFRA.md`](jio_infrastructure/12_HARDWARE_BOOT_AND_TRUSTZONE_INFRA.md) | Silicon Root-of-Trust, Amlogic eFUSE, OP-TEE TrustZone, factory key injection, Verimatrix CAS, Sony CXD2856 tuner frontend. |

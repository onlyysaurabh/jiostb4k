# 05. IPTV, LiveTV, EPG Metadata & Unicast DRM Key Infrastructure

> **Parent Topic:** [`jio_infrastructure/README.md`](README.md)  
> **Source Packages:** [`JioLiveTV.apk`](../ota_packages/extracted/apks/jio_system_priv_app/JioLiveTV.apk), [`JioInputSource.apk`](../ota_packages/extracted/apks/jio_system_priv_app/JioInputSource.apk), [`Bioscope.apk`](../ota_packages/extracted/apks/jio_system_priv_app/Bioscope.apk)

---

## 1. Architectural Overview

Reliance Jio’s television delivery combines multicast DVB-IP transport with HTTP Live Streaming (HLS) / MPEG-DASH unicast video on demand and catch-up services. The linear streaming stack comprises:
1. **Unicast Key Management (`ucast-key.iptv.jio.com`):** Delivers cryptographic decryption keys and DRM licenses for encrypted IPTV streams.
2. **Metadata & EPG Delivery (`jiotv.data.cdn.jio.com` / `jltf.akamaized.net`):** Distributes real-time Electronic Program Guides (EPG) and Cloud DVR configurations.
3. **Catchup TV CDN (`jiotv.catchup.cdn.jio.com`):** Serves time-shifted linear channel segments across Akamai edge nodes.
4. **On-Device Hybrid Engine (`JioLiveTV.apk` & `JioInputSource.apk`):** Interfaces with Android’s `TvProvider` database, hardware Amlogic video decoders, and tuner HAL.

```
                      ┌──────────────────────────────────────────────┐
                      │          JioLiveTV.apk / DVB-IP Engine       │
                      │           (Amlogic Hardware Pipeline)        │
                      └──────────────────────┬───────────────────────┘
                                             │
             ┌───────────────────────────────┼───────────────────────────────┐
             │                               │                               │
             ▼                               ▼                               ▼
 ┌───────────────────────┐       ┌───────────────────────┐       ┌───────────────────────┐
 │   DRM Key Exchange    │       │     EPG & Cloud DVR   │       │   Catchup & Streaming │
 ├───────────────────────┤       ├───────────────────────┤       ├───────────────────────┤
 │ ucast-key.iptv.jio.com│       │ jiotv.data.cdn.jio.com│       │ jiotv.catchup.cdn.jio │
 │ (AES-128 / Widevine)  │       │ jltf.akamaized.net    │       │ jltf.akamaized.net    │
 └───────────────────────┘       └───────────────────────┘       └───────────────────────┘
```

---

## 2. Unicast DRM & Key Management Infrastructure

### 2.1 The Unicast Key Server (`ucast-key.iptv.jio.com`)
* **FQDN:** `ucast-key.iptv.jio.com`
* **Transport:** HTTPS (Port 443)
* **Function:** Validates subscriber channel entitlement and issues per-session or per-channel AES decryption keys for live unicast IPTV streams.
* **Client Binding:** Invoked directly by `JioInputSource.apk` and `JioLiveTV.apk` when transitioning from unencrypted preview feeds to protected pay-TV tiers.

---

## 3. Metadata, EPG & Program Schedule Endpoints

### 3.1 JioTV Data CDN (`jiotv.data.cdn.jio.com`)
* **Underlying Edge:** Akamai Technologies (AS16625)
* **EPG Query API:**
  ```http
  GET /apis/v1.3/getepg/get?channel_id=<CHANNEL_ID> HTTP/1.1
  Host: jiotv.data.cdn.jio.com
  ```
  Returns program titles, synopsis descriptions, episode markers, genre tags, and airing times.
* **Cloud DVR Configuration:**
  ```http
  GET /cloud_dvr/services_0.json HTTP/1.1
  Host: jiotv.data.cdn.jio.com
  ```
  Defines cloud recording quotas, allowed recording durations per channel, and storage node mappings. (Returns HTTP 450 Forbidden if accessed without valid subscriber token).

### 3.2 Akamai LiveTV Data Store (`jltf.akamaized.net`)
Delivers static channel manifests and master schedules:
* **Master Channel Manifest:**
  ```text
  https://jltf.akamaized.net/LiveTV/channels.json
  ```
* **Daily Program Schedule Directory:**
  ```text
  https://jltf.akamaized.net/LiveTV/PROD/data/program_schedule/
  ```

### 3.3 Bioscope Video Feed APIs (`api-bs.jio.com`)
Privileged application `Bioscope.apk` renders personalized short video feeds and live stream highlights:
* `https://api-bs.jio.com/bioscope/v1/app/feed/feed_expand`
* `https://api-bs.jio.com/bioscope/v1/identity/getOauth?from=livetv`
* `https://api-bs.jio.com/bioscope/v1/identity/getSession?from=livetv`
* `https://api-bs.jio.com/bioscope/v2/app/feed/personalized?from=livetv`

---

## 4. Catchup TV & Streaming CDN Infrastructure

* **Host:** `jiotv.catchup.cdn.jio.com`
* **Protocol:** HLS (`.m3u8` playlists and `.ts` transport stream segments)
* **Time-Shift Window:** Typically allows subscribers to seek backwards up to 7 days for supported channels.
* **Edge Enforcement:** URL tokens and IP-origin verification enforce geo-blocking and Jio-only ASN routing.

---

## 5. Subscriber SMS/OTP Authentication Backends

In addition to FTTH broadband line binding, the Live TV client supports mobile OTP authorization:
* `http://jiotv.jio.ril.com/apis/v1.3/stbotplogin/sendotp`
* `http://jiotv.jio.ril.com/apis/v1.3/stbotplogin/verifyotp`
* `https://tv.media.jio.com/apis/v1.3/stbotplogin/sendotp`
* `https://tv.media.jio.com/apis/v1.3/stbotplogin/verifyotp`

---

## 6. On-Device TV Engine & DVB-IP Broadcast IPC

The system handles channel changes and tuner hardware interaction via Android broadcast intents:

| Action String | Component | Description |
| :--- | :--- | :--- |
| `com.jio.catv.intent.action.TUNE_CHANNEL` | `JioLiveTV.apk` | Instructs the Amlogic hardware decoder to tune to a specific logical channel number (LCN). |
| `com.jio.catv.intent.action.DVBIP_MODE_BOUQUET_CHANGE` | `JioLiveTV.apk` | Changes the active channel bouquet (multicast group or unicast service bundle). |

### 6.1 Third-Party MSO Integration (Hathway)
Within `JioLiveTV.apk`, deep link scheme handler `myjiopayment-hathway:` exists to allow Hathway cable TV subscribers to settle account balances or activate subscription tiers directly from the STB interface.

---

## 7. Network Gating & Dynamic Channel Bouquet Selection

Reverse engineering of [`JioLiveTV.apk`](../ota_packages/extracted/apks/jio_system_priv_app/JioLiveTV.apk) (`com.jio.stb.catv`) reveals how linear TV delivery is locked to authorized carrier networks:

### 7.1 TR-069 Network Type Ingestion ([`a.java:27`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_livetv/sources/com/jio/stb/catv/sdk/a.java#L27))
Upon launch and on every connectivity change, `JioLiveTV` queries the TR-069 ContentProvider:
```java
Cursor cursor = context.getContentResolver().query(
    Uri.parse("content://com.tr069.data.provider/PARAMETERS"),
    null,
    "path",
    new String[]{"Device.JioSTB.Network.NetworkCheck.NetworkType"},
    null
);
```

### 7.2 Bouquet Mapping Matrix ([`JioSdk.java:503-524`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_livetv/sources/com/jio/stb/catv/sdk/JioSdk.java#L503-L524))
The detected network type dictates the active linear broadcast channel list:

| Reported Network Type | Target Channel Bouquet | Service State |
| :--- | :--- | :--- |
| **`FTTH`** | **Bouquet `406` / `310`** | Full HD/4K linear broadcast channels enabled over JioFiber |
| **`LTE`** | **Bouquet `412`** | Cellular-optimized bitrate tier |
| **`5G_subscriber`** | **Bouquet `407`** | JioAirFiber 5G high-speed tier |
| **`Enterprise`** | **Bouquet `405`** | Commercial / Hotel premises tier |
| **`NonJioNetwork`** | **Bouquet `421`** | **Blackout / Service Block:** All linear TV channels removed |
| **`NetworkTypeNotAvailable`** | **Bouquet `400`** | Offline fallback state |

### 7.3 SSO Credential Handshake ([`SsoTokenHandler.java:268`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_livetv/sources/pc/d.java#L268))
`JioLiveTV` binds to `com.media.jio.sso.stb` via action `service.sso`. It invokes `getLoginData()` to retrieve the subscriber's active `ssoToken` and `subscriberId`. If `ssoToken` is missing (as occurs when connected to non-Jio networks due to ZLA rejection), playback stops immediately and prompts the user to verify broadband connectivity.

---
## 🔗 Related Documents

| Related Document | Relationship |
| :--- | :--- |
| [`../NETWORK_ANALYSIS.md`](../NETWORK_ANALYSIS.md) | Linear stream and catch-up TV traffic capture. |
| [`07_ADTECH_MERCURY_AND_MONETIZATION.md`](07_ADTECH_MERCURY_AND_MONETIZATION.md) | Programmatic ad engine and impression/click attribution injected into the Live TV UI. |
| [`04_CORE_AUTH_SSO_AND_USER_MANAGEMENT.md`](04_CORE_AUTH_SSO_AND_USER_MANAGEMENT.md) | Media authentication cluster (`*.media.jio.com`) and SSO token issuance for playback entitlement. |

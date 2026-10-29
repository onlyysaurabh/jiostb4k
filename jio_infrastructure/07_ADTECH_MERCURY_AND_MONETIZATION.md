# 07. JioAds, Mercury Platform & Monetization Infrastructure

> **Parent Topic:** [`jio_infrastructure/README.md`](README.md)  
> **Source Packages:** [`JioAdsPushService.apk`](../ota_packages/extracted/apks/jio_system_priv_app/JioAdsPushService.apk), [`JioScreensaver.apk`](../ota_packages/extracted/apks/jio_system_priv_app/JioScreensaver.apk), [`JioLauncher.apk`](../ota_packages/extracted/apks/jio_system_priv_app/JioLauncher.apk), [`JioLiveTV.apk`](../ota_packages/extracted/apks/jio_system_priv_app/JioLiveTV.apk)

---

## 1. Architectural Overview

Reliance Jio operates an enterprise programmatic advertising and campaign delivery network branded as **Mercury**. The system orchestrates display ads across the Android TV launcher, sponsored screensavers, dynamic interstitial videos in JioLiveTV, and sponsored banners in JioStore:

```
                      ┌──────────────────────────────────────────────┐
                      │          On-Device Ad Dispatchers            │
                      │ (JioAdsPushService.apk / JioScreensaver.apk) │
                      └──────────────────────┬───────────────────────┘
                                             │
             ┌───────────────────────────────┼───────────────────────────────┐
             │                               │                               │
             ▼                               ▼                               ▼
 ┌───────────────────────┐       ┌───────────────────────┐       ┌───────────────────────┐
 │   Mercury Ad Engine   │       │ Attribution & Clicks  │       │ Push Campaign Sync    │
 ├───────────────────────┤       ├───────────────────────┤       ├───────────────────────┤
 │ • mercury.jio.com     │       │ • mercury-ck.jio.com  │       │ • mercury.akamaized   │
 │ • mercury-stg.jio.com │       │ • adtracker.jiocinema │       │ • jioads.akamaized    │
 │ (api, mapi, vapi.php) │       │ • moloco.jiocinema.com│       │ (JioadsPush.json)     │
 └───────────────────────┘       └───────────────────────┘       └───────────────────────┘
```

---

## 2. Mercury Ad Serving APIs (`mercury.jio.com`)

The core ad decision engine delivers targeting payloads via PHP backend services:

| Environment | Endpoint | Protocol | Purpose |
| :--- | :--- | :--- | :--- |
| **Production General API** | `https://mercury.jio.com/delivery/api.php` | HTTPS | Standard JSON ad payload decision engine. |
| **Production Mobile API** | `https://mercury.jio.com/delivery/mapi.php` | HTTPS | Lightweight mobile and leanback display ads. |
| **Production Video API** | `https://mercury.jio.com/delivery/vapi.php` | HTTPS | VAST/VMAP video pre-roll and mid-roll ad configurations. |
| **Staging Endpoints** | `https://mercury-stg.jio.com/delivery/{api,mapi,vapi}.php` | HTTPS | Pre-production testing and staging campaign verification. |

---

## 3. Attribution, Impression & Click Tracking (`mercury-ck.jio.com`)

Attribution is tracked via specialized tracking endpoints with granular client telemetry query parameters:
* **Click Tracking:** `https://mercury-ck.jio.com/delivery/ck.php`
* **Conversion / Notification Tracking:** `https://mercury-ck.jio.com/delivery/cn.php`
* **Staging Tracker:** `https://mercury-ck-stg.jio.com/delivery/cn.php`

### 3.1 Reverse-Engineered Query Parameter Taxonomy
A live tracking URL extracted from [`JioScreensaver.apk`](../ota_packages/extracted/apks/jio_system_priv_app/JioScreensaver.apk) reveals the telemetry payload:

```text
https://mercury-ck.jio.com/delivery/ck.php?oaparams=2__asi=186131__source=__cb=2fxc2dl8kp__dle=2__at=5__ob=1__cd=7__aud=-1__c=79813__tm=0__rl=0__li=__bi=__mi=__ro=__ag=__rr=0.0000__rt=4__rc=1__rcs=91032ad7bbcb6cf72875e8e8207dcfba80173f7c__aiv=1__biv=3__ssf=0__bae=0__mn=JHSC200__ifa=98920183-b7d9-924e-fe7f-c938d4a0173a__av=3.0.52.7__vr=AN-2.3.7__cgi=defaultCGI__uid=5288145589__br=Jio__osv=11__os=1__dt=4__a=4942__ai=com.jio.halotv__cid=4942_186131_79813_250614_0_2fxc2dl8kp_
```

| Parameter | Meaning | Extracted Value | Function |
| :--- | :--- | :--- | :--- |
| `mn` | Model Name | `JHSC200` | Device hardware generation |
| `ifa` | Identifier for Advertising | `98920183-b7d9-...` | Unique advertising ID |
| `osv` | OS Version | `11` | Android 11 |
| `uid` | User ID | `5288145589` | Jio subscriber profile identifier |
| `ai` | Application ID | `com.jio.halotv` | Calling system package |
| `cid` | Campaign ID | `4942_186131_...` | Specific ad campaign tracking tag |

---

## 4. Push Campaign Sync & Static CDN Assets

To reduce backend load, campaign schedules are published as static JSON manifests on Akamai:
* **STB Production Campaign Schedule:**
  ```text
  https://mercury.akamaized.net/push/v2//STB/PROD/JioadsPush.json
  ```
* **Master Campaign Manifest:**
  ```text
  https://mercury.akamaized.net/push/v2/JioadsPushMaster.json
  ```
* **Tracking Pixels & Beacons:**
  * `https://jioads.akamaized.net/beacon/anb.gif`
  * `https://jiojap.akamaized.net/beacon1/1x1.gif`
  * `https://mercury.akamaized.net/mdt/TargetingValidator.js`

---

## 5. Partner & Third-Party Ad Networks

### 5.1 JioCinema & Moloco Integration
Inside `JioLiveTV.apk`, programmatic ad exchange integrations interface with **Moloco**:
* `https://adtracker.jiocinema.com/i?ev=click&asi=`
* `https://adtracker.jiocinema.com/i?ev=imp&asi=`
* `https://moloco.jiocinema.com/`
* `https://tr-jio-imp.adsmoloco.com/`
* `https://tr-jio-view.adsmoloco.com/`

### 5.2 Internal PHP Ad Spot Server
Discovered in `JioSphere.apk`:
```text
https://ajdivotdelbloab24.jio.com/getad.php?adspots=2cac2401
https://ajdivotclibloab24.jio.com/
```
Provides direct internal ad-slot injection for pre-loaded browser homepages and widgets.

---
## 🔗 Related Documents

| Related Document | Relationship |
| :--- | :--- |
| [`06_TELEMETRY_ANALYTICS_AND_PUSH.md`](06_TELEMETRY_ANALYTICS_AND_PUSH.md) | Telemetry ingestion (`devents.magnum.jio.com`) and push notification delivery fleet. |
| [`../NETWORK_ANALYSIS.md`](../NETWORK_ANALYSIS.md) | Ad/tracking traffic capture. |
| [`05_IPTV_LIVETV_EPG_AND_DRM.md`](05_IPTV_LIVETV_EPG_AND_DRM.md) | Ad interstitials and sponsored banners injected into the Live TV UI. |

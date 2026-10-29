# 04. Core APIs, Subscriber Authentication & Identity (SSO) Infrastructure

> **Parent Topic:** [`jio_infrastructure/README.md`](README.md)  
> **Source Packages:** [`JioStbSsoService.apk`](../ota_packages/extracted/apks/jio_system_priv_app/JioStbSsoService.apk), [`PADI.apk`](../ota_packages/extracted/apks/jio_system_priv_app/PADI.apk), [`JioVoice.apk`](../ota_packages/extracted/apks/jio_system_priv_app/JioVoice.apk), [`JioHotelLauncher.apk`](../ota_packages/extracted/apks/jio_system_priv_app/JioHotelLauncher.apk)

---

## 1. Executive Summary & Architecture

Reliance Jio decouples subscriber identity, broadband line entitlement, and application session management into a centralized authentication fabric. Set-Top Boxes, companion applications, and third-party OTT partners (e.g., Netflix) obtain authorization tokens through a hierarchy of API gateways:

```
                      ┌──────────────────────────────────────────────┐
                      │          Jio 4K Set-Top Box                  │
                      │   (JioStbSsoService.apk / PADI.apk)          │
                      └──────────────────────┬───────────────────────┘
                                             │
             ┌───────────────────────────────┼───────────────────────────────┐
             │                               │                               │
             ▼                               ▼                               ▼
 ┌───────────────────────┐       ┌───────────────────────┐       ┌───────────────────────┐
 │   Core API Gateway    │       │    JioID SSO & IAM    │       │   Partner PADI Gateway │
 ├───────────────────────┤       ├───────────────────────┤       ├───────────────────────┤
 │ • api.jio.com         │       │ • jioid.jio.com       │       │ • partnerapi.jio.com  │
 │ • api-bs.jio.com      │       │ • auth.media.jio.com  │       │ • pp-api-raasgw.jio   │
 │ • api-sit.jio.com     │       │ • prod.media.jio.com  │       │ • siglyapi.jio.com    │
 │ (F5 BigIP ADC)        │       │ • signup.jio.com      │       │ (Netflix & OTT Token) │
 └───────────────────────┘       └───────────────────────┘       └───────────────────────┘
```

---

## 2. Core API Gateway (`api.jio.com` & `api-bs.jio.com`)

* **Primary IP:** `103.63.129.21` (AS55836, Reliance Industries Limited)
* **Load Balancer / Reverse Proxy:** F5 BigIP Application Delivery Controller (ADC)
* **Transport:** HTTPS (TLS 1.2 / TLS 1.3) over TCP port 443

### 2.1 Core Subscriber Verification Endpoints
The following endpoints are polled by virtually every privileged Jio system package during device boot and network state transitions:

```http
GET /ftth/v1/network/check HTTP/1.1
GET /ftth/v2/users/me HTTP/1.1
GET /v1/network/check HTTP/1.1
GET /v2/users/me HTTP/1.1
```

### 2.2 App-Name Context Header / Parameter
Requests distinguish client subsystems via the `app-name` query parameter:
* `app-name=RJIL_JioSTB` (STB system daemon and SSO)
* `app-name=RJIL_JioPush2` (`JioHotelLauncher.apk`, `JioLiveTV.apk`)
* `app-name=RJIL_JioAds_Android` (`JioAdsPushService.apk`, `JioLauncher.apk`)

### 2.3 Staging & Sandbox Gateways
* `http://api-sit.jio.com/` (System Integration Testing)
* `http://api-st.jio.com/` (Staging Environment)
* `http://api.jiolabs.com/` (JioLabs Innovation Sandbox)

---

## 3. Single Sign-On & Media IAM Suite

### 3.1 JioID & Account Activation
* **Master Identity Provider:** `https://jioid.jio.com/`
* **Subscriber Portal & Self-Care:** `https://signup.jio.com/`
  * Activation endpoint: `/Signup/portal/activation.jspx?jioactivation=jioactivation`
  * Password reset endpoint: `/Signup/portal/forgotPassword.jspx`

### 3.2 Media Authentication Cluster (`*.media.jio.com`)
Media streaming applications (`JioLiveTV.apk`, `Bioscope.apk`, `JioVoice.apk`) validate playback sessions through dedicated media auth brokers:
* **Production Auth:** `https://auth.media.jio.com/`
* **JSON Web Token Issuer:** `https://api-jmauth.media.jio.com/`
* **Production Media Gateway:** `https://prod.media.jio.com/apis/common/v3/login/`
* **QA Replica Login:** `https://qa.media.jio.com/mdp_qa/apis/common/v3/replicalogin/`
* **JioTV Media Net:** `https://qa-auth.jiotv.jiomedia.net/`

### 3.3 The Zero Login Architecture (ZLA) & Auto-Authentication Engine

A central discovery from reverse engineering [`JioStbSsoService.apk`](../ota_packages/extracted/apks/jio_system_priv_app/JioStbSsoService.apk) is Jio's **Zero Login Architecture (ZLA)**. The Set-Top Box does **not require a username, password, or physical SIM card** to authenticate. Instead, identity is derived directly from the **carrier physical transport network**.

#### 3.3.1 ZLA Execution Flow (`MediaLoginActivity.java:626-735`)
During boot or upon any network state transition, [`BootReceiver`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_sso/sources/com/media/jio/sso/stb/receiver/BootReceiver.java) triggers `doSynchronousZLACall()`:

1. **Cleartext HTTP Request Construction:**
   ```http
   GET /ftth/v2/users/me?app-name=RJIL_JioSTB HTTP/1.1
   Host: api.jio.com
   x-request-data: {"rememberUser":"T","upgradeAuth":"Y","deviceInfo":{"consumptionDeviceName":"STB","info":{"type":"android","platform":{"name":"<Build.MANUFACTURER> <Build.MODEL>"},"androidId":"<Settings.Secure.android_id>"}}}
   ```
2. **Network-Based Identity Resolution (Zero User Credentials):**
   - Notice that **no subscriber ID, phone number, or password is sent** in the `x-request-data` payload.
   - The carrier's Broadband Network Gateway (BNG) and AAA / PCRF infrastructure inspect the client's public ingress IP address.
   - If the request originates from an active **JioFiber FTTH connection** within **AS55836**, the carrier core resolves the IP address to the subscriber's circuit ID and returns full authentication claims.
3. **Response Schema (`l3.w` & `l3.u`):**
   ```json
   {
     "code": 200,
     "ssoToken": "<MASTER_JWT_BEARER_TOKEN>",
     "jToken": "<SESSION_TOKEN>",
     "lbCookie": "<F5_BIGIP_STICKY_PERSISTENCE_COOKIE>",
     "packageMapping": [ ... ],
     "sessionAttributes": {
       "user": {
         "commonName": "Subscriber Full Name",
         "mail": "subscriber@email.com",
         "mobile": "98XXXXXXXX",
         "subscriberId": "1000XXXXXX",
         "uid": "USER_ID",
         "unique": "UNIQUE_ID"
       }
     }
   }
   ```
4. **Local Database Persistence:**
   Tokens and identity claims are committed to the on-device SQLite database ([`JioDatabase_Impl.java`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_sso/sources/com/media/jio/sso/stb/db/JioDatabase_Impl.java#L57-L63)) across three relational tables:
   - `login`: Stores `id`, `loginType` (`ZLA`), `subscriberId`, `ssoToken`, `jToken`, `lbCookie`, `mobileNumber`, `deviceId`, and `connectedOnt`.
   - `customerinfo`: Stores personal demographic records (name, email, billing address, PIN code, profile photo).
   - `planofferings`: Stores active broadband and OTT subscriptions (`serviceType`, `planId`, `planName`, `startDate`, `endDate`, `autoRenew`).

---

### 3.4 Cross-Application Token Distribution & IPC Broker (`AIDLServer.java`)

All media applications installed on the STB obtain subscriber session credentials by binding to `JioStbSsoService.apk` via Android Inter-Process Communication (IPC):

```
                   JioStbSsoService (com.media.jio.sso.stb)
                     │  AIDLServer (action: "service.sso")
                     │
         ┌───────────┼───────────┬───────────┐
         ▼           ▼           ▼           ▼
     JioLiveTV    JioVoice   JioCinema     JioTV+
   (com.jio.stb  (com.android (com.jio.  (com.jio.media.
      .catv)      .voice)      .media)    stb.ottplay)
```

1. **Client Binding Mechanism:**
   Client apps instantiate an intent with action `service.sso` and package `com.media.jio.sso.stb`:
   ```java
   // From JioLiveTV SsoTokenHandler.java (Line 268) & JioVoice SsoServerRequest.java (Line 225)
   Intent intent = new Intent("service.sso");
   intent.setPackage("com.media.jio.sso.stb");
   context.bindService(intent, serviceConnection, Context.BIND_AUTO_CREATE);
   ```
2. **Interface Invocation:**
   Once connected, the client obtains the `IAidlServer` proxy and calls `getLoginData()`:
   ```java
   String jsonResponse = aidlServer.getLoginData();
   JSONObject obj = new JSONObject(jsonResponse);
   String ssoToken = obj.getString("ssoToken");
   String subscriberId = obj.getString("subscriberId");
   ```
3. **Security Vulnerability: Fail-Open Whitelist Bypass:**
   - The AIDL server is exported **without permissions**.
   - In [`MediaLoginActivity.java:3806-3826`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_sso/sources/com/media/jio/sso/stb/activity/MediaLoginActivity.java#L3806-L3826), the service attempts to verify whether the calling package is in the system whitelist by querying `/apis/v2.0/service/get`.
   - **Fail-Open Implementation:** If the HTTP request throws an exception (e.g., DNS error, timeout, or disconnected network), `c0065aT.c()` evaluates to `true`:
     ```java
     if (c0065aT.c()) { // c() returns true on network/parsing exception
         r(c0065aT);
         return o(str, jVarF); // Returns master subscriber token data!
     }
     ```
   - An unprivileged third-party APK can extract the user's master JWT and subscriber identity by simply querying the AIDL interface while the STB is offline or during a network failure.

---

## 4. Why Jio Services Fail on Non-Jio Networks: The Multi-Tier Network Lock

A core architectural characteristic of the Jio 4K STB ecosystem is that applications like **JioLiveTV, JioTV+, and JioCinema refuse to function when connected to non-Jio networks** (e.g., Airtel, ACT, Vi, or mobile hotspots). Reverse engineering proves that this enforcement is implemented via a **5-stage multi-tier network lock**:

```
                       Network Connection Established
                                     │
              ┌──────────────────────┴──────────────────────┐
              ▼                                             ▼
  Stage 1: Ingress ZLA Check                    Stage 2: TR-069 Classification
  api.jio.com/ftth/v2/users/me                  api.jio.com/common/v1/network/check
  • Non-Jio IP -> 401 Unauthorized              • Authenticated with STB Serial & JWT
  • No ssoToken / jToken generated              • Returns "Network": "NonJioNetwork"
              │                                             │
              ▼                                             ▼
  Stage 3: Application Gating                  Stage 4: Local Gateway Verification
  JioLiveTV / JioTV+ TR-069 Query              https://192.168.29.1/ (Local ONT)
  • Reads NetworkCheck.NetworkType             • OntModuleManager fetches MAC/Serial
  • NonJioNetwork -> Switches to               • Mismatch triggers ScreenLockReceiver
    restricted Bouquet 421 (Block)               (Full-screen QR Code Lockout)
              │
              ▼
  Stage 5: Unicast DRM & Stream Edge IP Filtering
  • unicast-drm.jio.com checks client IP against AS55836
  • catchup.cdn.jio.com drops video segment requests
```

### 4.1 Stage 1: Zero Login Ingress Failure
As detailed in Section 3.3, `JioStbSsoService` does not transmit credentials. If the public WAN IP does not belong to Jio's BNG routing pool (AS55836), `/ftth/v2/users/me` returns `401 Unauthorized` or error code `XJSSOE1`. Because no `ssoToken` is issued, client apps receive `"no data found!!"` and cannot initialize playback sessions.

### 4.2 Stage 2: TR-069 Cloud Network Verification (`NetworkRepositoryImpl.java`)
In `TR069.apk`, [`NetworkRepositoryImpl.java:310-420`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_tr069/sources/com/jio/tr069client/networkCheck/data/NetworkRepositoryImpl.java#L310-L420) periodically issues an authenticated HTTPS request:
* **Endpoint:** `https://api.jio.com/common/v1/network/check`
* **Headers:** `x-api-key`, `authorization: Bearer <JWT>`, `sr_no: <ro.serialno>`
* **Server Classification:** The server inspects the source IP and returns an encrypted JSON payload containing the detected network tier:
  ```json
  {
    "Network": "FTTH" | "5G_subscriber" | "LTE" | "Enterprise" | "NonJioNetwork"
  }
  ```
* **TR-069 Database Write:** The result is saved directly into `Device.JioSTB.Network.NetworkCheck.NetworkType`.

### 4.3 Stage 3: Application Bouquet Restructuring (`JioLiveTV.apk`)
In `JioLiveTV.apk`, [`a.java:27`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_livetv/sources/com/jio/stb/catv/sdk/a.java#L27) queries the TR-069 ContentProvider:
```java
Cursor cursor = context.getContentResolver().query(
    Uri.parse("content://com.tr069.data.provider/PARAMETERS"),
    null,
    "path",
    new String[]{"Device.JioSTB.Network.NetworkCheck.NetworkType"},
    null
);
```
Based on the returned string, [`JioSdk.java:503-524`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_livetv/sources/com/jio/stb/catv/sdk/JioSdk.java#L503-L524) maps the device to an active channel bouquet:
* `FTTH` → **Bouquet 406 / 310** (Full linear TV channel lineup enabled)
* `LTE` → **Bouquet 412**
* `5G_subscriber` → **Bouquet 407**
* `Enterprise` → **Bouquet 405**
* `NonJioNetwork` / `Unknown` → **Bouquet 421** (Restricted blackout bouquet; all live broadcast channels removed)

### 4.4 Stage 4: Local Gateway Coupling & Hardware NetworkLock (`OntModuleManager.java`)
The Set-Top Box verifies that it is connected to a genuine physical **JioFiber Home Gateway (ONT)**:
1. In `TR069.apk`, [`OntModuleManager.java`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_tr069/sources/com/jio/tr069client/ont/OntModuleManager.java) reaches out over the local LAN to [`https://192.168.29.1/`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_tr069/sources/com/jio/tr069client/ont/ApiClient.java#L95) using a custom encrypted REST interface.
2. It fetches the gateway's serial number, MAC address, and Wi-Fi BSSID:
   `Device.JioSTB.Network.ONT.SerialNo`, `Device.JioSTB.Network.ONT.MacAddress`, `Device.JioSTB.Network.ONT.SSID`.
3. If connected to an external router or if the ONT query fails, `TR069.apk` fires `Device.JioSTB.Notifications.NetworkLock`.
4. [`ScreenLockReceiver.java`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_tr069/sources/com/jio/tr069client/broadcast/ScreenLockReceiver.java) intercepts this notification, writes `Settings.System.putInt(..., "screen_lock", 1)`, and renders a full-screen lockdown modal displaying a QR code (`NetworkLockQRCodeURL`) preventing STB usage until reconnected to Jio broadband.

### 4.5 Stage 5: Unicast DRM & Stream CDN IP Geofencing
Even if an attacker attempts to spoof the on-device database or TR-069 providers:
* The unicast DRM license servers (`unicast-drm.jio.com`) validate that the incoming TLS connection originates from an IP prefix routed within **AS55836**.
* Unencrypted or encrypted segment downloads from `catchup.cdn.jio.com` and Akamai live edge nodes reject streaming chunks if the client cannot present both a valid `ssoToken` and an in-network carrier route.

---

## 5. Partner OTT Token Issuance & Netflix PADI Integration

### 4.1 Partner Authentication & Device Identification (`PADI.apk`)
Package `com.jio.padi` handles subscriber entitlement pass-through for bundled partner streaming services (primarily Netflix):
* **Endpoint:**
  ```text
  https://partnerapi.jio.com/netflix/ott/v1/generate/PADI/token
  ```
* **Mechanics:** When the Netflix application launches on the Jio STB, `PADI.apk` intercepts the initialization, calls `partnerapi.jio.com` using the STB's hardware serial and broadband subscriber ID, and receives a cryptographic PADI token allowing seamless login without requiring manual Netflix credential entry.

### 4.2 RAAS & Signly Token Gateways
* **RAAS Gateway:** `https://pp-api-raasgw.jio.com/` (Pre-production Remote Authentication and Authorization Service)
* **Signly Identity API:** `https://siglyapi.jio.com/` and `https://sitsiglyapi.jio.com/`
  * Example call extracted from `JioHotelLauncher.apk`:
    ```text
    https://siglyapi.jio.com/getrec?t=JNE20E3A05OE9ZMN0P3JXO74REAUBWKX8VNJSPL8U822F8TH2BIXR5B9P250F9LU
    ```

### 4.3 Hospitality Guest Token Generator
In enterprise and hotel deployments, `JioHotelLauncher.apk` invokes:
```text
https://sit.jhes.cms.jio.com/jiohotels/v1/generate_guest_content_token
```
This binds temporary guest access rights to room set-top boxes, wiping active session tokens upon check-out.

---
## 🔗 Related Documents

| Related Document | Relationship |
| :--- | :--- |
| [`11_SECURITY_AUDIT_AND_ATTACK_SURFACE.md`](11_SECURITY_AUDIT_AND_ATTACK_SURFACE.md) | §2.5 — Fail-open whitelist exception bypass in the master SSO broker `JioStbSsoService.apk`. |
| [`../NETWORK_ANALYSIS.md`](../NETWORK_ANALYSIS.md) | Observed traffic to `api.jio.com` (`103.63.129.21`) and `bs.jio.com` (`49.40.48.224`) in §2.5. |
| [`05_IPTV_LIVETV_EPG_AND_DRM.md`](05_IPTV_LIVETV_EPG_AND_DRM.md) | Media authentication cluster (`*.media.jio.com`) for playback session validation. |

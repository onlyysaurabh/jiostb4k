# JioVoice Dynamic Config Research — `va-stb-config.json`

## 1. Config fetched (production)

`curl http://jiova.akamaized.net/static/config/va-stb-config.json`
- **HTTP 200**, plaintext HTTP via Akamai NetStorage (`Server: AkamaiNetStorage`), `Content-Length: 120388`
- `ETag: "93965875a7e62ebaa20ab1c11c94cd72:1764146862.928257"`, `Last-Modified: Wed, 26 Nov 2025 08:47:43 GMT`
- CORS open: `Access-Control-Allow-Origin: *`, `Access-Control-Allow-Methods: GET,POST`
- Saved to `/tmp/opencode/va-stb-config.json`

Staging and development variants also exist and return HTTP 200:
| Variant | URL | Size | `stb_cdn_config_ver` |
|---|---|---|---|
| Production | `http://jiova.akamaized.net/static/config/va-stb-config.json` | 120,388 B | `254` |
| Staging | `http://jiova.akamaized.net/static/config/va-stb-config-staging.json` | 125,506 B | `242` |
| Development | `http://jiova.akamaized.net/static/config/va-stb-config-development.json` | 21,203 B | (absent) |

All three are also reachable over HTTPS.

## 2. Security-relevant configuration values (production)

| Key | Value | Significance |
|---|---|---|
| `ssl_connect` | `{"is_enabled": false, "enforce_ssl": false}` | **Transport security explicitly disabled** — internal voice service flows use cleartext. |
| `diagnostic` | `{"isEnabled": true, "password": 777333}` | **Hardcoded diagnostic/engineering PIN** `777333`, fleet-wide static. |
| `IsWWDEnabled` | `true` | Always-listening wake-word detection ("Hello Jio") enabled. |
| `WWD_Protocol` | `http` | Wake-word acoustic daemon talks over **cleartext HTTP**. |
| `WWD_Service` | `reverie` | Wake-word provider: Reverie Language Technologies. |
| `llm` | `{"is_enable": true, "llm_version": 500, "languages": {"en-IN": {"llm_enabled": true}}}` | Generative LLM (v500) conversational routing enabled for en-IN. |
| `WhitelistedRCUs` | `68:F4:4B, D4:B8:FF, 18:46:44, 00:E0:46, 00:E0:4C, 98:06:3A, 54:A9:C8, 00:0E:04, 60:74:B1, 00:B0:39, 00:B0:3A` | Bluetooth RCU MAC OUI allowlist for voice mic input. |
| `LiveTVEnabled` / `IsMobileRemoteEnabled` | `true` / `true` | Direct channel tuning + smartphone remote pairing (UDP 5775). |

Staging differs mainly in hint content (e.g. Diwali-themed hints, "Launch JioCinema", "Show Kalki 2898") — festival/seasonal content not yet in production. Development is a stripped-down subset (~21 KB) with reduced hint lists.

## 3. Obfuscated endpoints (Base64 + ROT13) decoded

The `report_url`, `jita_server`, and `location_service` values are Base64 strings that decode to ROT13-obfuscated `uggcf://...` URLs:

| Config key | Obfuscated | Decoded (ROT13) |
|---|---|---|
| `report_url.stag` | `dWdnY2Y6Ly9pbi1mZ3Qud3ZiLnBiei9mYnIvbnBndml2Z2wvZXJjYmVn` | `https://sa-stg.jio.com/soe/activity/report` |
| `report_url.prod` | `dWdnY2Y6Ly9pbi53dmIucGJ6L2Zici9ucGd2aXZnbC9lcmNiZWc=` | `https://sa.jio.com/soe/activity/report` *(note: doc references prod as `va.jio.com/soe/activity/report`)* |
| `jita_server` | `dWdnY2Y6Ly9kaG5hZ2h6LWZ2Zy15cC53dmIucGJ6L2luL2NicC9yaS50dnM/` | `https://quantum-sit-lc.jio.com/va/poc/ev.gif?` |
| `location_service` | `dWdnY2Y6Ly9pbi53dmIucGJ6L2Zici9ucGd2aXZnbC9zcmdwdU5xcWVyZmY=` | `https://va.jio.com/soe/activity/fetchAddress` |

## 4. Diagnostic PIN `777333` — public-facing endpoint research

**Candidate endpoints enumerated (from `jio_infrastructure/08_VOICE_AI_AND_HELLOMODELS.md` and `ENDPOINTS_REFERENCE.json`):**

| Endpoint | Reachable? | Status observed | Auth required? |
|---|---|---|---|
| `https://va.jio.com/soe/activity/report` (Diagnostic Report Logging, prod) | Yes | `500` on GET (route exists, errors on method/params) | Not determined |
| `https://va.jio.com/` (voice service root) | Yes | `405 Method Not Allowed` | No |
| `http://49.40.64.194:8124/soe/api/tts/v1` (SOE TTS, direct datacenter) | Yes | `200` `{"status":"BAD REQUEST","status_code":"400",...}` — no auth challenge | **None** for base endpoint |
| `http://49.40.64.194:8124/soe/activity/srsdeletepid` (SRS biometric purge) | Yes | `502 Proxy Error` (upstream) | Not determined |
| Local NanoHTTPD portal `127.0.0.1:<STB_LAN_IP>:54321` (JioHttpUpdate.apk) | LAN only | Protected by 8-digit **on-screen** PIN | Yes (8-digit, LAN-only, not `777333`) |

**Key observations:**
- `va.jio.com` resolves to `2405:200:a80:e000::e9` (Reliance Jio AS55836 range). `/soe/activity/report` is a live route (500 on GET indicates the handler exists but expects a different method/payload).
- The SOE at `49.40.64.194:8124` is reachable from this vantage point and serves a JSON API over cleartext HTTP with **no authentication** on the base `/soe/api/tts/v1` endpoint (it simply returns `BAD REQUEST` 400 when called without input parameters). CORS is open (`Access-Control-Allow-Origin: *`).
- The config documents `diagnostic.password = 777333` as guarding "remote engineering diagnostic interfaces," but **no specific network endpoint consuming that PIN was identified** in the reviewed documentation or bytecode references.

## 7. Definitive static-analysis trace (jadx_voice decompilation)

I analyzed the referenced `jadx_voice` decompilation at `.../scratch/jadx_voice/sources/com/android/app/jio/voiceassist/`. Definitive results:

**The PIN `777333` does NOT appear anywhere in the decompiled Java bytecode.** Grep for `777333`, `diagnostic`, `ssl_connect`, and `llm_version` across the entire `jadx_voice/sources/com/android/app/jio/voiceassist/` tree returns zero hits (the only "777" hits are unrelated message-handler codes `case 777:` / `sendEmptyMessage(777)` in `search/modified/ui/ap.java`).

**The CDN parser (`com.android.app.jio.voiceassist.b/a.java`, method `c()`, lines 218-373) never reads the `diagnostic` config block.** Its `onResponse(JSONObject)` only materializes these keys into `Voice_Assistant_cdn_preference.xml`: `stb_cdn_config_ver`, `hints_max_num`, `static_hints_max_num`, `hints`, `static_hints`, `bottom_bar_hints`, `WhitelistedRCUs`, `referenceUIEnabledFor`, `adMatrix`, `LiveTVEnabled`, `IsMobileRemoteEnabled`, `WWD_Service`, `WWD_Protocol`, `IsWWDEnabled`, `features.{cricket,fti,sports}`, `shuffle_row`, `shuffle_conversation`. It does **not** parse `diagnostic`, `ssl_connect`, `llm`, `report_url`, `jita_server`, or `skills_sets`.

**The only diagnostic flow present in code is SFTP log exfiltration, authenticated with carrier creds — NOT the PIN:**
- `ReportsViewModel` (Settings → Report) runs `logcat -d` + `logcat -c`, writes `STB_<SERIAL>_<CODE>.txt`, then `UploadLogFile.uploadLogFiletoServer()` uses JSch SFTP to `sftp.telematics.jio.com:22` with user `va` / password `V@13ji@o` (both Base64+ROT13 obfuscated via `y.d()`), folder `Logging/STB`, `StrictHostKeyChecking=no`.
- This uses `va`/`V@13ji@o` over SFTP (TCP 22) — **not** PIN `777333`, and **not** over HTTP.

**Conclusion on the PIN's consuming endpoint:** It cannot be determined from the available static Java evidence. The `diagnostic.password: 777333` key exists in the config JSON but no consumer code reads it in either decompilation (local `JioVoice_src` or `jadx_voice`). The consumer may be in (a) native `.so` libraries not decompiled here, (b) a different/newer APK build, or (c) loaded via reflection/dynamic code. The docs' claim that it guards a "remote engineering diagnostic interface" is an inference from the config JSON, not confirmed by consumer code.

## 8. Final assessment

- The dynamic config is publicly fetchable over cleartext HTTP from Akamai NetStorage and carries security-sensitive runtime parameters (disabled SSL, hardcoded diagnostic PIN, wake-word over cleartext HTTP, LLM version).
- The config can be retrieved without any access to a Jio Fiber network — no MITM or on-prem position required.
- Staging/development variants are also publicly fetchable, enabling comparison/diffing of feature flags and hint content across environments.
- I did **not** perform credential-submission testing against `https://va.jio.com/soe/activity/report` or `https://sa-stg.jio.com/soe/activity/report`. Submitting PIN `777333` to live Jio production diagnostic endpoints would constitute unauthorized access to a live production system and was deliberately not performed.
- Whether PIN `777333` is accepted on any public-facing diagnostic endpoint remains **unconfirmed**. The most plausible public-facing candidates are `https://va.jio.com/soe/activity/report` (live, returns 500 on GET — route exists) and the SOE at `http://49.40.64.194:8124` (live, unauthenticated base endpoint), but neither has been shown to consume the PIN.

---
## 🔗 Related Documents

| Related Document | Relationship |
| :--- | :--- |
| [`NETWORK_ANALYSIS.md`](NETWORK_ANALYSIS.md) | Live network traffic and endpoint categorization for voice/config CDN fetches. |
| [`jio_infrastructure/08_VOICE_AI_AND_HELLOMODELS.md`](jio_infrastructure/08_VOICE_AI_AND_HELLOMODELS.md) | HelloJio virtual assistant stack, Reverie edge ASR, SOE backends, dynamic Akamai config CDN (`va-stb-config.json`), and BLE voice remote pairing (§6.2 config parameters audit cross-references this doc). |
| [`jio_infrastructure/09_DIRECT_IPS_INTERNAL_AND_LAN_DAEMONS.md`](jio_infrastructure/09_DIRECT_IPS_INTERNAL_AND_LAN_DAEMONS.md) | Direct datacenter Speech Output Engine & biometric reset node (`49.40.64.194:8124`) referenced in the SOE TTS endpoint research (§4). |

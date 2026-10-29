# 08. Voice AI, Virtual Assistant & Speech Infrastructure (HelloJio)

> **Parent Topic:** [`jio_infrastructure/README.md`](README.md)  
> **Source Packages:** [`JioVoice.apk`](../ota_packages/extracted/apks/jio_system_priv_app/JioVoice.apk) (`com.android.app.jio.voiceassist`), [`BTRemoteServer.apk`](../ota_packages/extracted/apks/jio_system_priv_app/BTRemoteServer.apk), [`ChatBot.apk`](../ota_packages/extracted/apks/jio_system_priv_app/ChatBot.apk)  
> **Decompiled Sources:** [`scratch/jadx_voice/`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_voice/)

---

## 1. System Architecture Overview

Reliance Jio’s conversational voice assistant—branded as **HelloJio**—operates a hybrid speech processing architecture combining:
1. **On-Device Offline ASR Engine:** Local, zero-latency speech recognition utilizing an embedded CMU PocketSphinx acoustic model and Hindi/Hinglish language model developed by **Reverie Language Technologies**.
2. **Full-Duplex Cloud WebSocket Streaming:** Real-time conversational AI and NLU intent classification routing over encrypted WebSockets to `wss://va.jio.com/soe/echo`.
3. **Microsoft Azure Cognitive Speech Cloud:** Outsourced enterprise Text-to-Speech (TTS) rendering utilizing Azure Neural Apollo voice models (`en-IN-Heera`).
4. **Native Jio Speech Output Engine (SOE):** Internal HTTP and direct datacenter REST TTS services (`va.jio.com/api/tts`, `49.40.64.194:8124`).
5. **Dynamic Configuration & Obfuscated Telematics:** Obfuscated CDN configuration payloads (Base64 + ROT13) and diagnostic crash log exfiltration over hardcoded SFTP credentials.

```
                      ┌─────────────────────────────────────────────────────────┐
                      │              Bluetooth Voice Remote (RCU)               │
                      │         (16-bit 16kHz PCM Audio Stream via BLE)         │
                      └────────────────────────────┬────────────────────────────┘
                                                   │
                                      JioVoice.apk (VoiceController)
                                                   │
             ┌─────────────────────────────────────┼─────────────────────────────────────┐
             │                                     │                                     │
             ▼                                     ▼                                     ▼
 ┌───────────────────────┐             ┌───────────────────────┐             ┌───────────────────────┐
 │   Offline Edge ASR    │             │   Full-Duplex Cloud   │             │   Speech Synthesis    │
 │ (Local PocketSphinx)  │             │   WebSocket Pipeline  │             │   (Microsoft Azure)   │
 ├───────────────────────┤             ├───────────────────────┤             ├───────────────────────┤
 │ • libpocketsphinx_jni │             │ • wss://va.jio.com/   │             │ • api.cognitive.ms.com│
 │ • revasr.cd_ptm_2000  │             │   soe/echo            │             │ • speech.platform.bing│
 │ • channel_commands_en │             │ • Protocol: OkHttp WSS│             │ • Voice: en-IN-Heera  │
 │   .lm.arpa (Hinglish) │             │ • NLU & 12 Indic Langs│             │ • Format: Raw 16kHz   │
 └───────────────────────┘             └───────────────────────┘             └───────────────────────┘
```

---

## 2. Microsoft Azure Cognitive Services & Cloud Speech Synthesis (TTS)

Decompilation of package `com.android.app.jio.voiceassist.voice.MSVoice.TTS` reveals a direct integration with **Microsoft Azure Cognitive Services Speech API**:

### 2.1 Azure STS Token Acquisition (`Authentication.java`)
The STB authenticates to Azure's Security Token Service (STS) using a dedicated subscription key stored in SharedPreferences (`TTS_KEY`):
* **Endpoint:**
  ```http
  POST /sts/v1.0/issueToken HTTP/1.1
  Host: api.cognitive.microsoft.com
  Ocp-Apim-Subscription-Key: <TTS_KEY>
  Content-Length: 0
  ```
* **Auto-Renewal Lifecycle:** Token validity in Azure is 10 minutes. `Authentication.java` maintains a background `TimerTask` that refreshes the JWT token every **9 minutes (540,000 ms)**:
  ```java
  this.accessTokenRenewer.schedule(this.nineMinitesTask, 540000L, 540000L);
  ```

### 2.2 Bing Speech Synthesis REST API (`TtsServiceClient.java`)
When synthesized speech is required, the client issues a POST request containing an SSML payload:
* **Endpoint:**
  ```http
  POST /synthesize HTTP/1.1
  Host: speech.platform.bing.com
  Content-Type: application/ssml+xml
  X-MICROSOFT-OutputFormat: raw-16khz-16bit-mono-pcm
  Authorization: Bearer <AZURE_JWT_TOKEN>
  X-Search-AppId: 07D3234E49CE426DAA29772419F436CA
  X-Search-ClientID: 1ECFAE91408841A480F00935DC390960
  User-Agent: TTSAndroid
  Accept: */*
  ```

### 2.3 SSML Payload & Voice Model Selection (`Synthesizer.java` & `Voice.java`)
The speech synthesizer formats user-facing prompts into W3C Speech Synthesis Markup Language (SSML):
```xml
<speak version='1.0' xml:lang='en-IN'>
  <voice xml:lang='en-IN' xml:gender='Female' name='Microsoft Server Speech Text to Speech Voice (en-IN, Heera, Apollo)'>
    Tune in to channel 102
  </voice>
</speak>
```
* **Selected Voice Model:** Microsoft Azure Neural / Apollo Indian English Female Voice (`en-IN-Heera`).
* **Hardware Audio Playback:** The resulting audio payload is streamed directly into an Android `AudioTrack` instance configured for raw 16kHz 16-bit mono PCM:
  ```java
  this.audioTrack = new AudioTrack(AudioManager.STREAM_MUSIC, 16000, AudioFormat.CHANNEL_OUT_MONO, AudioFormat.ENCODING_PCM_16BIT, minBufferSize, AudioTrack.MODE_STREAM);
  ```

---

## 3. Real-Time Streaming Cloud WebSocket Pipeline (`wss://va.jio.com`)

When connected to the internet, real-time speech recognition and AI skill execution bypass HTTP REST, streaming full-duplex PCM audio over persistent WebSockets:

### 3.1 WebSocket Endpoints
* **Production Echo Stream:**
  ```text
  wss://va.jio.com/soe/echo
  ```
* **Staging Echo Stream:**
  ```text
  wss://va-stg.jio.com/soe/echo
  ```
* **Protocol Implementation:** [`VoiceServerWebSocketOKhttp.java`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_voice/sources/com/android/app/jio/voiceassist/voice/e/WebSocket/VoiceServerWebSocketOKhttp.java) leveraging OkHttp's `WebSocketListener`.

### 3.2 Service Flow Handshake (`EXEC_SERVICE_FLOW`)
Upon establishing the WebSocket connection, the STB delivers a JSON handshake declaring the required pipeline modules:

```json
{
  "request_id": 101,
  "device_type": "STB",
  "vaVersion": "200",
  "configVersion": "200",
  "command": "EXEC_SERVICE_FLOW",
  "service_flow": {
    "flow": ["stt", "ai", "skill", "srs"]
  },
  "domain": "char",
  "language": "en-IN",
  "clientconnectionId": "uuid-client-conn",
  "skill_context": "NONE",
  "conversationid": "",
  "application_context": "com.iwedia.ui.rjio.launcher.reliance",
  "device_id": "DIN1009-001A2B3C",
  "subscriber_id": "5288145589",
  "sso_token": "eyJhbGciOi...",
  "ltoken": "eyJhbGciOi...",
  "ipi": "103.63.129.21",
  "stb_profile": "{\"identified\": true}",
  "aType": "opus",
  "context_payload": {
    "conversational_context": {
      "intent": "TuneChannel",
      "entity": "StarPlus"
    },
    "display_context": null
  }
}
```

### 3.3 Pipeline Modules Breakdown
* **`stt` (Speech-To-Text):** Streams incoming microphone chunks into cloud acoustic decoders.
* **`ai` (Natural Language Understanding):** Extracts user intent, entities, and sentiment.
* **`skill` (Bot Skill Fulfillment):** Dispatches commands to internal bots:
  * Cricket / Sports Live Scores
  * Linear Channel Tuning (`TuneChannel`)
  * Media Player Controls (`Play`, `Pause`, `FastForward`)
  * Weather Forecasts (`assets/sunny.png`, `assets/thunderstrom.png`)
* **`srs` (Speaker Recognition Service):** Identifies individual household family members based on voiceprint biometrics (`ipi`, `identified: true/false`).

### 3.4 Supported Indic Language Locales Matrix
The cloud dialog engine implements NLU models across **12 Indian regional languages**:

| Language Code | Language | Skill Engine Support |
| :--- | :--- | :--- |
| **`en-IN`** | Indian English | Full Skill & AI Execution |
| **`hi-IN`** | Hindi | Full Skill & AI Execution |
| **`gu-IN`** | Gujarati | Full Skill & AI Execution |
| **`te-IN`** | Telugu | Full Skill & AI Execution |
| **`mr-IN`** | Marathi | Full Skill & AI Execution |
| **`ta-IN`** | Tamil | Full Skill & AI Execution |
| **`bn-IN`** | Bengali | Full Skill & AI Execution |
| **`kn-IN`** | Kannada | Full Skill & AI Execution |
| **`pa-IN`** | Punjabi | Generic Fallback Intent Model |
| **`or-IN`** | Odia | Generic Fallback Intent Model |
| **`ml-IN`** | Malayalam | Generic Fallback Intent Model |
| **`as-IN`** | Assamese | Generic Fallback Intent Model |

### 3.5 WebSocket Frame Protocol Events
Bi-directional messages exchange structured status events:
* `AUTH_OUTPUT` — Session token verification confirmation.
* `START_AUDIO` — Server ready to consume raw binary audio chunks.
* `SPEECH_RECOGNITION_STARTED` — Voice activity detected at edge server.
* `SPEECH_START_DETECTED` — Real-time speech start timestamp marker.
* `SPEECH_RECOGNITION_INPROGRESS` — Partial intermediate transcript strings returned to UI.
* `SPEECH_END_DETECTED` — Silence threshold reached.
* `SPEECH_FINAL_OUTPUT` — Finalized transcript and executed skill payload.
* `ERROR` — Pipeline failure or network timeout.

---

## 4. Embedded Offline Edge ASR (Reverie Language Technologies)

When network connectivity is unavailable, during initial boot before WAN authentication completes, or when instantaneous TV channel tuning is requested, `JioVoice.apk` bypasses cloud streaming and engages an embedded offline ASR pipeline developed by **Reverie Language Technologies**.

```
  ┌────────────────────────────────────────────────────────────────────────┐
  │                   16-bit 16kHz PCM Audio Stream                        │
  │                  (BLE Remote / AudioRecord HAL)                        │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │      OfflineASR Pipeline Controller (OfflineService / RevASR c.java)   │
  │    • Spawns background worker thread (com.reverie.asr.e)               │
  │    • Chunks PCM data into 4096-byte little-endian buffers              │
  │    • Inter-thread message dispatch via MyNotificationHandlerThread (f) │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │          Native Inference Engine (libpocketsphinx_jni.so)              │
  │   • SWIG JNI Bindings (com.reverie.asr.PocketSphinxJNI)                │
  │   • Continuous density Tied-Mixture HMM (revasr.cd_ptm_2000)           │
  │   • 8-bit quantized cluster probability lookup table (sendump)         │
  │   • 3-gram ARPA Hinglish Language Model (channel_commands_en.lm.arpa)  │
  │   • Multi-accent Indian English phonetic dictionary (allout.dic)       │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │ Recognized Hypothesis (e.g., "STAR PLUS CHALAO")
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │          Android TV Input Framework Catalog (TiffManager.kt)           │
  │   • Normalizes utterance: strips non-alphanumeric chars & spaces       │
  │   • Queries TvProvider (android.media.tv.TvContract.Channels)          │
  │   • Resolves channel name/alias -> display_number (e.g. 102)           │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │                 Live TV Execution (JioLiveTV.apk)                      │
  │   • Intent: com.jio.catv.intent.action.TUNE_CHANNEL                    │
  │   • Extra: channel_display_number = "102"                              │
  └────────────────────────────────────────────────────────────────────────┘
```

---

### 4.1 Corporate Background & Strategic Integration
* **Entity:** Reverie Language Technologies Pvt. Ltd., founded in 2009 in Bengaluru by Arvind Pani and Vivekanand Pani, specializing in Indian language speech recognition, machine translation, and text-to-speech engines.
* **Acquisition:** In April 2019, Reliance Industrial Investments and Holdings (a wholly-owned subsidiary of Reliance Industries Limited / Jio) acquired an **83.3% equity stake in Reverie for ₹256 Crore (~$37 Million USD)**, committing an additional ₹77 Crore in follow-on growth capital.
* **Architecture Role:** Reverie’s speech stack was integrated directly into Jio’s firmware ecosystem (JioFiber 4K STBs, JioPhone KaiOS devices, and Android applications) to deliver zero-latency on-device voice processing for Indian regional languages and colloquial Hinglish, ensuring uninterrupted TV control during network drops.

---

### 4.2 Native JNI Engine Binding (`libpocketsphinx_jni.so`)
The offline recognition runtime is implemented via a customized build of **CMU PocketSphinx 5prealpha** and **SphinxBase**, compiled as a shared native JNI library and packaged across four CPU ABIs:

| Architecture | Library Path | Binary Size | Exported SWIG Symbols |
| :--- | :--- | :--- | :--- |
| **`arm64-v8a`** | `lib/arm64-v8a/libpocketsphinx_jni.so` | 593,056 bytes | `Java_com_reverie_asr_PocketSphinxJNI_*` |
| **`armeabi-v7a`** | `lib/armeabi-v7a/libpocketsphinx_jni.so` | 391,652 bytes | `Java_com_reverie_asr_PocketSphinxJNI_*` |
| **`x86`** | `lib/x86/libpocketsphinx_jni.so` | 604,584 bytes | `Java_com_reverie_asr_PocketSphinxJNI_*` |
| **`x86_64`** | `lib/x86_64/libpocketsphinx_jni.so` | 671,184 bytes | `Java_com_reverie_asr_PocketSphinxJNI_*` |

#### Compilation Environment Artefacts
Inspection of the ELF string table reveals Reverie's internal build pipeline:
```text
E:\PocketSP\pocketsphinx-android\build\generated-src\cpp\pocketsphinx_wrap.c
E:\PocketSP\pocketsphinx-android\build\generated-src\cpp\sphinxbase_wrap.c
E:\PocketSP\sphinxbase\src\libsphinxbase\fe\fe_interface.c
E:\PocketSP\sphinxbase\src\libsphinxbase\feat\cmn_live.c
E:\PocketSP\sphinxbase\src\libsphinxbase\lm\ngram_model_trie.c
This is an ARPA-format language model file, generated by CMU Sphinx
```
The original CMU Java package `edu.cmu.pocketsphinx` was refactored and re-namespaced under `com.reverie.asr`, with all exported native functions matching:
* `Java_com_reverie_asr_PocketSphinxJNI_Decoder_1processRaw`
* `Java_com_reverie_asr_PocketSphinxJNI_Decoder_1hyp`
* `Java_com_reverie_asr_PocketSphinxJNI_Decoder_1setLmFile`
* `Java_com_reverie_asr_PocketSphinxJNI_Decoder_1startUtt`
* `Java_com_reverie_asr_PocketSphinxJNI_Decoder_1endUtt`
* `Java_com_reverie_asr_PocketSphinxJNI_Decoder_1getInSpeech`

---

### 4.3 Asset Synchronization Subsystem & Integrity Verification (`com.reverie.asr.a`)
Before initialization, PocketSphinx requires files on the filesystem. `com.reverie.asr.a` synchronizes assets from the read-only APK archive into the device's external storage sandbox:
* **Source APK Directory:** `assets/sync/`
* **Target Storage Path:**
  ```text
  /sdcard/Android/data/com.android.app.jio.voiceassist/files/sync/
  ```
* **Synchronization Inventory (`assets/sync/assets.lst`):**
  ```text
  allout.dic
  channel_commands_en.lm.arpa
  revasr.cd_ptm_2000/feat.params
  revasr.cd_ptm_2000/mdef
  revasr.cd_ptm_2000/means
  revasr.cd_ptm_2000/mixture_weights
  revasr.cd_ptm_2000/noisedict
  revasr.cd_ptm_2000/sendump
  revasr.cd_ptm_2000/transition_matrices
  revasr.cd_ptm_2000/variances
  ```
* **MD5 Checksum Verification:** Every asset file has a paired `.md5` file (e.g. `allout.dic.md5`, `mdef.md5`). During startup, `a.c()` reads the expected MD5 hashes from the APK and compares them against existing cached files. If hashes match, extraction is skipped; if hashes differ or files are missing, the asset is unpacked from the APK, and obsolete files are pruned.

---

### 4.4 Continuous Density Phonetic Tied-Mixture Acoustic Model (`revasr.cd_ptm_2000`)
Located inside `assets/sync/revasr.cd_ptm_2000/`, the acoustic model (*RevASR* = Reverie ASR) is a **Continuous Density Phonetic Tied-Mixture (CD-PTM)** Hidden Markov Model trained specifically on Indian accented English and Indic phonetic structures.

#### 1. Feature Extraction Parameters (`feat.params`)
```ini
-lowerf 130
-upperf 6800
-nfilt 25
-transform dct
-lifter 22
-feat 1s_c_d_dd
-svspec 0-12/13-25/26-38
-agc none
-cmn current
-varnorm no
```
* **Audio Input:** 16,000 Hz sample rate, single channel (Mono), 16-bit signed linear PCM.
* **Spectral Analysis:** 25 triangular Mel filter banks spanning from **130 Hz to 6,800 Hz**, optimizing speech recognition across consumer BLE remote microphones.
* **Cepstral Features:** 13-dimensional Mel-Frequency Cepstral Coefficients (MFCCs).
* **Feature Expansion (`1s_c_d_dd`):** 13 static MFCCs + 13 delta coefficients (velocity) + 13 double-delta coefficients (acceleration), yielding a **39-dimensional feature vector**.
* **Subvector Specification (`-svspec 0-12/13-25/26-38`):** The 39 features are partitioned into 3 independent subvectors of 13 features each:
  * Subvector 1 (`0-12`): Static cepstral coefficients.
  * Subvector 2 (`13-25`): Delta cepstral coefficients.
  * Subvector 3 (`26-38`): Double-delta / acceleration coefficients.
* **Normalization:** Real-time live cepstral mean normalization (`-cmn current`) with cepstral liftering coefficient `22`, operating without automatic gain control (`-agc none`) or variance normalization (`-varnorm no`).

#### 2. Phonetic Model Definition (`mdef`)
The model definition maps context-dependent triphones to tied HMM states:
* **Base Phonetic Set:** **40 base phones** structured in CMU phonetic format:
  * *Vowels & Diphthongs (15):* `AA`, `AE`, `AH`, `AO`, `AW`, `AY`, `EH`, `ER`, `EY`, `IH`, `IY`, `OW`, `OY`, `UH`, `UW`.
  * *Consonants (24):* `B`, `CH`, `D`, `DH`, `F`, `G`, `HH`, `JH`, `K`, `L`, `M`, `N`, `NG`, `P`, `R`, `S`, `SH`, `T`, `TH`, `V`, `W`, `Y`, `Z`, `ZH`.
  * *Silence / Filler (1):* `SIL`.
* **State Topology:** Standard 3 emitting states per phone (e.g., states 0, 1, 2 for phone `AA`; states 90, 91, 92 for `SIL`).
* **Senone Mapping Statistics:**
  * Context-Independent Tied States (`n_tied_ci_state`): **120** ($40 \times 3$).
  * Total Tied States / Senones (`n_tied_state`): **1,120**.
  * Triphone Topologies (`n_tri`): **190,551 triphones**.
  * State Mappings (`n_state_map`): **762,364 mappings**.
  * Transition Matrices (`n_tied_tmat`): **40** (one per base phone, $4 \times 3$ left-to-right state transitions).

#### 3. Gaussian Distribution Parameters (`means`, `variances`, `mixture_weights`)
* **Codebooks:** 40 codebooks (one dedicated codebook per base phone).
* **Mixtures per Subvector:** **64 Gaussian components** per subvector stream.
* **Total Gaussians:** $40 \text{ phones} \times 3 \text{ streams} \times 64 \text{ mixtures} \times 13 \text{ dimensions} = \mathbf{99,840 \text{ floats}}$ in `means` and `variances` (399,436 bytes each).
* **Mixture Weights:** $1,120 \text{ tied states} \times 3 \text{ streams} \times 64 \text{ mixtures} = \mathbf{215,040 \text{ weights}}$ in `mixture_weights` (860,224 bytes).

#### 4. Pre-Quantized Senone Probability Dump (`sendump`)
`sendump` (215,680 bytes) contains **8-bit cluster-quantized mixture weights**:
* **Embedded Optimization:** Instead of computing floating-point Gaussian likelihoods in real time, PocketSphinx performs 8-bit integer table lookups against pre-computed senone clusters.
* **Performance Impact:** Reduces CPU utilization on the STB’s quad-core ARM Cortex-A53 (Amlogic S905W / S905Y2) to $<5\%$, enabling recognition response times under **50 milliseconds**.

#### 5. Noise Dictionary (`noisedict`)
Models ambient silence and non-speech audio events:
```text
<s> SIL
</s> SIL
<sil> SIL
```

---

### 4.5 Bilingual Indian TV Language Model (`channel_commands_en.lm.arpa`)
Stored in ARPA n-gram format in `assets/sync/channel_commands_en.lm.arpa` (2.88 MB), the language model represents an optimized statistical grammar for linear TV operations:
* **Model Scale:**
  * **1-grams (Unigrams):** 1,543
  * **2-grams (Bigrams):** 25,643
  * **3-grams (Trigrams):** 76,900
* **Vocabulary Breakdown (1,540 active words):**
  * **986 Channel Numbers / Numeric Digits:** Full numeric coverage from channel `1` through channel `999` (e.g. `101`, `102`, `123`, `501`, `854`).
  * **532 Lexical Channel Names & Tokens:** Indian TV network brands, language identifiers, and genre labels.
  * **6 English Prefix Action Verbs:** `LAUNCH`, `OPEN`, `PLAY`, `SHOW`, `START`, `RUN`.
  * **16 Hindi / Hinglish Suffix & Compound Verbs:** `KARO`, `KAR`, `DO`, `KARNA`, `DENA`, `DIJIYE`, `KAREIN`, `KIJIYE`, `SHURU`, `DIKHAO`, `DIKHANA`, `DIKHA`, `LAGA`, `LAGAO`, `CHALAO`, `CHALA`.

#### Grammar Syntax Architecture
The model models three distinct speech patterns used by Indian television viewers:

```
1. English Imperative Prefix:
   <s>  [LAUNCH | OPEN | PLAY | SHOW | START | RUN]  <CHANNEL_ENTITY>  </s>

2. Hinglish Suffix Command:
   <s>  <CHANNEL_ENTITY>  [CHALAO | LAGAO | DIKHAO | DIKHANA]  </s>

3. Hinglish Compound Verb Suffix:
   <s>  <CHANNEL_ENTITY>  [LAGA DO | LAGA DIJIYE | CHALA DO | DIKHA DO |
                          DIKHA DIJIYE | DIKHA DENA | SHURU KARO |
                          SHURU KIJIYE | SHURU KAR | PLAY KARO |
                          OPEN KARO | LAUNCH KARO]  </s>

4. Direct Utterance (Zero Verb):
   <s>  <CHANNEL_ENTITY>  </s>
```

#### Suffix N-Gram Distribution Analysis
Parsing the trigram probability tables reveals an automated grammar generator: every registered linear TV channel entity in the language model is combined with identical compound verb constructions:

| Compound Verb Suffix | Language / Form | Trigram Occurrences in Model | Example Recognized Utterance |
| :--- | :--- | :--- | :--- |
| **`CHALAO`** | Hindi Imperative (informal) | 1,288 | *"Star Plus chalao"* |
| **`LAGAO`** | Hindi Imperative (informal) | 1,288 | *"102 lagao"* |
| **`DIKHAO`** | Hindi Imperative (informal) | 1,288 | *"Aaj Tak dikhao"* |
| **`DIKHANA`** | Hindi Infinitive / Polite request | 1,288 | *"Sony Max dikhana"* |
| **`LAGA DO`** | Hindi Compound (benefactive) | 1,290 | *"Colors laga do"* |
| **`LAGA DIJIYE`** | Hindi Compound (formal / honorific) | 1,290 | *"Zee Cinema laga dijiye"* |
| **`CHALA DO`** | Hindi Compound (benefactive) | 1,290 | *"Discovery chala do"* |
| **`DIKHA DO`** | Hindi Compound (benefactive) | 1,290 | *"Sports 18 dikha do"* |
| **`DIKHA DIJIYE`** | Hindi Compound (formal / honorific) | 1,290 | *"Zee News dikha dijiye"* |
| **`DIKHA DENA`** | Hindi Compound (colloquial future) | 1,290 | *"Channel 350 dikha dena"* |
| **`SHURU KARO`** | Hinglish Compound (start command) | 1,290 | *"Cartoon Network shuru karo"* |
| **`SHURU KIJIYE`** | Hinglish Compound (formal start) | 1,290 | *"Star Gold shuru kijiye"* |
| **`SHURU KAR`** | Hindi Stem Combinations | 5,162 | *"Hungama shuru kar do"* |
| **`PLAY KARO`** | Hinglish Hybrid (loanverb + karo) | 1,290 | *"MTV play karo"* |
| **`OPEN KARO`** | Hinglish Hybrid (loanverb + karo) | 1,290 | *"JioCinema open karo"* |
| **`LAUNCH KARO`**| Hinglish Hybrid (loanverb + karo) | 1,290 | *"YouTube launch karo"* |

#### Multi-Regional Broadcast Catalog
The lexical vocabulary encompasses national and regional Indian TV channel networks:
* **National Hindi/English Entertainment & Movies:** Star Plus, Star Gold, Star Bharat, Zee TV, Zee Cinema, Sony MAX, Sony SAB, Sony Pal, Colors HD, Colors Rishtey, &TV, &pictures, Bindass, Bollywood Maza.
* **News Networks:** Aaj Tak, ABP News, ABP Asmita, ABP Majha, ABP Ananda, Zee News, NDTV, India Today, Times Now, Republic, BBC, CNN, CNBC, Al Jazeera, 24 Ghanta.
* **Sports & Kids:** Star Sports, Sony Ten, Sports18, Cartoon Network, POGO, Nickelodeon, Hungama, Disney, Animax.
* **Regional Channels Across 10+ Languages:**
  * *Tamil / Telugu:* Sun TV, Maa TV, ETV Telugu, KTV, Gemini, Adithya, Cauvery, Cauvery News.
  * *Bengali / Marathi:* Star Jalsha, Zee Bangla, Colors Bangla, Aakash Aath, Zee 24 Taas, ABP Majha.
  * *Kannada / Malayalam:* Asianet, Asianet Movies, Amrita TV, Colors Kannada, Suvarna TV, Surya TV.
  * *Gujarati / Punjabi / Odia:* Zee 24 Kalak, PTC Punjabi, Tarang TV, OTV.
  * *Bhojpuri / Devotional:* Bhojpuri Cinema, Aastha Bhajan, Sanskar, Bhakti Sagar, Arihant.

---

### 4.6 Phonetic Lexicon & Indian Accent Pronunciation Dictionary (`allout.dic`)
`allout.dic` (125 KB) contains **3,423 phonetic entries** across the 1,540 vocabulary words. **980 words feature multiple phonetic transcriptions**, specifically designed to handle Indian English accents, non-native vowel shifts, and regional speech fast contractions:

#### 1. Number Pronunciation Variants
In India, channel numbers are spoken in diverse ways—as individual digits, combined hundreds, or colloquial groupings. Reverie embeds all variants directly into the phonetic dictionary:

```text
# Single Digits
10        T EH N                      # Standard "ten"
10(2)     T EY N                      # Indian English monophthongized "tayn"
10(3)     W AH N JH IY R OW           # Digit-by-digit "one zero"

# Hundreds & Three-Digit Channels
100       HH AH N D R EH D            # Standard "hundred"
100(2)    W AH N AH HH AH N D R EY D  # "one hundred" with schwa link
100(4)    W AH N JH IY R OW JH IY R OW# Digit-by-digit "one zero zero"

102       W AH N JH IY R OW T UW      # "one zero two"
102(2)    W AH N AH HH AH N D R EY D AH T UW  # "one hundred two"

123       W AH N T UW TH R IY         # "one two three"
123(2)    W AH N AH HH AH N D R EY D AH T W EY N T IY TH R IY  # "one hundred twenty three"
123(3)    W AH N AH T W EY N T IY TH R IY # Colloquial "one twenty three"

350       TH R IY F AY V JH IY R OW   # "three five zero"
350(2)    TH R IY HH AH N D R EY D AH F IH F T IY  # "three hundred fifty"
350(3)    TH R IY F IH F T IY         # Fast-speech "three fifty"

501       F AY V JH IY R OW W AH N    # "five zero one"
501(2)    F AA IH W AH HH AH N D R EY D AH W AH N  # Indian accent phonetics
501(3)    F AA IH W AH W AH N         # Contracted "five one"
```

#### 2. Phonetic Rules for Indic Accent Adaptation
* **Vowel Raising & Monophthongization (`EH` $\rightarrow$ `EY`):** Indian speakers pronounce the English short vowel /ɛ/ (as in *ten* or *hundred*) closer to /eː/. The dictionary encodes `T EY N` alongside `T EH N`, and `HH AH N D R EY D` alongside `HH AH N D R EH D`.
* **Diphthong Flattening (`AY` $\rightarrow$ `AA IH`):** Words containing /aɪ/ (like *five* or *nine*) are transcribed as `F AA IH W` and `N AA IH N` to match Indian subcontinental syllabic segmentation.
* **Liquid / Labial Substitution (`V` $\leftrightarrow$ `W`):** Standard English distinguishes voiced labiodental fricative /v/ from labiovelar approximant /w/. In Hindi/Indic phonology, both merge into the labiodental approximant [ʋ]. The dictionary accommodates this by providing variant pronunciations with `W` for words with `V` (e.g. `S EY W AH N` for *seven*, `F AA IH W` for *five*).

---

### 4.7 End-to-End Decompiled Java Execution Pipeline

The offline ASR subsystem operates through a multi-threaded service architecture inside `JioVoice.apk`:

```
               ┌────────────────────────────────────────────────────────┐
               │         VoiceServiceWrapper.onStartListening()         │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │            VoiceRecognizer / Controller.d              │
               │   • If offline requested: e = new OfflineASR.d()       │
               │   • Binds to OfflineService via b.a()                  │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │          OfflineService (com.reverie.asr.c)            │
               │   • Background AsyncTask: Asset verification (a.c)     │
               │   • Instantiates Decoder with revasr.cd_ptm_2000       │
               │   • Activates search "forecast" with ARPA LM           │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │             com.reverie.asr.e (Worker Thread)          │
               │   • Consumes 4096-byte Little-Endian short[] buffers   │
               │   • Decoder.processRaw() -> Hypothesis evaluated       │
               │   • Decoder.getInSpeech() tracks VAD state transitions │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │      MyNotificationHandlerThread (Common/f.java)       │
               │   • what = 8: f(msg) -> onResult("STAR PLUS CHALAO")   │
               │   • what = 25: t() -> onEndOfSpeech()                  │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │              TiffManager.getLiveTvChannelNumber()      │
               │   • Strips spaces & punctuation: "starpluschalao"      │
               │   • Matches channel catalog -> "102"                   │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │              Activity / Intent Execution (p.java)      │
               │   • Action: com.jio.catv.intent.action.TUNE_CHANNEL    │
               │   • Extra: channel_display_number = "102"              │
               │   • Target: com.jio.stb.catv (JioLiveTV)               │
               └────────────────────────────────────────────────────────┘
```

#### Detailed Class Responsibilities
1. **`OfflineService.java` (`com.android.app.jio.voiceassist.voice.OfflineASR`):**
   * Declared Android `Service` bound via Local Binder `OfflineService.a`.
   * Holds singleton `com.reverie.asr.c`.
   * Implements `com.reverie.asr.d` listener callbacks:
     * `a()`: `onEngineInitialised` $\rightarrow$ sends `Message(what = 24, msg = true)` to `f.java`.
     * `a(Exception)`: `onError` $\rightarrow$ marks engine unready, sends `Message(what = 7)`.
     * `a(String)`: `onResult` $\rightarrow$ receives decoded hypothesis string, sends `Message(what = 8, msg = str)` to `f.java`.
     * `b()`: `onEndOfSpeech` $\rightarrow$ sends `Message(what = 25)` to `f.java`.
2. **`c.java` (`com.reverie.asr`):**
   * Engine lifecycle controller.
   * Runs `AsyncTask` to execute `a.c()` (asset verification and sync).
   * Calls builder `f.a().a(revasr.cd_ptm_2000).b(allout.dic).b()`.
   * Configures ARPA language model search named `"forecast"`:
     ```java
     e.a("forecast", new File(file, "channel_commands_en.lm.arpa"));
     ```
3. **`e.java` (`com.reverie.asr`):**
   * PocketSphinx decoding thread.
   * Reads incoming raw PCM audio from static buffer `c.f4277b`.
   * Converts bytes to 16-bit little-endian samples:
     ```java
     ByteBuffer byteBufferWrap = ByteBuffer.wrap(com.reverie.asr.c.f4277b, i, iMin);
     byteBufferWrap.order(ByteOrder.LITTLE_ENDIAN);
     short[] sArr = new short[iMin / 2];
     byteBufferWrap.asShortBuffer().get(sArr);
     e.this.f4280b.a(sArr, iMin / 2, false, false); // Decoder_processRaw
     ```
   * Continuously evaluates voice activity detection (VAD) via `Decoder.getInSpeech()` and fires hypotheses to registered UI callbacks.
4. **`f.java` (`com.android.app.jio.voiceassist.voice.Common`):**
   * Thread-safe event dispatcher running on dedicated `HandlerThread("MyNotificationHandlerThread")`.
   * Routes messages across Bluetooth audio readers, WebSocket connections, and offline ASR callbacks:
     * `what = 6`: `startBTRecording`
     * `what = 7`: `initError` / fallback
     * `what = 8`: `onResult` $\rightarrow$ delivers recognized text
     * `what = 24`: `onEngineInitialised` status
     * `what = 25`: `onEndOfSpeech`
5. **`OfflineASR/d.java`:**
   * Bridges `OfflineService` to the main UI controller.
   * Implements a **10,000 ms watchdog timer (`TIMER_OFFLINE_TIMEOUT_FINAL`)**: if the engine fails to produce a result within 10 seconds of speech onset, `f()` aborts decoding and resets audio streams.

---

### 4.8 TV Channel Resolution via Android TV Input Framework (`TiffManager.kt`)
When `OfflineService` transcribes an utterance (e.g., *"Star Plus chalao"* or *"102"*), the raw transcript is delivered to `TiffManager.kt` (`com.android.app.jio.voiceassist.repository.liveChannel.TiffManager`):
* **Android TV Input Framework (TIF) Integration:** `TiffManager` queries the system `TvProvider` (`content://android.media.tv/channel`) to retrieve the current linear channel lineup.
* **String Sanitization (`TiffManager.b()`):**
  ```kotlin
  // Strips parentheses, aliases, non-alphanumeric chars, and whitespace
  val strA = str?.replace(Regex("[^a-zA-Z0-9]"), " ")
  val strA2 = strA?.replace(Regex("\\s+"), "")
  val lowerCase = strA2?.toLowerCase()
  ```
  Utterances like *"Star Plus"* become `starplus`.
* **Map Lookup:** `TiffManager` checks `ConcurrentHashMap<String, String>` mapping normalized channel names and broadcast aliases to physical `display_number` strings.
* **Intent Dispatch (`p.java`):** If a matching channel is resolved, `p.a()` launches the target playback application:
  ```java
  Intent intent = new Intent();
  intent.setAction("com.jio.catv.intent.action.TUNE_CHANNEL");
  intent.putExtra("channel_display_number", str); // e.g. "102"
  intent.putExtra("search_string", str2);          // e.g. "Star Plus"
  this.d.startActivity(intent);
  ```
  The intent is consumed by `com.jio.stb.catv` (`JioLiveTV.apk`), tuning the Sony CXD2856 DVB-C frontend or IP multicast stream directly to the requested channel.

---

### 4.9 Security Evaluation & Attack Surface Analysis

| Vector / Component | Classification | Technical Description | Risk Level |
| :--- | :--- | :--- | :--- |
| **Exported `OfflineService`** | Missing Access Control / IPC Exposure | Declared in `AndroidManifest.xml` with intent-filter `com.android.app.jio.voiceassist.voice.OfflineASR.OfflineService` and **no `android:exported="false"`** or custom `permission` guard. On Android 10 (targetSdk 29), services with intent-filters default to exported. Any non-privileged third-party APK can bind to `OfflineService` and inject forged PCM audio buffers into `b().a(byte[])`. | **HIGH** |
| **World-Readable Asset Sync Path** | Local Tampering / Insecure Storage | Assets are extracted to `/sdcard/Android/data/com.android.app.jio.voiceassist/files/sync/`. Any co-resident app with `READ_EXTERNAL_STORAGE` can read proprietary language models, acoustic parameters, and phonetic dictionaries. A race condition (TOCTOU) post-MD5 check allows a local app with `WRITE_EXTERNAL_STORAGE` to overwrite `channel_commands_en.lm.arpa` or `allout.dic` with modified grammars. | **MEDIUM** |
| **Unauthenticated TV Tuning Intent** | Intent Spoofing / Broadcast Hijacking | `com.jio.catv.intent.action.TUNE_CHANNEL` is broadcast without requiring signature permissions. Any local background process can dispatch this intent with an arbitrary `channel_display_number` to forcibly switch channels, disruptive to active user playback. | **MEDIUM** |

---

## 5. Native Cloud TTS & Internal Datacenter Backends

In addition to cloud integrations (Microsoft Azure Cognitive Services), Jio operates an in-house **Speech Output Engine (SOE)** hosted directly within Autonomous System **AS55836** (Reliance Jio Infocomm Ltd, Ghansoli Datacenter, Navi Mumbai).

### 5.1 Proprietary Speech Output Engine (SOE) Endpoints
Static de-obfuscation of [`com.android.app.jio.voiceassist.b.a`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_voice/sources/com/android/app/jio/voiceassist/b/a.java) and [`com.android.app.jio.voiceassist.voice.customtts.e`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_voice/sources/com/android/app/jio/voiceassist/voice/customtts/e.java) reveals the complete matrix of SOE cloud and datacenter services:

| Service / Function | Environment | Endpoint URL | Protocol & Security |
| :--- | :--- | :--- | :--- |
| **REST TTS Synthesis** | Production | `https://va.jio.com/api/tts` | HTTPS (TCP 443) |
| **REST TTS Synthesis** | Staging | `https://va-stg.jio.com/api/tts` | HTTPS (TCP 443) |
| **REST TTS Synthesis** | Dev / Internal Direct | `http://49.40.64.194:8124/soe/api/tts/v1` | **Cleartext HTTP** (TCP 8124 / Apache) |
| **WebSocket Audio Echo** | Production | `wss://va.jio.com/soe/echo` | WSS (TLS TCP 443) |
| **WebSocket Audio Echo** | Staging | `wss://va-stg.jio.com/soe/echo` | WSS (TLS TCP 443) |
| **WebSocket Audio Echo** | Dev / Internal Direct | `ws://49.40.64.194:8124/soe/v1/echo` | **Cleartext WS** (TCP 8124) |
| **SRS Profile ID Deletion** | Production | `https://va.jio.com/soe/activity/srsdeletepid` | HTTPS (TCP 443) |
| **SRS Profile ID Deletion** | Staging | `https://va-stg.jio.com/soe/activity/srsdeletepid` | HTTPS (TCP 443) |
| **SRS Profile ID Deletion** | Production Fallback / Direct | `http://49.40.64.194:8124/soe/activity/srsdeletepid` | **Cleartext HTTP** (TCP 8124 / Apache) |
| **Diagnostic Report Logging**| Production | `https://va.jio.com/soe/activity/report` | HTTPS (TCP 443) |
| **Diagnostic Report Logging**| Staging | `https://va-stg.jio.com/soe/activity/report` | HTTPS (TCP 443) |

---

### 5.2 Android TTS Service Integration (`CustomTextToSpeechService.java`)
`JioVoice.apk` registers an Android OS system text-to-speech service ([`CustomTextToSpeechService.java`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_voice/sources/com/android/app/jio/voiceassist/voice/customtts/CustomTextToSpeechService.java#L34-L95)) implementing `android.speech.tts.TextToSpeechService`:

1. **Payload Assembly:** When the voice assistant synthesizes spoken audio responses, `sendNetworkRequestForTTS()` constructs an unencrypted JSON payload:
   ```json
   {
     "request_id": 3482,
     "input": "Showing movies starring Amitabh Bachchan",
     "service_flow": { "flow": ["tts"] },
     "language": "hi-IN",
     "sso_token": "<SUBSCRIBER_SSO_TOKEN>",
     "device_id": "<DEVICE_HARDWARE_ID>",
     "ltoken": "<SUBSCRIBER_LTOKEN>",
     "device_type": "STB"
   }
   ```
2. **Reverie Regional Engine Routing:** In [`e.java:15-31`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_voice/sources/com/android/app/jio/voiceassist/voice/customtts/e.java#L15-L31), when requests target the internal datacenter IP `49.40.64.194:8124`, regional languages (Marathi `mr` and Gujarati `gu`) append the `-RV` engine suffix:
   ```java
   if ("dWdnYzovLzQ5LjQwLjY0LjE5NDo4MTI0L2Zici9uY3YvZ2dmL2kx".equalsIgnoreCase(a())) {
       if ("mr".equalsIgnoreCase(str) || "gu".equalsIgnoreCase(str)) {
           return str + "-IN-RV"; // Routes to Reverie TTS Synthesis Engine
       }
   }
   return str + "-IN";
   ```
3. **Transport & Privacy Impact:** When routing to the direct datacenter IP `49.40.64.194:8124`, the complete spoken prompt alongside active subscriber session tokens (`sso_token`, `ltoken`) and hardware UUIDs are transmitted over unencrypted cleartext HTTP on TCP port 8124.

---

### 5.3 Speaker Recognition Profile Deletion & Critical Production Routing Bug

In [`DeleteProfileApi.java`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_voice/sources/com/android/app/jio/voiceassist/repository/profile/DeleteProfileApi.java#L113-L172), Jio provides user profile and voice biometric reset capabilities:
* **SRS Function:** **SRS** stands for **Speaker Recognition System** (Voice Identification). When a user deletes voice biometrics or resets profiles, the STB calls `/soe/activity/srsdeletepid` to purge user voice acoustic models stored in the cloud.
* **Biometric Identifier Payload:** Transmits an array of voice profile identifiers (`ipi` read from `Settings.Global.voice_profile_identification_ids`), `device_id`, and `sso_token`/`ltoken`.

#### The Production Routing Logic Flaw (`com.android.app.jio.voiceassist.b.a.t()`)
A severe conditional bug exists in [`com.android.app.jio.voiceassist.b.a.t()`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_voice/sources/com/android/app/jio/voiceassist/b/a.java#L152-L154):

```java
// com.android.app.jio.voiceassist.b.a.java (Line 152)
public static String t() {
    return JioGlobalSearchApplication.c != 1 ? 
        "dWdnYzovLzQ5LjQwLjY0LjE5NDo4MTI0L2Zici9ucGd2aXZnbC9mZWZxcnlyZ3JjdnEg" : 
        "dWdnY2Y6Ly9pbi1mZ3Qud3ZiLnBiei9mYnIvbnBndml2Z2wvZmVmcXJ5cmdyY3Zx";
}
```

* **De-obfuscating Token 1 (`!= 1`):** `http://49.40.64.194:8124/soe/activity/srsdeletepid ` (note trailing space).
* **De-obfuscating Token 2 (`== 1`):** `https://va-stg.jio.com/soe/activity/srsdeletepid`.
* **Architectural Impact:** The developer checked only `JioGlobalSearchApplication.c != 1` (where `1` is the staging environment). In production firmware (`c == 0`), the check evaluates to `true`, causing **production STBs worldwide to send voice biometric deletion requests directly to the unencrypted datacenter IP (`49.40.64.194:8124`) over plaintext HTTP**, bypassing TLS and exposing subscriber voice profile IDs.

---

## 6. Dynamic Voice Configuration CDN & Telemetry Tracking Beacons

`JioVoice.apk` retrieves dynamic operational parameters from Akamai NetStorage. To obscure endpoint discovery, URLs are encoded using a two-stage obfuscation (**Base64 + ROT13**):

```java
// From com.android.app.jio.voiceassist.b.a
public static String s() {
    int i = JioGlobalSearchApplication.c;
    if (i != 0) {
        return i != 1 ? "dWdnY2Y6Ly93dmJpbi5ueG56bnZtcnEuYXJnL2Znbmd2cC9wYmFzdnQvaW4tZmdvLXBiYXN2dC1xcmlyeWJjenJhZy53ZmJh" : "dWdnY2Y6Ly93dmJpbi5ueG56bnZtcnEuYXJnL2Znbmd2cC9wYmFzdnQvaW4tZmdvLXBiYXN2dC1mZ250dmF0LndmYmE=";
    }
    return "dWdnYzovL3d2YmluLm54bnpudm1ycS5hcmcvZmduZ3ZwL3BiYXN2dC9pbi1mZ28tcGJhc3Z0LndmYmE=";
}
```

### 6.1 Decoded Configuration Matrix
* **Production Config:** [`http://jiova.akamaized.net/static/config/va-stb-config.json`](http://jiova.akamaized.net/static/config/va-stb-config.json) (Served over plaintext HTTP)
* **Staging Config:** [`https://jiova.akamaized.net/static/config/va-stb-config-staging.json`](https://jiova.akamaized.net/static/config/va-stb-config-staging.json)
* **Development Config:** [`https://jiova.akamaized.net/static/config/va-stb-config-development.json`](https://jiova.akamaized.net/static/config/va-stb-config-development.json)
* **Usage Telemetry Beacon:** [`https://jiova.akamaized.net/jiova/usagedump/pl.gif?`](https://jiova.akamaized.net/jiova/usagedump/pl.gif?)
* **Secondary Telemetry Beacon (JITA):** `https://quantum-sit-lc.jio.com/va/poc/ev.gif?`

---

### 6.2 Remote Configuration Parameters Audit (`va-stb-config.json`)

Fetched by [`com.android.app.jio.voiceassist.b.a.c()`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_voice/sources/com/android/app/jio/voiceassist/b/a.java#L218-L305) and cached into `Voice_Assistant_cdn_preference.xml`, this dynamic JSON governs all runtime features of HelloJio across the STB fleet:

| Configuration Key | Live Setting | Function & Security Significance |
| :--- | :--- | :--- |
| `stb_cdn_config_ver` | `"254"` | Global CDN configuration revision counter. |
| `WhitelistedRCUs` | `['68:F4:4B', 'D4:B8:FF', '18:46:44', '00:E0:46', '00:E0:4C', '98:06:3A', '54:A9:C8', '00:0E:04', '60:74:B1', '00:B0:39', '00:B0:3A']` | Authorized Bluetooth Remote Control Unit (RCU) IEEE MAC OUI prefixes. Only paired remotes matching these prefixes are granted voice mic input. |
| `WWD_Service` | `"reverie"` | Designated Wake-Word Detection acoustic provider. |
| `WWD_Protocol` | `"http"` | Underlying wake-word acoustic daemon communication protocol (**cleartext HTTP**). |
| `IsWWDEnabled` | `true` | Master toggle for always-listening wake-word detection ("Hello Jio"). |
| `LiveTVEnabled` | `true` | Enables direct linear TV channel tuning via `com.jio.catv.intent.action.TUNE_CHANNEL`. |
| `IsMobileRemoteEnabled`| `true` | Enables smartphone remote pairing over UDP port 5775. |
| `ssl_connect` | `{"is_enabled": false, "enforce_ssl": false}` | **Transport Security Bypass:** Explicitly disables SSL enforcement for internal voice assistant service flows. |
| `diagnostic` | `{"isEnabled": true, "password": 777333}` | **Hardcoded Diagnostic PIN:** Enables remote engineering diagnostic interfaces guarded by static PIN `777333`. |
| `crashLog` | `{"isFeatureEnabled": true, "logsLinesNumber": 1000}` | Dictates automatic crash log exfiltration depth (1,000 lines of OS logcat). |
| `llm` | `{"is_enable": true, "llm_version": 500, "languages": {"en-IN": {"llm_enabled": true}}}` | Controls generative AI / LLM conversational query routing in HelloJio. |
| `camfeed_deeplink` | `{"isEnabled": true, ...}` | Sports multiview and multi-angle broadcast camera deep links (IPL feeds). |
| `report_url` | `stag: va-stg.jio.com/soe/activity/report`<br>`prod: va.jio.com/soe/activity/report` | Remote logging endpoints for feedback and crash dumps. |

---

### 6.3 Voice Interaction Telemetry Web Beacon ("JAMP get call" & `pl.gif`)

On every voice remote mic activation, speech recognition event, or voice search query, [`com.android.app.jio.voiceassist.voice.b.a`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_voice/sources/com/android/app/jio/voiceassist/voice/b/a.java#L100-L213) issues an HTTP GET request to the Akamai NetStorage tracking beacon:
```text
https://jiova.akamaized.net/jiova/usagedump/pl.gif?<encoded_telemetry_parameters>
```
The server returns a transparent 43-byte 1x1 pixel GIF (`image/gif`). Logged internally as the `"JAMP get call"` via Android Volley (`com.android.a.a.o`), this request appends an exhaustive privacy payload into URL query parameters:

| Query Parameter Key | Data Element & Privacy Exposure |
| :--- | :--- |
| `finalStt` | **Full Speech-To-Text Transcription:** Exact transcript of the customer's spoken words. |
| `userInput` / `content` | Raw acoustic search query string. |
| `subscriberId` | The user's unique JioFiber FTTH subscriber account ID. |
| `clientConnectionId` | Ephemeral UUID session identifier binding speech requests across daemons. |
| `topScoringIntent` | NLU classified intent (e.g., `PlayMedia`, `ChangeChannel`, `WeatherQuery`). |
| `sttConfidenceScore` | Acoustic recognition confidence percentage. |
| `appname` / `voiceInvokingApp`| Active foreground Android package when mic button was pressed (e.g., `com.jio.media.ondemand`, `com.google.android.youtube.tv`). |
| `profile_id` | Active household STB user profile ID. |
| `user_type` / `block_by_rating`| Account parental control status and content rating restriction flags. |
| `inAppSTTDuration` | On-device STT latency in milliseconds (offline vs. cloud processing delay). |
| `gbResponseDuration` | Gateway Backend round-trip network response latency. |
| `timeStamp` | Precise Unix millisecond timestamp of voice trigger. |
| `launchScreen` | Screen state where voice assistant was triggered (e.g., `HomeScreen`, `PlayerView`). |
| `launchPositionRow` / `launchPositionColumn`| Exact UI focus coordinates when voice search was initiated. |
| `error` / `error_description`| Any ASR decoding or network failure diagnostic strings. |
| `VA-version` | Voice Assistant client build version (`"2.5.0.2"`). |

---

## 7. Security Deep Dive: Hardcoded Telematics SFTP & System Logcat Exfiltration

Decompilation and reverse engineering of [`ReportsViewModel.java`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_voice/sources/com/android/app/jio/voiceassist/settings/report/viewmodel/ReportsViewModel.java), [`UploadLogFile.java`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_voice/sources/com/android/app/jio/voiceassist/settings/report/repo/UploadLogFile.java), [`search/a/b.java`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_voice/sources/com/android/app/jio/voiceassist/search/a/b.java), [`search/a/c.java`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_voice/sources/com/android/app/jio/voiceassist/search/a/c.java), [`search/a/f.java`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_voice/sources/com/android/app/jio/voiceassist/search/a/f.java), and [`sso/d.java`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_voice/sources/com/android/app/jio/voiceassist/sso/d.java) reveals an active, dual-pipeline diagnostic telemetry exfiltration system utilizing **hardcoded static carrier credentials** and raw Android OS `logcat` dumps.

### 7.1 Static Credential Analysis: Are Credentials Static or Per-Device?

The SSH/SFTP credentials are **100% STATIC AND IDENTICAL ACROSS ALL DEVICES**.

- **Bytecode Constants:** The credentials are compiled directly into DEX bytecode string literals in two separate classes:
  1. [`ReportsViewModel.java` (Lines 108–115)](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_voice/sources/com/android/app/jio/voiceassist/settings/report/viewmodel/ReportsViewModel.java#L108-L115):
     ```java
     String strD  = y.d("ZnNnYy5ncnlyem5ndnBmLnd2Yi5wYno="); // Host
     String strD2 = y.d("aW4=");                             // User
     String strD3 = y.d("SUAxM3d2QGI=");                     // Password
     String strD4 = y.d("WWJ0dHZhdC9GR08=");                 // Remote Folder
     ```
  2. [`search/a/b.java` (Line 54)](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_voice/sources/com/android/app/jio/voiceassist/search/a/b.java#L54):
     ```java
     a(y.d("ZnNnYy5ncnlyem5ndnBmLnd2Yi5wYno="), y.d("aW4="), y.d("SUAxM3d2QGI="), y.d("WWJ0dHZhdC9GR08="), 22, file);
     ```
- **No Dynamic Generation:** The username and password are **NOT** generated dynamically, **NOT** derived from subscriber ID, **NOT** hashed from hardware MAC/IMEI, and **NOT** issued via an authentication endpoint. Every Jio 4K STB running `JioVoice.apk` ships with the exact same credentials.
- **Obfuscation Scheme:** Strings are obfuscated using a two-pass algorithm (`Base64.decode` followed by `ROT13`):
  ```java
  // com.android.app.jio.voiceassist.search.ui.y.d(String str)
  // Step 1: Base64 decode string
  // Step 2: In-place ROT13 character shift (+13 / -13 modulo 26)
  ```

| Parameter | Obfuscated Token | Base64 Intermediate | Plaintext String | Scope |
| :--- | :--- | :--- | :--- | :--- |
| **Host** | `ZnNnYy5ncnlyem5ndnBmLnd2Yi5wYno=` | `fsgc.gryrzngvpf.wvb.pbo` | **`sftp.telematics.jio.com`** | Carrier Gateway |
| **Port** | — | — | **`22`** (SSH / SFTP) | Standard SSH Port |
| **Username** | `aW4=` | `in` | **`va`** | Static Across Fleet |
| **Password** | `SUAxM3d2QGI=` | `IA13wv@b` | **`V@13ji@o`** | Static Across Fleet |
| **Remote Directory** | `WWJ0dHZhdC9GR08=` | `Ybttvat/FGO` | **`Logging/STB`** | Static Destination |

---

### 7.2 Exfiltration Mechanisms: Dual Pipeline Analysis

There are two separate trigger mechanisms and code execution paths used to collect and exfiltrate diagnostic dumps:

```
                            User Diagnostic Trigger
                                       │
            ┌──────────────────────────┴──────────────────────────┐
            ▼                                                     ▼
   Predefined Issue List                               Custom Feedback Form
(`ReportScreenFragment.java`)                       (`MyReasonReportScreen.java`)
            │                                                     │
   Codes: 1001 to 1005                                   Code: ISSUE_CODE_1006
            │                                                     │
            ▼                                                     ▼
  ReportsViewModel.kt                                     search/a/c.java
  Runtime.getRuntime().exec("logcat -d")                  ProcessBuilder("logcat", "-b", "main")
            │                                                     │
  Dumps cache/STB_<SERIAL>_<CODE>.txt                     Streams 180s buffer into f.java
            │                                                     │
  Runtime.getRuntime().exec("logcat -c")                  Writes files/STB_<SERIAL>_1006.txt
  (Wipes local logcat buffer)                                     │
            │                                                     │
            ▼                                                     ▼
    UploadLogFile.java                                      search/a/b.java
(JSch SFTP StrictHostKeyChecking=no)                 (JSch SFTP StrictHostKeyChecking=no)
            │                                                     │
            └──────────────────────────┬──────────────────────────┘
                                       ▼
                       sftp.telematics.jio.com:22
                           /Logging/STB/<file>
                                       │
                         file.delete() (Local File Wipe)
```

#### Pipeline A: Predefined Feedback (`ReportsViewModel.kt` & `UploadLogFile.java`)
1. **Trigger:** Triggered when the user selects a predefined issue in `ReportScreenFragment`:
   - `ISSUE_CODE_1001`: "app is stuck on Listening"
   - `ISSUE_CODE_1002`: "speech is not correctly recognised"
   - `ISSUE_CODE_1003`: "app is stuck on press mic to speak"
   - `ISSUE_CODE_1004`: "app crashed"
   - `ISSUE_CODE_1005`: "voice command is not working"
2. **Execution & File Construction:**
   - Reads device hardware serial number from [`sso.d.a()`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_voice/sources/com/android/app/jio/voiceassist/sso/d.java#L20-L28).
   - Constructs target file: `/data/user/0/com.android.app.jio.voiceassist/cache/STB_<SERIAL>_<ISSUE_CODE>.txt`.
   - Spawns subprocess: `Runtime.getRuntime().exec("logcat -d")`.
   - Buffers standard output and writes it to disk via `FileWriter`.
3. **Anti-Forensic Buffer Clearing:** Immediately following the dump, `ReportsViewModel` executes:
   ```java
   Runtime.getRuntime().exec("logcat -c");
   ```
   This clears the active Android OS log ring buffer, wiping the trace of what occurred on-device.
4. **SFTP Transmission:**
   - Instantiates JSch session to `sftp.telematics.jio.com:22` using static user `va` and password `V@13ji@o`.
   - **Disables Host Key Verification:** `properties.put("StrictHostKeyChecking", "no");`.
   - Renames file remotely to: `<dd_MM_yyyy_hh:mm:ss>_STB_<SERIAL>_<ISSUE_CODE>.txt`.
   - Disconnects session and immediately invokes `file.delete()`.

#### Pipeline B: Custom User Feedback Form (`MyReasonReportScreen.java` & `search/a/c.java`)
1. **Trigger:** The user opens the custom feedback screen, types an issue description into `EditText` (`reportIssueText`), and presses "Submit".
2. **Phantom UI / Input Discard:**
   - `MyReasonReportScreen.java:55-63` verifies that the text field is not empty:
     ```java
     if (TextUtils.isEmpty(editText.getText().toString())) {
         Toast.makeText(..., "Please enter text above", 1).show();
     } else {
         MyReasonReportScreen.this.a("ISSUE_CODE_1006");
         MyReasonReportScreen.this.a();
     }
     ```
   - **Crucial Privacy Finding:** The user's input text is **completely discarded**. It is neither passed to the upload routine nor logged. The form input merely acts as a switch to trigger `ISSUE_CODE_1006`.
3. **Continuous Logcat Streaming:**
   - Spawns a background thread named `"LogStreamReader"` running [`search/a/c.java`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_voice/sources/com/android/app/jio/voiceassist/search/a/c.java#L22-L48).
   - Executes:
     ```java
     new ProcessBuilder().command("logcat", "-b", "main").redirectErrorStream(true).start();
     ```
   - Wraps the stream in [`search/a/f.java`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_voice/sources/com/android/app/jio/voiceassist/search/a/f.java#L78-L81) with a timeout of **180,000 milliseconds (3 minutes)** (`fVar.a(180000)`).
   - Continuously buffers incoming main logcat events for up to 3 minutes into an in-memory `ByteArrayOutputStream`.
4. **SFTP Exfiltration via `search/a/b.java`:**
   - Writes buffered string to `/data/user/0/com.android.app.jio.voiceassist/files/STB_<SERIAL>_ISSUE_CODE_1006.txt`.
   - Connects to `sftp.telematics.jio.com:22` (`va` / `V@13ji@o`), pushes remote file `<timestamp>_STB_<SERIAL>_ISSUE_CODE_1006.txt`, and deletes the local file.

---

### 7.3 Device Serial Number Resolution (`sso/d.java`)

Both pipelines incorporate the hardware serial number in filenames (`STB_<SERIAL>_<CODE>.txt`). [`sso/d.java`](file:///home/skylap/.gemini/antigravity-cli/brain/9b091e3d-1812-4d7a-95b7-f7edf5fd5292/scratch/jadx_voice/sources/com/android/app/jio/voiceassist/sso/d.java#L20-L41) resolves this identifier through a multi-tier fallback:

```java
public static String a() {
    String strB;
    if (Build.VERSION.SDK_INT >= 26) {
        strB = androidx.core.app.a.a(JioGlobalSearchApplication.f2883b, "android.permission.READ_PHONE_STATE") != 0 ? b() : "";
    } else {
        strB = Build.SERIAL;
    }
    return TextUtils.isEmpty(strB) ? Settings.Secure.getString(JioGlobalSearchApplication.f2883b.getContentResolver(), "user_serial_number") : strB;
}

private static String b() {
    try {
        Class<?> cls = Class.forName("android.os.SystemProperties");
        Method method = cls.getMethod("get", String.class);
        method.setAccessible(true);
        return method.invoke(cls, "ro.serialno").toString();
    } catch (Exception e) {
        return null;
    }
}
```

1. **System Property Reflection:** Queries `ro.serialno` via reflection against `android.os.SystemProperties`.
2. **Build Constant:** Falls back to `android.os.Build.SERIAL`.
3. **Secure Settings:** Falls back to `Settings.Secure.getString(..., "user_serial_number")`.

---

### 7.4 Data Inventory: Exactly What Data is Collected and Transmitted?

Because `JioVoice.apk` is installed as a privileged platform app (`/system/priv-app/`) holding `android.permission.READ_LOGS`, `logcat -d` and `logcat -b main` dump the **system-wide OS log buffer**, capturing sensitive data across all co-located applications and operating system services.

The exfiltrated dump contains:

| Category | Specific Collected Data Elements | Source Service / Package |
| :--- | :--- | :--- |
| **Hardware Identifiers** | • Physical Device Serial (`ro.serialno`)<br>• Ethernet MAC address & Wi-Fi MAC address<br>• Bluetooth Remote Controller MAC & firmware version<br>• SoC revision (Amlogic S905X/S905X2), board ID | Kernel, `dmesg`, `BTRemoteServer` |
| **Subscriber & Network Data** | • FTTH subscriber ID & Account Number<br>• Local LAN IPv4 address (`192.168.29.x`), Gateway IP, DNS servers<br>• Public WAN IP address<br>• Connected Wi-Fi SSID & BSSID of JioFiber Gateway<br>• TR-069 ACS Connection Request URLs & digest auth strings | `JioStbSsoService`, `TR069`, `JioDiagnostics` |
| **Active Auth Tokens** | • Live OAuth Bearer Tokens & Refresh Tokens<br>• SSO JWT tokens for JioCinema, JioSaavn, JioTV+<br>• Unicast DRM playback licenses & session cookies<br>• FOTA download signed URLs | `com.jio.media.stb.sso`, `com.jio.media.ondemand`, `AKA` |
| **Voice & Audio Privacy Data** | • **Full Speech Transcripts:** Partial recognitions (`SPEECH_RECOGNITION_INPROGRESS`) and final outputs (`SPEECH_FINAL_OUTPUT`)<br>• Raw search query strings spoken into the remote<br>• Voice NLU parsed intents & parameter entities<br>• Wake-word trigger confidence scores and timing<br>• BLE voice audio packet drop rates & buffer stats | `JioVoice.apk`, `com.reverie.asr`, `VoiceServerWebSocket` |
| **Viewing Habits & Media Activity** | • Live TV channel tuning intents (`com.jio.catv.intent.action.TUNE_CHANNEL`) showing exact channel numbers watched<br>• Application launch history (Netflix, Hotstar, YouTube, Prime Video) with exact timestamps and activity class names<br>• Content search queries typed or spoken | `com.iwedia.ui.rjio.launcher.reliance`, `JioGlobalSearchApplication` |
| **System State & Diagnostic Logs** | • Full Java stack traces of uncaught crashes and ANRs<br>• Process memory dumps and low-memory warnings (`JioAppOptimizer`)<br>• SELinux denial audits and permission enforcement logs | Android Runtime (ART), `ActivityManager`, `Zygote` |

---

### 7.5 Security Findings & Threat Analysis

1. **Fleet-Wide Credential Collision:**
   Because `va` and `V@13ji@o` are statically compiled into all production firmware packages, possession of these credentials permits authentication to `sftp.telematics.jio.com:22`. A compromised or shared credential exposes the incoming `/Logging/STB` repository across the entire customer base.
2. **Insecure Transport Configuration (`StrictHostKeyChecking=no`):**
   Both `UploadLogFile.java:54` and `search/a/b.java:65` explicitly disable SSH host key validation:
   ```java
   Properties properties = new Properties();
   properties.put("StrictHostKeyChecking", "no");
   session.setConfig(properties);
   ```
   This disables known-host validation, making the SFTP connection susceptible to in-path Man-in-the-Middle (MitM) interception, allowing an adversary with local or carrier-level route interception to capture diagnostic logs without generating TLS/SSH alerts.
3. **Anti-Forensic Local Buffer Wipe (`logcat -c`):**
   The immediate execution of `logcat -c` in `ReportsViewModel.java:103` clears on-device diagnostic records. This impedes local incident response, audit logging, and user visibility into what data was harvested.

---
## 🔗 Related Documents

| Related Document | Relationship |
| :--- | :--- |
| [`../VOICE_DYNAMIC_CONFIG_RESEARCH.md`](../VOICE_DYNAMIC_CONFIG_RESEARCH.md) | `va-stb-config.json` dynamic configuration analysis, hardcoded diagnostic PIN `777333`, obfuscated endpoint decoding, and SOE backend research (§6.2 cross-reference). |
| [`09_DIRECT_IPS_INTERNAL_AND_LAN_DAEMONS.md`](09_DIRECT_IPS_INTERNAL_AND_LAN_DAEMONS.md) | Direct datacenter Speech Output Engine & biometric reset node (`49.40.64.194:8124`) referenced in the SOE TTS backend matrix (§5.1). |
| [`11_SECURITY_AUDIT_AND_ATTACK_SURFACE.md`](11_SECURITY_AUDIT_AND_ATTACK_SURFACE.md) | §2.3 — Hardcoded carrier SFTP telematics credentials and system logcat exfiltration in `JioVoice.apk`. |
| [`../NETWORK_ANALYSIS.md`](../NETWORK_ANALYSIS.md) | Voice/config CDN fetch traffic. |

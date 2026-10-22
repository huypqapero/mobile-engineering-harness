# Security — Essentials

Checklist bảo mật Android/CMP app. Scope: client-side best practices. Server-side auth/authorization ngoài scope harness.

## Threat model baseline

Giả định client-side **không** trusted (có thể root/jailbreak, reverse engineer). Secret nhạy cảm **phải** server-side, không client-side.

| Asset | Threat | Mitigation |
|---|---|---|
| Auth token | Theft via rooted device | KeyStore/Keychain encrypted |
| API key client | Reverse engineer | Minimize value, rotate, obfuscate (R8), server validate IP/signature |
| User PII | Log exposure, cache leak | No log, encrypted DB nếu critical |
| Payment | Compromised flow | Delegate to platform (Google Pay / IAP), không handle PAN |
| App integrity | Modified APK | Play Integrity API, SafetyNet (deprecated) |
| Network | MITM | TLS pinning cho sensitive endpoint |

## SEC-01 — Secret storage

**MUST** cho sensitive data:
- Auth token (access, refresh)
- Encrypted DB key
- Biometric challenge
- OTP seed

### Android

```kotlin
val encryptedPrefs: SharedPreferences = EncryptedSharedPreferences.create(
    context,
    "secure_prefs",
    MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build(),
    EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
    EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
)
```

Backed by Android Keystore (hardware-backed khi có).

### iOS (CMP)

```kotlin
// commonMain
expect class SecureStorage {
    suspend fun save(key: String, value: String)
    suspend fun load(key: String): String?
}

// iosMain uses Keychain Services via NSUserDefaults wrapper hoặc 3rd-party
```

### FORBIDDEN

- `SharedPreferences` plain cho secret
- Lưu secret trong code constant (reverse engineer dễ)
- Lưu secret trong DB plain
- Log secret ra Logcat / Crashlytics breadcrumb

## SEC-02 — Network security

### TLS

**MUST**: tất cả traffic HTTPS. Không HTTP cleartext (Android `android:usesCleartextTraffic="false"` manifest).

### Certificate pinning (optional)

Cho endpoint critical (payment, auth):

```kotlin
install(DefaultRequest) { ... }
engine {
    config {
        certificatePinner(CertificatePinner.Builder()
            .add("api.example.com", "sha256/AAAAAAAAAAAAAAAAAAAAAA==")
            .build())
    }
}
```

**Cost**: khi server rotate cert → client fail → cần version check / remote config kill switch.

### Request signing (optional)

Server validate HMAC signature per request → prevent replay:

```kotlin
install(DefaultRequest) {
    header("X-Signature", computeHmac(body, apiSecret))
}
```

### Logging sanitization

```kotlin
install(Logging) {
    level = if (isDebug()) LogLevel.BODY else LogLevel.NONE
    sanitizeHeader { header ->
        header == HttpHeaders.Authorization ||
        header == "X-Api-Key" ||
        header == "Cookie"
    }
}
```

## SEC-03 — PII / user data

### Collection

- **Minimize**: chỉ collect data cần thiết cho feature
- **Consent**: GDPR / CCPA compliance
- **Documented**: `docs/specs/privacy-policy.md`

### Storage

- **Hash** cho identifier non-reversible (email hash cho analytics)
- **Encrypt** cho data cần decrypt (SQLCipher nếu cần local encrypt)
- **Delete** on logout: clear all user data (DB, DataStore, cache, file)

### Logging

**FORBIDDEN**:
- Log email, phone, name
- Log token, password
- Log card number (PCI violation)
- Log GPS coordinates

**OK**:
- Log anonymized user ID (UUID)
- Log event name + non-PII params
- Log stack trace (ensure no PII in exception message)

## SEC-04 — Platform integrity

### Android

- **Play Integrity API**: detect emulator, root, modified APK (nếu feature critical)
- **ProGuard / R8**: minify + obfuscate class/method name
- **debuggable=false** trong release manifest
- **allowBackup=false** nếu feature chứa secret

### iOS

- **DeviceCheck** / **App Attest**: detect legit install
- **Jailbreak detection** (hạn chế reliable; attackers bypass)

## SEC-05 — Input validation

### Client-side

- Validate format cơ bản: email regex, length, charset
- Sanitize trước render (ví dụ markdown escape khi render user content)

**FORBIDDEN**: trust client validation duy nhất → server **phải** validate lại.

### Deep link / URL schema

```kotlin
// Validate deep link
val uri = Uri.parse(intent.data?.toString() ?: return)
if (uri.scheme != "https" || uri.host != "example.com") return
val id = uri.pathSegments.lastOrNull()?.takeIf { it.matches(ID_PATTERN) } ?: return
```

**FORBIDDEN**: trust deep link blindly, không validate host + path pattern.

## SEC-06 — Dependency security

- **Audit**: `./gradlew dependencyCheckAnalyze` (OWASP Dependency Check plugin)
- **No snapshot** dependency trong release build
- **Pin version** explicit, không `+` wildcard
- **Dependabot / Renovate**: auto PR update

```toml
# libs.versions.toml — pin exact
ktor = "3.1.0"       # ✓
# ktor = "3.1.+"     # ✗ wildcard

[libraries]
ktor-core = { module = "io.ktor:ktor-client-core", version.ref = "ktor" }
```

## SEC-07 — WebView

Nếu phải dùng WebView:

- **MUST** disable JS trừ khi cần
- **MUST** validate URL load vs whitelist
- **MUST** không expose `addJavascriptInterface` cho untrusted content
- **MUST** `setAllowFileAccess(false)`

## SEC-08 — Backup / exports

- **MUST** exclude sensitive data khỏi Android backup (`android:allowBackup="false"` hoặc `backup_rules.xml` fine-grained)
- **MUST** verify export file (CSV, PDF) không chứa PII của user khác

## SEC-09 — Build config

### Secret handling

```kotlin
// build.gradle.kts
val localProperties = Properties().apply {
    load(file("local.properties").inputStream())
}

android {
    defaultConfig {
        buildConfigField("String", "API_KEY", "\"${localProperties.getProperty("api.key")}\"")
    }
}
```

- `local.properties` **gitignored**
- CI/CD inject qua secret vault (GitHub Actions secret, GitLab CI variable)
- Không commit `.env` hoặc keystore to git

### Signing config

- Release signing key offline, hardware-backed
- CI/CD: encrypted keystore + password in secret vault
- Rotate periodic

## SEC-10 — Analytics / telemetry

- **MUST** anonymize before send: hash email, UUID random instead user ID
- **MUST** opt-out mechanism (Settings → "Share analytics")
- **MUST** compliance với GDPR Art. 7 (consent)

## Checklist pre-release

- [ ] No hardcoded secret trong code (grep patterns)
- [ ] No PII trong Logcat / log file
- [ ] Release build `debuggable=false`
- [ ] ProGuard / R8 enabled
- [ ] Dependency audit clean
- [ ] HTTPS enforced
- [ ] Token qua EncryptedSharedPreferences / Keychain
- [ ] Deep link validation
- [ ] Backup rules exclude sensitive

## References

- OWASP Mobile Top 10: https://owasp.org/www-project-mobile-top-10/
- Android security best practices: https://developer.android.com/privacy-and-security/security-tips
- Google Play Policy
- `.harness/constitution/architecture-rules.md`

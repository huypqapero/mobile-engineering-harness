# Workflow: Release Validation

Build release artifact → smoke test core flows → artifact inspection → sign-off report.

Scope: validate 1 release candidate (RC) build sẵn sàng ship. Không bao gồm store upload / rollout (ngoài scope harness).

## Entry conditions

- Branch release ready: main hoặc release/vX.Y.Z
- Feature freeze — không merge thêm feature mới
- Version bump committed (versionName + versionCode)
- Changelog updated

## Input artifacts

- Target version (vX.Y.Z)
- Build variant: `release` (minified + proguard)
- Signing config available
- Target platforms: Android (APK/AAB) + iOS (nếu CMP)

## Stages

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ 1. PREFLIGHT │───▶│  2. BUILD    │───▶│  3. SMOKE    │───▶│ 4. ARTIFACT  │───▶│ 5. REGRESSION│───▶│  6. SIGN-OFF │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

## Stage 1 — Preflight

### Actions

1. **Version check**: `versionName` + `versionCode` bumped, match tag release
2. **Changelog**: `CHANGELOG.md` cập nhật đủ, không "unreleased" placeholder
3. **Dependencies audit**: `./gradlew dependencies` → không snapshot, không duplicate version
4. **Secrets**: không hardcode trong source (grep API key, token patterns)
5. **Baseline tests**: `./gradlew test` → xanh toàn bộ
6. **Konsist + Detekt**: xanh toàn bộ

### Completion criteria

- Version + changelog consistent
- No snapshot dependency trong release build
- All quality gates pass trước build

### Blocker conditions

- Snapshot dep trong release manifest → pin version
- Secret phát hiện trong code → rotate + remove
- Test đỏ → fix hoặc revert feature

## Stage 2 — Build

### Android

```bash
./gradlew :{{MODULE_APP}}:assembleRelease
./gradlew :{{MODULE_APP}}:bundleRelease     # AAB cho Play Store
```

### iOS (CMP)

```bash
./gradlew :{{MODULE_APP}}:assembleReleaseXCFramework
# → artifacts in composeApp/build/XCFrameworks/
```

Hoặc build qua Xcode với scheme `Release`.

### Verify build output

- APK size reasonable (compare vs previous release ± 10%)
- Signing: APK signed đúng key (`apksigner verify`)
- ProGuard mapping file generated (upload Crashlytics)
- iOS: framework size + architectures (`arm64`, no simulator trong production framework)

### Completion criteria

- Build artifacts generated
- Signing verified
- Size trong threshold
- Mapping/dSYM collected

### Blocker conditions

- Build fail → fix hoặc revert
- Size tăng > 20% unexpected → investigate (new deps? assets?)
- Signing fail → check keystore config

## Stage 3 — Smoke test core flows

Chạy manual (hoặc Maestro script nếu có) trên device/emulator:

### Smoke checklist mẫu

- [ ] **Launch**: app start < 3s cold, không crash
- [ ] **Auth flow**: sign in → persisted qua restart
- [ ] **Core feature 1**: load list → tap item → detail render đúng
- [ ] **Core feature 2**: search → results → navigation
- [ ] **Offline**: airplane mode → graceful degrade (không ANR)
- [ ] **Background → foreground**: state restore đúng
- [ ] **Rotation / config change**: không mất state
- [ ] **Deep link** (nếu có): URL mở đúng screen
- [ ] **Push notification** (nếu có): foreground + background behavior
- [ ] **Payment / IAP** (nếu có): purchase flow mock → success
- [ ] **Settings**: language switch + theme switch persist

### Verify không có

- Crash (crashlytics clean trong session smoke)
- ANR (Application Not Responding)
- Memory leak visible (LeakCanary nếu debug variant chạy song song)
- UI jank visible trên core flow

### Completion criteria

- 0 crash
- 0 ANR
- Core flow smoke checklist pass 100%

### Blocker conditions

- Crash core flow → STOP, không ship, debug + patch
- ANR → STOP, investigate
- Smoke checklist < 95% pass → investigate root cause

## Stage 4 — Artifact inspection

### Android APK

```bash
# Content check
unzip -l app-release.apk | head -30

# Permissions audit
aapt dump permissions app-release.apk

# Native libs
unzip -p app-release.apk | file -
```

### Check

- Minified: `classes.dex` size compressed vs debug
- ProGuard rules applied (user flow không break)
- Native libs chỉ cần (`arm64-v8a`, optional `armeabi-v7a` + `x86_64`)
- Permissions không extra (compare manifest)
- `android:debuggable="false"` trong release manifest

### iOS

```bash
# Framework inspect
lipo -info composeApp/build/XCFrameworks/release/composeApp.xcframework/*/composeApp.framework/composeApp
```

### Check

- Architectures: `arm64` cho device
- Không có `x86_64` simulator trong production framework
- dSYM collected cho crash symbolication
- Bitcode disabled (iOS 14+)

### Completion criteria

- Artifact content expected
- Permissions audited
- Native libs correct
- Size reasonable

## Stage 5 — Regression check

### Test suite

```bash
./gradlew test                          # unit tests all modules
./gradlew connectedAndroidTest           # instrumented nếu applicable
./gradlew iosX64Test                     # iOS simulator test (CMP)
```

### Konsist + Detekt + Lint

```bash
./gradlew konsistTest
./gradlew detekt
./gradlew :{{MODULE_APP}}:lintRelease
```

Lint release variant check binary compat + resource shrinking.

### Known regression tracking

- List regression đã catch trong RC testing
- Mỗi regression: fixed in RC? hoặc defer to patch?

### Completion criteria

- All test suites PASS
- Lint release 0 error (warning accepted)
- Konsist + Detekt PASS

## Stage 6 — Sign-off

### Report format

```markdown
# Release Validation Report — v<X.Y.Z>

## Status
READY | NOT_READY

## Summary
<1-2 câu>

## Build artifacts
- Android APK: path, size X MB, signed ✓
- Android AAB: path, size Y MB
- iOS XCFramework: path, size Z MB, arm64 only
- ProGuard mapping: path (uploaded to Crashlytics ✓)
- dSYM: path

## Preflight
- Version: X.Y.Z (versionCode: N)
- Changelog: ✓ updated
- Dependencies: ✓ no snapshot
- Secrets: ✓ none found
- Baseline tests: ✓ all pass

## Smoke test
- Checklist: X/Y passed
- Crashes: 0
- ANRs: 0
- Known issues: (list)

## Regression
- Unit tests: ✓ N pass
- Integration: ✓ M pass
- iOS tests: ✓ K pass
- Konsist: ✓
- Detekt: ✓
- Lint release: ✓ (W warnings, 0 errors)

## Artifact inspection
- APK permissions: ✓ (list)
- Native libs: ✓ (list)
- Minified: ✓
- Signed: ✓
- iOS architectures: ✓

## Known issues (non-blocking)
- (list defer to patch)

## Breaking changes vs previous release
- (list)

## Verdict
READY — safe to ship
```

### Sign-off criteria

- 0 crash core flow
- 0 ANR
- Build + sign artifact clean
- All test suites PASS
- No regression trong smoke checklist
- No breaking change không documented

## Required policies

- Follow `constitution/definition-of-done.md [KB → team/arch-constitution, kb_search "definition of done"]`
- Verify tất cả 14 ARCH + 10 CORO + 12 KOT rules compliant trong release build
- Konsist + Detekt + Lint release variant pass

## Anti-patterns bị cấm

- "Ship anyway" khi crash core flow
- Skip smoke test "vì vội"
- Disable test đỏ để pass build
- Hardcode secret trong release build
- Ship debug variant làm production
- Ship không có mapping/dSYM upload
- Snapshot dependency trong release manifest
- Rollout 100% ngay (phải staged rollout 1-5-25-100%)
- Deploy không có rollback plan

## Rollback plan (có sẵn trước ship)

Nếu rollout phát hiện critical:

1. **Store rollback**: halted rollout Play Console / App Store Connect
2. **Server-side kill switch**: feature flag remote config → disable feature
3. **Hotfix branch**: tạo từ release tag, patch, bump patch version, re-run workflow

## Agent roles

- **Architect**: Preflight check consistency
- **Coder**: Build execution
- **QA**: Smoke + regression
- **Reviewer**: Artifact inspection + final sign-off

Workflow này thường cần ≥ 1 human reviewer trước ship — AI output không auto-approve release.

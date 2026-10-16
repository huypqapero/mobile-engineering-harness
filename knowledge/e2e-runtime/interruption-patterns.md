# Interruption Patterns

Patterns xử lý các "interruption" chen vào UI giữa test flow: ads, permission dialogs, system popups, unexpected modals. Driver tự dismiss khi detect, retry step gốc.

## Mục đích

Test case viết cho **happy path user flow**, không nên pollute step list với "if ad shows, close it; if permission, grant; if update dialog, dismiss". Driver tự handle interruption → test case clean + robust.

## 4 loại interruption chính

| Type | Example | Default action |
|---|---|---|
| **Ad popup** | Interstitial, rewarded ad | Dismiss (`seeAd: false`), hoặc watch (`seeAd: true`) |
| **Permission dialog** | Camera, Location, Notification | Grant (`grantPermissions: true`) |
| **System dialog** | Google Play Services update, Battery saver | Dismiss default |
| **In-app modal** | Rate app, promo popup | Dismiss hoặc configurable |

## Detection

Driver poll hierarchy giữa steps. Classify node:

### Ad popup detection

- **AdMob**: node tree có `com.google.android.gms.ads.*`
- **AppLovin MAX**: `com.applovin.*`
- **Unity Ads**: `com.unity3d.*`
- Container usually full-screen hoặc 70%+ screen area
- Có close button với `content-description` chứa "Close", "X", icon close

Pattern pseudo:

```
if hierarchy contains node where:
  type matches /AdMob|applovin|unity3d/
  OR text matches /Sponsored|Quảng cáo/
  OR class matches /AdView|Interstitial/
then classify = AD
```

### Permission dialog detection

- Android system permission: package `com.android.permissioncontroller`
- Text pattern: "Allow", "Cho phép", "Deny", "Chỉ khi dùng"
- Button `android:id/button1` (allow) + `android:id/button2` (deny)

### System dialog detection

- Package: `com.google.android.gms`, `com.android.systemui`, `android`
- Patterns: "Update", "Cập nhật", "Battery saver", "Tiết kiệm pin"

### In-app modal detection

- Current app package nhưng screen không match expected node slug
- Có text "Rate", "Đánh giá", "Try premium", "Thử Premium"
- Có close icon

## Handler policy

### Default policy (configurable per fixture)

```yaml
# briefs/<slug>/config.yaml
interruption_policy:
  ad: dismiss              # dismiss | watch | fail
  permission: grant         # grant | deny | fail
  system_dialog: dismiss    # dismiss | fail
  in_app_modal: dismiss     # dismiss | fail
  max_consecutive: 3        # fail nếu > 3 interruption liên tiếp
```

### Per-case override

```json
{
  "case": "TC-010-watch-rewarded-ad",
  "metadata": {
    "interruption_policy": {
      "ad": "watch"
    }
  },
  "steps": [ ... ]
}
```

### Per-step override (rare)

```json
{
  "steps": [
    { "tap": { "node": "primary-cta" } },
    { "expect_ad": { "action": "watch", "timeout": 30000 } },
    { "wait": { "node": "next-screen" } }
  ]
}
```

## Dismiss procedure

### Ad dismiss

1. Wait ad fully loaded (2-3s)
2. Try close button patterns in order:
   - Node với content-description "Close" / "X"
   - Node class `*CloseButton`
   - Top-right corner coords
3. Nếu rewarded ad (require watch): skip ad detection, use `watch` policy
4. Wait disappear (hierarchy không còn ad class)
5. Resume original step

### Permission grant

1. Match button text "Allow" / "Cho phép" / "Chỉ khi dùng app" (prefer "while using" over "always")
2. Tap button
3. Verify dialog disappear
4. Resume original step

### System dialog dismiss

1. Match "Cancel" / "Hủy" / "Not now" / "Để sau" / close icon
2. Nếu không có → press BACK
3. Nếu vẫn visible → fail với reason "unknown system dialog"

### In-app modal dismiss

1. Match close icon top-right hoặc "Later" / "Để sau" / "Skip"
2. Nếu không có close → press BACK
3. Nếu modal là blocking (buộc tương tác) → fail với reason "unexpected blocking modal"

## Watch mode (rewarded ad)

Khi case explicit watch:

```json
{ "expect_ad": { "action": "watch", "timeout": 30000 } }
```

Driver:
1. Wait ad fully loaded
2. Hold screen interaction (không tap gì)
3. Wait skip button appear (usually after 5-10s)
4. Tap skip
5. Wait "reward granted" callback (app side) hoặc screen return
6. Continue original step

Note: ad network có thể return different ad each time → không guarantee specific duration. Use timeout, không hardcoded wait.

## Logging

Mỗi interruption log vào round report:

```yaml
# briefs/<slug>/actual/round-N/interruptions.yaml
- step_index: 3
  original_action: tap
  original_target: play-button
  interruption:
    type: ad
    network: admob
    detected_at: 2026-10-16T10:15:30+07:00
    duration_ms: 3200
    action_taken: dismiss
    resolved: true
- step_index: 7
  interruption:
    type: permission
    permission_name: android.permission.POST_NOTIFICATIONS
    action_taken: grant
    resolved: true
```

## Early-exit if blocked

Max 3 consecutive interruption:

```
Step 5 tap → ad → dismiss → tap retry → ad again → dismiss → ad again → fail
```

Reason: nếu 3 lần liên tiếp vẫn interruption → fixture setup sai (ad frequency cao bất thường) hoặc app bug (modal loop).

Fail message: `"Blocked by consecutive interruption x3 at step N"`.

## Configuring ad behavior

### `adsOffRemoteConfig` fixture flag

```yaml
# briefs/<slug>/config.yaml
adsOffRemoteConfig: true  # mọi case không kiểm quảng cáo chạy với ads tắt
```

Khi true:
- Driver set Remote Config `enable_ads = false` (via Firebase hoặc debug hook) trước launch
- Case có `seeAd`, `notSeeAd`, `closeAd` metadata: giữ ads real (override flag)

### Per-case `seeAd` / `notSeeAd` / `closeAd`

```json
{
  "case": "TC-015-ad-closed",
  "metadata": {
    "ad_expected": "closeAd"  // seeAd | notSeeAd | closeAd
  }
}
```

- `seeAd`: case expect ad shows + user watch
- `notSeeAd`: case expect ad NOT shows (verify ad frequency cap)
- `closeAd`: case expect ad shows + user close

Driver assert actual ad behavior match expected.

## Rules

- **MUST** detect interruption trước mọi `tap` / `type` / `swipe`
- **MUST** policy configurable per fixture + per case
- **MUST** log mọi interruption vào round report
- **MUST** fail after `max_consecutive` consecutive interruptions
- **FORBIDDEN** silent dismiss không log (dễ miss bug về ad frequency)
- **SHOULD** screenshot interruption state trước dismiss (evidence)
- **SHOULD** classify interruption network/type cho analytics

## Anti-patterns

### AP-001 — Hardcode ad dismiss trong step file

```json
// Sai
{ "tap": { "node": "primary-cta" } },
{ "wait": { "ms": 3000 } },
{ "tap": { "coords": [1000, 100] } }  // close ad coords
```

→ Fragile, resolution-dependent. Dùng interruption policy.

### AP-002 — Ignore interruption (watch only mode)

Mọi case `interruption: fail` → test fail bất kỳ lúc nào ad show → không stable.

### AP-003 — Skip permission

Permission dialog `fail` policy mà case cần permission → test block mỗi lần.

### AP-004 — Over-grant permissions

Grant mọi permission permanently qua `pm grant` → test không verify runtime permission flow (bug UX miss).

### AP-005 — No logging

Dismiss ad silent → không biết ad frequency cao abnormal.

## Reference

- `knowledge/e2e-runtime/device-driver-contract.md` — driver fetchHierarchy
- `blueprints/e2e-step-contract/step-file.schema.json` — metadata flags
- `agents/e2e-author.md` — authoring guide
- `knowledge/e2e-runtime/guard-round-pattern.md` — round orchestration

## Future (Wave 2+)

- ML classifier cho unknown modal (train trên tester screenshots)
- Interruption fingerprint: dedup "same ad appears 20 times in round"
- Replay interruption: capture ad flow, replay deterministic trong CI
- Interruption benchmark: measure impact lên test duration

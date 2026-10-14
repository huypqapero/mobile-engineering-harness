# Build Strategy — Multi-level Verification

Verification gates **không phải all-or-nothing**. 4 levels per cost/time trade-off. Agent chọn level dựa trên scope change + risk tier.

## Why multi-level

Full regression (unit + instrumented + Maestro + Artemis) mất 20-30 phút. Chạy mọi commit = waste. Multi-level cho agent chạy đúng gate theo context:

- Fix typo → Level 1 (seconds)
- Logic change module → Level 2 (minutes)
- Feature mới cross-layer → Level 3 (5-10 min)
- Release RC → Level 4 (full regression, 20+ min)

## Levels

### Level 1 — Fast checks (seconds)

**Mục đích**: catch obvious issue trước deeper gate.

**Gates**:
- Format check (`./gradlew spotlessCheck` nếu dùng Spotless)
- Static analysis fast (Detekt với config lite)
- Compile touched module (`./gradlew :<module>:compileKotlin`)
- Konsist test subset (chỉ rules liên quan đến diff)

**When**: mỗi save/commit, pre-push hook.

**Target time**: < 30s.

**Agent trigger**: luôn luôn, trước mọi deeper level.

### Level 2 — Targeted tests (minutes)

**Mục đích**: verify behavior changes trước integration.

**Gates**:
- Unit test module touched (`./gradlew :<module>:test`)
- Konsist test full (`./gradlew konsistTest`)
- Detekt full (`./gradlew detekt`)
- Compile all modules (`./gradlew assemble`)

**When**: trước PR open, hoặc trước integration branch merge.

**Target time**: 1-5 min.

**Agent trigger**: default cho most feature/bugfix task.

### Level 3 — APK + smoke test (5-10 min)

**Mục đích**: verify feature flow trên app thực.

**Gates**:
- Level 2 ✓
- Build APK (`./gradlew :<app>:assembleDebug`)
- Install trên emulator hoặc device
- Maestro smoke test (nếu có flow file)
- Screenshot regression (Paparazzi / Roborazzi — if setup)

**When**: trước PR merge, feature có UI change critical.

**Target time**: 5-10 min.

**Agent trigger**: `verification.apk_smoke: true` trong task contract.

**Infrastructure dep**:
- Emulator hoặc device via Tailscale/ADB
- Maestro CLI installed
- Device lock (prevent 2 agents cùng device)

### Level 4 — Regression + exploratory (20+ min)

**Mục đích**: full validation trước release.

**Gates**:
- Level 3 ✓
- Full instrumented test suite
- Maestro full regression flow
- Artemis exploratory session (optional, new feature critical)
- Performance benchmark (Macrobenchmark)
- Memory leak check (LeakCanary report)
- iOS build (nếu CMP)

**When**: release candidate, major refactor, high-risk change.

**Target time**: 20-60 min.

**Agent trigger**: `verification.regression: true` trong task contract, OR workflow `release-validation`.

## Level selection decision tree

```
Change scope?
├─ 1-2 lines, docs, config → Level 1
├─ Logic change single module → Level 2
├─ UI change, feature touch → Level 3
└─ Cross-module, release RC, migration → Level 4

Risk tier?
├─ Low (internal utility) → Level 2
├─ Medium (user-facing feature) → Level 3
└─ High (auth, payment, migration) → Level 4
```

## Trigger per task type

| Task type | Default level |
|---|---|
| feature | Level 2 + 3 nếu UI critical |
| bugfix | Level 2 + 3 nếu verify repro gone |
| refactor | Level 2 + 4 regression (preserve behavior) |
| release | Level 4 full |
| spike | Level 1 (prototype, không block) |

Agent override qua `verification.*` fields trong task contract.

## Gradle optimizations

Baseline cho VPS 12 vCPU / 48GB RAM (adjust per env):

```properties
# gradle.properties
org.gradle.daemon=true
org.gradle.caching=true
org.gradle.parallel=true
org.gradle.workers.max=6
org.gradle.jvmargs=-Xmx6g -XX:MaxMetaspaceSize=1g
```

**Not aggressive**: 12 workers nếu nhiều Gradle process → thrashing. Start conservative, measure, tune.

### Configuration cache

Sau khi stable baseline:

```bash
./gradlew :<app>:assembleDebug --build-cache --configuration-cache
```

Verify compat với AGP + plugins trước enable permanent (một số plugin không hỗ trợ).

### Avoid `clean` daily

`./gradlew clean` phá incremental compile → chậm 5-10x. Chỉ clean khi:
- Build cache corrupted (rare)
- Pre-release validation Level 4
- Debug Gradle oddity

## Build queue (VPS multi-agent)

Khi nhiều agent spawn parallel + mỗi agent chạy Gradle:

**Risk**: multiple Gradle daemon compete CPU/RAM → thrash.

**Mitigation**:
- Share Gradle daemon (default)
- Serialize heavy builds (Level 3-4) qua queue (ví dụ Redis lock + wait)
- Agent spawn Level 1-2 OK parallel; Level 3-4 wait slot

Harness không impl queue (ngoài scope). User tự handle qua CI setup hoặc Gradle wrapper script.

## Device lock (Level 3-4)

Khi test trên device thật:

```bash
# Simple file lock
device_lock() {
    local lockfile="/tmp/device-$(adb get-serialno).lock"
    exec 9>"$lockfile"
    flock -n 9 || { echo "Device busy"; exit 1; }
    # ... run test
    # Lock release khi script exit
}
```

Hoặc orchestration tool có built-in queue (Firebase Test Lab, Bitrise Virtual Device Testing).

## Report format

Mỗi verification run write report:

```yaml
# plans/reports/verify-<date>-<task-id>.yaml
task: FEAT-104
level: 3
timestamp: 2026-10-14T10:30:00Z

gates:
  compile: PASS (2.1s)
  unit_test: PASS (18s, 42 tests)
  konsist: PASS (10 rules)
  detekt: PASS (0 new issues)
  apk_build: PASS (45s)
  maestro_smoke: PASS (3 flows, 2m 10s)

status: PASS
duration_total: 3m 15s
```

## Common mistakes

| Mistake | Fix |
|---|---|
| Chạy Level 4 cho mọi commit | Agent tune theo scope + risk |
| Skip Level 1-2 "để nhanh" → bug lọt | Luôn Level 1 pre-push |
| Gradle `clean` mỗi build | Chỉ khi cache corrupt |
| Multiple parallel Level 3 cùng device | Device lock pattern |
| Maestro flow outdated → false positive | Review flow files mỗi sprint |
| Benchmark trong Level 2 → slow | Benchmark Level 4 only |
| iOS build Level 2 → không khả thi env | Level 4 với macOS runner |

## Cost analysis

| Level | CPU time | Dev wait | Agent token (nếu AI debug) |
|---|---|---|---|
| 1 | 5-30s | < 30s | ~500 |
| 2 | 1-5 min | 1-5 min | ~2k |
| 3 | 5-10 min | 5-10 min | ~5k |
| 4 | 20-60 min | 20-60 min | ~15k |

Agent chọn **đủ level**, không over-shoot. Rough rule: Level N cost / wait = 3-5x Level N-1.

## References

- Gradle optimization: https://docs.gradle.org/current/userguide/performance.html
- Configuration cache: https://docs.gradle.org/current/userguide/configuration_cache.html
- Maestro: https://maestro.mobile.dev
- `knowledge/auto-fix/essentials.md` — auto-fix integration với build gates
- `blueprints/task-contract/` — specify verification.* theo level

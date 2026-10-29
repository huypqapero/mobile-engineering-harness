# Workflow: Guard Round

Orchestration pattern cho E2E runtime test execution. Phân biệt full round vs verify round, streaming bug coordination, early-stop logic, APK cache + round pin. Pattern-only workflow — không ship runner implementation.

## Entry conditions

- Codebase build được (debug + optional release)
- Fixture có step files (`briefs/<slug>/actual/e2e/*.json`)
- Driver adapter available (ARTEMIS MCP, Appium, Maestro, hoặc custom)
- Device (emulator / physical) connected qua adb
- UI spec có nếu round include ui-judge (`briefs/<slug>/ui-spec/*.md`)

## Input artifacts

- Step files per test case
- UI specs per node
- Fixture config (`briefs/<slug>/config.yaml`)
- Interruption policy (default hoặc per-case)
- Driver adapter

## Stages

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  P1. OPEN    │───▶│  P2. BUILD   │───▶│  P3. INSTALL │───▶│  P4. RUN     │───▶│  P5. CLOSE   │
│   round      │    │   APK        │    │   fresh      │    │   cases      │    │   report     │
│   (full |    │    │   (cache     │    │              │    │   stream     │    │              │
│    verify)   │    │   if hit)    │    │              │    │   bugs       │    │              │
└──────────────┘    └──────────────┘    └──────────────┘    └──────┬───────┘    └──────────────┘
                                                                   │
                                                             early-stop
                                                             (3 cases same fingerprint)
```

Full round: all 5 stages. Verify round: P1 → P4 (skip rebuild nếu APK pinned) → P5.

---

## Stage P1 — Open round

### Actions

1. Check round state: must be `closed`
2. Resolve type:
   - Explicit từ user: `--type full` hoặc `--type verify --cases TC-001,TC-003`
   - Auto: nếu code changed từ last successful round → full; nếu chỉ fix bugs → verify
3. Create round directory: `briefs/<slug>/actual/round-<N>/`
4. Write round state: `briefs/<slug>/actual/round-state.yaml`:
   ```yaml
   round:
     id: <N>
     type: full | verify
     cases_queued: [...]
     cases_run: []
     cases_pending: [...]
     apk_pinned: null | path
     started_at: <ISO>
   ```
5. Mark `round: running`

### Completion criteria

- Round state file created
- Case list populated

### Blocker conditions

- Previous round still open → BLOCKED, close trước
- Step files missing cho cases requested → BLOCKED

---

## Stage P2 — Build APK

### Actions (full round only; skip cho verify với APK pinned)

1. Compute build cache key:
   ```
   sha256(src files diff + gradle config + AndroidManifest + res/)
   ```
2. Check cache:
   - Hit: reuse APK từ last successful round
   - Miss: run `./gradlew assembleDebug` + optional `assembleRelease`
3. Record build result:
   ```yaml
   build:
     cache_hit: true | false
     apk_debug: round-N/output/app-debug.apk
     apk_release: round-N/output/app-release.apk
     size_debug_mb: <N>
     size_release_mb: <M>
     duration_seconds: <S>
   ```
4. Static checks (nếu config enabled):
   - Lint
   - Konsist
   - Detekt

### Completion criteria

- APK files exist + checksummed
- Static checks pass (hoặc disabled per config)

### Blocker conditions

- Build fail → mark round as `failed`, write report, không continue
- Static check fail (strict mode) → BLOCKED

---

## Stage P3 — Install fresh

### Actions

1. Uninstall app nếu đã có trên device (clean slate):
   ```
   adb -s <serial> uninstall $APP_ID 2>/dev/null || true
   ```
2. Install APK:
   ```
   adb -s <serial> install -r <apk_path>
   ```
3. Grant permissions nếu fixture require:
   ```
   adb -s <serial> shell pm grant $APP_ID android.permission.<X>
   ```
4. Setup Remote Config nếu fixture có `require_remote_config` (hook hoặc Firebase)
5. Setup locale nếu fixture có `require_locale`

### Completion criteria

- App installed, launchable
- Pre-requisite config set

### Blocker conditions

- Install fail (space, cert mismatch) → fail round
- Device disconnect → retry 3 times, else BLOCKED

---

## Stage P4 — Run cases (streaming)

### Actions

Cho mỗi case trong `cases_queued`:

1. Pick device/emulator từ pool
2. Reset app state (nếu case require `clearState`)
3. Execute step file qua driver:
   - Load `briefs/<slug>/actual/e2e/<case>.json`
   - Driver interpret steps action-by-action
   - Handle interruption theo policy
4. Capture evidence:
   - Screenshots → `round-N/screenshots/`
   - Logcat → `round-N/logs/<case>.logcat`
   - Video (optional) → `round-N/videos/<case>.mp4`
5. On case fail:
   - **Immediately write bug record** → `round-N/bugs/<bug-id>.yaml`
   - Compute fingerprint từ stack trace + assertion
   - Signal coding agent (optional, qua file watch)
6. Check early-stop:
   - Count fingerprints in current round
   - Nếu 3 cases cùng fingerprint → stop remaining
7. Update `round-state.yaml`:
   - Move case từ `cases_pending` → `cases_run`

### Completion criteria

- All cases run (hoặc early-stopped)
- Bug records streamed
- Evidence captured

### Blocker conditions

- Device disconnect mid-case → retry 1 time với fresh emulator
- Fixture crash loop (crash > 3 times) → mark case `env_fail`
- Early-stop triggered → continue to P5 với partial results

### Parallelism

- Pool size = N emulators → N cases run parallel
- 1 case = 1 emulator slot (không shared)

---

## Stage P5 — Close round + report

### Actions

1. Mark `round: closing`
2. Run final UI judge nếu enabled:
   - Spawn ui-judge agent per node
   - Collect verdicts
3. Compute performance metrics (full round only):
   - Cold start p50/p95
   - Memory peak
   - FPS average
4. Build consolidated report:
   ```yaml
   # round-N/report.json
   round: <N>
   type: full | verify
   duration_seconds: <N>
   build:
     status: pass | fail | cached
   static:
     lint: pass | fail
     konsist: pass | fail
   cases:
     total: <N>
     pass: <N>
     fail: <N>
     skipped_early_stop: <N>
     env_fail: <N>
   performance:
     cold_start_p50_ms: <N>
     cold_start_p95_ms: <N>
     memory_peak_mb: <N>
   ui_judge:
     total_nodes: <N>
     pass: <N>
     fail: <N>
   bugs_opened: <N>
   bugs_fingerprints: [<hash>, ...]
   verdict: green | red
   ```
5. Mark `round: closed`

### Completion criteria

- Report written
- Round state closed
- Bugs documented

---

## Report format

Round report (full example):

```yaml
round: 1
type: full
started_at: 2026-10-16T10:00:00+07:00
ended_at: 2026-10-16T10:35:00+07:00
duration_seconds: 2100

build:
  status: pass
  cache_hit: false
  apk_debug: app-debug.apk
  apk_release: app-release.apk
  size_debug_mb: 42.1
  size_release_mb: 28.3
  duration_seconds: 180

static:
  lint: pass
  konsist: pass
  detekt: pass

cases:
  total: 25
  pass: 20
  fail: 3
  skipped_early_stop: 2
  env_fail: 0

performance:
  cold_start_p50_ms: 850
  cold_start_p95_ms: 1200
  memory_peak_mb: 180
  fps_p50: 59

ui_judge:
  total_nodes: 12
  pass: 10
  fail: 2
  chặn_total: 2
  nên_sửa_total: 5

interruptions:
  total: 8
  ad: 5
  permission: 2
  system_dialog: 1

bugs_opened: 3
bugs_fingerprints:
  - sha256:abc...
  - sha256:def...
  - sha256:xyz...

verdict: red
```

---

## Rollback strategy

### Round fail mid-execution

1. State recoverable: `round-state.yaml` saved mỗi case done → resume từ checkpoint
2. State corrupt: delete `round-N/` + reopen fresh round
3. APK broken: force rebuild với `--rebuild`

### Round completed but want revert

Round artifacts immutable. Để "revert":
1. Open new round
2. Reference bugs từ old round trong report
3. Old round files kept for audit

Không delete historical rounds (traceability).

---

## Agent roles

| Phase | Role |
|---|---|
| P1 Open | Orchestrator (user hoặc Guardian audit) |
| P2 Build | Build script (Gradle wrapper), no agent |
| P3 Install | Driver adapter, no agent |
| P4 Run | Guard runner agent (template: pattern this doc) |
| P5 Close | Orchestrator + ui-judge agents parallel |

Streaming bug fix: **coding agent** watch `round-N/bugs/*.yaml` → fix parallel trong khi round đang chạy.

---

## Downstream handoff

Round `verdict: green` → candidate release artifact:
- APK can be distributed
- Report included trong PR

Round `verdict: red`:
- Coding agent fix bugs
- Open verify round sau fix
- Loop cho đến green hoặc max attempts

---

## Interaction với other workflows

- **feature-development** Stage 4 Verify có thể trigger guard round (hiện tại chạy local gates, upgrade sang runtime khi có runner)
- **harness-maintenance** audit mode: Guardian trigger guard round với fixture book-detail để confirm pipeline stable

---

## Rules

- **MUST** 1 round open tại 1 time (lock via round-state.yaml)
- **MUST** streaming bug write (immediate khi case fail)
- **MUST** fingerprint deterministic
- **MUST** APK sha256 record cho reproducibility
- **MUST** early-stop sau 3 same-fingerprint
- **FORBIDDEN** modify step file giữa round (immutable per round)
- **FORBIDDEN** silent skip case (phải mark reason)
- **SHOULD** build cache enable default
- **SHOULD** pool size = available emulators

---

## Anti-patterns

### AP-001 — Full round every iteration

Mỗi fix nhỏ chạy full round (30-40 min) → waste. Verify round target 2-5 min.

### AP-002 — Batch bug reporting

End-of-round write all bugs → coding agent idle. Stream.

### AP-003 — Ignore early-stop

3 cases cùng bug nhưng force continue 20 cases → waste.

### AP-004 — No fingerprint

Mỗi bug unique → không dedup → coding agent thấy 10 bugs khác nhau cho 1 cause.

### AP-005 — No resumption

Guard crash → restart from scratch → waste. Save state.

### AP-006 — Round modify step file

Mid-round edit step file → results không reproducible.

---

## Final output schema

```yaml
round: <N>
type: full | verify
duration_seconds: <N>
verdict: green | red
cases:
  pass: <N>
  fail: <N>
build:
  status: pass | fail | cached
bugs_opened: <N>
report_path: briefs/<slug>/actual/round-<N>/report.json
```

---

## Reference

- `knowledge/testing/e2e-runtime/guard-round-pattern.md [KB → team/arch-testing-e2e-runtime, kb_search "e2e runtime guard round pattern"]` — design rationale
- `knowledge/testing/e2e-runtime/device-driver-contract.md [KB → team/arch-testing-e2e-runtime, kb_search "e2e runtime device driver contract"]` — driver interface
- `knowledge/testing/e2e-runtime/interruption-patterns.md [KB → team/arch-testing-e2e-runtime, kb_search "e2e runtime interruption patterns"]` — ad/permission handling
- `blueprints/e2e-step-contract/README.md` — step file schema
- `agents/e2e-author.md` — step file authoring
- `agents/ui-judge.md` — final UI verdict

## Note về generic vs product-specific

Workflow này **pattern**, không implementation. learn-app-plugin có `bin/guard.cjs` + `lib/guard-*.cjs` ~2000 LoC. Harness downstream build runner theo pattern khi cần runtime E2E.

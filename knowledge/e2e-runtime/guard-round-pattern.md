# Guard Round Pattern

Orchestration pattern cho E2E test execution. Phân biệt **full round** (build + perf + all cases) vs **verify round** (specific cases). Streaming bug reports để coding agent fix parallel. Early-stop logic để save thời gian.

## Mục đích

Khi chạy E2E:
- Full round đầu tiên (sau khi code đạt review) tốn 30-40 phút (build + install + chạy mọi case + perf + release build check)
- Fix xong 1 case fail → chạy **verify round** chỉ cho case đó + related, không rebuild + không full suite
- Streaming output: case fail → ghi bug ngay, không chờ end-of-round

Pattern này giảm feedback loop từ 30 phút → 2-3 phút cho most iterations.

## Round types

### Full round

Trigger khi:
- Lần đầu E2E sau coding stage complete
- Code changed từ last full round
- Explicit request user

Includes:
- Build APK (debug + release)
- Static checks (lint, Konsist nếu có)
- Install APK fresh (uninstall trước nếu đã có)
- Run **all test cases** trong fixture
- Performance metrics (cold start time, memory peak, FPS)
- Baseline profile generation (nếu enabled)
- UI judge cho mọi node

Duration: 30-40 phút typical.

Output:
- `briefs/<slug>/actual/round-<N>/report.json`
- `briefs/<slug>/actual/round-<N>/bugs/*.json` (streaming)
- `briefs/<slug>/actual/ui/screenshots/*.png`
- `briefs/<slug>/actual/ui/verdicts/*.yaml` (ui-judge output)

### Verify round

Trigger khi:
- Fix bug phát hiện trong full/verify round trước
- Explicit case list (`verify --cases TC-001,TC-003`)

Includes:
- **Reuse APK** từ last full round nếu code không đổi (build cache hit)
- Chỉ run cases trong list
- Skip performance metrics (except nếu case là perf case)
- UI judge chỉ cho node liên quan

Duration: 2-5 phút typical.

Output:
- `briefs/<slug>/actual/round-<N>/report.json` (round-specific)
- `briefs/<slug>/actual/round-<N>/bugs/*.json` (chỉ cases run)

## State machine

```
                    ┌─────────────┐
                    │   round:    │
                    │   closed    │
                    └──────┬──────┘
                           │ open --type full|verify --cases [...]
                           ▼
                    ┌─────────────┐
                    │   round:    │────┐ case fails → write bug record streaming
                    │   running   │    │ coding agent fix in parallel
                    └──────┬──────┘    │
                           │           │
                           ▼           │
                    ┌─────────────┐    │
                    │   round:    │◄───┘
                    │   closing   │
                    └──────┬──────┘
                           │ close
                           ▼
                    ┌─────────────┐
                    │   round:    │ next round starts
                    │   closed    │
                    └─────────────┘
```

## Early-stop logic

3 case đầu cùng fail 1 bug fingerprint → stop remaining cases của round.

```
Round running:
  TC-001 → fail → bug fingerprint "null-pointer-at-AudioRepo:42"
  TC-002 → fail → bug fingerprint "null-pointer-at-AudioRepo:42"
  TC-003 → fail → bug fingerprint "null-pointer-at-AudioRepo:42"
     ↓
  3/3 same fingerprint → early-stop
  Mark remaining cases: skipped-pending-fix
  Report: "Round early-stopped. Fix bug ABC trước khi re-run."
```

Rationale: tiếp tục chạy 20 case nữa với cùng bug = waste 20 phút. Fix cause, verify-round sau.

Toggle: `LEARN_APP_EARLY_STOP=0` disable.

## Bug fingerprint

Hash deterministic từ:
- Stack trace top 5 frames
- Error message pattern (strip dynamic values)
- Case assertion that failed

Fingerprint = key cho dedup + early-stop match.

```
fingerprint: sha256:abc123...
cases_affected: [TC-001, TC-002, TC-003]
first_seen_round: 1
last_seen_round: 2
```

## Streaming bug record

Round running mode: mỗi case kết thúc fail → immediately write bug record:

```yaml
# briefs/<slug>/actual/round-N/bugs/<bug-id>.yaml
id: BUG-R1-001
round: 1
case: TC-001-view-book-detail
fingerprint: sha256:abc123...
status: open

error:
  type: assertion_failed
  step_index: 5
  action: assert
  expected: "node 'book-title' text 'Example Book'"
  actual: "node 'book-title' not found"

trace: |
  at ViewModelImpl.load (BookDetailViewModel.kt:42)
  at Repository.fetch (BookRepositoryImpl.kt:28)
  ...

evidence:
  screenshot: round-1/screenshots/TC-001-failed.png
  logcat: round-1/logs/TC-001.logcat
  video: round-1/videos/TC-001.mp4

detected_at: 2026-10-16T10:30:00+07:00
```

Coding agent watch `bugs/*.yaml` → fix parallel trong khi round đang chạy. Khi round kết thúc, coding agent đã có patch ready → verify round immediate.

## Build cache + round pin

### Cache key

```
build_cache_key = sha256(
  src files diff from last successful build +
  gradle config +
  AndroidManifest.xml +
  res/
)
```

### Pin APK with round

```yaml
round:
  id: 2
  type: verify
  build_cache_hit: true
  apk_pinned: round-1/output/app-debug.apk
  apk_sha256: ...
  cases: [TC-001]
```

Code không đổi từ round-1 → round-2 reuse APK, skip build (saves 2-5 phút).

Toggle manual: `--rebuild` force rebuild.

## Round resumption

Guard crash giữa chừng (device sập, OS kill):

1. Round state saved periodically (sau mỗi case done)
2. Resume detect round open + apk_pinned exists → không build lại
3. Chỉ run cases chưa có kết quả

```
Round state before crash:
  cases_run: [TC-001 pass, TC-002 pass]
  cases_pending: [TC-003, TC-004, TC-005]

Resume:
  Reuse APK round-N
  Run only [TC-003, TC-004, TC-005]
```

## Case parallelism

Multiple emulator pool → cases run parallel:

```yaml
pool:
  - serial: emulator-5554
    status: running
    current_case: TC-001
  - serial: emulator-5556
    status: running
    current_case: TC-002
  - serial: emulator-5558
    status: idle
```

Rules:
- 1 case = 1 emulator slot (không shared)
- Emulator fail → requeue case lên emulator khác
- Max concurrent = pool size (user config)

## Report format

Round report consolidate:

```yaml
# briefs/<slug>/actual/round-N/report.json
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

static:
  lint: pass
  konsist: pass

cases:
  total: 25
  pass: 20
  fail: 3
  skipped_early_stop: 2

performance:
  cold_start_p50_ms: 850
  cold_start_p95_ms: 1200
  memory_peak_mb: 180

ui_judge:
  total_nodes: 12
  pass: 10
  fail: 2

bugs_opened: 3
bugs_fingerprints: [sha256:abc..., sha256:def..., sha256:xyz...]

verdict: red  # green nếu 0 fail
```

## Decision procedure

### Start round

1. Check round state: must be `closed`
2. If `type: full`:
   - Clear last round cache (optional)
   - Rebuild APK
   - Install fresh
   - Queue all cases
3. If `type: verify`:
   - Check `apk_pinned` + cache valid
   - Queue only specified cases
4. Mark `round: running`

### Run case

1. Pick emulator từ pool
2. Reset emulator state (not device power cycle, chỉ app clearState nếu case require)
3. Execute step file qua driver
4. Capture screenshot/logcat/video
5. Run assertions
6. Write result + bug record streaming
7. Mark emulator idle
8. Check early-stop condition

### Close round

1. All cases done hoặc early-stopped
2. Compute report
3. Mark `round: closing`
4. Final checks (perf aggregate, ui-judge final)
5. Mark `round: closed`
6. Notify coding agent

## Rules

- **MUST** 1 round open tại 1 thời điểm (lock)
- **MUST** streaming bug write (không batch cuối round)
- **MUST** fingerprint deterministic (test ổn định cùng input)
- **MUST** APK sha256 record cho reproducibility
- **FORBIDDEN** modify step file giữa round (immutable per round)
- **FORBIDDEN** skip case silently (phải mark reason: early-stop / env-fail / abort)
- **SHOULD** build cache enable mặc định
- **SHOULD** parallel pool size = emulator count available

## Anti-patterns

### AP-001 — Full round every iteration

Mỗi fix nhỏ chạy full round → waste 30-40 phút. Dùng verify round cho targeted.

### AP-002 — Batch bug reporting

Chờ end-of-round write all bugs → coding agent idle 30 phút. Streaming is key.

### AP-003 — Ignore early-stop

3 case fail cùng bug nhưng force continue → waste.

### AP-004 — No fingerprint

Mỗi bug unique key → không dedup, coding agent fix 1 cause nhưng thấy 10 bugs khác nhau.

### AP-005 — No resumption

Guard crash → restart from scratch → waste thời gian built. Save round state.

## Reference

- `knowledge/e2e-runtime/device-driver-contract.md` — driver interface
- `knowledge/e2e-runtime/runner-neutral-step.md` — step file schema
- `agents/guard-runner.md` (future harness) — runner agent template
- `workflows/guard-round.md` — orchestration workflow

## Note về generic vs product-specific

Pattern này generic. learn-app-plugin có `bin/guard.cjs` + `lib/guard-*.cjs` ~2000 LoC implement. Harness không ship implementation — downstream build runner theo pattern.

# Changelog

Tất cả thay đổi đáng chú ý của Mobile Engineering Harness.

Format tuân theo [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) và semver.

## [0.5.0] — 2026-10-14

### Added — P1 content catch-up

#### Skills
- **`skills/android-network/SKILL.md`** — Ktor Client integration: DTO + API service + mapper + Repository impl + MockEngine test. HttpClient config checklist, auth strategies, error mapping, retry policy.
- **`skills/android-database/SKILL.md`** — SQLDelight: schema design, DAO, migration, Flow queries, offline-first pattern, in-memory test driver.

#### Workflows
- **`workflows/refactor-module.md`** — 5-stage preserve-behavior refactor (baseline → plan → refactor → compare → verify). Golden rule: no observable behavior change.
- **`workflows/release-validation.md`** — 6-stage release candidate validation (preflight → build → smoke → artifact → regression → sign-off). Android APK + iOS XCFramework coverage.

#### Knowledge
- **`knowledge/data/repository-pattern.md`** — Interface in domain, impl in data; `ApiResult` return; offline-first; data source split; testing with Fake.
- **`knowledge/data/network.md`** — Ktor config essentials, JSON tolerant setup, auth strategies, error type mapping, platform engine via expect/actual.
- **`knowledge/data/persistence.md`** — SQLDelight / DataStore / filesystem / SecureStorage decision guide. Thread safety, lifecycle, testing.
- **`knowledge/data/caching.md`** — L1-L4 cache tier strategy, invalidation patterns, TTL guidance, size limits, common use cases.

#### Blueprints
- **`blueprints/network-service/README.md`** — standalone Ktor service pattern (`CatalogApi`): DTO, API, Mapper, Repository impl, DI binding, MockEngine tests. Dùng khi cần API cho feature không warrant full feature blueprint.

#### Verification
- **`verification/detekt/README.md`** — Detekt setup guide + custom rule roadmap. Enforces KOT (Kotlin conventions) + CORO (concurrency) rules.
- **`verification/detekt/detekt-config-template.yml`** — baseline config: `UnsafeCallOnNullableType`, `SwallowedException`, `GlobalCoroutineUsage`, `InjectDispatcher`, `LargeClass`, naming, complexity thresholds. Compose-friendly exclusions.

### Changed

- `AGENTS.md`: task routing + 2 new skills; workflows table + 2 new; file index refreshed.

### Rationale

P1 catches high-ROI gaps vs reference blueprint — add 2 skills covering API/DB (nearly every feature touches these), 2 workflows covering refactor + release (lifecycle gaps), knowledge/data (4 topics missing), and verification/detekt (second enforcement layer besides Konsist).

Still deferred (P2): 3 skills (`refactor`, `debug`, `performance`), additional blueprint splits, deep knowledge expansion (patterns, security, performance subfolders), evaluations/rubrics folder.

## [0.4.0] — 2026-10-14

### Added

- **`constitution/kotlin-conventions.md`** — 12 KOT rules (naming, null safety, immutability, visibility, sealed types, extensions, scope functions, exception handling, collection ops, resources, documentation).
- **`skills/android-coroutines/SKILL.md`** — dedicated procedure cho async/Flow/cancellation work; previously only knowledge/essentials.
- **`workflows/fix-bug.md`** — 5-stage: reproduce → isolate → cause → fix → verify. Cause-level fix discipline, không mask symptom.
- **`workflows/review-pull-request.md`** — PR audit workflow với 10 dimensions + evidence-based findings + severity levels.
- **`agents/`** folder — role prompts cho multi-agent orchestration:
  - `architect.md` — Plan + inspect, no code
  - `implementer.md` — Execute theo plan, minimal scope
  - `reviewer.md` — Independent audit, evidence-based
  - `test-engineer.md` — Behavior coverage, deterministic test

### Changed

- `AGENTS.md`: task routing table thêm `android-coroutines`; thêm "Workflows" + "Agent roles" sections; file index updated.

### Rationale

Fill P0 gap vs reference blueprint theo evidence-driven priority. Skip P1/P2 (6 skills khác, 20+ knowledge split files, 4 blueprints khác) để tránh YAGNI + context bloat.

## [0.3.0] — 2026-10-14

### Added

- **`bootstrap.sh`** — one-liner curl-pipe installer:
  ```bash
  curl -fsSL https://raw.githubusercontent.com/huypqapero/mobile-engineering-harness/main/bootstrap.sh | bash
  ```
  Clones upstream vào `~/.mobile-engineering-harness/` + symlinks CLI thành `mehcli` ở `~/.local/bin/`.
  Supports: idempotent re-run, PATH check, pass-through subcommand (`bash -s init --project .`).
- **`self-update` subcommand**: `mehcli self-update` git pulls latest từ installed location.
- **`version` subcommand**: `mehcli version` prints tag + commit + upstream path.
- **Env vars** cho bootstrap: `MEH_INSTALL_DIR`, `MEH_BIN_DIR`, `MEH_REF` (pin specific tag).

### Changed

- README quickstart dùng one-liner install thay vì manual clone + symlink.
- Install script branding thành `mehcli` (giữ filename `install.sh` cho backward compat).

## [0.2.0] — 2026-10-14

### Added

- **`install.sh` CLI với 4 subcommands**: `init`, `install`, `update`, `uninstall`.
- **`init --project <path>`**: scaffold `.harness-overlay/` + copy schema template + create upstream symlink.
- **`uninstall --overlay <path>`**: remove rendered files (preserve `overlay.yaml`, `constitution/`, `blueprints/`, upstream symlink).
- **`uninstall --purge`**: nuke entire overlay directory with double confirm.
- **`update --overlay <path>`**: idempotent re-render alias cho `install`.
- **Flag `--dry-run`**: preview actions không execute.
- **Flag `--yes` / `-y`**: skip confirmation prompts cho CI.
- **Manifest tracking**: `.manifest.yaml` ghi rendered files + upstream commit + install time.
- **Auto-generated overlay `README.md`** liệt kê commands + agent resolution order.

### Changed

- `install.sh` refactor từ single-flow sang subcommand dispatcher.
- `install` command bây giờ ghi manifest + render thêm `README.md` cho overlay.

### Fixed

- Help text không leak `set -euo pipefail` ở cuối output (macOS BSD awk compat).

### Migration from 0.1.0

Overlay cũ không có `.manifest.yaml`. Chạy lại `install` sẽ auto-tạo manifest từ hardcoded list — không mất gì. `uninstall` fallback hardcoded list khi manifest missing.

## [0.1.0] — 2026-10-14

### Added

- Initial 2-layer harness.
- `constitution/` — 14 ARCH rules + 10 CORO rules + engineering principles + DoD.
- `knowledge/` — Clean+MVI, Compose, MVI, Coroutines essentials.
- `skills/` — 5 procedures (`android-feature`, `android-compose`, `android-mvi`, `android-code-review`, `android-testing`).
- `blueprints/reference-feature/` — generic `ItemCatalog` golden sample.
- `workflows/feature-development.md` — 5-stage orchestration.
- `verification/` — Konsist test template + `verify.sh` template.
- `evaluations/templates/` — 5 scenario templates.
- `install.sh` — simple render script với placeholder substitution.

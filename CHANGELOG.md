# Changelog

Tất cả thay đổi đáng chú ý của Mobile Engineering Harness.

Format tuân theo [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) và semver.

## [0.6.0] — 2026-10-14

### Added — P2 reference blueprint completion

#### Skills (3 more)
- **`skills/android-refactor/SKILL.md`** — Preserve-behavior refactor patterns: P-01 extract function, P-02 extract class, P-03 inline, P-04 move cross-layer, P-05 rename, P-06 split file, P-07 extract feature module. Pair với `workflows/refactor-module.md`.
- **`skills/android-debug/SKILL.md`** — Diagnose Android bugs: D-01 reproduce deterministic, D-02 isolate scope, D-03 logging/breakpoint, D-04 prove root cause, D-05 platform-specific (adb/Xcode), D-06 common bug patterns, D-07 coroutine debug, D-08 Compose recomposition debug.
- **`skills/android-performance/SKILL.md`** — Measure-first optimization: P-01 startup (baseline profile, lazy init), P-02 Compose recomposition, P-03 lazy list, P-04 memory, P-05 network, P-06 DB query, P-07 battery. SLO baseline table.

#### Blueprints (3 more)
- **`blueprints/compose-screen/README.md`** — standalone Compose screen pattern (route stateful + content stateless). Dùng khi feature đơn giản không warrant full feature stack.
- **`blueprints/repository/README.md`** — standalone Repository (domain interface + data impl với remote + local source + sync).
- **`blueprints/usecase/README.md`** — standalone UseCase (orchestrate multi-source, validation+action, Flow transformation). Decision tree "khi nào cần UseCase".

#### Knowledge (3 more domains)
- **`knowledge/patterns/common-patterns.md`** — Design patterns thực dùng trong Kotlin/Android (Factory, Builder DSL, Singleton via DI, Adapter, Facade, Decorator, Strategy, Observer via Flow, State sealed, Command via Intent, Chain of Responsibility). Patterns to AVOID. Rule: pattern chỉ áp dụng khi có problem cụ thể.
- **`knowledge/security/essentials.md`** — Threat model baseline + 10 security sections (SEC-01..10): secret storage (KeyStore/Keychain), network (TLS, cert pinning), PII, platform integrity, input validation, dependency security, WebView, backup, build config, analytics.
- **`knowledge/performance/essentials.md`** — SLO targets table + startup/Compose/memory/lazy list/network/DB/battery optimization patterns. Profiling workflow: measure → hypothesize → optimize → re-measure.

#### Evaluations (2 subfolders)
- **`evaluations/rubrics/README.md`** — Shared scoring rubric: score scale (90-100 → <40), dimension weights (default), severity classification per rule. Baseline vs harness comparison format.
- **`evaluations/regression/README.md`** — Trend tracking across harness versions + model variants. YAML record format, alert thresholds, model matrix.

#### Verification (1 subfolder)
- **`verification/lint/README.md`** — Android Lint setup + custom rule roadmap. Scaffold `lint.xml`, baseline strategy, Compose Lint rules, custom rule example skeleton. Hoãn custom rule tới khi evidence.

### Changed
- `AGENTS.md`: task routing + 3 new skills; file index refreshed cho tất cả P2 additions.

### Rationale
P2 completes the reference blueprint structural match: 11 skills (match reference), 5 blueprints (match reference), 5 workflows (match reference), knowledge covering all 7 reference domains (architecture + presentation gộp vào mvi/compose + coroutines + data + patterns + security + performance), full verification 3-tool stack (Konsist + Detekt + Lint), evaluations 3-subfolder (templates + rubrics + regression).

Harness upstream v0.6.0 ≈ 100% reference blueprint coverage. Chuyển sang evidence-driven refinement.

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

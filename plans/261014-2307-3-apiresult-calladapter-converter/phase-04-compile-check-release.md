# Phase 4 — Compile-check snippets + release notes

## Task 4.1 — Scratch compile-check (outside repo)
- Target: `/tmp/harness-issue3-compile/` (never committed).
- Steps: Gradle 8.13 JVM project (Kotlin JVM + serialization plugin) with deps Retrofit 2.11, converter-kotlinx-serialization, OkHttp mockwebserver, Ktor client 3.x (core, mock, content-negotiation, json), Ktorfit lib 2.x, Konsist, kotlin-test. Copy verbatim from docs: `ApiResult` + extensions, `DomainError`, `ErrorMapper` (both branches — JVM has both libs), `ApiResultCallAdapterFactory`, `ApiResultConverterFactory`, `safeRequest`, and the rendered Konsist test (placeholders substituted). Add tests: Retrofit MockWebServer 200/404/malformed JSON/204 Unit; Ktor MockEngine 200/404/timeout-free IO error; Ktorfit converter unit-level 404; cancellation is rethrown.
- Verify: `gradle test` exits 0 with all tests passing; the Konsist test file compiles (`compileTestKotlin` succeeds).

## Task 4.2 — Release notes
- `CHANGELOG.md`: add `## [0.11.0] — 2026-10-14` (Changed — breaking: ARCH-004; Added: ErrorMapper/adapter/converter/safeRequest/migration/Konsist; Rationale).
- `README.md` release history: add `- **v0.11.0**: ...` line.
- Verify: `grep -n "0.11.0" CHANGELOG.md README.md` prints ≥ 2 lines.

## Failure Protocol
If any Verify step does not meet its stated pass condition, STOP this phase.
Do not improvise a fix, retry blindly, or reason around the failure.
Spawn the `kongming` subagent for next-step counsel and pass:
- the phase and task id,
- what you attempted (the steps you ran),
- the exact command and its full output,
- the pass condition it failed to meet.
Apply kongming's guidance, then re-run the Verify step.
If `kongming` cannot be spawned in this environment, STOP and report the same
failure evidence to the user. Never continue by self-reasoning.

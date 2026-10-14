# Phase 2 — Rules, rubric, Konsist

## Task 2.1 — ARCH-004
- Target: `constitution/architecture-rules.md` `## ARCH-004`.
- Steps: rename "Repository impl không kế thừa base class; network trả ApiResult"; Severity MUST; Scope `data/src/.../repository/*Impl.kt` + `data/src/.../remote/*Api.kt`; Rationale (inheritance coupling, quên bọc → raw exception lọt, adapter là cơ chế chính thức của lib); Pattern (impl chỉ implement interface domain; API trả `ApiResult<Dto>` qua CallAdapter/Converter/safeRequest; mapping ở `ErrorMapper`; không `withContext(ioDispatcher)` quanh network call); Verification: Konsist `ARCH-004 repository impl does not extend base repository` + `ARCH-004 api services return ApiResult`; Violation example.
- Verify: `grep -n "BaseRepository" constitution/architecture-rules.md` only inside the Violation example or migration note.

## Task 2.2 — CORO-002
- Target: `constitution/concurrency-rules.md` line ~20.
- Steps: "IO blocking (file, DB đồng bộ): `withContext(ioDispatcher)` tại local source sở hữu IO đó. Network suspend call (Retrofit/Ktor/Ktorfit) đã main-safe, không bọc."
- Verify: `grep -c BaseRepository constitution/concurrency-rules.md` prints 0.

## Task 2.3 — Rubric
- Target: `evaluations/rubrics/README.md:49`.
- Steps: `ARCH-004 Repository impl không kế thừa base class, API trả `ApiResult` qua adapter/converter — HIGH`.
- Verify: `grep -n "ARCH-004" evaluations/rubrics/README.md` contains `HIGH` and not `BaseRepository`.

## Task 2.4 — Konsist tests
- Target: `verification/architecture-tests/TemplateArchitectureRulesTest.kt`.
- Steps: add two tests after ARCH-003, using only existing placeholders (`{{MODULE_DATA}}`):
  1. classes in data module named `*RepositoryImpl` → `assertFalse { hasParent { it.name.endsWith("BaseRepository") } }`.
  2. classes + interfaces in data module named `*Api` → non-private suspend functions → `returnType?.name?.startsWith("ApiResult") == true`.
  Add needed imports (`com.lemonappdev.konsist.api.ext.list.functions`).
- Verify: phase 4 compile-check compiles the rendered file against Konsist; until then `grep -c "ARCH-004" verification/architecture-tests/TemplateArchitectureRulesTest.kt` ≥ 2.

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

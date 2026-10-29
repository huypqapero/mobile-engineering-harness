---
name: coding-feature
description: Implement feature end-to-end xuyên 4 modules (data + domain + presenter + composeApp wiring) theo MVI + Clean Architecture của {{PRODUCT_NAME}}. Trigger khi tạo feature mới hoặc modify behavior cross-layer.
priority: P0
---

# Skill: coding-feature

## Trigger

- "Implement feature X"
- "Add screen Y" cần touch data + domain + presenter
- "Modify behavior of feature Z" cross-layer

## Inputs

Bắt buộc:
- Spec file `docs/specs/<feature>.md` hoặc rõ requirement
- Feature name (dùng cho package, route)
- Data source (REST endpoint, local DB, cache strategy)

Optional:
- Design mock hoặc frame reference
- Analytics event list
- Remote config key

## Prerequisites

Trước khi code, đọc:

1. Project root `CLAUDE.md` — 14 rules
2. `constitution/architecture-rules.md [KB → develop/constitution, kb_search "architecture rules"]` — ARCH-001..014
3. `knowledge/coding/clean-arch/clean-mvi.md [KB → develop/coding-clean-arch, kb_search "clean arch clean mvi"]`
4. Spec file liên quan

## Execution procedure

### Step 1 — Requirement analysis (5 phút)

- Extract acceptance criteria từ spec
- Identify 5 UI states cần cover (loading / empty / error / offline / success)
- List external deps: API endpoints, DB tables, remote config, analytics events
- Decide: cần UseCase mới hay gọi Repository interface direct?

### Step 2 — Package layout

Tạo structure:

```
presenter/src/commonMain/kotlin/{{PACKAGE_ROOT_PATH}}/presenter/feature/<name>/
├── <Name>Api.kt                 ← public surface (route + optional config)
├── <Name>Screen.kt              ← route composable + content
├── <Name>ViewModel.kt           ← extends BaseViewModel
├── <Name>Contract.kt            ← State + Intent + Effect
└── components/                  ← private composables (nếu > 3)
```

Nếu có domain model mới:

```
domain/src/commonMain/kotlin/{{PACKAGE_ROOT_PATH}}/domain/model/<name>/
└── <Name>.kt
```

Nếu có use case mới:

```
domain/src/commonMain/kotlin/{{PACKAGE_ROOT_PATH}}/domain/usecase/<name>/
└── <Verb><Noun>UseCase.kt
```

Nếu có repository mới hoặc extend:

```
domain/src/commonMain/kotlin/{{PACKAGE_ROOT_PATH}}/domain/repository/
└── <Name>Repository.kt           ← interface

data/src/commonMain/kotlin/{{PACKAGE_ROOT_PATH}}/data/repository/
└── <Name>RepositoryImpl.kt       ← implement interface, không kế thừa base class

data/src/commonMain/kotlin/{{PACKAGE_ROOT_PATH}}/data/mapper/
└── <Name>Mapper.kt               ← object + extensions

data/src/commonMain/kotlin/{{PACKAGE_ROOT_PATH}}/data/remote/
└── <Name>Api.kt                  ← service trả ApiResult<Dto>

data/src/commonMain/kotlin/{{PACKAGE_ROOT_PATH}}/data/dto/
└── <Name>Dto.kt                  ← @Serializable DTO
```

### Step 3 — Implement bottom-up

Thứ tự fix lỗi:

1. **Domain model** — pure Kotlin data class
2. **Repository interface** — ở `domain/repository/`
3. **DTO + Mapper** — `data/dto/` + `data/mapper/`
4. **API service** — `data/remote/`, trả `ApiResult<Dto>` (`skills/coding-network` Step 4)
5. **Repository impl** — implement interface, `api.x().map { it.toDomain() }` (ARCH-004)
6. **UseCase** (nếu có logic) — pure function class, `invoke(...)` suspend
7. **DI binding** — thêm vào `DataModule.kt` + `DomainModule.kt` + `PresenterModule.kt`
8. **Contract** — State + Intent + Effect
9. **ViewModel** — extend `BaseViewModel`, override `onIntent`
10. **Screen** — route composable + stateless content + 5 state render
11. **Navigation** — thêm route vào `NavRoute.kt` + wire ở `AppNavHost.kt`
12. **Analytics** — track event tại ViewModel.onIntent

### Step 4 — Verify

Chạy đủ gates (xem `definition-of-done.md`):

```bash
./gradlew :domain:build
./gradlew :data:build
./gradlew :presenter:build
./gradlew :composeApp:assembleDebug
./gradlew :domain:test :presenter:test :data:test
./gradlew konsistTest
./gradlew detekt
```

### Step 5 — Report

Theo mẫu `definition-of-done.md §Report`.

## Required policies

- ARCH-001 domain purity
- ARCH-002 presenter không data
- ARCH-003 ViewModel deps
- ARCH-005 mapper object + ext
- ARCH-006 feature self-contained
- ARCH-007 MVI 1-chiều
- ARCH-008 5 states
- ARCH-009 nav type-safe
- ARCH-011 DI binding
- CORO-001..010

## Reference selection

Load thêm khi task yêu cầu:

- Compose heavy UI → `knowledge/coding/compose/essentials.md [KB → develop/coding-compose, kb_search "compose essentials"]`
- Complex state transition → `knowledge/coding/mvi/essentials.md [KB → develop/coding-mvi, kb_search "mvi essentials"]`
- Concurrent operations → `knowledge/coding/coroutines/essentials.md [KB → develop/coding-coroutines, kb_search "coroutines essentials"]`
- Platform SDK integration → `android-sdk-structure` skill (nếu có)

## Output contract

Deliverable gồm:

- Feature plan ngắn (list file touched + rationale)
- Code implementation theo structure trên
- Unit test tối thiểu: ViewModel state transition, Repository impl, Mapper
- Verification report theo mẫu DoD

## Validation

Trước khi tuyên bố DONE:

- [ ] Konsist pass
- [ ] Unit test pass
- [ ] Detekt pass
- [ ] Build Android debug pass
- [ ] 5 states đã render (loading / empty / error / offline / success)
- [ ] Nav route type-safe
- [ ] Analytics event wire đúng chỗ

## Failure / recovery

- Konsist fail → fix violation, không disable test
- Build fail do code có sẵn (không phải code mới) → ghi rõ trong report, không gộp fix ngoài scope
- Spec có open item blocking → BLOCKED, hỏi user
- iOS target chưa test được trong env → VERIFIED_WITH_LIMITATIONS, document

## Anti-patterns bị cấm

- Tạo UseCase trivial 1-1 không logic
- Expose DTO ra ngoài data module
- Mix business logic vào ViewModel (phải ở UseCase hoặc domain function)
- Composable có logic nghiệp vụ (phải stateless, delegate ViewModel)
- Nav string literal thay vì `NavRoute` sealed class
- Test skip, `@Ignore` tạm thời không có issue link

---

## Harness context

- Workflow: `workflows/feature-development.md`
- Guardrails: `~/.claude/rules/primary-workflow.md, development-rules.md, review-audit-self-decision.md, orchestration-protocol.md`


## Overlay gate (D-full)

Trước Step 1, verify `.harness-overlay/overlay.yaml` tồn tại. Nếu không, abort với status `BLOCKED` và chỉ dẫn user:

> Chưa có overlay. Chạy skill `harness-init` để scaffold trước, sau đó quay lại skill này.

Khi gặp placeholder `{{X}}` trong procedure/code example, resolve bằng mapping ở `AGENTS.md §Placeholder resolution` (Read overlay 1 lần đầu session, cache qua context).

# Workflow: Feature Development

Orchestrate việc implement feature end-to-end. Trạng thái máy, không checklist tự do.

## Entry conditions

- Spec file có tại `docs/specs/<feature>.md` HOẶC requirement rõ ràng từ user
- Branch feature đã checkout
- Open items của spec không block implementation hiện tại

## Input artifacts

- Spec file (bắt buộc)
- Design mock / frame reference (nếu có)
- 14 rules project `CLAUDE.md`
- Constitution `.harness/constitution/`
- Blueprint `.harness/blueprints/complete-mvi-feature/`

## Stages

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  1. INSPECT  │───▶│   2. PLAN    │───▶│ 3. IMPLEMENT │───▶│  4. VERIFY   │───▶│  5. REPORT   │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                                                 │  ▲
                                                 ▼  │
                                            fix bounded
                                            (max 3 iter)
```

---

## Stage 1 — Inspect

### Actions

1. Read spec file (`docs/specs/<feature>.md`)
2. Read project `CLAUDE.md` + `docs/architecture.md`
3. Scan existing related files:
   - Repository interfaces hiện có → có thể extend?
   - UseCase hiện có → reuse?
   - Models hiện có → reuse?
   - Nav routes hiện có?
4. Load relevant knowledge:
   - MVI pattern: `.harness/knowledge/mvi/essentials.md`
   - Compose patterns: `.harness/knowledge/compose/essentials.md`
   - Nếu async-heavy: `.harness/knowledge/coroutines/essentials.md`
5. Identify open questions trong spec

### Completion criteria

- Hiểu rõ 5 UI states cần render
- List file sẽ touch (file mới + file sửa)
- Blocker open question → stop và hỏi user; không guess

### Blocker conditions

- Spec thiếu critical info (API shape, auth required, feature flag)
- Infrastructure chưa sẵn (API endpoint chưa deploy)
- Rules conflict → cần user resolve

---

## Stage 2 — Plan

### Actions

1. Write 1-page implementation plan tại `plans/261014-XXXX-<feature>/plan.md`:
   - Overview (1 paragraph)
   - File touched (list + rationale)
   - Decision log: UseCase cần không? Repo mới hay extend?
   - Analytics event mới
   - Remote config key mới
   - Risk (nếu có)
2. Choose skill route:
   - Primary: `android-feature`
   - UI-heavy → secondary: `android-compose`
   - State complex → secondary: `android-mvi`

### Completion criteria

- Plan < 200 dòng
- File list cụ thể, path đầy đủ
- Không "may need to" — commit cụ thể

### Blocker conditions

- File list > 20 files → chia sub-feature trước
- Cross-feature coupling phát hiện → raise về architecture decision

---

## Stage 3 — Implement

### Actions theo thứ tự (bottom-up)

1. Domain model + Repository interface (nếu mới)
2. DTO + Mapper
3. API service (Ktor)
4. Repository impl (extend `BaseRepository`)
5. UseCase (nếu cần logic)
6. DI binding (3 modules: Data/Domain/Presenter)
7. Contract (State + Intent + Effect)
8. ViewModel (`BaseViewModel`)
9. Screen (route + content + 5 states)
10. Nav route + wire `AppNavHost.kt`
11. Analytics + Remote config (nếu có)

### Rules enforcement

- ARCH-001..014 từ constitution
- CORO-001..010 từ constitution
- Reference `.harness/blueprints/complete-mvi-feature/README.md`

### Completion criteria

- Mọi file đã sửa
- Code compile cục bộ: `./gradlew :<module>:build`
- Không TODO không link issue

### Blocker conditions

- Build fail do code có sẵn (không phải code mới) → stop, report ra
- Need new dependency library → stop, confirm với user
- Platform SDK integration (ExoPlayer, AVPlayer) → load skill `android-sdk-structure` nếu có

---

## Stage 4 — Verify

### Required gates (theo thứ tự chạy)

```bash
# 1. Compile
./gradlew :composeApp:assembleDebug

# 2. Unit tests
./gradlew :domain:test :presenter:test :data:test

# 3. Architecture tests
./gradlew konsistTest

# 4. Code quality
./gradlew detekt
```

### Fix loop (bounded)

- Fail → analyze root cause:
  - Lỗi code mới → fix
  - Lỗi code cũ (pre-existing) → ghi report, không gộp fix ngoài scope
  - Lỗi environment (tool version, cache) → clear + rerun 1 lần
- Max 3 iteration fix cho cùng 1 gate; sau 3 lần fail → report BLOCKED

### Completion criteria

- 4 gates PASS (hoặc document limitation)
- iOS build nếu env support (`./gradlew :composeApp:iosX64MainKlibrary`) — else VERIFIED_WITH_LIMITATIONS

### Blocker conditions

- Gate fail sau 3 fix iteration
- Konsist chưa setup → BLOCKED, propose setup
- Test không chạy được do env → VERIFIED_WITH_LIMITATIONS, document

---

## Stage 5 — Report

### Actions

Write report tại `plans/reports/android-feature-261014-XXXX-<feature>.md`:

```
Status: VERIFIED | VERIFIED_WITH_LIMITATIONS | BLOCKED | FAILED

Summary:
<1-2 câu, outcome, không process>

Files changed:
- domain/src/.../BookDetail.kt (new, +45)
- data/src/.../BookRepositoryImpl.kt (+15)
...

Architecture compliance:
- ARCH-001 domain purity: PASS (konsist verified)
- ARCH-003 ViewModel deps: PASS (manual + konsist)
- ARCH-007 MVI 1-chiều: PASS
- ARCH-008 5 states: PASS (loading/empty/error/offline/success all rendered)

Concurrency compliance:
- CORO-001 scope: PASS
- CORO-004 cancellation: PASS

Verification:
- compile: PASS (./gradlew :composeApp:assembleDebug)
- konsist: PASS (./gradlew konsistTest)
- detekt: PASS
- unit_tests: PASS (12 new tests, 0 fail)
- ios_build: SKIPPED (env limitation)

Limitations:
- iOS build chưa test (no macOS runner)
- UI instrumented test chưa viết

Open questions:
- Cần cache paginated chapters không? (depend content pipeline spec open item)
```

### Completion criteria

- Report file tạo
- Report dẫn tới verifiable artifacts (test run log, build log)
- Open questions nếu có → listed cuối

---

## Rollback strategy

Nếu feature cần revert:

1. `git revert <commit>` thay vì `git reset --hard` (safe for branch sharing)
2. Nếu đã merge → tạo revert PR
3. Nếu rollback vì bug: tạo issue + plan fix forward

## Agent roles

Giai đoạn solo (1 agent) → 1 agent thực hiện cả 5 stages, chuyển skill mindset khi vào từng stage:

- Stage 1-2: "Architect"
- Stage 3: "Implementer"
- Stage 4: "Test Engineer"
- Stage 5: "Reviewer" (self-review)

Giai đoạn team (sau khi harness ổn) → delegate Stage 4 cho `android-code-review` agent độc lập.

## Final output schema

```yaml
feature: <name>
status: VERIFIED | ...
files_changed: <count>
tests_added: <count>
rules_verified:
  - ARCH-001
  - ARCH-003
  - ...
gates:
  compile: PASS
  konsist: PASS
  detekt: PASS
  tests: PASS
  ios_build: SKIPPED
limitations:
  - ...
open_questions:
  - ...
```

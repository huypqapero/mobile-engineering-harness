# Claude Code — Harness Entry (Upstream)

Đây là entry chung cho mọi sản phẩm consume upstream harness qua `.harness-overlay/`.

## Nạp context theo thứ tự

1. Project root `CLAUDE.md` (file này) — context project-specific + routing rules (ưu tiên cao nhất)
2. `.harness-overlay/overlay.yaml` — vars product
3. `.harness-overlay/upstream/AGENTS.md` — generic entry + full file index
4. Skill tương ứng trong `skills/<name>/SKILL.md` khi task invoke skill
5. `constitution/` khi cần verify rule (14 ADR + CORO + KOT + DoD)
6. `knowledge/<category>/<domain>/` khi cần kiến thức nền

## Task routing (bắt buộc check trước khi execute)

Match user intent theo keyword trước. Nếu match → trigger skill wrapper, KHÔNG tự chế workflow.

| User intent | Entry skill | Fallback khi skill không fit |
|---|---|---|
| "implement/add/build feature X", "làm/thêm tính năng X" | `/feature` | solo `architect` + `coder` |
| "fix bug/crash X", "sửa bug/lỗi X" | `/bugfix` | solo `tech-lead` triage |
| "release vX.Y.Z", "ship version", "phát hành" | `/release` | solo `tech-lead` + `project-manager` co-sign |
| "triage bug X", "phân loại bug" | `/bug-triage` | — |
| "parallel features A, B, C", "N feature cùng sprint" | `/parallel-features` | — |
| "review PR N", "check code" | solo `reviewer` | — |
| "verify/test/QA X" | solo `qa` scope A hoặc B | — |
| "plan/design arch X" | solo `architect` | — |
| "chuẩn hóa spec + screenshot thành brief" | `/business-prepare-feature` | — |
| Mơ hồ, không match | **ask clarify, KHÔNG tự chế workflow** | — |

Full routing table 30+ row: `AGENTS.md §Task routing`.

## Delegate rule (solo mindset vs spawn subagent)

### Solo mindset (1 session, 1 role)
Khi:
- Task scope ≤ 1 role (chỉ Coder, chỉ Reviewer, chỉ QA)
- User muốn kiểm soát từng stage
- Context nhỏ, không cần isolation
- Fast turnaround

→ Prompt "Role=X, đọc `agents/X.md`, task=...".

### Spawn subagent (Task tool)
Khi:
- Pipeline > 2 role (feature-full-flow, parallel-features)
- Cần context isolation (parallel worktree)
- User request orchestrator pattern
- Task tốn token, cần preserve main context

→ Invoke `/feature`, `/bugfix`, `/release` skill wrapper (chúng tự spawn subagent qua Orchestrator agent).

### Mindset chain (1 session chuyển role)
Khi:
- Feature nhỏ, bạn muốn giám sát từng stage
- Không cần parallel

→ Prompt "Trong 1 session, lần lượt Role=Architect → Role=Coder → Role=Reviewer".

## Fast-path trigger (bugfix)

Tech Lead approve fast-path **CHỈ KHI** cả 4 điều kiện AND:

1. Scope ≤ 1 file touch presenter (không touch domain contract, không touch repository signature)
2. Không touch shared file: `AppNavHost.kt`, `*Module.kt` (DI), `strings.xml`, `AnalyticsEvent.kt`, `build.gradle.kts`
3. Label match: `type:bugfix` | `type:ui-tweak` | `scope:single-screen`
4. No new dependency: không SDK mới, không expect/actual mới, không migration

**Cấm fast-path** ngay cả khi 4 match: security diff, ADR-011 high-risk, cross-feature contract change, migration.

Fast-path PASS → Architect → Coder thẳng, skip Tech Lead plan review. Reviewer vẫn chạy sau code.

Chi tiết: `agents/tech-lead.md §Fast-path skip rule`.

## Max retry + escalation path

| Loop | Max retry | Escalate to |
|---|---|---|
| Architect ↔ Tech Lead review | 2 vòng revise | Project Manager (scope cut hoặc dời deadline) |
| Coder ↔ QA bug fix (cùng signature) | 3 lần | Tech Lead triage lại (re-classify code/design/spec bug) |
| QA Scope B integration fail | 1 lần | Tech Lead → re-plan phần failed |
| Spec gap / unresolved requirement | — | Product Analyst update PRD + PM re-evaluate deadline |

Vượt max → auto escalate, KHÔNG retry thêm.

## Agent collaboration — handoff doc + Change Request

### Handoff doc (bắt buộc giữa agent)

Mỗi handoff tạo `plans/handoff/<feature>/<from>-to-<to>.md`:

```markdown
# Handoff: <feature>
## Meta
- From: <agent> | To: <agent> | Date: YYYY-MM-DD | Status: ready|blocked|needs-context
## Artifact delivered
- Path: <file> | Version: <n>
## Acceptance criteria met
- [x] <criteria>
## Open questions / Blocking issues
- <list>
```

Orchestrator chỉ chuyển tiếp khi file này tồn tại, status = ready, acceptance check hết.

### Change Request flow

Khi downstream (Designer / Tech Lead / Coder) phát hiện gap upstream (PRD thiếu state, plan missing branch):

1. Downstream tạo `briefs/<slug>/change-requests/CR-<id>.md`
2. Notify owner artifact gốc (BA / Architect / Product Analyst)
3. Owner update artifact + version mới
4. PM đánh giá impact deadline nếu CR expand scope
5. Orchestrator mark downstream artifact "needs re-validate"

Không được tự ý sửa artifact đã approved. Phải qua CR flow.

## Scope guard (khi nào raise user)

Agent **MUST raise user, không tự quyết** khi:

- Scope cut > 30% business value (ảnh hưởng commitment đã công bố)
- Deadline dời > 2 tuần
- ADR violation có evidence rõ ràng (constitution rule cứng)
- Security concern plausible (auth / token / encryption)
- Cross-feature contract change (feature A impact feature B subscribe)
- Migration (schema, data, user data)
- CR flow max 2 vòng vẫn chưa resolve

Agent **MAY tự quyết** (không raise) khi:

- Minor style choice khớp blueprint pattern
- Choose between 2 equivalent lib util đã existing
- Pattern selection cùng ADR profile

## Quality gates (bắt buộc trước DONE)

Trước khi tuyên bố DONE / APPROVE / merge:

1. `./gradlew :{{MODULE_DOMAIN}}:test :{{MODULE_PRESENTER}}:test :{{MODULE_DATA}}:test` PASS
2. `./gradlew konsistTest` PASS, 0 violation
3. `./gradlew detekt` PASS, no new issue
4. Build smoke: `./gradlew :{{MODULE_APP}}:assembleDebug` PASS
5. Unit test coverage trên code mới (happy + ≥ 2 edge case)
6. Reviewer verdict APPROVE (hoặc APPROVE_WITH_CHANGES resolved)

Fail bất kỳ gate → không được tuyên bố DONE. Chi tiết: `constitution/definition-of-done.md`.

## Reference index

| Doc | Mục đích |
|---|---|
| `AGENTS.md` | Full file index + task routing table (30+ row) + agent roles 14 role + workflows list |
| `agents/workflows/README.md` | 5 pipeline routing docs (feature-full-flow, bugfix-fast-path, bug-triage, release-gate, parallel-features) + artifact ownership + handoff rules |
| `knowledge/README.md` | 7-category knowledge index (coding/product/design/pm/testing/meta/cross-cutting) + lookup pattern + naming convention |
| `constitution/` | 14 ADR + CORO + KOT rules với ID + Konsist verify + Severity |

## Architecture constraints (quick reference)

- Dependency bất biến: `{{MODULE_APP}} → {{MODULE_PRESENTER}} → {{MODULE_DOMAIN}} ← {{MODULE_DATA}}`
- `{{MODULE_DOMAIN}}` thuần Kotlin common, **cấm** import Android/iOS/Firebase
- ViewModel chỉ gọi UseCase hoặc Repository **interface**, không gọi `*Impl`
- Platform SDK chỉ ở `{{MODULE_DATA}}/{androidMain,iosMain}` qua `expect/actual`
- 1 feature = 1 package tự chứa trong `{{MODULE_PRESENTER}}/.../{{FEATURES_ROOT}}/`
- MVI 1 chiều: `Intent → State + Effect`
- Mọi screen remote-data đủ 5 state (loading / empty / error / offline / success)
- Trước DONE: unit test touched + Konsist + Detekt + build (xem Quality gates ở trên)

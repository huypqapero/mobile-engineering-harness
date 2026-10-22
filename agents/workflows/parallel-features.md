# Workflow: Parallel Features

Chạy nhiều feature độc lập song song trong cùng sprint. PM request, Tech Lead + Orchestrator điều phối. Dùng khi deadline hard + scope frozen + có team capacity.

## Trigger

- PM thấy deadline conflict không thể cắt scope
- Multiple feature độc lập về owned package (ít share code)
- Có capacity spawn parallel agent (token budget đủ)

## Diagram

```
          PM request parallel
                 │
                 ▼
         Tech Lead feasibility check
                 │
         ┌───────┴───────┐
         │               │
       APPROVE          REJECT ──► chuyển `feature-full-flow.md` sequential
         │
         ▼
    Orchestrator spawn Architect subagent
         │
         ▼
    Architect decompose spec ──► N feature plan
         │                        │
         ▼                        │
    isolation-check.yaml          │
         │                        │
    ┌────┴────┐                   │
    │         │                   │
  SAFE    UNSAFE                  │
    │         │                   │
    │         └──► merge back sequential
    │
    ▼
    Spawn N × (Coder + Reviewer + QA) parallel worktree
    │
    ▼
    Mỗi feature chạy Stage 7-8 độc lập
    │
    ▼
    Aggregate shared files (DI, Nav, strings) sequential
    │
    ▼
    Integration test full
    │
    ▼
    Release gate (single sign-off cho bundle)
```

## Precondition

Tech Lead approve parallel chỉ khi:

- [ ] N feature đã qua Stage 1-6 độc lập (PRD + Design + Tech Brief + Plan + Review)
- [ ] Mỗi feature có `plan.md` riêng + Tech Lead APPROVE
- [ ] Owned packages không overlap (verified qua `isolation-check.yaml`)
- [ ] Shared files touched identified rõ (DI module, NavHost, strings.xml)
- [ ] Cross-feature dependency = none (hoặc explicit sequential chain)
- [ ] Có capacity: ít nhất 2× token budget của sequential + 1× merge overhead

## Stage sequence

### Stage 1 — PM request + Tech Lead feasibility

**Input**: PM backlog có N feature với deadline chồng lấp

**Tech Lead activity**:
1. Audit N feature: scope, module boundary, cross-dep
2. Estimate token/time cost sequential vs parallel
3. Verdict: APPROVE_PARALLEL / REJECT (go sequential)

**Output**: `plans/reports/parallel-feasibility-<sprint>.md`

---

### Stage 2 — Spec decomposition (Architect)

**Owner**: `architect` (spec decomposition mode — xem `architect.md` section "Spec decomposition")

**Input**: N PRD + design + tech-brief

**Activity**:
1. Produce `plans/<date>/plans/<feature-name>.md` per feature (N file)
2. Produce `plans/<date>/isolation-check.yaml`:

```yaml
features:
  feature-login:
    owned_packages:
      - presenter/.../login
      - domain/model/auth
      - data/dto/auth
    shared_files:
      - AppNavHost.kt (add route)
      - DomainModule.kt (bind UseCase)
      - strings.xml (add keys)
    cross_dep: []
  feature-signup:
    owned_packages:
      - presenter/.../signup
      - domain/model/auth (SHARED — chú ý)
    shared_files:
      - AppNavHost.kt (add route)
      - DomainModule.kt
    cross_dep: []
```

**Verification** (Orchestrator đọc isolation-check.yaml):
- Nếu 2 feature share owned_package → UNSAFE, chuyển sequential cho cặp đó
- Nếu cross_dep ≠ none → sequential cho chain đó
- Nếu shared files chỉ append (không conflict logic) → SAFE để parallel

---

### Stage 3 — Spawn parallel execution

**Owner**: `orchestrator`

**Activity**: Với mỗi feature SAFE parallel:

1. Create worktree isolated (`git worktree add .worktrees/<feature>`)
2. Spawn subagent chain: Coder → Reviewer → QA (Scope A)
3. Mỗi lane có handoff doc riêng: `plans/handoff/<feature>/*.md`

Deadline cho mỗi lane: giữ nguyên như sequential (parallel chỉ chia nhỏ wall time, không chia nhỏ work).

---

### Stage 4 — Shared file aggregation (sequential)

**Owner**: `orchestrator`

**Activity** sau khi N lane done Stage 7-8 độc lập:

1. Collect shared file edit từ mỗi lane (DI module, NavHost, strings.xml, AnalyticsEvent)
2. Apply merge sequential (không parallel vì cùng file):
   - Lane 1 edit `DomainModule.kt` → commit
   - Lane 2 edit cùng `DomainModule.kt` → rebase + merge
   - Repeat cho N lane
3. Build + Konsist + Detekt pass sau mỗi merge
4. Nếu conflict → raise Tech Lead decide

**Rule**: Shared file aggregation phải sequential. Parallel shared file edit → merge conflict + corruption.

---

### Stage 5 — Integration test

**Owner**: `qa` scope B

**Activity**:
1. Full E2E chạy trên build integrated
2. Regression test: feature cũ không gãy
3. Cross-feature interaction test (ví dụ login A rồi vào feature B)

**Gate**:
- PASS → GOTO Release Gate (single sign-off cho bundle)
- FAIL per feature → `bug-triage.md`, có thể rollback feature đó độc lập (dễ hơn full-flow)
- FAIL integration → merge issue, raise Tech Lead

---

### Stage 6 — Release Gate

Xem `release-gate.md`. Co-sign cho bundle (không per-feature trừ khi staged rollout per feature flag).

## Isolation safety rules

### SAFE parallel

- Owned package tuyệt đối riêng biệt
- Shared file edit = append-only (ví dụ thêm Nav route, thêm string key)
- Không share domain model class (nếu share → cần coordination)
- Resource namespace prefix riêng (`feature_login_*` vs `feature_signup_*`)

### UNSAFE — phải sequential

- Share repository, share UseCase (1 feature modify signature → feature kia break)
- Edit shared state file (ví dụ `SessionManager.kt` logic)
- Database schema migration chồng chéo
- Nav logic phức tạp (A → B hard-coded, B → C conditional)

### UNSAFE workarounds

- Nếu bắt buộc share domain → extract shared code vào Stage 1 (sequential prep), rồi N feature parallel consume
- Nếu bắt buộc edit shared logic → do one feature đi trước (sequential), N-1 feature parallel sau

## Token budget guide

| Mode | Cost multiplier vs single feature | Wall time |
|---|---|---|
| Sequential N feature | N × | N × |
| Parallel N feature (SAFE) | 1.3-1.5 × N | 1-1.5 × |
| Parallel N feature (UNSAFE) | 2 × N (lots of retry) | 1-2 × |

Rule of thumb: parallel chỉ worth khi N ≥ 3 và SAFE. N = 2 → sequential thường hiệu quả hơn.

## Anti-patterns

- Parallel 2 feature không check isolation → DI module corruption, nav route conflict
- Spawn parallel không có worktree isolation → file race
- Shared file aggregation parallel → merge conflict chaos
- Release gate per feature trong parallel bundle (nên bundle gate)
- Fast-path giữa parallel execution → không consistent, confusion
- Skip integration test vì "mỗi feature đã PASS Scope A"

## Rollback

Khi 1 feature trong bundle fail Stage 5:

1. Isolate: revert owned package + revert shared file portion của feature đó
2. Rebuild bundle without failed feature
3. Re-run Stage 5 integration
4. Release bundle N-1 feature + defer failed feature sang sprint sau

Nếu 2+ feature fail → consider revert toàn bundle, chuyển sequential cho sprint sau.

## Pair với workflow khác

- `feature-full-flow.md` — mỗi feature parallel vẫn chạy Stage 1-6 như full-flow (chỉ Stage 7-8 parallel)
- `bug-triage.md` — khi QA FAIL trong parallel lane
- `release-gate.md` — bundle sign-off cuối

## Pair với skill

- `coding-orchestrator` — spawn + merge logic
- `worktree` — git worktree management
- `harness-handoff` — context handoff giữa lanes

# feature — `--parallel`

Kick off parallel execution khi N feature độc lập cần ship cùng sprint (deadline hard + scope frozen + team capacity). Tech Lead check feasibility, Architect decompose + isolation-check, Orchestrator spawn N × (Coder + Reviewer + QA) song song, aggregate shared files sequential, release bundle gate.

> Dùng khi ≥ 2 feature đã qua Stage 1-6 độc lập. 1 feature → bỏ `--parallel` (xem `single.md`). Rule of thumb: parallel chỉ worth khi N ≥ 3 và SAFE; N = 2 thường sequential rẻ hơn.

## Inputs

Bắt buộc:
- **Feature list**: ≥ 2 feature slug, mỗi feature phải đã có `plans/<date>-<slug>/plan.md` approved
- **Target release**: version/date chung cho bundle

Optional:
- `--mode <safe|unsafe-force>`: default safe (reject nếu isolation-check fail)
- `--max-concurrent <N>`: giới hạn số lane parallel, default = số feature

## Procedure

### Step 1 — Tech Lead feasibility check

Spawn Task:

```
Role = Tech Lead. Đọc:
- agents/tech-lead.md
- agents/workflows/parallel-features.md

Features: {{feature list}}
Target release: {{date/version}}

Task:
1. Audit N feature:
   - Scope boundary (owned package, shared file)
   - Cross-feature dependency
   - Module touch
2. Estimate cost: sequential vs parallel (token + wall time)
3. Verify precondition:
   - [ ] N feature đã qua Stage 1-6 độc lập
   - [ ] Mỗi feature có plan.md + Tech Lead APPROVE
   - [ ] Owned packages không overlap
   - [ ] Shared files identified
   - [ ] Cross-dep = none (hoặc explicit sequential chain)
   - [ ] Capacity ≥ 2× token budget sequential + merge overhead

Verdict: APPROVE_PARALLEL | REJECT (go sequential)

Output: plans/reports/parallel-feasibility-{{sprint}}.md
```

Nếu REJECT → surface user, suggest chạy `/feature` (single) cho từng feature sequential.

### Step 2 — Architect spec decomposition

Spawn Task Architect spec-decomposition mode:

```
Role = Architect. Đọc agents/architect.md section "Spec decomposition".

Features approved parallel: {{list}}

Task:
1. Với mỗi feature produce `plans/<date>/plans/<feature-name>.md` (dùng plan.md có sẵn, enrich isolation info)
2. Produce `plans/<date>/isolation-check.yaml`:
   - owned_packages per feature
   - shared_files per feature (DI module, NavHost, strings.xml, AnalyticsEvent)
   - cross_dep per feature

Verification:
- Nếu 2 feature share owned_package → UNSAFE, chuyển sequential cho cặp đó
- Nếu cross_dep ≠ none → sequential cho chain
- SAFE combination → ready for parallel spawn
```

### Step 3 — Orchestrator spawn parallel

Spawn Task Orchestrator:

```
Role = Orchestrator. Đọc agents/workflows/parallel-features.md.

Isolation check: plans/<date>/isolation-check.yaml
Features SAFE for parallel: {{list sau filter}}

Task:
1. Với mỗi feature SAFE:
   - Create git worktree isolated: `.worktrees/<feature>`
   - Spawn Task subagent chain parallel: Coder → Reviewer → QA scope A
   - Mỗi lane có handoff doc riêng tại plans/handoff/<feature>/*.md
2. Monitor lane progress
3. Nếu lane fail → không ảnh hưởng lane khác, surface user

Deadline mỗi lane giữ nguyên sequential (parallel chia wall time, không chia work).
```

### Step 4 — Shared file aggregation (sequential)

Sau N lane done Stage 7-8 độc lập:

```
Role = Orchestrator (merge mode).

Task:
1. Collect shared file edit từ mỗi lane:
   - DI module (DomainModule.kt, DataModule.kt, PresenterModule.kt)
   - NavHost (AppNavHost.kt)
   - strings.xml
   - AnalyticsEvent.kt
2. Apply merge sequential (KHÔNG parallel vì cùng file):
   - Lane 1 edit → commit
   - Lane 2 rebase + merge
   - Repeat N lane
3. Build + Konsist + Detekt pass sau mỗi merge
4. Nếu conflict → raise Tech Lead decide

Output: integrated branch sẵn sàng cho integration test.
```

### Step 5 — Integration test (QA Scope B)

Spawn Task QA scope B:

```
Role = QA scope B. Full-flow E2E trên build integrated.

Task:
1. Full E2E test
2. Regression test (feature cũ không gãy)
3. Cross-feature interaction test (ví dụ login A rồi vào feature B)

Verdict:
- PASS → GOTO Release Gate
- FAIL per feature → /bug --mode triage, có thể rollback feature đó độc lập
- FAIL integration → merge issue, raise Tech Lead
```

### Step 6 — Release bundle gate

Trigger skill `release` với `--features <list>`.

Co-sign cho bundle (không per-feature trừ khi staged rollout per feature flag).

## Isolation safety rules

### SAFE parallel

- Owned package tuyệt đối riêng biệt
- Shared file edit = append-only (thêm Nav route, string key)
- Không share domain model class
- Resource namespace prefix riêng (`feature_login_*` vs `feature_signup_*`)

### UNSAFE — phải sequential

- Share repository, share UseCase (1 feature modify signature → feature kia break)
- Edit shared state file (`SessionManager.kt`)
- Database schema migration chồng chéo
- Nav logic phức tạp (A → B hard-coded, B → C conditional)

### UNSAFE workarounds

- Nếu bắt buộc share domain → extract shared code vào Stage 1 (sequential prep), rồi N feature parallel consume
- Nếu bắt buộc edit shared logic → 1 feature đi trước (sequential), N-1 feature parallel sau

## Pre-flight check

- [ ] ≥ 2 feature trong list
- [ ] Mỗi feature đã có plan.md + Tech Lead APPROVE
- [ ] Git worktree support available (git version ≥ 2.5)
- [ ] Disk space đủ cho N worktree
- [ ] Token budget ≥ 1.5 × N × single-feature-cost

## Token budget guide

| Mode | Cost multiplier vs single | Wall time |
|---|---|---|
| Sequential N feature | N × | N × |
| Parallel N feature (SAFE) | 1.3-1.5 × N | 1-1.5 × |
| Parallel N feature (UNSAFE) | 2 × N (lots of retry) | 1-2 × |

Rule of thumb: parallel chỉ worth khi N ≥ 3 và SAFE. N = 2 → sequential thường hiệu quả hơn.

## Rollback

Khi 1 feature trong bundle fail Stage 5:

1. Isolate: revert owned package + revert shared file portion của feature đó
2. Rebuild bundle without failed feature
3. Re-run Stage 5 integration
4. Release bundle N-1 feature + defer failed feature sang sprint sau

Nếu 2+ feature fail → consider revert toàn bundle, chuyển sequential.

## Khi NÀO không dùng mode này

- N = 1 feature → bỏ `--parallel` (single)
- Features chưa plan → chạy `/feature` (single) cho từng feature trước
- Features có cross-dep heavy → sequential thường rẻ hơn + ít rủi ro
- Deadline flexible → không cần parallel

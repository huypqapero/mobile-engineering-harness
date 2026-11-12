# bug — `--mode fix` (default)

Kick off bugfix-fast-path pipeline. Tech Lead triage check 4 fast-path conditions, route fast-path (3 stage, 1-4h) / mini-plan (4 stage) / full-flow (fallback). Dành cho bug mới chưa classify, mặc định thử fast-path trước.

> Dùng mode này khi: bug mới có evidence, chưa biết loại. Nếu đã biết là design/spec bug, hoặc fast-path đã fail cần re-classify → `--mode triage` (xem `mode-triage.md`).

## Inputs

Bắt buộc:
- **Bug description**: symptom + repro steps
- **Evidence**: screenshot / logcat / crash log / Sentry link

Optional:
- `--id <BUG-xxx>`: bug tracker ID (Linear/Jira/GitHub Issue)
- `--severity <BLOCKER|HIGH|MEDIUM|LOW>`: default HIGH
- `--affected-screen <name>`: screen bị impact (giúp Tech Lead scout nhanh)

## Procedure

### Step 1 — Tech Lead triage

Spawn Task:

```
Role = Tech Lead. Đọc:
- agents/tech-lead.md (Step 7 Bug triage)
- agents/workflows/bugfix-fast-path.md
- agents/workflows/bug-triage.md (classification rules)

Bug:
- Description: {{bug-description}}
- Evidence: {{evidence paths/links}}
- ID: {{bug-id}}
- Severity: {{severity}}

Task triage:
1. Reproduce evidence
2. Scout codebase xác định file ảnh hưởng (dùng Grep/Read, hoặc skill coding-scout nếu cần)
3. Chạy 4 điều kiện fast-path:
   - Scope ≤ 1 file presenter
   - Không touch shared file (DI, Nav, strings, Analytics, gradle)
   - Label fit (type:bugfix | type:ui-tweak | scope:single-screen)
   - No new dependency
4. Check forbidden flags: security / ADR-011 high-risk / cross-feature contract / migration
5. Verdict:
   - FAST-PATH APPROVED → Stage 2a
   - MINI-PLAN → Stage 2b (Architect shortform)
   - FULL-FLOW → chuyển qua skill `feature` với spec = bug report

Output: plans/reports/triage-bugfix-{{id}}.md với verdict + rationale + file list ước tính.
```

### Step 2a — Fast-path implement (nếu APPROVED)

Spawn Task Coder:

```
Role = Coder. Fast-path mode. Đọc agents/coder.md + triage report.

Scope cứng ≤ 1 file production code.
Task:
1. Fix root cause (không workaround che symptom)
2. Add regression test cover scenario bug
3. Smoke test local + Konsist + Detekt pre-check
4. STOP + raise nếu phát hiện phải touch file thứ 2 → quay triage mini-plan

Output: diff + regression test + brief handoff doc.
```

### Step 2b — Mini-plan (nếu MINI-PLAN)

Spawn Task Architect shortform:

```
Role = Architect, mini-plan mode. Đọc agents/architect.md + triage report.

Task: Viết mini-plan ≤ 50 lines (root cause + fix approach + files touched + risk + verification), save tại plans/<date>-<slug>/mini-plan.md.

Rồi handoff Tech Lead quick review (ADR compliance + regression coverage).
```

Sau mini-plan approved → spawn Coder theo Step 2a flow.

### Step 3 — QA Scope A verify

Spawn Task QA:

```
Role = QA scope A per-screen. Đọc agents/qa.md.

Task verify:
1. Reproduce bug trên build mới → verify fix PASS
2. Run regression test Coder viết
3. Smoke test adjacent flow để catch side-effect
4. Visual compare qua ui-judge nếu UI change

Verdict:
- PASS → close bug, update lesson-miner feed
- FAIL (retry < 3) → loop lại Coder
- FAIL (retry = 3) → auto-escalate Tech Lead (có thể design bug ẩn, chuyển `--mode triage`)
```

### Verify matrix (route theo loại bug)

Dùng chung cho single `fix` và `bug-fix` (cả mode batch lẫn note; bên đó gom thành 4 tier none/unit/preview/device). QA chọn verification + evidence **theo bản chất bug** (Tech Lead gán `bug_type` ở Step 1), không dùng 1 cách verify cho mọi loại:

| `bug_type` | Verification bắt buộc | Evidence | Công cụ |
|---|---|---|---|
| `ui` | Render + đối chiếu design gốc | screenshot / PNG | `/testing-preview` (skip nếu thiếu `android` CLI / design ref) |
| `logic` | Unit + regression test (happy + ≥1 edge) PASS | test report | `./gradlew :<module>:test` |
| `navigation` | E2E user journey | E2E report + screenshot | ARTEMIS (`artemis-android`) |
| `crash` / ANR | Reproduction/regression + log analysis | test report + logcat | ARTEMIS + `adb logcat` |
| `ads` | Test lifecycle + callback (sandbox scenario) | E2E + log + screenshot | ARTEMIS |
| `animation` | UI validation qua thời gian | video / chuỗi frame | ARTEMIS `mobile_take_screenshot` loop |

Bug lai (vd UI + logic) → chạy cả hai hàng. Verify FAIL → loop Coder (single: max 3; parallel lane: max 2) → escalate triage.

### Step 4 — Close + record

- Signoff tại `plans/reports/bugfix-signoff-{{id}}.md`
- Nếu bug thuộc class recurring → trigger `lesson-miner` ingest

## Pre-flight check

- [ ] Bug report có evidence (không chỉ "nó bị lỗi")
- [ ] Repo clean
- [ ] Branch bugfix riêng (hoặc hotfix branch)
- [ ] Có thể reproduce được local hoặc dev build

## Timing guide

| Pipeline | Agent | Typical time |
|---|---|---|
| Fast-path (≤ 1 file) | tech-lead + coder + qa | 1-4h |
| Mini-plan (2-3 files) | + architect | 4-8h |
| Full-flow (invoke `feature`) | 7+ agent | days |

## Khi NÀO không dùng mode này

- Feature mới không phải fix → dùng `/feature`
- Chỉ triage không fix → dùng tech-lead agent standalone
- Đã biết design/spec bug → `--mode triage`
- Spec gap → chuyển product-analyst update PRD trước

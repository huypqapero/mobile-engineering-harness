# Workflow: Bugfix Fast-path

Pipeline rút gọn cho bugfix nhỏ. Skip Product/PM/Designer/Tech-Lead-review khi thỏa 4 điều kiện fast-path.

## Trigger

- Bug reported (user, QA, monitoring, lesson-miner)
- Scope nghi ngờ nhỏ, cần Tech Lead xác nhận

## Diagram

```
                  Bug report
                       │
                       ▼
                  tech-lead  ── triage
                       │
            ┌──────────┼──────────┐
            │          │          │
    4 cond MATCH   partial     NO match
            │          │          │
            ▼          ▼          ▼
       Fast-path   Mini-plan   Full flow
            │          │          │
            │          ▼          └──► feature-full-flow.md
            │     architect
            │     (shortform)
            │          │
            │          ▼
            │     tech-lead review
            │          │
            └──────┬───┘
                   │
                   ▼
                 coder
                   │
                   ▼
                 qa
                   │
          ┌────────┼────────┐
          │                 │
         PASS              FAIL
          │                 │
          ▼                 ▼
        close           bug-triage.md
```

## 4 điều kiện fast-path (AND)

Tech Lead approve fast-path **CHỈ KHI** cả 4 PASS:

1. **Scope ≤ 1 file touch** trong presenter layer. Không touch domain contract, không touch repository method signature.
2. **Không touch shared file**: không chạm `AppNavHost.kt`, `*Module.kt` (DI), `strings.xml`, `AnalyticsEvent.kt`, module `build.gradle.kts`.
3. **Label match**: task có label `type:bugfix` hoặc `type:ui-tweak` hoặc `scope:single-screen`.
4. **No new dependency**: không add SDK mới, không add expect/actual, không data migration.

**Cấm fast-path ngay cả khi 4 match** nếu:
- Diff liên quan security (auth, encryption, token handling)
- ADR-011 flag change (high-risk per constitution)
- Cross-feature contract change (feature A đổi state ảnh hưởng feature B subscribe)
- Migration (schema, data, user data)

## Stage sequence

### Stage 1 — Bug intake (Tech Lead)

**Input**: Bug report (bất kể nguồn: user, QA, monitoring, lesson-miner)

**Activity**:
1. Đọc report + reproduce evidence
2. Scout codebase xác định file ảnh hưởng (dùng skill `coding-scout` nếu cần)
3. Chạy 4 điều kiện check
4. Verdict:
   - **FAST-PATH APPROVED**: 4 điều kiện match, không có forbidden flag
   - **MINI-PLAN**: Scope lớn hơn 1 file nhưng vẫn < full feature, dùng Architect shortform
   - **FULL-FLOW**: Scope rộng → chuyển `feature-full-flow.md`

**Output**: `plans/reports/triage-bugfix-<id>.md` ghi verdict + rationale

---

### Stage 2a — Fast-path implement (Coder)

**Chỉ khi FAST-PATH APPROVED**

**Owner**: `coder`

**Input**: Bug report + Tech Lead note xác định file + root cause

**Activity**:
1. Fix root cause (không workaround che symptom)
2. Add regression test cover scenario bug
3. Smoke test local
4. Konsist + Detekt pre-check

**Output**: Code change + regression test + handoff doc

**Rules**:
- Scope cứng ≤ 1 file production code
- Nếu thấy phải touch file thứ 2 → stop, raise Tech Lead → mini-plan hoặc full-flow
- Không "while I'm here let me also refactor..."

---

### Stage 2b — Mini-plan (Architect shortform)

**Chỉ khi MINI-PLAN**

**Owner**: `architect`

**Input**: Bug report + Tech Lead note scope

**Activity**: Viết mini-plan ≤ 50 lines, không full architecture section:

```markdown
# Mini-plan: fix <bug id>

## Root cause
<1-2 câu>

## Fix approach
<1-2 câu>

## Files touched
- <file 1> (modify)
- <file 2> (modify)

## Risk + mitigation
- <risk>

## Verification
- Regression test: <scenario>
- Konsist rule check: <id>
```

**Output**: `plans/<date>-<slug>/mini-plan.md`

**Handoff**: Tech Lead quick review (checklist rút gọn: ADR compliance + regression test cover) → Coder

---

### Stage 3 — Verify (QA Scope A)

**Owner**: `qa` scope A per-screen

**Activity**:
1. Reproduce bug trên build mới → verify fix PASS
2. Run regression test
3. Smoke test adjacent flow để catch side-effect
4. Visual compare qua `ui-judge` nếu UI change

**Gate**:
- PASS → close bug, update lesson-miner feed
- FAIL → GOTO `bug-triage.md`

**Max retry**: cùng signature fail 3 lần → auto escalate Tech Lead, phân loại lại (có thể design bug ẩn)

---

### Stage 4 — Close + record

**Owner**: `tech-lead`

**Activity**:
1. Record signoff tại `plans/reports/bugfix-signoff-<id>.md`
2. Trigger `lesson-miner` ingest nếu bug thuộc class recurring
3. Nếu fast-path count tăng cho module nào đó → PM review potential refactor backlog

## So sánh thời gian

| Pipeline | Stage count | Agent involved | Typical time |
|---|---|---|---|
| Fast-path | 3 stage | tech-lead + coder + qa | 1-4h |
| Mini-plan | 4 stage | + architect | 4-8h |
| Full-flow | 8 stage | 7+ agent | days-weeks |

## Khi fast-path hoạt động sai

### Signal

- QA FAIL retry 3 lần → có thể design bug, không phải code bug
- Fix patch 1 bug nhưng gây regression khác → scope không isolate
- Coder phải touch file thứ 2 giữa chừng → 4 điều kiện sai

### Response

- Rollback fast-path attempt
- Escalate Tech Lead triage lại, chuyển mini-plan hoặc full-flow
- Update `plans/reports/triage-bugfix-<id>.md` với lesson "fast-path mis-triage"

## Anti-patterns

- Tech Lead approve fast-path không run 4-điều-kiện check ("chắc nhỏ thôi")
- Coder expand scope giữa chừng không raise Tech Lead
- QA skip regression test vì "fix 1 dòng không hỏng gì"
- Skip visual compare khi diff touch UI
- Workaround che symptom thay vì fix root cause ("add try-catch là xong")

## Pair với workflow khác

- `feature-full-flow.md` — khi scope không fit fast-path
- `bug-triage.md` — khi QA FAIL
- `release-gate.md` — bugfix critical cần hotfix release

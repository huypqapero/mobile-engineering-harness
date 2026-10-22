# Workflow: Release Gate

Co-sign flow giữa Tech Lead + PM trước khi feature/version được release ra production. Last defense gate.

## Trigger

- Feature complete tất cả stage của `feature-full-flow.md`
- Bugfix critical cần hotfix
- Scheduled release theo sprint cadence

## Diagram

```
Feature xong Stage 8                 Release schedule
         │                                   │
         └─────────────┬─────────────────────┘
                       │
                       ▼
              Collect evidence
                       │
          ┌────────────┼────────────┐
          │                         │
    Tech side check            Business side check
          │                         │
          ▼                         ▼
     tech-lead                 project-manager
          │                         │
    ┌─────┼─────┐            ┌──────┼──────┐
    │     │     │            │             │
   OK   WARN  FAIL          OK           FAIL
    │     │     │            │             │
    │     │     └──block─────┼─────────────┘
    │     │                  │
    │     └── fix minor ──┐  │
    │                     │  │
    ▼                     ▼  ▼
Signoff  ◄─────────── Co-sign
    │
    ▼
Release trigger
    │
    ▼
Post-release monitor
    │
    ▼
Lesson feedback
```

## 2 side check

### Tech side (Tech Lead sign)

Checklist:

- [ ] **Build**: `./gradlew :<app-module>:assembleRelease` PASS
- [ ] **Konsist**: `./gradlew konsistTest` PASS, 0 violation
- [ ] **Detekt**: `./gradlew detekt` PASS, no new issue
- [ ] **Unit test**: all PASS, no `@Ignore` sneak in
- [ ] **Integration test**: all PASS (nếu có)
- [ ] **Reviewer verdict**: APPROVE (không chấp nhận APPROVE_WITH_CHANGES unresolved)
- [ ] **QA Scope A**: PASS mọi screen touched
- [ ] **QA Scope B**: PASS full-flow + regression
- [ ] **No open BLOCKER** trong bug tracker cho release này
- [ ] **No new ADR violation**
- [ ] **Performance baseline**: startup time, memory, APK size không degrade > threshold
- [ ] **ProGuard/R8**: shrink/obfuscation config verified
- [ ] **Signing**: production keystore ready, cert không expire
- [ ] **Crashlytics/monitoring**: version mapping uploaded

**Output**: `plans/reports/tech-signoff-<version>.md`

### Business side (PM sign)

Checklist:

- [ ] **Acceptance criteria**: toàn bộ AC trong PRD đạt (reference `briefs/<slug>/acceptance-criteria.md`)
- [ ] **Scope**: feature frozen, không CR pending ảnh hưởng
- [ ] **Release window**: match marketing campaign hoặc platform policy
- [ ] **Rollout strategy**: % staged rollout defined (ví dụ 10% → 50% → 100%)
- [ ] **Rollback plan**: điều kiện rollback + process rõ
- [ ] **Marketing**: launch material ready (nếu có)
- [ ] **Support team briefed**: FAQ, known issue, user-facing changelog
- [ ] **Analytics tracking**: events verified in staging
- [ ] **Legal/compliance**: privacy policy update (nếu feature touch user data), T&C
- [ ] **Localization**: strings dịch đủ ngôn ngữ target
- [ ] **Platform policy**: review guideline, age rating, permission disclosure

**Output**: `plans/reports/business-signoff-<version>.md`

## Co-sign document

`plans/reports/release-readiness-<version>.md`:

```markdown
# Release Readiness — v<X.Y.Z>

## Version
- Code: <git sha>
- Build: <build number>
- Branch: release/<X.Y.Z>

## Tech Lead signoff
- Signed: YYYY-MM-DD HH:MM
- Report: plans/reports/tech-signoff-<version>.md
- Verdict: READY | READY_WITH_WARNINGS | NOT_READY
- Open items (nếu WARNINGS): <list>

## PM signoff
- Signed: YYYY-MM-DD HH:MM
- Report: plans/reports/business-signoff-<version>.md
- Verdict: READY | READY_WITH_WARNINGS | NOT_READY

## Decision
- RELEASE | HOLD | ROLLBACK

## Rollout plan
- Phase 1: 10% at <date>
- Phase 2: 50% at <date>
- Phase 3: 100% at <date>

## Rollback trigger
- Crash rate > 0.5% (baseline + 0.3%)
- ANR rate > 0.2%
- Critical bug class escalated to BLOCKER

## Post-release monitoring plan
- Owner: <who>
- Dashboard: <link>
- Review at: 24h / 72h / 7d
```

## Decision matrix

| Tech | PM | Decision |
|---|---|---|
| READY | READY | RELEASE |
| READY | READY_WITH_WARNINGS | RELEASE (log warning) |
| READY_WITH_WARNINGS | READY | RELEASE (fix warning in next cycle) |
| READY_WITH_WARNINGS | READY_WITH_WARNINGS | HOLD, discuss |
| NOT_READY | * | HOLD, address block |
| * | NOT_READY | HOLD, address block |

Không có bypass. Không có "ship rồi fix hotfix sau" trừ khi stakeholder override (phải log + justify).

## Rollback flow

Nếu post-release monitor trigger rollback:

1. PM thông báo stakeholder
2. Tech Lead revert deploy (store console hoặc feature flag kill switch)
3. Open P0 bug với evidence (crash log, metric chart)
4. Chạy `bug-triage.md` để classify + fix
5. Re-release qua gate này

## Post-release feedback

Sau 7 ngày release stable:

1. **Metric audit** (PM): adoption, engagement, business metric match forecast?
2. **Technical audit** (Tech Lead): crash rate, ANR, perf regression?
3. **Lesson ingest** (`lesson-miner`):
   - Bug class post-release → rule mới cho pre-release gate
   - Metric miss expectation → calibrate feasibility scoring của PM
4. **Changelog + release note** (`ak-sumup` hoặc manual)

## Anti-patterns

- Tech Lead ký ngay cả khi QA Scope B chưa chạy
- PM ký với scope không khớp PRD ("close enough")
- "Hotfix sau" strategy khi bug thực tế BLOCKER
- Rollback trigger không define → không ai biết khi nào rollback
- Rollout 100% ngay không staged (trừ hotfix critical)
- Post-release không monitor → bug reach user mà team không biết

## Pair với workflow khác

- `feature-full-flow.md` Stage 9 — gate này là Stage 9
- `bug-triage.md` — khi phát hiện bug tại gate hoặc post-release
- `parallel-features.md` — khi release bundle nhiều feature, gate chung

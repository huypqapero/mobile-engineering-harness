---
name: release
description: Kick off release-gate workflow. Tech Lead chạy 14-item tech checklist (build, Konsist, Detekt, test, reviewer verdict, QA scope A+B, performance baseline, signing, monitoring), PM chạy 12-item business checklist (AC, scope frozen, release window, rollout plan, rollback trigger, marketing, legal, localization). Co-sign file release-readiness-<version>.md.
priority: P0
---

# Skill: release

Thin wrapper invoke release co-sign gate qua Tech Lead + PM, không spawn implementation agent.

## Trigger

- "Release v<X.Y.Z>" / "Ship version X"
- "Chuẩn bị release" / "Phát hành phiên bản X"
- Feature complete tất cả Stage 1-8 của feature-full-flow
- Hotfix critical cần production
- Scheduled sprint release

## Inputs

Bắt buộc:
- **Version**: semver `vX.Y.Z` hoặc build number
- **Branch**: release/<version> hoặc hotfix/<version>

Optional:
- `--features <list>`: list feature slug trong release (nếu bundle)
- `--rollout <staged|full>`: default staged (10% → 50% → 100%)
- `--target-date <YYYY-MM-DD>`: release window
- `--rollback-trigger <path>`: file define rollback condition (crash rate, ANR rate)

## Procedure

### Step 1 — Collect evidence

Spawn Task Tech Lead đầu tiên, chạy aggregate evidence:

```
Role = Tech Lead. Đọc agents/workflows/release-gate.md.

Version: {{version}}
Branch: {{branch}}
Features in release: {{features list}}

Task:
1. Collect git log release/<prev> ... release/<current>
2. List PR merged, feature slug, bugfix included
3. Save intermediate tại plans/reports/release-evidence-{{version}}.md

KHÔNG ký release ở step này.
```

### Step 2 — Tech side checklist

Spawn Task Tech Lead:

```
Role = Tech Lead. Chạy 14-item tech checklist tại agents/workflows/release-gate.md section "Tech side":

- [ ] Build release pass
- [ ] Konsist pass 0 violation
- [ ] Detekt pass no new issue
- [ ] Unit test all PASS, no @Ignore sneak in
- [ ] Integration test all PASS
- [ ] Reviewer verdict APPROVE (không chấp APPROVE_WITH_CHANGES unresolved)
- [ ] QA Scope A pass mọi screen touched
- [ ] QA Scope B pass full-flow + regression
- [ ] No open BLOCKER trong bug tracker
- [ ] No new ADR violation
- [ ] Performance baseline (startup, memory, APK size) không degrade > threshold
- [ ] ProGuard/R8 config verified
- [ ] Signing: production keystore ready, cert không expire
- [ ] Crashlytics/monitoring version mapping uploaded

Verdict: READY | READY_WITH_WARNINGS | NOT_READY
Output: plans/reports/tech-signoff-{{version}}.md
```

### Step 3 — Business side checklist

Spawn Task PM:

```
Role = Project Manager. Chạy 12-item business checklist tại agents/workflows/release-gate.md section "Business side":

- [ ] AC toàn PRD đạt (reference briefs/*/acceptance-criteria.md)
- [ ] Scope frozen, no CR pending
- [ ] Release window match marketing/platform policy
- [ ] Rollout strategy defined (% staged)
- [ ] Rollback plan + trigger rõ
- [ ] Marketing material ready
- [ ] Support team briefed (FAQ + known issue + user-facing changelog)
- [ ] Analytics tracking verified staging
- [ ] Legal/compliance (privacy policy update nếu feature touch user data)
- [ ] Localization strings đủ ngôn ngữ target
- [ ] Platform policy (review guideline, age rating, permission disclosure)
- [ ] Launch dependency clear

Verdict: READY | READY_WITH_WARNINGS | NOT_READY
Output: plans/reports/business-signoff-{{version}}.md
```

### Step 4 — Co-sign decision

Apply decision matrix:

| Tech | PM | Decision |
|---|---|---|
| READY | READY | RELEASE |
| READY | READY_WITH_WARNINGS | RELEASE (log warning) |
| READY_WITH_WARNINGS | READY | RELEASE (fix warning next cycle) |
| READY_WITH_WARNINGS | READY_WITH_WARNINGS | HOLD, discuss |
| NOT_READY | * | HOLD, address block |
| * | NOT_READY | HOLD, address block |

**Không có bypass**. Không có "ship rồi fix hotfix sau".

Save co-sign file `plans/reports/release-readiness-{{version}}.md` với 2 signature + decision + rollout plan + rollback trigger + post-release monitoring plan.

### Step 5 — Trigger release (ngoài agent)

Nếu RELEASE:
- Build release APK/AAB
- Upload Firebase App Distribution hoặc Play Store internal track
- Staged rollout theo plan

Nếu HOLD:
- Surface block cho user
- Open blocker ticket
- Re-run skill này sau khi block resolved

### Step 6 — Post-release monitoring

Setup 24h / 72h / 7d review:
- Owner: Tech Lead (crash/ANR), PM (adoption/metric)
- Dashboard link trong release-readiness file
- Trigger rollback nếu metric crossing threshold

Sau 7 ngày stable → ingest lesson qua `lesson-miner`.

## Pre-flight check

- [ ] Feature tất cả merged vào release branch
- [ ] CI pipeline xanh trên release branch
- [ ] QA Scope B đã chạy ít nhất 1 lần đầy đủ
- [ ] Marketing + support stakeholder biết release window
- [ ] Rollback plan có owner

## Pair với skill khác

- `feature` — khi feature chưa qua Stage 8, skill `release` sẽ reject
- `bugfix` — hotfix flow kick off bugfix, rồi gọi `release` cho hotfix version
- `bug-triage` — khi release gate phát hiện bug critical cuối phút

## Khi NÀO không dùng skill này

- Feature chưa complete Stage 1-8 → chạy `feature` trước
- Chỉ cần build APK không release → gọi gradle task hoặc `tera-distribute` skill (nếu có)
- Internal dev build → không cần full release gate, dùng `tera-distribute` distribute Firebase cho tester

## Rollback flow

Nếu post-release trigger rollback:

1. PM thông báo stakeholder
2. Tech Lead revert deploy (store console hoặc feature flag kill switch)
3. Open P0 bug với evidence (crash log + metric chart)
4. Chạy `bug-triage` để classify
5. Fix → chạy `release` cho hotfix version

Nếu 2+ feature trong bundle fail → consider revert toàn bundle, chuyển sequential sprint sau.

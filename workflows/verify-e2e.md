# Workflow: Verify E2E

Regression test full pipeline của harness qua fixtures. Hybrid validation (golden snapshot structural + semantic assertion content quality). Bash orchestrator + Python validators. Không spawn agent — chỉ verify artifact đã produce.

## Entry conditions

- Repo tại `mobile-engineering-harness/` (hoặc downstream product consume harness)
- Python 3 + `pyyaml` + `jsonschema` installed
- Fixture tồn tại trong `verification/e2e/fixtures/<slug>/`

## Input artifacts

- Fixture bundle: `config.yaml` + `input/` + `expected/`
- Agent-produced output: `actual/` (optional — nếu chưa có, skip stages tương ứng)
- Schema: `verification/brief-schema/brief.schema.json`

## Stages

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  1. BRIEF    │───▶│   2. PLAN    │───▶│   3. CODE    │───▶│  4. GATES    │───▶│  5. REPORT   │
│   validate   │    │   validate   │    │  dry Konsist │    │ cross-ref +  │    │  consolidate │
│   schema +   │    │   contract + │    │   static     │    │  checksums   │    │              │
│   semantic + │    │  structural  │    │              │    │              │    │              │
│   golden     │    │              │    │              │    │              │    │              │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
     exit 1              exit 2              exit 3              exit 4              exit 5
```

Stage 2, 3 skip tự động nếu fixture không có `actual/plan.yaml` hoặc `actual/code/`. Stage 1, 4 bắt buộc.

---

## Stage 1 — Brief validation

### Actions

1. Load `actual/brief.yaml`
2. Validate schema (`brief.schema.json`) — Draft 2020-12 JSON schema
3. Apply semantic rules từ `expected/brief.semantics.yaml`:
   - min_confirmed_requirements, max_blocker_issues, max_unresolved_requirements
   - min_acceptance_criteria, required_requirement_types
   - all_ac_bind_confirmed, all_requirements_have_source, components_ambiguous_resolved
4. Diff với `expected/brief.golden.yaml` — ignore noise fields (timestamps, checksums)

### Completion criteria

- Schema errors = 0
- Semantic failures = 0
- Golden drift = 0 (hoặc intentional + regenerate với `--update-golden`)

### Blocker conditions

- Schema fail → rc=1
- Semantic fail → rc=2
- Golden drift → rc=20 (acceptable khi intentional)

---

## Stage 2 — Plan validation (optional)

### Actions

1. Nếu `actual/plan.yaml` tồn tại:
2. Validate task-contract required fields (id, type, goal, acceptance_criteria)
3. Match với `expected/plan.structure.yaml`:
   - Expected files subset trong plan.files
   - Required scope modules present
   - brief_id reference back tới Feature Brief

### Skip condition

- `actual/plan.yaml` không tồn tại → skip (fixture không require plan check)

---

## Stage 3 — Code structure (optional, dry Konsist)

### Actions

1. Nếu `actual/code/` tồn tại:
2. Verify `expected_files` present
3. Scan `forbidden_patterns` (regex) qua glob — fail nếu match
4. Scan `required_patterns` qua specific file — fail nếu không match
5. Static only, không spawn Gradle/Konsist thật

### Rules enforced (từ `expected/code.konsist.expected.yaml`)

- ARCH-001: domain không import android/compose
- ARCH-002: presenter không import data impl
- ARCH-003: ViewModel extend BaseViewModel
- ARCH-004: Repository impl không kế thừa BaseRepository
- ARCH-005: Mapper object + extensions
- ARCH-007: MVI Intent sealed

### Skip condition

- `actual/code/` không tồn tại → skip

---

## Stage 4 — Gates (cross-reference)

### Actions

1. brief.yaml readable + non-empty
2. Mọi `sources[].path` resolve về file trong `actual/assets/sources/`
3. Mọi `issues[].affected_requirements` resolve về `requirements[].id`

### Completion criteria

- 0 broken reference
- 0 orphan issue

---

## Stage 5 — Report

### Actions

1. Collect stage results từ temporary YAML
2. Compute overall status (PASS / PARTIAL / FAIL)
3. Build markdown report tại `verification/e2e/reports/e2e-{date}-{fixture}.md`
4. Include stage breakdown table + failure details + open issues

---

## Fix loop

Nếu stage fail:

- **Stage 1 schema fail**: brief.yaml không đủ required fields. Fix brief generator hoặc update fixture expected.
- **Stage 1 semantic fail**: brief content quality thấp (missing REQ types, blocker count exceed). Agent re-run hoặc adjust `brief.semantics.yaml` nếu rule quá strict.
- **Stage 1 golden drift**: harness thay đổi làm output format đổi. 2 options:
  1. Harness bug: fix skill/schema restore baseline
  2. Intentional change: run `--update-golden` + review diff + commit new golden
- **Stage 2 structure mismatch**: plan thiếu scope module hoặc file list. Check `architect` role output.
- **Stage 3 code violation**: Konsist pattern vi phạm (import android trong domain). Fix code hoặc update expected rule.
- **Stage 4 broken reference**: `sources[].path` không có file snapshot. Fetch adapter miss file.

Max 3 iteration fix cho cùng stage; sau 3 lần fail → report BLOCKED, human intervention required.

---

## Rollback

E2e không mutate harness source. Rollback = reset `fixtures/<slug>/actual/` + `reports/`:

```bash
rm -rf verification/e2e/fixtures/<slug>/actual
rm verification/e2e/reports/e2e-*-<slug>.md
```

Nếu `--update-golden` ghi sai golden:

```bash
git checkout verification/e2e/fixtures/<slug>/expected/brief.golden.yaml
```

---

## Report format

Mỗi run produce markdown tại `verification/e2e/reports/`:

```markdown
# E2E Report — <fixture>

Date: <ISO 8601>
Harness version: <tag or commit>
Duration: <seconds>

## Summary

Status: PASS | PARTIAL | FAIL
Stages run: N / M
Golden drift: K

## Stage breakdown

| Stage | Status | Exit code | Notes |
...

## Failure details

<if any>

## Open issues

<list>
```

---

## Agent roles

E2e là **tool-driven**, không agent-driven như các workflow khác. Guardian hoặc maintainer trigger qua CLI:

```bash
./verification/e2e/scripts/run-e2e.sh <fixture> [options]
```

Agent role optional:
- **Maintainer**: trigger e2e trước PR merge, review output
- **Guardian** (`workflows/harness-maintenance.md`): auto-trigger e2e trong `audit mode` để confirm fixtures stable sau harness change

## Downstream handoff

E2e PASS → harness release OK:
- Guardian add e2e status vào release report
- CHANGELOG mention regression count

E2e FAIL → block release:
- Fix regression trước khi tag version mới
- Hoặc update fixtures (nếu intentional breaking) với explain trong CHANGELOG

## Final output schema

```yaml
fixture: <slug>
harness_version: v0.X.Y
duration_seconds: <N>
overall_status: PASS | PARTIAL | FAIL
stages:
  - name: brief
    status: pass | fail | skip
    exit_code: <int>
    drift_count: <int>
    details: <string>
  - name: plan
    ...
```

## Anti-patterns bị cấm

- Chạy `--update-golden` trong CI auto (phải human review)
- Skip stage 1 brief validation
- Delete `expected/` artifacts để "pass" test
- Modify fixture input trong `actual/` directory
- Reuse report file (mỗi run tạo file mới với timestamp)

## Reference

- `verification/e2e/README.md` — layout + usage
- `verification/e2e/runbook.md` — detailed how-to + troubleshoot
- `verification/brief-schema/brief.schema.json` — schema
- `blueprints/task-contract/README.md` — plan contract reference

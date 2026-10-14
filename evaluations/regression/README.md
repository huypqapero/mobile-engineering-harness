# Evaluation Regression Suite

Track eval scores over time qua harness versions + model versions. Dùng để detect regression khi update rule, update model, hoặc expand harness.

## Why regression tracking

Harness evolve → risk:
- Rule mới conflict rule cũ
- Rule mới quá strict → false positive
- Model behavior drift
- Context size grow → quality drop

Regression suite = snapshot score baseline per version → compare over time.

## Setup

### Record per eval run

Mỗi lần chạy eval E01-E05 → ghi vào `regression/runs/<date>-<harness-version>-<model>.yaml`:

```yaml
# runs/2026-10-14-v0.5.0-opus-4-7.yaml
date: 2026-10-14
harness_version: v0.5.0
model: claude-opus-4-7
scenarios:
  E01:
    score: 85
    verdict: VERIFIED_WITH_LIMITATIONS
    violations:
      blocker: 0
      high: 2
      medium: 3
      low: 4
    notes: "Missed isOffline branch in error state"
  E02:
    score: 90
    verdict: VERIFIED
    findings_caught: 7
    findings_total: 8
    notes: "Missed ARCH-013 non-null assertion in mapper"
  E03:
    score: 78
    verdict: VERIFIED_WITH_LIMITATIONS
    violations:
      blocker: 0
      high: 1
      medium: 2
      low: 2
    notes: "Used flatMap instead of flatMapLatest"
```

### Baseline recording

Baseline run (no harness, same model):

```yaml
# runs/2026-10-14-baseline-opus-4-7.yaml
date: 2026-10-14
harness_version: baseline
model: claude-opus-4-7
scenarios:
  E01:
    score: 55
    verdict: NEEDS_REWORK
    violations:
      blocker: 1
      high: 4
      medium: 5
      low: 6
    notes: "Hardcoded Dispatchers.IO; expose MutableStateFlow; mapper !!"
```

## Trend analysis

Script analyze `regression/runs/*.yaml` → report:

```markdown
# Regression Report — Harness v0.3.0 → v0.5.0 (opus-4-7)

Scenario E01:
- v0.3.0: 82 (-> baseline 55 = +27)
- v0.4.0: 85
- v0.5.0: 88

Scenario E02:
- v0.3.0: 85
- v0.4.0: 90
- v0.5.0: 90

Scenario E03:
- v0.3.0: 75
- v0.4.0: 78
- v0.5.0: 82

Trend: monotonic improvement.
Alert: none.
```

Alert thresholds:
- Score drop > 10 points between consecutive version → **investigate**
- Score drop > 20 points → **block release**
- BLOCKER count tăng → **block**

## Scenarios tracked

| ID | Scenario | Dimension focus |
|---|---|---|
| E01 | Create MVI feature | Architecture + MVI + 5 states |
| E02 | Review broken PR (8 bugs) | Finding detection accuracy |
| E03 | Search debounce + cancel | Concurrency |
| E04 | Compose list optimization | Compose stability + recomposition |
| E05 | Test quality audit | Test craftsmanship |

## Model matrix

Record cho mỗi model variant quan trọng:
- `claude-opus-4-7` (current)
- `claude-sonnet-4-6` (fast tier)
- `claude-haiku-4-5` (budget tier)
- Codex / Gemini nếu dùng

So sánh cross-model → identify harness areas model nào vẫn miss.

## When to run

- **Pre-release harness**: chạy toàn bộ matrix trước tag mới
- **Monthly**: chạy lại baseline, verify model stable
- **Khi upstream rule add/change**: run E01-E05 verify không regression

## Hoãn tới khi scale

Hiện tại (v0.5.0): baseline chưa run thực tế. Regression tracking cần baseline + 2+ data point mới useful.

**Minimum viable**: 1 baseline run + 1 harness run cho E01 → prove improvement delta ≥ 30% (goal document trong `evaluations/rubrics/README.md`).

Scale sau khi:
- Harness dùng production ≥ 1 product
- Có ≥ 5 iteration (rule tune theo evidence)
- Baseline + harness mỗi scenario có ≥ 3 run avg (reduce noise)

## Report output location

```
plans/reports/eval-regression-<date>.md
```

## Reference

- `.harness/evaluations/templates/` — scenario definitions
- `.harness/evaluations/rubrics/` — scoring criteria
- `.harness/plans/` — baseline + regression run outputs per project

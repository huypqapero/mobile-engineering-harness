# E2E Runbook

How to run e2e tests, interpret output, troubleshoot failures.

## Prerequisites

### Python environment

```bash
pip3 install pyyaml jsonschema
# hoặc với venv
python3 -m venv .venv
source .venv/bin/activate
pip install pyyaml jsonschema
```

### Repo state

- E2e scripts chạy từ repo root (`mobile-engineering-harness/`)
- Fixtures tồn tại trong `verification/e2e/fixtures/`
- Scripts có execute permission (`chmod +x verification/e2e/scripts/*.sh`)

## Run modes

### Full pipeline (default)

```bash
./verification/e2e/scripts/run-e2e.sh book-detail
```

Chạy 5 stages:
1. **Brief**: validate brief package schema + semantic
2. **Plan**: validate plan artifact (nếu có)
3. **Code**: dry Konsist check (nếu có code)
4. **Gates**: cross-reference links, checksum
5. **Report**: consolidate findings

Stage 2, 3 skip tự động nếu fixture không có `expected/plan.*` hoặc `expected/code.*`.

### Specific stages

```bash
./verification/e2e/scripts/run-e2e.sh book-detail --stages 1,4
```

Chỉ chạy stage 1 (brief) + 4 (gates). Dùng khi debug.

### All fixtures

```bash
./verification/e2e/scripts/run-e2e.sh --all
```

Lặp qua mọi fixture trong `verification/e2e/fixtures/`.

### Verbose

```bash
./verification/e2e/scripts/run-e2e.sh book-detail --verbose
```

In chi tiết validator output + stage transition.

### Update golden (maintainer)

```bash
./verification/e2e/scripts/run-e2e.sh book-detail --update-golden
```

Sau intentional harness change:
1. Chạy fixture through agent manual
2. Produce output vào `briefs/<slug>/`, `plans/<date>-<slug>/`
3. Run với `--update-golden` → copy output vào `fixtures/<slug>/expected/*.golden.yaml`
4. Commit golden update với changelog note

**Cấm** auto `--update-golden` trong CI. Golden regenerate luôn human review.

## Exit codes

| Code | Meaning | Action |
|---|---|---|
| 0 | All stages pass | Celebrate |
| 1 | Stage 1 brief fail | Check brief schema + semantic validator output |
| 2 | Stage 2 plan fail | Check plan contract schema |
| 3 | Stage 3 code fail | Check Konsist dry-run output |
| 4 | Stage 4 gates fail | Check references + checksums |
| 5 | Stage 5 report fail | Rare — report builder error |
| 10 | Setup error | Deps missing, fixture path invalid |
| 20 | Golden diff | Output drift từ golden (expected khi intentional change) |

## Output

Mỗi run tạo report tại:

```
verification/e2e/reports/e2e-261016-<fixture>.md
```

Format:

```markdown
# E2E Report — <fixture-name>

Date: 2026-10-16
Harness version: v0.14.1
Duration: 12s

## Summary

Status: PASS | FAIL | PARTIAL
Stages run: 5 / 5
Golden diff: 0 drift | N drift (listed below)

## Stage breakdown

- Stage 1 Brief: PASS (12/12 semantic rules, 0 schema error)
- Stage 2 Plan: SKIP (no plan artifact)
- Stage 3 Code: SKIP (no code artifact)
- Stage 4 Gates: PASS (all references resolve)
- Stage 5 Report: PASS

## Semantic rules result

| Rule | Expected | Actual | Status |
|---|---|---|---|
| min_confirmed_requirements | ≥ 3 | 5 | PASS |
| max_blocker_issues | 0 | 0 | PASS |
| all_ac_bind_confirmed | true | true | PASS |

## Golden diff

<empty if no drift, else list field-by-field>

## Open issues

<if any, listed here>
```

## Troubleshoot

### `python3: module 'yaml' not found`

```bash
pip3 install pyyaml
```

### `jsonschema.exceptions.ValidationError`

Fixture output không match schema. Fix:
1. Check `verification/brief-schema/brief.schema.json` latest
2. Compare fixture brief.yaml fields vs schema
3. Update fixture expected hoặc report bug trong brief generator

### `Golden drift detected but intentional`

Harness change làm output format đổi:
1. Run `--update-golden`
2. Review diff trong `fixtures/<slug>/expected/*.golden.yaml`
3. Commit golden update với changelog entry explain change

### `Checksum mismatch`

Input file thay đổi sau khi fixture snapshot:
1. Check `fixtures/<slug>/input/` không bị edit tay
2. Nếu intentional update spec: recompute checksum + update brief.golden.yaml

### Stage 3 Code skip khi expected code có

Konsist tool không available:
```bash
which konsist   # should exist
# nếu không: install qua Gradle project ngoài harness
```

E2e dry-check không run Konsist thật, chỉ validate expected rule list vs actual via static parse.

## CI integration (Wave 2)

Script tương lai `/.github/workflows/e2e.yml`:

```yaml
# Reference, chưa implement v0.15.0
name: E2E Harness
on: [push, pull_request]
jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install pyyaml jsonschema
      - run: ./verification/e2e/scripts/run-e2e.sh --all
```

Secrets cho MCP (Confluence/Figma token) chỉ cần nếu fixture có remote source. Pilot `book-detail` dùng local-only.

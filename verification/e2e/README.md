# E2E Verification

Full pipeline regression test cho harness. Chạy fixtures qua các stage (brief → plan → code → verify → review) và so sánh output với golden snapshots + semantic rules.

## Mục đích

- **Regression detect**: khi harness thay đổi (skill update, schema update, workflow refactor), chạy e2e để confirm fixtures vẫn produce output expected.
- **Hybrid validation**: golden snapshot (structural: schema, file layout, field presence) + semantic assertion (content quality: REQ coverage, AC verifiability, blocker count).
- **Trusted baseline**: cung cấp fixtures làm reference cho downstream product khi onboard harness.

## Scope

E2e này **không spawn agent** — không gọi Claude Code / Codex để execute skill. Agent run là responsibility của user; e2e runner chỉ verify output artifacts:

1. **Brief package** (từ `briefs/<slug>/`) match schema + semantic rules
2. **Plan artifact** (từ `plans/<date>-<slug>/`) match task-contract schema
3. **Code structure** (dry Konsist check) — expected file list, không build full
4. **Diff với golden snapshots** — detect drift structural

Nếu user muốn test agent output thật, workflow:
1. User chạy agent với fixture input
2. Agent produce brief/plan/code vào product repo
3. E2e runner compare output với expected

## Layout

```
verification/e2e/
├── README.md                 # file này
├── runbook.md                # how to run + troubleshoot
├── scripts/
│   ├── run-e2e.sh            # orchestrator entry
│   ├── stage-1-brief.sh      # verify brief package
│   ├── stage-2-plan.sh       # verify plan artifact
│   ├── stage-3-code.sh       # dry Konsist check
│   ├── stage-4-gates.sh      # schema + reference validation
│   └── stage-5-report.sh     # consolidate report
├── validators/               # Python (pyyaml + jsonschema deps)
│   ├── validate_brief.py
│   ├── validate_plan.py
│   ├── validate_code_structure.py
│   ├── diff_golden.py
│   └── report_builder.py
├── fixtures/
│   └── book-detail/          # pilot fixture
│       ├── config.yaml       # fixture metadata
│       ├── input/            # source (spec + screenshots)
│       │   ├── spec.md
│       │   └── screenshots/
│       └── expected/         # golden + semantic
│           ├── brief.golden.yaml
│           ├── brief.semantics.yaml
│           ├── plan.structure.yaml
│           └── code.konsist.expected.yaml
└── reports/                  # e2e run output
    └── e2e-<date>-<fixture>.md
```

## Quick start

```bash
# Install deps (one-time)
pip3 install pyyaml jsonschema

# Run e2e cho 1 fixture
./verification/e2e/scripts/run-e2e.sh book-detail

# Run tất cả fixtures
./verification/e2e/scripts/run-e2e.sh --all

# Dry run (chỉ validator, không stage code)
./verification/e2e/scripts/run-e2e.sh book-detail --stages 1,2,4
```

Chi tiết: xem `runbook.md`.

## When to run

| Khi nào | Lý do |
|---|---|
| Trước release harness | Confirm fixtures still pass sau version bump |
| Sau skill update (L2) | Regression check theo Guardian workflow |
| Sau schema update | Verify golden snapshots không drift bất ngờ |
| Khi onboard product mới | Reference baseline cho team |

## Hybrid validation strategy

### Golden snapshot (structural)

Store expected output exact:
- `brief.golden.yaml` — expected brief.yaml content (frozen)
- `plan.structure.yaml` — expected file list, directory layout

Diff logic: `diff_golden.py` so sánh field-by-field, ignore timestamp + checksum (noise).

**Khi nào update golden:** sau khi harness intentional change, maintainer re-generate golden + review diff + commit.

### Semantic assertion (content quality)

Rules check runtime:
- `brief.semantics.yaml` liệt kê constraints:
  - `min_confirmed_requirements: 3`
  - `max_blocker_issues: 0`
  - `required_requirement_types: [functional, ui]`
  - `all_ac_bind_confirmed: true`
  - `components_ambiguous_resolved: true`

Validator `validate_brief.py` enforce rules. Nếu brief thay đổi structure nhưng vẫn pass semantic → OK (chỉ fail nếu nội dung quality degrade).

## Fixture design

Mỗi fixture là 1 feature mẫu đầy đủ:

- **Input**: realistic spec + screenshot (có conflict, ambiguity để test reconciliation)
- **Expected brief**: output ideal sau khi chạy `input-prepare-feature` manual bằng agent
- **Expected plan**: output ideal sau khi chạy `android-feature` planning stage
- **Expected code structure**: file list + Konsist rules dự kiến pass

Pilot `book-detail` là canonical example. Thêm fixture khác (headless feature, parallel feature, SDK extraction) khi scope mở rộng.

## Integration với Guardian

Khi Guardian run `audit mode` hoặc `evolve mode` trong `workflows/harness-maintenance.md`:

- Trigger e2e trước khi propose change
- E2e fail → Guardian document regression, không merge change
- E2e pass → Guardian regenerate golden nếu change intentional, commit vào PR

E2e là **safety net** cho Guardian self-maintenance (xem Protected Baseline rule L2+).

## Reference

- `runbook.md` — chi tiết how-to-run + exit codes + troubleshoot
- `workflows/verify-e2e.md` — workflow Guardian/maintainer trigger e2e
- `verification/brief-schema/brief.schema.json` — schema brief.yaml dùng trong validator
- `blueprints/task-contract/template.yaml` — schema plan.yaml

## Future (Wave 2+)

- Agent spawn integration (optional): e2e có thể trigger Claude Code CLI để auto-run agent + capture output
- Multi-fixture parallel run
- CI integration (GitHub Actions wrapping bash script)
- Benchmark mode: measure skill execution time + token cost per fixture

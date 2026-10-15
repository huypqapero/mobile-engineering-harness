# Feature Briefs

Output directory của input layer. Mỗi feature có 1 subfolder `briefs/<slug>/` chứa Feature Brief package.

## Layout

```
briefs/
├── README.md                       # file này
├── <feature-slug-1>/
│   ├── brief.yaml                  # manifest (schema-validated)
│   ├── requirements.md
│   ├── design.md
│   ├── acceptance-criteria.md
│   ├── issues.md
│   └── assets/
│       └── sources/
│           ├── spec.md
│           └── screenshots/
└── <feature-slug-2>/
    └── ...
```

## Lifecycle

1. **Create** — skill `input-prepare-feature` orchestrate 5-phase pipeline → populate `briefs/<slug>/`
2. **Validate** — skill `input-validate-brief` chạy 12 gates
3. **Consume** — workflow `feature-development` Stage 1 Inspect đọc làm authoritative input
4. **Immutable** — brief không edit tay sau validate. Re-generate qua `input-prepare-feature` nếu source thay đổi.

## Naming convention

- Slug: kebab-case, unique forever
- Pattern: `^[a-z0-9]+(-[a-z0-9]+)*$`
- Example: `book-detail`, `login-flow`, `payment-checkout`

## Rules

- **MUST** không commit secrets trong `assets/sources/` (filter trước khi snapshot)
- **MUST** preserve checksum match giữa `brief.yaml.sources[]` và file thật
- **MUST** không delete brief khi downstream plan đã reference (giữ traceability)
- **SHOULD** version bump brief khi source material thay đổi significantly

## Reference

- `blueprints/feature-brief/README.md` — package specification
- `workflows/prepare-feature-brief.md` — 5-phase pipeline
- `skills/input-prepare-feature/SKILL.md` — orchestrator
- `verification/brief-schema/brief.schema.json` — JSON schema

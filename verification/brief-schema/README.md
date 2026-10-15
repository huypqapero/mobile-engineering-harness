# Brief Schema

JSON schema validate cho `briefs/<slug>/brief.yaml`. Áp dụng bởi skill `input-validate-brief` tại gate CONTRACT-001.

## Files

- `brief.schema.json` — JSON Schema Draft 2020-12 definition

## Usage

### Trong skill `input-validate-brief`

```python
# Pseudo-code
import yaml, json, jsonschema

brief = yaml.safe_load(open("briefs/book-detail/brief.yaml"))
schema = json.load(open("verification/brief-schema/brief.schema.json"))

validator = jsonschema.Draft202012Validator(schema)
errors = list(validator.iter_errors(brief))

if errors:
    # Gate CONTRACT-001 FAIL
    for e in errors:
        print(f"  path={e.absolute_path}  msg={e.message}")
```

### Manual check

```bash
# Install validator
pip install check-jsonschema pyyaml

# Validate
check-jsonschema \
  --schemafile verification/brief-schema/brief.schema.json \
  briefs/book-detail/brief.yaml
```

## Key constraints enforced

### Structural

- `id` kebab-case pattern `^[a-z0-9]+(-[a-z0-9]+)*$`
- `generated_at` ISO 8601 date-time với timezone
- Required fields: id, title, version, generated_at, goal, sources, requirements, acceptance_criteria

### Semantic

- Minimum 1 spec source trong `sources.spec[]`
- Minimum 1 requirement
- Minimum 1 acceptance_criterion
- Minimum 1 requirement_ids reference trong mỗi AC
- Minimum 2 candidates trong ambiguous component

### Conditional

- Nếu `evidence_status: confirmed` → `source_references[]` BẮT BUỘC non-empty với quote field
- Checksum pattern `sha256:[0-9a-f]{64}`
- Source path phải start với `assets/sources/`

### Enum enforcement

- Requirement type: functional / non-functional / navigation / validation / ui
- Evidence status: confirmed / inferred / unresolved
- Issue severity: blocker / high / info
- Issue status: open / resolved / accepted
- Issue type: 9 giá trị enum (xem schema)
- Component type: 25 Compose primitives + custom
- Screen state: content / loading / error / empty / offline / disabled

## Updating schema

Khi harness evolve và cần field mới:

1. Update `brief.schema.json` với field + validation rule
2. Update `blueprints/feature-brief/brief.yaml.template` reflect field mới
3. Bump schema version trong `$id` (future: v2.json)
4. Guardian audit backward compat: brief v1 có load được schema v2 không?

## Future

Wave 2: thêm `profile` field cho multi-team support (consume `profiles/*.yaml`).

Wave 3: thêm `sources.figma` + `sources.repository` schema entries khi integrate Figma MCP + repo context.

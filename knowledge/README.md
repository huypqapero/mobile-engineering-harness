# Knowledge Base

7 category × 18 domain. Phân cấp 2 tầng: `knowledge/<category>/<domain>/`.

## Structure

```
knowledge/
├── coding/              Engineering layer — ngôn ngữ, framework, pattern
│   ├── compose/            Compose Multiplatform UI
│   ├── coroutines/         Async / Flow / cancellation
│   ├── mvi/                UiState + Intent + Effect
│   ├── clean-arch/         Clean Architecture + layer boundary
│   ├── patterns/           Common patterns (data class, sealed, repository)
│   └── data/               Caching, network, persistence, repository-pattern
│
├── product/             Product layer — BA, spec, wireframe
│   ├── essentials.md       Market research + wireframe + AC formula
│   └── input-analysis/     Spec extraction + reconciliation rules (5 files)
│
├── design/              Design layer — UI/UX final
│   ├── design-system/      Token, screen states, WCAG, dark mode, asset
│   └── visual-compare/     Figma vs screenshot grading
│
├── pm/                  Project management layer
│   └── essentials.md       Feasibility, deadline, scope, release
│
├── testing/             Testing layer
│   └── e2e-runtime/        Custom APK driver, device contract, step files
│
├── meta/                Meta layer — orchestrator, governance, debug loop
│   ├── agent-orchestration/   Multi-agent patterns + model-tier
│   ├── harness-governance/    Permission + ADR enforcement
│   └── auto-fix/              Error loop detection (debugging)
│
└── cross-cutting/       Cross-cutting concerns
    ├── performance/        Startup, UI, memory, network
    ├── security/           OWASP, encryption, auth
    ├── build-strategy/     Gradle, variant, build-time
    └── shared-library/     SDK publish artifact: mindset + pattern + layer + brainstorm + testing-kit + rules
```

### `shared-library/` detail (SDK knowledge set)

6 file, đọc theo thứ tự khi design SDK mới:

1. `sdk-mindset.md` — ADR SDK-001..006: SDK ≠ feature module, 3 guarantee, anti-pattern
2. `pattern-catalog.md` — design pattern canonical ↔ component ↔ ref SDK (OkHttp/Retrofit/Firebase/...)
3. `layered-architecture.md` — 5-layer kernel-plugin, 3 SPI mandatory, Konsist enforcement
4. `brainstorm-process.md` — Phase 0 top-down 10-step, use case matrix 3-axis, straw-man rule
5. `testing-kit-rules.md` — `:lib-testing` artifact mandatory, fake/driver/assertion spec
6. `essentials.md` — rule checklist cứng (LIB-SCOPE/API/CONFIG/PORT/DEP/PATTERN/PUBLISH/GOV)

## Category routing

Agent nào consume knowledge category nào:

| Category | Agent chính consume |
|---|---|
| `coding/` | `coder`, `architect`, `reviewer`, `qa`, `tech-lead` |
| `product/` | `product-analyst`, `tech-lead` (upstream input) |
| `design/` | `designer`, `ui-judge`, `qa` (visual) |
| `pm/` | `project-manager`, `tech-lead` (release co-sign) |
| `testing/` | `qa`, `e2e-author`, `coder` (regression) |
| `meta/` | `orchestrator`, `harness-guardian`, `tech-lead` (triage) |
| `cross-cutting/` | Mọi agent khi touch non-functional concern |

## Lookup pattern

### 1. Agent → knowledge
Mỗi agent `.md` có section `## Pair với knowledge` liệt kê file reference. Load khi task yêu cầu, không load mặc định (token efficient).

### 2. Skill → knowledge
Mỗi `skills/<name>/SKILL.md` reference knowledge trong workflow steps. Thin wrapper (`feature`, `bugfix`, ...) delegate transitive qua agent.

### 3. Workflow → knowledge
`agents/workflows/*.md` reference knowledge trong stage context, agent spawn tự load.

## File naming convention

- `essentials.md` — nội dung core của domain (default)
- `<rule-family>-rules.md` — khi có rule set lớn với ID pattern (REQ-RULE-001...)
- `<pattern>.md` — khi domain có nhiều pattern tách biệt (ví dụ `data/caching.md`, `data/network.md`)
- Flat structure (1 file) nếu domain < 300 lines
- Split theo sub-domain nếu > 500 lines

## Dependency version

- Last structure refactor: 2026-10-22 (harness v0.21.x)
- Previous flat structure: deprecated, không tồn tại active reference

## Add domain mới

1. Chọn category phù hợp (hoặc tạo category mới nếu không fit — hiếm)
2. Tạo folder `knowledge/<category>/<domain>/`
3. Viết `essentials.md` (< 300 lines, 10 section max)
4. Update index này
5. Update agent có liên quan section "Pair với knowledge"
6. Review heuristic size: nếu > 500 lines → split sub-domain file

## Anti-patterns

- Flat domain top-level (bypass category) → KHÔNG, phải nằm trong 1 category
- Duplicate content giữa 2 category (ví dụ MVI patterns trong cả `coding/` và `patterns/`) → KHÔNG, pick one
- `essentials.md` > 500 lines không split → KHÔNG, phình gây token overhead
- Reference knowledge path không có trailing slash hoặc inconsistent format → verify batch sau refactor

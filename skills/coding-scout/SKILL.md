---
name: coding-scout
description: Fast codebase scouting cho Android/KMP project — tìm file liên quan, trace cross-module relationship, summarize implementation context. Dùng trước khi plan/implement/review để agent không guess cấu trúc code. Trigger khi task hỏi "file nào", "ở đâu", "làm sao thấy", "có bao nhiêu caller", hoặc trước khi touch cross-module.
priority: P1
---

# Skill: coding-scout

Fast read-only codebase discovery. Trả về file paths + relationships + brief summary, không mở full file content. Ưu tiên native tools (Glob + Grep + Read specific lines) over spawn agent.

## Trigger

- "Tìm chỗ handle X trong codebase"
- "File nào gọi hàm Y"
- "Ở đâu định nghĩa Z"
- "Có bao nhiêu nơi dùng Repository/UseCase này"
- Trước khi plan feature cross-module (biết file sẽ touch)
- Trước khi refactor (biết blast radius)
- Trước khi review PR (biết context xung quanh diff)

## Inputs

Bắt buộc:
- Target: symbol name, concept, feature slug, hoặc file pattern
- Scope hint (optional): module (`{{MODULE_APP}}` / `{{MODULE_PRESENTER}}` / `{{MODULE_DOMAIN}}` / `{{MODULE_DATA}}`), package path, hoặc "full repo"

Optional:
- `--depth: shallow|full` (default: shallow — chỉ file list; `full` — read snippet mỗi file)
- `--trace: callers|callees|both` (default: callees)
- `--out: md|json` (default: md inline)

## Prerequisites

- Project đã clone, index khả dụng
- Nếu dùng semantic search: `knowledge/coding/clean-arch/*` cho layer boundary context

## Execution procedure

### Step 1 — Classify target type

| Target | Approach |
|---|---|
| Class/function name | Grep `class X` / `fun X` + find usages |
| File pattern | Glob `**/*.kt` filtered |
| Feature slug | Glob `**/features/<slug>/**` |
| Concept (e.g. "offline-first") | Grep keywords + knowledge/ cross-ref |

### Step 2 — Parallel search

**Rule:** chạy Glob + Grep + Read parallel trong 1 tool-call batch khi independent.

```
# Example: scout "BookRepository"
parallel:
  - Glob: "**/BookRepository.kt"           → file definitions
  - Glob: "**/BookRepositoryImpl.kt"       → impl files
  - Grep: "BookRepository" --files-with-matches  → all callers
  - Grep: "class.*BookRepository" -A 5     → class signatures
```

### Step 3 — Layer classify

Mỗi file match → gán layer theo path convention:

| Path pattern | Layer |
|---|---|
| `{{MODULE_DOMAIN}}/**/*.kt` | domain |
| `{{MODULE_DATA}}/**/*.kt` | data |
| `{{MODULE_PRESENTER}}/.../viewmodel/**` | presenter (VM) |
| `{{MODULE_PRESENTER}}/.../ui/**` | presenter (UI) |
| `{{MODULE_APP}}/**/di/**` | app (DI wiring) |
| `**/test/**` hoặc `**/*Test.kt` | test |

Flag violation nếu detect: domain import Android/iOS/Firebase (xem `knowledge/coding/clean-arch/*`).

### Step 4 — Trace relationships

**Callees** (file X dùng gì):
- Grep imports trong X
- Grep `: InterfaceName` nếu X implement
- Grep `UseCase(...)`, `Repository(...)` khởi tạo

**Callers** (gì dùng X):
- Grep `X(` + `X.` + `Inject X` + DI module reference
- Count unique files

### Step 5 — Report

Default format (`--out md`):

```markdown
## Scout: <target>

**Definition(s):**
- `path/to/File.kt:L42` — class signature summary

**Layer distribution:**
- domain: 2 files
- data: 3 files
- presenter: 1 file
- test: 4 files

**Callers (N files):**
- `path/to/CallerA.kt:L15` — usage context (1 line quote)
- `path/to/CallerB.kt:L89`
- ...

**Related knowledge:**
- `knowledge/coding/clean-arch/essentials.md §Clean Arch` (nếu scan touches architecture)

**Blast radius if changed:** <N callers, M modules>

**Suggested next skills:** coding-refactor (if restructure) | coding-feature (if extend) | coding-review (if audit)
```

### Step 6 — Depth control

**`--depth shallow`** (default): file paths + line hints only. Fast, low context cost.

**`--depth full`**: Read lines ±5 quanh match cho mỗi file top-5. Dùng khi cần hiểu code pattern thực sự.

Never read full file in scout — chỉ snippet. Caller/orchestrator sẽ Read file đầy đủ nếu cần.

## Required policies

- `knowledge/coding/clean-arch/*` — layer boundaries (dùng để classify)
- `constitution/architecture-rules.md` ARCH-RULE-* — detect violation trong result
- Read-only operation: KHÔNG Edit/Write trong scout

## Output contract

- File paths có line numbers (format `path:LN`)
- Layer classification cho mỗi file
- Caller count + blast radius
- Suggested next skill (routing hint)

## Validation

- [ ] Mọi file match có path + line number
- [ ] Layer classification không ambiguous (hoặc flag `unknown`)
- [ ] Blast radius tính đúng (count unique callers, không include self)
- [ ] Không mở full file content vào context (>50 lines)

## Failure / recovery

- Target không match → trả về empty + suggest broader pattern
- Match quá nhiều (>100 files) → báo cáo count + ask user narrow scope
- Semantic search unavailable → fallback grep + warn

## Anti-patterns

- **AP-001 — Dump full file content**: Scout là discovery, không là reader. Read snippets only.
- **AP-002 — Spawn subagent cho scout đơn giản**: Native Glob/Grep đủ. Chỉ spawn Explore agent nếu >3 queries và cross-module.
- **AP-003 — Guess thay vì scout**: Nếu agent không biết file ở đâu → MUST scout trước khi suggest/edit, không guess path.
- **AP-004 — Silent on no result**: Empty match → report "0 files" explicit + suggest fallback, không im lặng.
- **AP-005 — Mix scout với edit**: Scout read-only. Edit trong cùng call → user mất kiểm soát scope.

## Handoff

Scout result → caller skill:
- `coding-feature` khi plan cross-module feature
- `coding-refactor` khi chuẩn bị restructure
- `coding-review` khi audit PR context
- `coding-diagnose` khi tìm nguồn bug
- User direct khi hỏi "where is X"

## Compare với các tool khác

- Native `Glob`/`Grep`: dùng trực tiếp cho 1-2 query simple. Scout = wrapper + classify + report format.
- `ak-scout` agent: parallel multi-query, dùng khi >5 query hoặc cần semantic search. Scout skill prefer native tools.
- `ck-graphify`: build persistent knowledge graph. Dùng khi same codebase scout nhiều lần/tuần, không ad-hoc.

## Future

- Semantic search integration (gkg knowledge graph)
- Visual callgraph output (markdown-mermaid)
- Caching cho repeated scout cùng target

---

## Harness context

- Workflow: `workflows/feature-development.md (Stage 1 Inspect)`
- Guardrails: `~/.claude/rules/primary-workflow.md, development-rules.md, review-audit-self-decision.md, orchestration-protocol.md`


## Overlay gate (D-full)

Trước Step 1, verify `.harness-overlay/overlay.yaml` tồn tại. Nếu không, abort với status `BLOCKED` và chỉ dẫn user:

> Chưa có overlay. Chạy skill `harness-init` để scaffold trước, sau đó quay lại skill này.

Khi gặp placeholder `{{X}}` trong procedure/code example, resolve bằng mapping ở `AGENTS.md §Placeholder resolution` (Read overlay 1 lần đầu session, cache qua context).

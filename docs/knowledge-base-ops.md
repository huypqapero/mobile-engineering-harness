# Knowledge Base Operations

Hướng dẫn vận hành KB sau cutover 2026-10-29. Harness repo không còn `knowledge/` + `constitution/` + `briefs/` — toàn bộ KB sống trong [team-knowledge](https://github.com/huypqapero/team-knowledge) repo, access qua `team-knowledge-mcp` + `basic-memory` MCP server.

## Overview

```
┌─ Dev / BA / QA ─────┐          ┌─ Claude Code ──────────────┐
│  Edit markdown      │          │   kb_push, kb_update,       │
│  qua GitHub web     │          │   kb_search, kb_read,       │
│  hoặc clone local   │          │   kb_status + semantic qua  │
│                     │          │   basic-memory search_notes │
└──────────┬──────────┘          └──────────────┬──────────────┘
           │                                     │
           │          Git push/pull              │
           ▼                                     ▼
      ┌────────────────────────────────────────────┐
      │  github.com/huypqapero/team-knowledge (private)  │
      │  notes/<scope>/<category>/kb-<id>.md       │
      │  Branch: main (no PR review required)      │
      └────────────────────────────────────────────┘
```

### 2 MCP server

| Server | Role | Tool |
|---|---|---|
| `team-knowledge` | Write + sync + VN keyword search | `kb_push`, `kb_update`, `kb_search`, `kb_read`, `kb_status` |
| `basic-memory` | Semantic search + graph/context | `search_notes`, `read_note`, `write_note`, `edit_note`, ... |

Wire config đã sẵn trong `~/.claude.json` (2 server merge sẵn Oct 29).

## Install per machine (dev onboarding)

```bash
# 1. Prerequisite
# - macOS/Linux (Windows WSL)
# - Python 3.11+, Git, uv
# - Git identity set + GitHub HTTPS credential helper (gh auth setup-git)

# 2. Install 2 tool riêng venv
uv tool install "basic-memory==0.24.1"
cd <path-to-team-knowledge-mcp-source>
uv tool install .

# 3. Verify
bm --version       # Basic Memory version: 0.24.1
team-kb --help

# 4. Init clone
team-kb init \
  --remote "https://github.com/huypqapero/team-knowledge.git" \
  --repo "$HOME/team-knowledge" \
  --project team-knowledge

# 5. Wire MCP (Claude Code)
team-kb client-config --client claude
# → Ghép output vào ~/.claude.json .mcpServers (không overwrite entry khác)

# 6. Sync + verify
team-kb update
team-kb status
```

Config path: `~/.config/team-knowledge/config.json`. Clone path: `~/team-knowledge`. Chỉ `notes/` register với Basic Memory.

## Scope convention

Wrapper enforce scope format: `team/<slug>` hoặc `projects/<slug>`. Hierarchy phẳng, dùng tags cho context.

### `team/*` — knowledge chung team (framework + runtime cross-product)

| Scope | Chứa gì |
|---|---|
| `team/arch` | Index knowledge framework top-level (knowledge/README.md cũ) |
| `team/arch-coding-sdk` | SDK framework (mindset, essentials, pattern catalog, brainstorm, testing kit, layered arch) |
| `team/arch-coding-feature-store` | Feature Store framework (mindset, capability contract, module topology, data port, theme adapter, testing kit, essentials) |
| `team/arch-coding-compose` | Compose Multiplatform UI pattern |
| `team/arch-coding-coroutines` | Async / Flow / cancellation |
| `team/arch-coding-mvi` | UiState + Intent + Effect pattern |
| `team/arch-coding-clean-arch` | Clean Architecture + layer boundary |
| `team/arch-coding-patterns` | Common Kotlin patterns |
| `team/arch-coding-data` | Caching / network / persistence / repository pattern |
| `team/arch-constitution` | 14 ADR + CORO + KOT + Definition of Done |
| `team/arch-product` | BA / spec / wireframe framework |
| `team/arch-product-input-analysis` | Spec extraction + reconciliation rules |
| `team/arch-design-system` | Token + screen state + WCAG + dark mode |
| `team/arch-design-compare` | Figma vs screenshot grading |
| `team/arch-design` | Design layer index |
| `team/arch-pm` | Feasibility / deadline / scope / release |
| `team/arch-testing` | Testing framework rule |
| `team/arch-testing-e2e-runtime` | E2E runtime (APK driver, step files, interruption) |
| `team/arch-meta-orchestration` | Multi-agent orchestration patterns |
| `team/arch-meta-governance` | Harness governance + permission |
| `team/arch-meta-auto-fix` | Error loop detection |
| `team/arch-xcut-performance` | Performance (startup, UI, memory, network) |
| `team/arch-xcut-security` | OWASP, encryption, auth |
| `team/arch-xcut-build-strategy` | Gradle, variant, build-time |
| `team/business-index` | Index briefs cross-product |

### `projects/*` — runtime per product

| Scope | Chứa gì |
|---|---|
| `projects/<product-slug>` | Business + develop + testing cho 1 product cụ thể |

Ví dụ: `projects/taplisten`, `projects/paywall-kit`, `projects/chatbot-kit`.

## 5 Category enum (fixed, wrapper enforce)

| Category | Dùng cho |
|---|---|
| `decision` | ADR, architecture decision, PRD summary, mindset ADR, breaking change rationale |
| `pattern` | Reusable code pattern, canonical SDK design, pattern catalog, Compose pattern |
| `pitfall` | Anti-pattern, gotcha, flaky test, known bad approach |
| `runbook` | Rule checklist (essentials.md), process (brainstorm), spec, how-to, test plan, DoD |
| `lesson` | Verified learning from task, bug analysis conclusion, retro insight |

**Multi-tag strategy**: category chọn 1/5 enum, dùng `tags` để enrich. Ví dụ mindset note:

```yaml
category: decision
tags: [mindset, adr, framework, sdk, arch]
```

## Workflow: Agent push lesson

Agent (Claude Code / Codex) tự động capture khi:
- Có correction quan trọng từ user
- Decision lâu dài được đưa ra
- Fix đã verified qua test
- Pattern reusable xuất hiện trong task

Flow:

```
1. kb_search "<topic liên quan>"      → check đã có note tương tự chưa
2. (nếu có) kb_read <note_id>         → đọc note cũ, note revision
3. (nếu update) kb_push với note_id + expected_revision + content mới
   (nếu tạo mới) kb_push với title + scope + category + tags + content + verification
4. Verify published=true + check index.status
```

Verification level:
- `unverified` — hypothesis, chưa thấy evidence
- `observed` — thấy actual observation 1 lần, chưa reproduce
- `tested` — có test code + evidence (commit SHA, test name)

## Workflow: Dev / BA push note

Non-dev edit qua GitHub web:
1. Mở https://github.com/huypqapero/team-knowledge
2. Navigate `notes/<scope>/<category>/`
3. Edit file hoặc "Add file" tạo mới
4. Preview markdown
5. Commit directly to main (branch policy không require PR review)

Dev edit qua clone local:
```bash
cd ~/team-knowledge
# Edit notes/*
# Nhưng KHÔNG commit tay — dùng kb_push qua MCP để atomic + revision guard
# Nếu phải commit tay (ví dụ reconcile conflict):
#   git commit; git push
# Rồi team-kb update ở các clone khác
```

**Rule**: ghi shared knowledge qua `kb_push`. Manual edit tạo dirty file, wrapper refuse sync.

## Workflow: Fetch

Agent fetch khi task cần:

```
1. kb_update                           → sync latest từ remote (fetch + merge + reindex)
2. kb_search "<query>"                 → VN-aware keyword search
   HOẶC
   search_notes "<semantic query>"      → semantic search (basic-memory)
3. kb_read <note_id>                   → full content + revision
```

Agent không được dump toàn bộ note vào context — chỉ load note liên quan task.

## Workflow: Conflict resolve

Hai dev edit cùng note → merge conflict khi push. Flow:

```
1. kb_update (fail do dirty hoặc conflict)
2. cd ~/team-knowledge
3. git diff (xem 2 phía)
4. Reconcile manual trong editor
5. git add + commit
6. team-kb push
```

**Never**: `git push --force`, discard local edits, bypass `expected_revision`.

## Agent policy

Nạp vào `~/.claude/CLAUDE.md` (hoặc project CLAUDE.md) từ `team-kb instructions`:

> 1. Tự lưu khi có correction quan trọng, decision lâu dài, fix đã kiểm chứng.
> 2. Kiểm tra bài học mới trước khi hoàn tất task.
> 3. Khi user nói "push" thì thực hiện ngay. Kết quả chưa kiểm chứng = `unverified`.
> 4. Tìm + đọc bài cũ trước khi tạo/cập nhật.
> 5. Chỉ ghi bài học liên quan; không gửi nguyên transcript.
> 6. Gọi `kb_update` khi user yêu cầu; sau đó chỉ đọc tài liệu liên quan vào context.

## Reference locator trong agent/skill files

Agent/skill files (`agents/*.md`, `skills/*/SKILL.md`, workflow docs) reference KB qua inline locator:

```markdown
`knowledge/coding-feature-store/mindset.md [KB → team/arch-coding-feature-store, kb_search "coding feature store mindset"]` — ADR FS-001..007
```

Agent đọc locator → `kb_search "<query>"` → `kb_read <note_id>`. Path cũ giữ làm **context hint** (lúc migrate 2026-10-29), không phải link clickable.

## Troubleshoot

| Triệu chứng | Nguyên nhân | Fix |
|---|---|---|
| `kb_push` fail "scope must be team/… or projects/…" | Scope sai format | Dùng `team/<slug>` (hyphen) hoặc `projects/<slug>` |
| `kb_update` refuse "dirty files" | Clone có uncommit manual change | `cd ~/team-knowledge && git status` → commit hoặc stash |
| `kb_push` published=false | Local commit chưa push remote (offline / credential fail) | `team-kb push` không truyền note để retry |
| Merge conflict trên pull | 2 dev edit cùng note | Follow "Workflow: Conflict resolve" |
| Index status=failed | Basic Memory reindex lỗi | `bm reindex --project team-knowledge --search`; check model config |
| Semantic search miss cho VN | Embedding model không support VN tốt | Validate model trước; fallback `kb_search` (full-text VN-aware) |
| Agent push nhầm vào `arch-*` | Thiếu convention awareness | `arch-*` là framework rule, chỉ framework maintainer update. Dev lesson push vào `projects/<product>` |
| `team-kb --help` không ra | Chưa `uv tool install` | Chạy install step |

## Migration note (2026-10-29)

### Trước cutover

Harness repo chứa:
- `knowledge/` 9 category × 18 domain (~5500 LOC)
- `constitution/` 14 ADR + CORO + KOT + DoD (~800 LOC)
- `briefs/` 2 feature brief (~300 LOC)

Agent/skill reference qua file path (`knowledge/coding-sdk/sdk-mindset.md`).

### Sau cutover

- 51 notes migrated → `team-knowledge/notes/*`
- Harness repo delete `knowledge/`, `constitution/`, `briefs/`
- Agent/skill ref giữ context hint + inline KB locator `[KB → <scope>, kb_search "<query>"]`
- Script migrate: `scripts/migrate-knowledge-to-kb.py` (idempotent via capture_id)
- Script update ref: `scripts/update-knowledge-refs.py`

### Rollback

Content gốc ở git history:
```bash
git log --all --oneline -- knowledge/ constitution/ briefs/ | head -5
# Hoặc checkout archive branch:
git checkout archive/pre-kb-cutover-261029  # branch backup đã tạo
```

Hoặc rollback hoàn toàn:
```bash
git revert <cutover-commit>
```

## Mapping cutover path → scope

Reference `scripts/migrate-knowledge-to-kb.py` MAP table cho full list. Tóm tắt:

| Source path | Target scope |
|---|---|
| `knowledge/coding-sdk/*` | `team/arch-coding-sdk` |
| `knowledge/coding-feature-store/*` | `team/arch-coding-feature-store` |
| `knowledge/coding/<domain>/*` | `team/arch-coding-<domain>` |
| `knowledge/product/*` | `team/arch-product` |
| `knowledge/product/input-analysis/*` | `team/arch-product-input-analysis` |
| `knowledge/design/design-system/*` | `team/arch-design-system` |
| `knowledge/design/visual-compare/*` | `team/arch-design-compare` |
| `knowledge/pm/*` | `team/arch-pm` |
| `knowledge/testing/e2e-runtime/*` | `team/arch-testing-e2e-runtime` |
| `knowledge/meta/<domain>/*` | `team/arch-meta-<domain>` |
| `knowledge/cross-cutting/<domain>/*` | `team/arch-xcut-<domain>` |
| `constitution/*` | `team/arch-constitution` |
| `briefs/<slug>/*` | `projects/<slug>` |

## Governance

| Role | Permission |
|---|---|
| Framework maintainer (owner harness repo) | Push vào `team/arch-*` qua convention + review |
| Product dev | Push vào `projects/<product>` free; đọc `team/arch-*` |
| BA / PM | Edit `projects/<product>` qua GitHub web; đọc `team/arch-product` |
| QA | Push vào `projects/<product>` scope testing; đọc `team/arch-testing-*` |
| Agent (Claude/Codex) | Push qua `kb_push` với scope phù hợp task; không push vào `team/arch-*` trừ framework task |

**Convention mandatory**: `arch-*` scope là **framework rule read-only cho runtime agent**. Chỉ framework maintainer update qua review.

## Related tools

| Tool | Vai trò |
|---|---|
| `team-kb` CLI | init, update, push, search, read, status, instructions, client-config |
| `kb_*` MCP tool | Agent-callable version qua Claude Code / Codex |
| `bm` CLI | Basic Memory server management, reindex, project list |
| `basic-memory` MCP | Semantic search + graph context |
| `scripts/migrate-knowledge-to-kb.py` | Bulk migrate harness → KB (idempotent) |
| `scripts/update-knowledge-refs.py` | Batch update KB locator trong agent/skill files |

## FAQ

**Q: Semantic search bật như nào?**  
A: Default `index_mode=search` (full-text). Bật semantic: validate embedding model VN quality trước, `bm reindex --project team-knowledge` với model config, đổi `index_mode=full` trong wrapper config.

**Q: Agent push wrong scope → fix sao?**  
A: `kb_read <note_id>` → extract content → `kb_push` tạo note mới ở scope đúng (new capture_id) → old note delete manual (git rm trong clone, commit, push).

**Q: Framework rule update sao?**  
A: Vì cutover 2026-10-29 đã nuke harness knowledge/. Update rule framework = `kb_push` vào `team/arch-*` với tag `arch` + `framework`. **Yêu cầu review** qua chat/PR trong team-knowledge repo (branch policy có thể bật require review cho scope `team/arch-*` sau).

**Q: Có tool nào dump KB thành markdown offline cho reader?**  
A: `~/team-knowledge/notes/` chính là markdown. Clone repo đọc trực tiếp. GitHub web render OK.

## Unresolved

- Branch policy GitHub nên bật require PR review cho `notes/team/arch-*` (framework protection) sau khi team settle workflow?
- Semantic search embedding model cho VN — chọn `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, `BAAI/bge-m3`, hay model VN-specific? Cần validate với sample 10-20 note.
- Konsist test code (`verification/architecture-tests/*.kt`) hiện tại reference ADR qua ID (ADR-001..014). ADR prose giờ ở KB — test code có cần sync comment reference với note_id không, hay giữ ID abstract?
- Workflow tạo project mới (`harness-init` skill) có bootstrap wire 2 MCP server vào product `.mcp.json` không, hay dev tự wire?

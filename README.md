# Mobile Engineering Harness

> **AI coding harness** cho các sản phẩm Android / Compose Multiplatform tuân theo concept **Clean Architecture + SOLID + MVI + Compose + Coroutines**.

Harness biến AI agent (Claude Code, Codex, CLI agent khác) từ "generic coder" thành **"senior-aware coder"** nhận biết chuẩn kiến trúc + convention + verification gate của bạn — không phải nhắc lại rule mỗi task.

**Current version**: `v0.6.0` — **68 files** upstream, 11 skills, 5 workflows, 5 blueprints, 4 agent roles, 11 knowledge files, 3-tool verification stack (Konsist + Detekt + Lint), 5 eval scenarios + rubrics + regression tracking.

---

## Table of contents

1. [Install](#install)
2. [AI Harness là gì](#ai-harness-là-gì)
3. [Kiến trúc 2-layer](#kiến-trúc-2-layer)
4. [Current state](#current-state)
5. [Best practices](#best-practices)
6. [CLI reference](#cli-reference)
7. [Agent resolution order](#agent-resolution-order)
8. [Governance](#governance)
9. [Phạm vi áp dụng](#phạm-vi-áp-dụng)

---

## Install

### One-liner

```bash
curl -fsSL https://raw.githubusercontent.com/huypqapero/mobile-engineering-harness/main/bootstrap.sh | bash
```

Script tự:
- Clone upstream vào `~/.mobile-engineering-harness/`
- Symlink CLI thành `mehcli` ở `~/.local/bin/`
- Check prerequisites (git, python3, PyYAML)
- Warn nếu PATH chưa chứa `~/.local/bin`

### Quick start cho product mới (3 lệnh)

```bash
# 1. Scaffold overlay trong project Android
mehcli init --project /path/to/your/android-project

# 2. Edit .harness-overlay/overlay.yaml — điền vars product (xem overlay.schema.yaml)

# 3. Render templates + create manifest
mehcli install --overlay /path/to/your/android-project/.harness-overlay
```

Setup time ~15 phút.

### Install + run luôn (1 lệnh)

```bash
curl -fsSL https://raw.githubusercontent.com/huypqapero/mobile-engineering-harness/main/bootstrap.sh | bash -s init --project .
```

### Env vars cho bootstrap

| Var | Default | Khi dùng |
|---|---|---|
| `MEH_INSTALL_DIR` | `$HOME/.mobile-engineering-harness` | Custom install location |
| `MEH_BIN_DIR` | `$HOME/.local/bin` | Prefer `/usr/local/bin` (cần sudo) |
| `MEH_REF` | `main` | Pin version: `MEH_REF=v0.6.0 curl ... \| bash` |

---

## AI Harness là gì

### Vấn đề

AI coding agent (Claude Code, Codex) có kiến thức generic về Android/Kotlin. Nhưng khi làm việc trong 1 codebase thực tế:

- Mỗi task phải nhắc lại architecture (Clean Arch? MVVM? MVI? Which flavor?)
- Mỗi task phải nhắc lại convention (naming, module structure, DI framework)
- Mỗi task phải nhắc lại verification (Konsist? Detekt? CI gates nào?)
- AI quên rule giữa chừng → vi phạm architecture dù "đồng ý" ở prompt
- Không có cách enforce automatic: rule chỉ là text, không block code

### Giải pháp — Harness 5 layer

```
┌──────────────────────────────────────────────────────────────┐
│                       AI AGENT                                │
│         (Claude Code / Codex / CLI agent)                     │
└──────────────────────────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  LAYER 1 — CONSTITUTION (luật bắt buộc)                       │
│  MUST / SHOULD / FORBIDDEN rules với verification method      │
│  constitution/{architecture, concurrency, kotlin, dod}.md     │
└──────────────────────────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  LAYER 2 — KNOWLEDGE (kiến thức nền)                          │
│  Essentials per domain, link-first, không duplicate Google    │
│  knowledge/{architecture, compose, mvi, coroutines, data,     │
│             patterns, security, performance}/*.md             │
└──────────────────────────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  LAYER 3 — SKILLS (procedures per task type)                  │
│  Trigger + Prerequisites + Steps + Validation + Anti-patterns │
│  skills/android-{feature,compose,mvi,coroutines,network,...}  │
└──────────────────────────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  LAYER 4 — WORKFLOWS + AGENT ROLES (orchestration)            │
│  State machine: inspect → plan → implement → verify → report  │
│  workflows/*.md + agents/{architect,implementer,reviewer,...} │
└──────────────────────────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  LAYER 5 — VERIFICATION (automatic enforcement)               │
│  Konsist (architecture) + Detekt (code) + Lint (platform)     │
│  verification/{architecture-tests,detekt,lint,scripts}/        │
└──────────────────────────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  LAYER 6 — EVALUATION (feedback)                              │
│  Scenario templates + rubrics + regression tracking           │
│  evaluations/{templates,rubrics,regression}/                  │
└──────────────────────────────────────────────────────────────┘
```

### Nguyên tắc thiết kế

1. **Opinionated but configurable** — chuẩn kỹ thuật rõ ràng, cho phép product customize qua overlay
2. **Progressive disclosure** — không load toàn bộ context mỗi task; agent khám phá skill + knowledge theo nhu cầu
3. **Convention over configuration** — default sẵn, agent không reinvent mỗi task
4. **Verification over instruction** — rule có cách enforce (Konsist/Detekt), không chỉ là text
5. **Minimal sufficient architecture** — không tạo abstraction nếu chưa có lý do (YAGNI)
6. **Reproducibility** — cùng request + cùng config → implementation kiến trúc nhất quán
7. **Evidence-based completion** — không claim DONE khi chưa compile/test/verify

---

## Kiến trúc 2-layer

Harness tổ chức theo **2 tầng**:

### Upstream (generic, shared)

Repo này — chứa content generic parameterized bằng `{{VARS}}`. 1 source of truth cho rule + skill + workflow.

Install location: `~/.mobile-engineering-harness/`

### Overlay (product-specific)

Mỗi product có `.harness-overlay/` chứa:
- `overlay.yaml` — vars (package, module names, theme, SDK dùng)
- `upstream` → symlink hoặc submodule tới upstream repo
- `constitution/product-extensions.md` — rules đặc thù product
- `blueprints/live-reference-feature.md` — pointer tới live feature làm reference
- Rendered files: Konsist test, verify.sh, harness.yaml (từ templates)
- `.manifest.yaml` — track rendered files (clean install/uninstall)

### DRY ratio

Upstream carries ~78% content (reusable across products). Overlay chỉ ~22% product-specific.

```
Product A overlay (22%)  ──┐
Product B overlay (22%)  ──┼──→  Upstream (78%)
Product C overlay (22%)  ──┘
```

---

## Current state

### Breakdown v0.6.0

| Component | Count | Files |
|---|---|---|
| **Constitution** | 5 files | architecture-rules, concurrency-rules, kotlin-conventions, engineering-principles, definition-of-done |
| **Knowledge** | 11 files / 7 domains | architecture, compose, mvi, coroutines, data (4 files), patterns, security, performance |
| **Skills** | 11 skills | feature, compose, mvi, coroutines, network, database, refactor, debug, performance, code-review, testing |
| **Blueprints** | 5 patterns | reference-feature, network-service, compose-screen, repository, usecase |
| **Workflows** | 5 workflows | feature-development, fix-bug, review-pull-request, refactor-module, release-validation |
| **Agent roles** | 4 roles | architect, implementer, reviewer, test-engineer |
| **Verification** | 3 tools | Konsist (template), Detekt (config + custom rule scaffold), Android Lint (scaffold) |
| **Evaluations** | 5 scenarios + rubrics + regression | E01-E05 + shared rubric + trend tracking |

### Structure

```
mobile-engineering-harness/
├── README.md                        ← bạn đang đọc
├── AGENTS.md                        ← entry point generic cho AI
├── CLAUDE.md                        ← short entry cho Claude Code
├── CHANGELOG.md
├── harness.yaml.template            ← config template
├── install.sh                       ← CLI (symlink thành `mehcli`)
├── bootstrap.sh                     ← one-liner installer
├── overlay.schema.yaml              ← schema cho overlay.yaml
│
├── constitution/                    ← Layer 1: luật
├── knowledge/                       ← Layer 2: kiến thức
├── skills/                          ← Layer 3: procedures
├── workflows/                       ← Layer 4: orchestration
├── agents/                          ← Layer 4: role prompts
├── verification/                    ← Layer 5: enforcement
├── blueprints/                      ← Golden implementations
└── evaluations/                     ← Layer 6: feedback
```

---

## Best practices

### Khi dùng harness

#### DO

- **Install qua bootstrap.sh** — managed update + consistent location
- **Pin version** cho CI (`MEH_REF=v0.6.0`) để reproducible builds
- **Edit `overlay.yaml` thực tế** — không skip, mỗi field vai trò enforcement
- **Chạy `mehcli install` sau mỗi `self-update`** — rerender templates với latest upstream
- **Add Konsist + Detekt + Lint vào CI** — enforcement không skip
- **Review `product-extensions.md`** mỗi sprint — product-specific rule có drift không
- **Promote rule overlay → upstream** khi 2+ product cùng rule
- **Test harness bằng `evaluations/templates/`** — baseline measurement + regression tracking
- **Document deviation từ blueprint** trong PR

#### DON'T

- **Fork upstream rule trong overlay** — luôn add qua `constitution/product-extensions.md` extend, không override
- **Commit `.manifest.yaml`** nếu nó varies per machine (xem gitignore)
- **Hardcode absolute path** trong constitution/skills — dùng `{{PACKAGE_ROOT}}` placeholder
- **Add rule không có verification method** — rule không enforce được = decorative
- **Add file < 50 dòng** vào knowledge — short content → link-first thay vì tạo file riêng
- **Disable Konsist/Detekt test** khi fail — fix cause hoặc downgrade rule severity
- **Skip baseline measurement** → không biết harness thực sự improve hay không

### Khi viết rule mới

1. **Có user story thực tế** — AI đã vi phạm pattern này ≥ 3 lần
2. **Rule verifiable** — Konsist test hoặc Detekt rule hoặc explicit review checklist
3. **Severity rõ** — MUST (chặn task) / SHOULD (default) / MAY (option) / FORBIDDEN (never)
4. **Rationale 1 câu** — tại sao rule tồn tại
5. **Violation example + fix** — concrete, không vague "best practice"
6. **Add vào Konsist/Detekt** cùng commit — không delay enforcement

### Khi expand skill

1. **Trigger rõ** — khi nào invoke skill
2. **Prerequisites** — file cần đọc trước
3. **Procedure có steps rõ** — không "AI figure it out"
4. **Required policies** — rule nào từ constitution áp dụng
5. **Common mistakes** — anti-patterns với fix
6. **Output contract** — deliverable cụ thể

### Khi update harness

1. **Semver bump** rõ (breaking? feature? patch?)
2. **CHANGELOG entry** với rationale
3. **Backward compat check** — overlay cũ còn work?
4. **Test với 1 overlay thực** — regression check trước khi tag
5. **Tag + GitHub Release** — reproducible pin point

### Agent interaction patterns

#### Pattern 1 — Full feature end-to-end

```
User: "Implement Login feature với Google OAuth + save token"

AI resolution:
1. Load CLAUDE.md + AGENTS.md
2. Route task → skills/android-feature
3. Load constitution/architecture-rules + concurrency-rules
4. Load blueprint reference-feature
5. Follow workflow feature-development
6. Agent role: architect (plan) → implementer → test-engineer → reviewer
7. Verify: konsistTest + detekt + unit tests
8. Report theo DoD template
```

#### Pattern 2 — Code review PR

```
User: "Review PR #42"

AI resolution:
1. Route task → skills/android-code-review + workflow/review-pull-request
2. Agent role: reviewer
3. Scan diff 10 dimensions
4. Each finding: Rule ID, severity, file:line, evidence, fix
5. Report theo review template
```

#### Pattern 3 — Debug bug

```
User: "Fix crash in BookDetail khi offline"

AI resolution:
1. Route task → skills/android-debug + workflow/fix-bug
2. Agent role: debugger
3. Stages: reproduce → isolate → cause → fix → verify
4. Fix tại cause, không mask symptom
5. Add regression test
```

### Context cost optimization

Harness design cho **progressive disclosure** — tối ưu context budget:

- Agent **không** load toàn bộ harness mỗi task
- Load theo order:
  1. `AGENTS.md` (entry, ~200 lines) — always
  2. Skill tương ứng (SKILL.md, ~250 lines) — per task
  3. Constitution rule relevant — khi verify
  4. Knowledge essentials — khi deep concept
  5. Blueprint — khi tạo pattern mới

Mỗi task thường chỉ cần ~1500-3000 tokens harness context, không phải full 68 files.

---

## CLI reference

### Subcommands

```bash
mehcli init         --project <path>              # scaffold overlay + schema
mehcli install      --overlay <path>              # render templates + manifest
mehcli update       --overlay <path>              # idempotent re-render
mehcli uninstall    --overlay <path> [--purge]    # remove rendered; --purge nukes overlay
mehcli self-update                                # git pull upstream in-place
mehcli version                                    # print installed version
mehcli help
```

### Flags chung

| Flag | Hiệu lực |
|---|---|
| `--dry-run` | Print actions, không execute |
| `--yes`, `-y` | Skip confirmation (cho CI) |

### Chi tiết subcommand

**`init`** — scaffold overlay structure:
- Tạo `.harness-overlay/` trong project
- Copy `overlay.schema.yaml` → `.harness-overlay/overlay.yaml`
- Symlink `.harness-overlay/upstream` → upstream repo
- KHÔNG render; đợi user điền overlay.yaml

**`install`** — render templates:
- Đọc `overlay.yaml`, validate required fields
- Render 4 files: `ArchitectureRulesTest.kt`, `verify.sh`, `harness.yaml`, overlay `README.md`
- Ghi `.manifest.yaml` track rendered files + upstream commit
- Idempotent

**`update`** — alias `install`. Dùng sau `self-update` hoặc khi `overlay.yaml` đổi.

**`uninstall`** — remove rendered artifacts:
- Default: xóa 4 rendered files + manifest; **preserve** `overlay.yaml`, `constitution/`, `blueprints/`, upstream symlink
- `--purge`: xóa toàn bộ `.harness-overlay/` (2x confirm)
- Konsist test đã copy sang source → user xóa thủ công

**`self-update`** — `git pull` upstream trong installed location. Reports before/after commit.

### Submodule thay vì symlink (CI)

Sau khi `init`:

```bash
cd /path/to/your/android-project/.harness-overlay
rm upstream
cd ..
git submodule add https://github.com/huypqapero/mobile-engineering-harness.git .harness-overlay/upstream
```

### Setup Konsist dep (one-time per product)

Trong `gradle/libs.versions.toml`:

```toml
[versions]
konsist = "0.17.3"

[libraries]
konsist = { module = "com.lemonappdev:konsist", version.ref = "konsist" }
```

Copy rendered Konsist test:

```bash
cp .harness-overlay/verification/architecture-tests/ArchitectureRulesTest.kt \
   presenter/src/jvmTest/kotlin/<package>/harness/
```

Add test dep + run:

```bash
./gradlew konsistTest
```

### Setup Detekt (one-time per product)

```bash
cp .harness-overlay/upstream/verification/detekt/detekt-config-template.yml ./detekt.yml
./gradlew detekt
./gradlew detektBaseline       # generate baseline cho existing codebase
```

Chi tiết `.harness-overlay/upstream/verification/detekt/README.md`.

### Verify tổng

```bash
./.harness-overlay/verification/scripts/verify.sh
```

Chạy đủ gates: compile + unit tests + Konsist + Detekt + build.

---

## Agent resolution order

Khi AI agent nhận task trong project có overlay:

```
1. Project root CLAUDE.md (nếu có) — product-specific context cao nhất
   ↓
2. .harness-overlay/overlay.yaml — resolve vars
   ↓
3. .harness-overlay/upstream/AGENTS.md — generic entry (substitute vars)
   ↓
4. Skill tương ứng: upstream/skills/<name>/SKILL.md
   ↓
5. Constitution (upstream/constitution/) khi verify rule
   ↓
6. Knowledge (upstream/knowledge/) khi cần deep concept
   ↓
7. Blueprint: ưu tiên overlay/blueprints/live-reference-feature.md,
   fallback upstream/blueprints/reference-feature/README.md
```

### Rule precedence (cao → thấp)

1. **Project CLAUDE.md** — product/repo chủ ý override
2. **Overlay constitution** (`.harness-overlay/constitution/product-extensions.md`) — product-specific delta
3. **Upstream constitution** — generic baseline

Nếu cùng rule ID xuất hiện ở overlay + upstream → **overlay thắng**.

### Workflow + agent role interplay

```
WORKFLOW (orchestration)         AGENT ROLE (mindset)
────────────────────────         ────────────────────
feature-development              architect → implementer → test-engineer → reviewer
fix-bug                          debugger (role tích hợp trong agents/)
review-pull-request              reviewer
refactor-module                  architect → implementer → reviewer
release-validation               implementer + test-engineer + reviewer
```

1 agent có thể chuyển mindset qua các role trong 1 workflow. Multi-agent setup: dedicated subagent per role.

---

## Governance

### Upstream maintenance

- **Owner** sở hữu rule + skill upstream, bump version theo semver
- **Breaking rule change** → major bump; overlay specify `harness_version: ">=X.Y.0"` để pin
- **Review quarterly**: rule có outdated không, Compose/Coroutines có thay đổi, Konsist/Detekt API drift
- **CHANGELOG + GitHub Release** mỗi version — reproducible pin

### Overlay maintenance

- Product chỉ **add delta** qua `constitution/product-extensions.md`, không fork upstream rule
- **Promote overlay → upstream** khi 2+ product độc lập có cùng rule
- **Baseline measurement** định kỳ — chạy eval E01-E05 để verify không regression
- **Konsist/Detekt baseline** shrink mỗi sprint — fix 1-2 old issue

### Rule lifecycle

```
Discover → Propose → Review → Approve → Publish → Evaluate → Version
```

Mỗi rule có:
```yaml
id: COROUTINE-004
title: Preserve coroutine cancellation
level: MUST
rationale: Cancellation là part của structured concurrency
validation: Detekt SwallowedException + manual review
exceptions: []
sources: [concurrency-rules.md]
```

### Rule evolution

- Rule nào Konsist/Detekt **không bao giờ catch** (test luôn pass) → downgrade MUST → SHOULD hoặc delete (dead rule)
- Rule nào **bị vi phạm thường** nhưng Konsist không catch → thêm Detekt custom rule
- Rule nào **conflict** với rule khác → ADR giải quyết + merge

---

## Phạm vi áp dụng

| Loại sản phẩm | Fit | Note |
|---|---|---|
| **Compose Multiplatform** (Android + iOS) | ✓ chính | Full stack covered |
| **Android-only Jetpack Compose** | ✓ | Bỏ platform SDK iOS section trong `overlay.yaml` |
| **Android XML/MVVM legacy** | ⚠ | MVI rule phần lớn apply; Compose rule skip; cần adaptation |
| **Kotlin Multiplatform** (shared logic + native UI) | ✓ | Customize profile trong `overlay.yaml` |
| **iOS-only Swift/SwiftUI** | ✗ | Ngoài scope — harness Kotlin-centric |
| **React Native / Flutter** | ✗ | Khác ecosystem |

### Profile types (`overlay.yaml`)

```yaml
profile: app                     # Default: consumer app
# profile: sdk-library           # Phase 2: feature extract thành library
# profile: multiplatform-library # KMP shared library
```

`sdk-library` promote `MOD-001..003` severity SHOULD → MUST + thêm binary compat gate.

### Stack options

Harness support đa stack qua `stack.*` fields trong `overlay.yaml`:

| Field | Options | Note |
|---|---|---|
| `stack.ui` | `compose-multiplatform` / `compose-android` / `xml-android` | UI framework |
| `stack.di` | `koin` / `hilt` / `manual` | DI framework |
| `stack.network` | **`ktor`** (KMP) / **`ktorfit`** (KMP annotation) / **`retrofit`** (Android-only) | API client |
| `stack.database` | **`sqldelight`** (KMP + Android) / **`room`** (Android + KMP 2.7+) / `datastore` / `none` | Local DB |
| `stack.image` | `coil` / `glide` / `kamel` / `none` | Image loader |
| `stack.serialization` | `kotlinx-serialization` / `moshi` / `gson` | JSON serialization |

Decision guides chi tiết:
- Network: `.harness-overlay/upstream/knowledge/data/network.md §Library selection`
- Database: `.harness-overlay/upstream/knowledge/data/persistence.md §Relational DB`

Agent sử dụng stack value để chọn snippet trong knowledge/skills (ví dụ `stack.network: retrofit` → Retrofit code, không Ktor).

### Architecture profile (v0.8.0+)

Pick 1 trong 3 profiles qua `architecture.profile`:

| Profile | Target | ARCH-010 (platform SDK) |
|---|---|---|
| `cmp` | Compose Multiplatform (shared UI + logic) | **MUST enforce** |
| `kmp` | Kotlin Multiplatform (shared logic, native UI) | **MUST enforce** |
| `android-only` | Jetpack Compose Android | **SKIP** (relaxed) |

Chi tiết + migration guide: `.harness-overlay/upstream/knowledge/architecture/architecture-profiles.md`.

### Rule overrides (v0.8.0+)

Overlay có thể override rule MUST qua `rule_overrides` nhưng **rationale ≥ 50 chars bắt buộc**. Install validate — thiếu rationale → fail.

```yaml
rule_overrides:
  - rule: ARCH-008
    severity: SHOULD              # Downgrade từ MUST
    rationale: "Settings app simple không có remote data, 5-state coverage over-strict."
```

### Enforcement mode (v0.8.0+)

```yaml
enforcement:
  mode: strict     # Default: fail CI khi violation
  # mode: advisory # Warn only — dùng khi mới migrate hoặc evaluation phase
```

### Agent orchestration (v0.9.0+)

4 orchestration modes qua `orchestration.mode`:

| Mode | Khi dùng | Cost | Latency wall-clock |
|---|---|---|---|
| `single` | Task < 300 LOC, 1 feature | 1x | 1x |
| `team` | Cross-module hoặc high-risk | 2-3x | 3x (sequential handoff) |
| `parallel-features` | **Build 3-5 features từ spec cùng lúc** | 3-5x | **1.2-1.5x** (parallel speedup) |
| `auto` | Default — harness quyết dựa trên task | Varies | Varies |

```yaml
orchestration:
  mode: parallel-features     # Build N feature song song từ spec
  parallel:
    max_concurrent: 3
    isolation: feature-package           # Mỗi subagent 1 feature package, không conflict
    shared_file_strategy: coordinator    # DI/Nav/resources handled serial
```

Flow `parallel-features` (xem `workflows/parallel-feature-development.md`):

```
spec → architect decompose → isolation check → spawn N parallel Task subagents
     → aggregate shared files (coordinator) → reviewer audit → verify
```

Claude Code `Task` tool native support. Subagent per role, tool subset limit (ví dụ reviewer chỉ Read+Grep, không Edit → prevent bias).

Chi tiết: `knowledge/agent-orchestration/essentials.md`.

### Spec ingest từ Confluence + Figma (v0.13.0+)

Bước tuỳ chọn để sinh `docs/specs/<feature>.md` từ một Confluence page và Figma file/frame thay vì export tay. Ingest chỉ chạy khi nguồn được bật trong overlay **và** user đưa link. Thiếu một trong hai thì hành vi giữ nguyên như cũ.

```yaml
spec_sources:
  confluence:
    enabled: true
    access: auto            # auto (MCP trước, rồi REST + env) | mcp | rest
    base_url: "https://yourcompany.atlassian.net"
    space: "MOBILE"
  figma:
    enabled: true
    access: auto
    export_images: true     # PNG 1x → docs/specs/<feature>/design/
```

Credential **không** ghi vào overlay. `mehcli install` từ chối key dạng token/password. Có hai cách cấu hình:

- **MCP** (mặc định): `claude mcp add --transport http figma https://mcp.figma.com/mcp` và `claude mcp add --transport http atlassian https://mcp.atlassian.com/v2/mcp`, rồi đăng nhập OAuth qua `/mcp`. Cũng có thể dùng `mcp-atlassian` chạy local.
- **REST + env**: `FIGMA_ACCESS_TOKEN`; `CONFLUENCE_USERNAME` + `CONFLUENCE_API_TOKEN` (Cloud); `CONFLUENCE_PERSONAL_TOKEN` (Data Center).

Ví dụ prompt: "Build feature login từ https://yourcompany.atlassian.net/wiki/spaces/MOBILE/pages/123456/Login và https://www.figma.com/design/AbC123/App?node-id=12-34".

```
link → android-orchestrator Step 0 → android-spec-ingest → docs/specs/login.md (status: ready | draft)
     → draft: dừng hỏi user các open question blocking → ready → flow orchestrator như cũ
```

Spec dùng format `blueprints/feature-spec/template.md`. Chỗ suy luận hoặc thiếu dữ liệu được đánh dấu `[INFERRED → OQ-n]` / `[MISSING → OQ-n]`. UI state không có trong Figma là open question không chặn. API, auth, flag hoặc AC mơ hồ là open question chặn. Chi tiết: `skills/android-spec-ingest/SKILL.md`.

---

## Release history

Mỗi version một dòng. Chi tiết đầy đủ xem [`CHANGELOG.md`](./CHANGELOG.md).

- **v0.1.0**: harness 2 lớp đầu tiên, gồm 14 rule ARCH, 10 rule CORO, 5 skill, blueprint `ItemCatalog`, Konsist và `verify.sh`
- **v0.2.0**: CLI quản lý vòng đời (`init`/`install`/`update`/`uninstall`), manifest, `--dry-run`/`--yes`
- **v0.3.0**: cài đặt một lệnh qua `bootstrap.sh`, thêm `mehcli self-update` và `mehcli version`
- **v0.4.0**: `kotlin-conventions` (12 rule KOT), skill coroutines, workflow fix-bug và review-PR, các role trong `agents/`
- **v0.5.0**: skill network và database, workflow refactor và release, knowledge/data, Detekt
- **v0.6.0**: skill refactor, debug và performance, 3 blueprint, knowledge patterns/security/performance, rubrics/regression, Lint
- **v0.7.0**: data layer nhiều lựa chọn: Ktor/Ktorfit/Retrofit và SQLDelight/Room
- **v0.8.0**: `architecture.profile`, `rule_overrides` (lý do từ 50 ký tự trở lên), `enforcement.mode`
- **v0.9.0**: agent orchestration gồm 4 mode: single, team, parallel-features, auto
- **v0.10.0**: Factory pack gồm task YAML contract, build 4 level, auto-fix có fingerprint, phân loại lỗi, chọn model theo tier
- **v0.10.1 và v0.10.2**: MIT LICENSE và `CONTRIBUTING.md`
- **v0.11.0**: ARCH-004 mới, Repository không kế thừa `BaseRepository`, API trả `ApiResult` qua CallAdapter (Retrofit) / Converter (Ktorfit) / `safeRequest` (Ktor)
- **v0.13.0**: skill `android-spec-ingest` tuỳ chọn sinh `docs/specs/<feature>.md` từ Confluence + Figma (MCP hoặc REST + env), block `spec_sources`, blueprint `feature-spec`

**Sắp tới — v1.0.0**: Production proof, có từ 3 product trở lên dùng trong production và đo được ROI.

---

## References

- **Repo**: https://github.com/huypqapero/mobile-engineering-harness
- **Releases**: https://github.com/huypqapero/mobile-engineering-harness/releases
- **Changelog**: [`CHANGELOG.md`](./CHANGELOG.md)
- **Entry point AI agent**: [`AGENTS.md`](./AGENTS.md)
- **Overlay schema**: [`overlay.schema.yaml`](./overlay.schema.yaml)

### External resources

- [Clean Architecture — Uncle Bob](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Google Guide to app architecture](https://developer.android.com/topic/architecture)
- [Kotlin Coroutines best practices](https://developer.android.com/kotlin/coroutines/coroutines-best-practices)
- [Compose stability](https://developer.android.com/jetpack/compose/performance/stability)
- [Konsist](https://docs.konsist.lemonappdev.com/)
- [Detekt](https://detekt.dev)

### Related

Harness được design cho mọi Android/CMP product consume qua overlay. Chưa có public reference consumer repo.

---

## License

[MIT License](./LICENSE) — Copyright © 2026 huypqapero.

Free for commercial + private use. Attribution appreciated nhưng không required.

## Contributing

Issue + PR welcome. Khi contribute:
1. Open issue mô tả scope + rationale trước
2. Follow rule trong constitution/
3. Add Konsist/Detekt rule đi kèm nếu add rule mới
4. Update CHANGELOG + bump version
5. Test regression với ít nhất 1 real overlay nếu có

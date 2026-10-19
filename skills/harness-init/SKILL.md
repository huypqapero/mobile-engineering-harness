---
name: harness-init
description: Khởi tạo `.harness-overlay/overlay.yaml` cho consumer product từ gradle metadata + branding input. Scout `settings.gradle.kts`, `libs.versions.toml`, `AndroidManifest.xml` để auto-detect stack; hỏi 3 branding key còn thiếu; validate schema; output overlay ready-to-use. Trigger khi user nói "init harness", "setup harness overlay", "generate overlay cho project", hoặc lần đầu consume upstream harness.
priority: P0
---

# Skill: harness-init

## Trigger

- "Setup harness cho project này"
- "Init overlay"
- "Generate `.harness-overlay/overlay.yaml`"
- "Harness-init"
- Khi phát hiện consumer project chưa có `.harness-overlay/overlay.yaml` hoặc overlay thiếu field.

## Inputs

Bắt buộc có từ project root:
- `settings.gradle.kts` hoặc `settings.gradle` — list modules.
- `gradle/libs.versions.toml` hoặc `build.gradle.kts` — detect UI/DI/Network/Database stack.
- `AndroidManifest.xml` hoặc `build.gradle.kts namespace` — package root.

Hỏi user (interactive via AskUserQuestion):
- PRODUCT_NAME: tên product CamelCase (vd `Acme`).
- THEME_PREFIX: tiền tố theme (thường trùng PRODUCT_NAME).
- THEME_CLASS: tên class theme wrapper (vd `AcmeTheme`).

## Prerequisites

Trước khi init, đọc:

1. `overlay.schema.yaml` — schema reference, 17 keys và enum values.
2. `harness.yaml.template` — template với placeholder.
3. `references/overlay-schema-mapping.md` — map từ gradle marker → overlay key.

## Execution procedure

### Step 1 — Precondition check

```bash
# Target project root
PROJECT_ROOT="${1:-$PWD}"

# Required files
test -f "$PROJECT_ROOT/settings.gradle.kts" || test -f "$PROJECT_ROOT/settings.gradle" || {
  echo "ERROR: settings.gradle(.kts) not found. Run from Android/KMP project root."
  exit 1
}
```

Nếu `.harness-overlay/overlay.yaml` đã tồn tại:
- Hỏi user: overwrite / merge / abort.
- Nếu merge: giữ user-filled fields, chỉ fill fields trống.

### Step 2 — Auto-detect stack

Run `scripts/detect-stack.sh "$PROJECT_ROOT"` → output JSON:

```json
{
  "ui_framework": "compose-multiplatform|compose-android|xml-android",
  "di_framework": "koin|hilt|manual",
  "network_framework": "ktor|ktorfit|retrofit",
  "database_framework": "sqldelight|room|datastore|none",
  "mvi_base_class": "BaseViewModel",
  "package_root": "com.example.app",
  "modules": ["composeApp", "presenter", "domain", "data"]
}
```

Detection rules (xem `references/overlay-schema-mapping.md` cho full table):

| Marker trong libs.versions.toml / build.gradle | Infer |
|---|---|
| `compose-multiplatform` plugin | ui_framework = compose-multiplatform |
| `com.google.dagger.hilt-android` plugin | di_framework = hilt |
| `io.insert-koin:koin-core` | di_framework = koin |
| `io.ktor:ktor-client-core` | network_framework = ktor |
| `de.jensklingenberg.ktorfit` plugin | network_framework = ktorfit |
| `com.squareup.retrofit2:retrofit` | network_framework = retrofit |
| `app.cash.sqldelight` plugin | database_framework = sqldelight |
| `androidx.room:room-runtime` | database_framework = room |

### Step 3 — Interactive branding

Dùng `AskUserQuestion` để fill 3 key không detect được:

```
Q1: PRODUCT_NAME (CamelCase, vd Acme)?
Q2: THEME_PREFIX (default = PRODUCT_NAME)?
Q3: THEME_CLASS (default = <THEME_PREFIX>Theme)?
```

### Step 4 — Render overlay

Run `scripts/render-overlay.sh` với stack JSON + branding answers → ghi `.harness-overlay/overlay.yaml`:

```yaml
harness_version: ">=0.1.0"
product:
  name: <PRODUCT_NAME>
  package: <package_root>
  app_display_name: <PRODUCT_NAME>
modules:
  app: <modules[0]>
  presenter: presenter
  domain: domain
  data: data
ui:
  theme_prefix: <THEME_PREFIX>
  theme_class: <THEME_CLASS>
stack:
  ui: <ui_framework>
  mvi: <mvi_base_class>
  di: <di_framework>
  network: <network_framework>
  database: <database_framework>
  image: coil
  serialization: kotlinx-serialization
features_root: feature
targets:
  - android
  - ios
```

### Step 5 — Validate schema

Run `~/.claude/skills/.venv/bin/python3 scripts/validate-overlay.py .harness-overlay/overlay.yaml overlay.schema.yaml`:

- Required keys đủ chưa.
- Enum values hợp lệ chưa (vd `ui_framework` phải thuộc enum).
- Dependency logic đúng chưa (vd nếu `targets` chứa `ios`, `ui_framework` không được là `xml-android`).

### Step 6 — Install skills (project-local)

Symlink harness skills vào consumer `./.claude/skills/`:

```bash
HARNESS_ROOT="$(cd .harness-overlay/upstream 2>/dev/null && pwd || echo "")"
if [ -z "$HARNESS_ROOT" ]; then
  echo "WARN: .harness-overlay/upstream not found; agent must symlink harness repo first"
else
  "$HARNESS_ROOT/scripts/activate-claude-skills.sh" install \
    --from "$HARNESS_ROOT/skills" \
    --target .claude/skills
fi
```

Mỗi skill `./.claude/skills/<name>/` là symlink về `$HARNESS_ROOT/skills/<name>/`. Claude Code sẽ auto-discover.

### Step 7 — Install agents (project-local)

Tương tự Step 6, nhưng cho agents:

```bash
"$HARNESS_ROOT/scripts/activate-claude-agents.sh" install \
  --from "$HARNESS_ROOT/agents" \
  --target .claude/agents
```

### Step 8 — Install SessionStart hook

Patch consumer `./.claude/settings.json` để hook `check-overlay.sh` chạy mỗi session start:

```bash
"$HARNESS_ROOT/scripts/install-session-hook.sh" install --target .
```

Hook sẽ nhắc agent trigger `harness-init` nếu overlay bị xóa/missing sau này.

### Step 9 — Report

Output format:

```markdown
# Overlay init report — <date>

## Detected
- Modules: composeApp, presenter, domain, data
- Stack: compose-multiplatform + koin + ktor + sqldelight
- Package: com.example.app

## Interactive answers
- PRODUCT_NAME: Acme
- THEME_PREFIX: Acme
- THEME_CLASS: AcmeTheme

## Overlay written
- `.harness-overlay/overlay.yaml` (17 keys)
- Validation: PASS

## Installed
- Skills (project-local): N symlinks at `./.claude/skills/`
- Agents (project-local): M symlinks at `./.claude/agents/`
- SessionStart hook: `./.claude/hooks/check-overlay.sh` + settings.json patched

## Next step
- Restart Claude Code (hoặc `/reload`) để discover skills + agents mới.
- Thử: `/coding-feature` hoặc `/testing-android` để verify.
```

Lưu report vào `plans/reports/harness-init-<date>-<slug>.md`.

## Required policies

- Không ghi đè `.harness-overlay/overlay.yaml` existing khi user chưa confirm.
- Không hard-fail nếu auto-detect miss 1 field; fallback hỏi user.
- Luôn validate schema trước khi tuyên bố DONE.
- Script fail → report lỗi, không fix skill code trừ khi task cho phép.

## Reference selection

Load thêm khi task yêu cầu:

- Multi-module layout phức tạp → `references/overlay-schema-mapping.md §Multi-module`
- Hilt vs Koin migration cân nhắc → `references/overlay-schema-mapping.md §DI`

## Output contract

Deliverable:

- `.harness-overlay/overlay.yaml` filled + validated.
- `plans/reports/harness-init-<date>-<slug>.md` report.
- Pointer tiếp theo: skill coding-* nào consumer nên gọi.

## Validation

Trước khi tuyên bố DONE:

- [ ] `.harness-overlay/overlay.yaml` tồn tại.
- [ ] Schema validate PASS.
- [ ] Required keys (harness_version, product.name, product.package, modules.*, ui.theme_prefix, ui.theme_class) không trống.
- [ ] Enum fields match schema (ui_framework, di_framework, network_framework, database_framework).
- [ ] `./.claude/skills/` chứa symlink về `$HARNESS_ROOT/skills/*`.
- [ ] `./.claude/agents/` chứa symlink về `$HARNESS_ROOT/agents/*`.
- [ ] `./.claude/hooks/check-overlay.sh` tồn tại và `./.claude/settings.json` có entry SessionStart.
- [ ] Report ghi vào `plans/reports/`.

## Failure / recovery

- `detect-stack.sh` không parse được `libs.versions.toml` → fallback hỏi user tất cả stack keys qua AskUserQuestion.
- `validate-overlay.py` fail → in diff, hỏi user fix hay abort.
- `.harness-overlay/` không có quyền ghi → report `BLOCKED`, hỏi user chọn directory khác.

## Anti-patterns bị cấm

- Hardcode branding fields không hỏi user (PRODUCT_NAME, THEME_*).
- Skip validation step để DONE sớm.
- Ghi overlay partial (missing required keys) rồi tuyên bố success.
- Overwrite existing overlay không ask confirm.

---

## Harness context

- Workflow: standalone one-shot (chạy 1 lần khi onboard consumer).
- Guardrails: `~/.claude/rules/primary-workflow.md, development-rules.md, review-audit-self-decision.md, orchestration-protocol.md`

---
name: library
description: Tạo hoặc tách KMP/Android library (SDK pure headless, KHÔNG UI) publish ở repo riêng. Dispatcher theo --mode new|extract. new = greenfield SDK-mindset-first (Phase 0 Brainstorm → Contract → SPI Freeze → Impl → TestingKit → Publish). extract = tách code đã ổn định ≥ 6 tháng từ product (scout coupling → lift-and-shift vs clean-slate → extract + migrate source). Spawn library-architect agent. Trigger "tạo lib X dùng chung cho A và B", "design SDK cho ...", "tách module Y thành lib riêng".
priority: P1
---

# Skill: library

Dispatcher cho KMP/Android library repo riêng (SDK pure, **không UI** — nếu có UI + business flow dùng `/feature-store`).

**File này chỉ chọn mode.** Chi tiết thực thi nằm ở reference riêng từng mode — sau khi chọn mode, **đọc đúng file reference đó và theo procedure trong đó**:

| Mode | Khi nào | Reference thực thi |
|---|---|---|
| `--mode new` | Code **chưa tồn tại** — tạo lib mới từ zero | `references/mode-new.md` |
| `--mode extract` | Code **đã tồn tại** trong 1 product (≥ 2 consumer, ổn định ≥ 6 tháng) — tách + migrate source | `references/mode-extract.md` |

## Mode selection

1. User nêu rõ `--mode` → theo đó.
2. Không nêu → suy từ trigger phrase: "tạo / design / build SDK" → `new`; "tách / extract / move code" → `extract`.
3. Vẫn mơ hồ → hỏi user 1 câu, **không tự đoán**.

## Trigger

**`--mode new`**: "Tạo lib X dùng chung cho A và B" · "Build shared library / SDK cho ..." · "Setup repo lib Y publish Maven Central" · "Design SDK / khung SDK để review".

**`--mode extract`**: "Tách module Y ở product A thành lib riêng" · "Product B/C/D cần dùng lại code từ product A, extract thành lib" · "Move <feature> sang shared library".

**Không trigger** (cả hai mode):
- **< 5 consumer** (real + straw-man) cho clean-slate → BLOCKED, downgrade shared module monorepo. (`extract` lift-and-shift chấp nhận ≥ 2 real consumer với justification scope hẹp.)
- Chỉ 1 consumer thật ("sẽ có consumer sau") → BLOCKED.
- Util nhỏ < 200 lines cho 1-2 project → giữ monorepo shared module.
- Lib có UI Compose + business flow → dùng `/feature-store`.
- (`extract`) Boundary code chưa ổn định (< 6 tháng, API đang bay) → chờ settle.

## Prerequisites (shared — đọc trước mọi mode)

SDK knowledge set, bắt buộc đầy đủ, không skim. Skip → bias feature-first drift.

1. `knowledge/coding-sdk/sdk-mindset.md [KB → develop/sdk, kb_search "coding sdk sdk mindset"]` — ADR SDK-001..006
2. `knowledge/coding-sdk/pattern-catalog.md [KB → develop/sdk, kb_search "coding sdk pattern catalog"]`
3. `knowledge/coding-sdk/layered-architecture.md [KB → develop/sdk, kb_search "coding sdk layered architecture"]` — 5-layer kernel-plugin
4. `knowledge/coding-sdk/brainstorm-process.md [KB → develop/sdk, kb_search "coding sdk brainstorm process"]` — 10-step Phase 0
5. `knowledge/coding-sdk/testing-kit-rules.md [KB → develop/sdk, kb_search "coding sdk testing kit rules"]` — TestingKit mandatory
6. `knowledge/coding-sdk/essentials.md [KB → develop/sdk, kb_search "coding sdk essentials"]` — rule checklist
7. `agents/library-architect.md`
8. `agents/workflows/library-flow.md`
9. (`--mode extract`) `skills/coding-scout/SKILL.md` — map coupling

## Inputs (shared)

- Responsibility 1 câu (không có "và")
- Platform scope: KMP common / androidMain / cần iosMain?
- Publishing target: Maven Central / internal Nexus / GitHub Packages
- (Optional) Deadline, Steward (ai own lib dài hạn)

Input riêng từng mode: xem đầu file reference tương ứng.

## Shared policies (áp dụng mọi mode)

- SDK-level: SDK-001..006, Pattern Catalog mapping, 5-layer + Konsist rule, TEST-001..011 TestingKit. BRAIN-001..007 cho `new` + clean-slate `extract`.
- Rule-level (essentials): LIB-SCOPE / LIB-API / LIB-CONFIG / LIB-PORT / LIB-DEP / LIB-PATTERN / LIB-PUBLISH / LIB-GOV. `extract` thêm LIB-RES (resource prefix, consumer-rules).
- Validation gate, failure/recovery, anti-patterns, overlay gate: **chi tiết trong file reference từng mode**.

## Harness context

- Workflow: `agents/workflows/library-flow.md` (greenfield + extract mode)
- Agent: `agents/library-architect.md`
- Knowledge: full SDK knowledge set trong `knowledge/coding-sdk/`
- Scout (`extract`): `skills/coding-scout/SKILL.md`
- Sibling skill: `skills/feature-store/SKILL.md` (có UI + flow)
- Guardrails: `~/.claude/rules/development-rules.md`, `review-audit-self-decision.md`, `orchestration-protocol.md`

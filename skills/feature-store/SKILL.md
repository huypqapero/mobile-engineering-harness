---
name: feature-store
description: Tạo hoặc tách Feature Store artifact (KMP/Android library CÓ UI + business flow, 2-module topology core + ui, Runtime Config pattern cho adapter). Dispatcher theo --mode new|extract. new = greenfield FS-mindset-first (Phase 0 Brainstorm → Capability Contract → API + Theme + Flow → 2-module layout → testFixtures → Publish). extract = tách feature đã ổn định ≥ 6 tháng từ product (scout 5 coupling → lift-and-shift vs clean-slate → extract + migrate source). Spawn feature-store-architect agent. Trigger "tạo feature store X dùng chung cho A/B/C", "tách feature Y thành shared" (paywall, chatbot, onboarding, KYC).
priority: P1
---

# Skill: feature-store

Dispatcher cho Feature Store artifact repo riêng (KMP/Android library **có UI Compose + business flow**, 2-module topology `:core` + `:ui`, Runtime Config pattern). **Không UI** (headless infrastructure, API facade) → dùng `/library`.

**File này chỉ chọn mode.** Chi tiết thực thi nằm ở reference riêng từng mode — sau khi chọn mode, **đọc đúng file reference đó và theo procedure trong đó**:

| Mode | Khi nào | Reference thực thi |
|---|---|---|
| `--mode new` | Feature **chưa tồn tại** — tạo FS mới từ zero | `references/mode-new.md` |
| `--mode extract` | Feature **đã tồn tại** trong 1 product (có UI + flow, ≥ 2 consumer, ổn định ≥ 6 tháng) — tách + migrate source | `references/mode-extract.md` |

## Mode selection

1. User nêu rõ `--mode` → theo đó.
2. Không nêu → suy từ trigger phrase: "tạo / design / build" → `new`; "tách / extract / move" → `extract`.
3. Vẫn mơ hồ → hỏi user 1 câu, **không tự đoán**.

## Trigger

**`--mode new`**: "Tạo feature store X dùng chung cho A/B/C" · "Design kit UI dùng chung nhiều app" (paywall, chatbot, onboarding, KYC, review-prompt) · "Build shared flow Y publish Maven cho N consumer" · "Design khung feature-store để review".

**`--mode extract`**: "Tách feature Y ở product A thành feature store riêng" · "Product B/C/D cần dùng lại UI + flow của feature Y, extract thành shared" · "Move <feature-with-UI-and-flow> sang shared feature store".

**Không trigger** (cả hai mode):
- **Không có UI** (headless, chỉ data/logic) → dùng `/library` (SDK pure)
- **Không có business flow** (chỉ UI component thuần) → consider shared-ui-component (hiếm)
- **< 5 consumer** (real + straw-man) cho clean-slate → BLOCKED, downgrade feature thường trong app. (`extract` lift-and-shift chấp nhận ≥ 2 real consumer với justification scope hẹp.)
- Chỉ 1 app ("sẽ có app thứ 2 sau") → BLOCKED, giữ trong app presenter
- (`extract`) Boundary feature chưa ổn định (< 6 tháng, UI/flow đang bay) → chờ settle

## Prerequisites (shared — đọc trước mọi mode)

FS knowledge set, bắt buộc đầy đủ, không skim. Skip → bias feature-first drift, mất 4 guarantee FS.

1. `knowledge/coding-feature-store/mindset.md [KB → develop/feature-store, kb_search "coding feature store mindset"]` — ADR FS-001..007
2. `knowledge/coding-feature-store/capability-contract.md [KB → develop/feature-store, kb_search "coding feature store capability contract"]` — 6-trục YAML + decision tree
3. `knowledge/coding-feature-store/module-topology.md [KB → develop/feature-store, kb_search "coding feature store module topology"]` — 2-module template
4. `knowledge/coding-feature-store/data-port-runtime-config.md [KB → develop/feature-store, kb_search "coding feature store data port runtime config"]` — Runtime Config pattern + compileOnly + classpath guard
5. `knowledge/coding-feature-store/theme-adapter.md [KB → develop/feature-store, kb_search "coding feature store theme adapter"]` — Theme Contract (nếu U ≥ U1)
5b. `knowledge/coding-feature-store/scoped-composition.md [KB → develop/feature-store, kb_search "coding feature store scoped composition"]` — Scoped Composition U2S: app tự sắp layout màn từ khối đã nối state + intent (nếu U ≥ U2S)
6. `knowledge/coding-feature-store/testing-kit.md [KB → develop/feature-store, kb_search "coding feature store testing kit"]` — testFixtures mandatory
7. `knowledge/coding-feature-store/essentials.md [KB → develop/feature-store, kb_search "coding feature store essentials"]` — checklist rule cứng
8. `knowledge/coding-sdk/sdk-mindset.md [KB → develop/sdk, kb_search "coding sdk sdk mindset"]` — rule BCV/deprecation chung
9. `knowledge/coding-sdk/brainstorm-process.md [KB → develop/sdk, kb_search "coding sdk brainstorm process"]` — 10-step Phase 0 (dùng chung)
10. `agents/feature-store-architect.md` — role mindset
11. (`--mode extract`) `agents/workflows/feature-store-flow.md` — pipeline 12 stage
12. (`--mode extract`) `skills/coding-scout/SKILL.md` — map coupling

## Inputs (shared)

- Responsibility 1 câu (không "và")
- Platform scope: KMP common / androidMain / cần iosMain?
- **Design system diversity**: consumer chung Material 3 hay mỗi app brand khác? (ảnh hưởng Theme Contract scope)
- **Layout diversity theo từng màn**: các app chỉ đổi màu/chữ (U1), đổi 1-3 chỗ (U2), đổi bố cục nhưng giữ hành vi (U2S), hay UI khác hẳn (U3)?
- **Backend diversity**: consumer chung backend hay mix (Firebase, REST, GraphQL)? (ảnh hưởng D1/D2/D3)
- (Optional) Deadline, Steward (owner FS dài hạn)

Input riêng từng mode: xem đầu file reference tương ứng.

## Shared policies (áp dụng mọi mode)

- Luôn Scope lock trước spawn agent. Fail → block.
- Phase 0 Brainstorm trước Capability Contract (`new` + clean-slate `extract`).
- 2-module topology mandatory, không chấp nhận 3+ module trừ RFC đặc biệt.
- `compileOnly` adapter deps mandatory nếu có adapter built-in.
- Theme Contract mandatory nếu U ≥ U1 (dù lift-and-shift chỉ map Material3 1:1).
- Mức U chốt **theo từng màn**. Màn có U2S: `sealed interface XxxScope` + `XxxHost(content = { DefaultXxxLayout() })`, việc bắt buộc nằm ngoài `content` (`scoped-composition.md §FS-SCOPE-002`).
- testFixtures mandatory trước release 1.0.
- Breaking change `:core` yêu cầu RFC + sign-off ≥ 3/5.
- Quality gate, report format, failure/recovery, overlay gate, agent-spawn prompt: **chi tiết trong file reference từng mode**.

## Harness context

- Agent: `agents/feature-store-architect.md`
- Workflow pipeline: `agents/workflows/feature-store-flow.md` (12 stage, greenfield + extract mode)
- Knowledge: `knowledge/coding-feature-store/` (7 file) + shared `knowledge/coding-sdk/`
- Scout (`extract`): `skills/coding-scout/SKILL.md`
- Sibling skill: `skills/library/SKILL.md` (SDK pure headless, không UI)
- Guardrails: `~/.claude/rules/development-rules.md`, `review-audit-self-decision.md`, `orchestration-protocol.md`

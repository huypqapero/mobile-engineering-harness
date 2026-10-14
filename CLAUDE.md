# Claude Code — Harness Entry (Upstream)

Đây là entry chung cho mọi sản phẩm consume upstream harness qua `.harness-overlay/`.

**Nạp context theo thứ tự:**

1. Project root `CLAUDE.md` — context project-specific (ưu tiên cao nhất)
2. `.harness-overlay/overlay.yaml` — vars product
3. `.harness-overlay/upstream/AGENTS.md` (file bên cạnh folder này) — generic entry
4. Skill tương ứng trong `skills/<name>/SKILL.md`
5. `constitution/` khi cần verify rule
6. `knowledge/` khi cần kiến thức nền

Xem `AGENTS.md` cho đầy đủ: file index, task routing, quality gates, report format, placeholder reference.

**Short reminder** (chi tiết trong AGENTS.md):

- Dependency: `{{MODULE_APP}} → {{MODULE_PRESENTER}} → {{MODULE_DOMAIN}} ← {{MODULE_DATA}}`
- `{{MODULE_DOMAIN}}` thuần Kotlin common, cấm import Android/iOS/Firebase
- ViewModel chỉ gọi UseCase hoặc Repository interface, không gọi `*Impl`
- Platform SDK chỉ ở `{{MODULE_DATA}}/{androidMain,iosMain}` qua `expect/actual`
- 1 feature = 1 package tự chứa trong `{{MODULE_PRESENTER}}/.../{{FEATURES_ROOT}}/`
- MVI 1 chiều: Intent → State + Effect
- Mọi screen đủ 5 state (loading / empty / error / offline / success)
- Trước DONE: unit test touched + Konsist + Detekt + build

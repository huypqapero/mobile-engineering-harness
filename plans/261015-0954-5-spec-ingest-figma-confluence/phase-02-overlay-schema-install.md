# Phase 2 — Overlay schema + install validation

### Task 2.1 — Block spec_sources trong schema
- Goal: `overlay.schema.yaml` có block `spec_sources` optional, default tắt, có mô tả.
- Target files: `overlay.schema.yaml` (chèn sau block `orchestration:`, trước `detekt:`).
- Steps: thêm `spec_sources.confluence.{enabled: false, access: auto, base_url: "", space: ""}`, `spec_sources.figma.{enabled: false, access: auto, export_images: true}`, comment giải thích `access` options + env var + MCP, câu "KHÔNG ghi token vào file này".
- Verify: `python3 -c "import yaml;d=yaml.safe_load(open('overlay.schema.yaml'));s=d['spec_sources'];assert s['confluence']['enabled'] is False and s['figma']['enabled'] is False and s['confluence']['access']=='auto';print('ok')"` in `ok`.

### Task 2.2 — Validate spec_sources trong install.sh
- Goal: `read_overlay_vars` từ chối `access` sai enum và key giống credential dưới `spec_sources`.
- Target files: `install.sh` (Python heredoc trong `read_overlay_vars`, cạnh các validate khác).
- Steps:
  1. Duyệt đệ quy `spec_sources`; key (lowercase) chứa `token`, `password`, `secret`, `api_key`, `credential` → stderr `ERROR: spec_sources.<path> looks like a credential; ...` + exit 1.
  2. `spec_sources.{confluence,figma}.access` ∉ `mcp|rest|auto` → ERROR + exit 1.
  3. Không thêm mapping var mới (không template nào cần).
- Verify: chạy 3 overlay tạm trong `mktemp -d` (ngoài repo) qua `bash install.sh install --overlay <dir> --dry-run --yes`: (a) không có `spec_sources` → exit 0; (b) `figma.access: ftp` → exit ≠ 0, stderr chứa `access`; (c) `confluence.api_token: x` → exit ≠ 0, stderr chứa `credential`. Cả ba khớp.

## Failure Protocol
If any Verify step does not meet its stated pass condition, STOP this phase.
Do not improvise a fix, retry blindly, or reason around the failure.
Spawn the `kongming` subagent for next-step counsel and pass:
- the phase and task id,
- what you attempted (the steps you ran),
- the exact command and its full output,
- the pass condition it failed to meet.
Apply kongming's guidance, then re-run the Verify step.
If `kongming` cannot be spawned in this environment, STOP and report the same
failure evidence to the user. Never continue by self-reasoning.

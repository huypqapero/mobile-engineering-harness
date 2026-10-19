#!/usr/bin/env bash
# SessionStart hook: verify consumer project has `.harness-overlay/overlay.yaml`.
# If missing, print a reminder on stdout; Claude Code shows it to the agent via SessionStart event.
# Exit 0 always (non-blocking); the agent decides whether to trigger harness-init.

set -euo pipefail

PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
OVERLAY="$PROJECT_ROOT/.harness-overlay/overlay.yaml"

if [ ! -f "$OVERLAY" ]; then
  cat <<'MSG'
HARNESS CHECK: .harness-overlay/overlay.yaml không tồn tại ở project root.
Khi gặp placeholder {{X}} trong SKILL.md/knowledge/blueprint, resolve sẽ fail.
Khuyến nghị: trigger skill `harness-init` để scaffold overlay trước khi bắt đầu task coding/business.
MSG
  exit 0
fi

# Fast sanity: file is readable and non-empty
if [ ! -s "$OVERLAY" ]; then
  echo "HARNESS CHECK: $OVERLAY tồn tại nhưng empty. Chạy harness-init --revalidate."
  exit 0
fi

exit 0

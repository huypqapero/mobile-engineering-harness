#!/usr/bin/env bash
# code-graph.sh — code graph (Graphify, code-only, offline) dùng chung cho các skill harness
#
# Usage:
#   code-graph.sh ensure <worktree>   Build graph cho HEAD của worktree nếu chưa có; in đường dẫn graph.json
#   code-graph.sh path <worktree>     In đường dẫn graph.json của HEAD nếu đã build (exit 1 nếu chưa)
#   code-graph.sh prune <worktree> [keep]   Giữ <keep> bản build mới nhất (mặc định 3, ~65MB/bản trên repo 4.5k file)
#
# Graph nằm ngoài cây làm việc: <git-common-dir>/graphify/<commit>/graphify-out/graph.json,
# nên mọi worktree cùng commit dùng chung một bản và không bao giờ bị commit nhầm.
# Worktree có thay đổi chưa commit → key <commit>-dirty, luôn build lại.
# Build: tree-sitter AST, GRAPHIFY_BACKEND=none (không gọi LLM, không gửi code ra ngoài).
#
# Exit: 0 ok · 1 chưa có graph / build lỗi (log ở stderr) · 2 thiếu graphify hoặc không phải git repo
# Cài graphify: uv tool install graphifyy

set -euo pipefail

KEEP_DEFAULT=3
LOCK_WAIT_SECONDS=300

die() { printf 'code-graph: %s\n' "$1" >&2; exit "${2:-1}"; }

resolve() {
  local wt="$1"
  [ -d "$wt" ] || die "không thấy thư mục $wt" 2
  WT="$(cd "$wt" && pwd)"
  git -C "$WT" rev-parse --git-dir >/dev/null 2>&1 || die "$WT không phải git repo" 2
  COMMON="$(cd "$WT" && cd "$(git rev-parse --git-common-dir)" && pwd)"
  ROOT="$COMMON/graphify"
  KEY="$(git -C "$WT" rev-parse --short=12 HEAD)"
  DIRTY=0
  if [ -n "$(git -C "$WT" status --porcelain --untracked-files=no)" ]; then
    DIRTY=1
    KEY="$KEY-dirty-$(printf %s "$WT" | cksum | cut -d" " -f1)"
  fi
  DEST="$ROOT/$KEY"
  GRAPH="$DEST/graphify-out/graph.json"
}

newest_cache() {
  # Bản build sạch mới nhất có AST cache, để seed (cache theo nội dung file nên dùng chéo commit được)
  ls -1dt "$ROOT"/*/graphify-out/cache 2>/dev/null | grep -v -- '-dirty/' | head -1 || true
}

build() {
  local tmp="$ROOT/.tmp-$KEY-$$" seed
  rm -rf "$tmp"
  mkdir -p "$tmp/graphify-out"
  seed="$(newest_cache)"
  [ -n "$seed" ] && cp -R "$seed" "$tmp/graphify-out/cache"
  if ! GRAPHIFY_BACKEND=none graphify extract "$WT" --code-only --out "$tmp" >"$tmp/build.log" 2>&1; then
    tail -20 "$tmp/build.log" >&2
    rm -rf "$tmp"
    die "graphify extract lỗi cho $WT"
  fi
  printf '{"commit": "%s", "dirty": %s, "worktree": "%s", "built": "%s", "graphify": "%s"}\n' \
    "$(git -C "$WT" rev-parse HEAD)" "$([ "$DIRTY" -eq 1 ] && echo true || echo false)" "$WT" \
    "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$(graphify --version 2>/dev/null | awk '{print $2}')" >"$tmp/meta.json"
  rm -rf "$DEST"
  mv "$tmp" "$DEST"
}

cmd_ensure() {
  command -v graphify >/dev/null 2>&1 || die "chưa cài graphify (uv tool install graphifyy)" 2
  resolve "$1"
  if [ "$DIRTY" -eq 0 ] && [ -f "$GRAPH" ]; then
    echo "$GRAPH"
    return 0
  fi
  mkdir -p "$ROOT"
  local waited=0
  LOCK="$ROOT/.lock-$KEY"
  until mkdir "$LOCK" 2>/dev/null; do
    # Worker khác đang build cùng commit: chờ rồi dùng luôn bản đó
    [ "$waited" -ge "$LOCK_WAIT_SECONDS" ] && die "chờ lock $LOCK quá ${LOCK_WAIT_SECONDS}s (xoá thư mục lock nếu tiến trình build đã chết)"
    sleep 2
    waited=$((waited + 2))
  done
  trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT
  if [ "$DIRTY" -eq 1 ] || [ ! -f "$GRAPH" ]; then
    build
  fi
  cmd_prune_quiet "$KEEP_DEFAULT"
  echo "$GRAPH"
}

cmd_path() {
  resolve "$1"
  [ -f "$GRAPH" ] || exit 1
  echo "$GRAPH"
}

cmd_prune_quiet() {
  local keep="$1"
  { ls -1dt "$ROOT"/*/ 2>/dev/null || true; } | tail -n +"$((keep + 1))" | while read -r d; do
    [ "${d%/}" = "$DEST" ] || rm -rf "$d"
  done
}

[ $# -ge 2 ] || { awk 'NR==1 { next } /^$/ { exit } { sub(/^# ?/, ""); print }' "$0"; exit 2; }
case "$1" in
  ensure) cmd_ensure "$2" ;;
  path)   cmd_path "$2" ;;
  prune)  resolve "$2"; cmd_prune_quiet "${3:-$KEEP_DEFAULT}" ;;
  *)      die "lệnh không hỗ trợ: $1" 2 ;;
esac

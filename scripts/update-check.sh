#!/usr/bin/env bash
# Check for a newer mobile-engineering-harness and, when opted in, update it.
#
# Usage:
#   update-check.sh check [--quiet]      fetch upstream now, refresh the cache, print status
#   update-check.sh notify               SessionStart hook: print one line when an update is known;
#                                        refresh the cache in the background once a day
#   update-check.sh auto on|off|status   opt in/out of automatic `git pull --ff-only`
#
# Auto-update only moves a clean checkout on $MEH_UPDATE_BRANCH (default main). A pinned tag
# (detached HEAD) or another branch is reported, never moved. Rendered overlays in product repos
# are never touched: re-render with `mehcli update --overlay .harness-overlay` after an update.
# Env: MEH_UPDATE_CHECK=0 disables notify, MEH_UPDATE_INTERVAL seconds between checks (86400).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UP="${MEH_UPSTREAM_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/mobile-engineering-harness"
CONF_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/mobile-engineering-harness"
KEY="$(printf '%s' "$UP" | cksum | cut -d' ' -f1)"
CACHE="$CACHE_DIR/update-$KEY.env"
LOCK="$CACHE_DIR/update-$KEY.lock"
AUTO_FLAG="$CONF_DIR/auto-update"
INTERVAL="${MEH_UPDATE_INTERVAL:-86400}"
ALLOWED_BRANCH="${MEH_UPDATE_BRANCH:-main}"

usage() {
  sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

g() { GIT_TERMINAL_PROMPT=0 git -C "$UP" "$@"; }

# True when $1 is a strictly newer version than $2 (both vX.Y.Z).
newer() { [ -n "$1" ] && [ "$1" != "$2" ] && [ "$(printf '%s\n%s\n' "$1" "$2" | sort -V | tail -1)" = "$1" ]; }

write_cache() {
  mkdir -p "$CACHE_DIR"
  {
    for k in CHECKED_AT CURRENT CURRENT_TAG LATEST_TAG BRANCH BEHIND DIRTY FETCH_OK AUTO_BLOCKED UPDATED_FROM UPDATED_TO; do
      printf '%s=%q\n' "$k" "${!k:-}"
    done
  } > "$CACHE.tmp"
  mv "$CACHE.tmp" "$CACHE"
}

load_cache() {
  CHECKED_AT=0 CURRENT="" CURRENT_TAG="" LATEST_TAG="" BRANCH="" BEHIND=0 DIRTY=0 FETCH_OK=1
  AUTO_BLOCKED="" UPDATED_FROM="" UPDATED_TO=""
  # shellcheck disable=SC1090
  [ -f "$CACHE" ] && . "$CACHE"
  return 0
}

message() {
  if [ -n "$UPDATED_TO" ]; then
    echo "Harness đã tự cập nhật $UPDATED_FROM → $UPDATED_TO. Repo app có overlay: chạy \`mehcli update --overlay .harness-overlay\` để render lại template; thay đổi xem CHANGELOG.md."
  elif [ -z "$BRANCH" ]; then
    if newer "$LATEST_TAG" "$CURRENT_TAG"; then
      echo "Harness đang pin $CURRENT_TAG, bản mới nhất $LATEST_TAG. Đổi pin khi sẵn sàng: git -C $UP checkout $LATEST_TAG, rồi \`mehcli update --overlay .harness-overlay\`."
    fi
  elif [ "${BEHIND:-0}" -gt 0 ]; then
    local why=""
    [ -n "$AUTO_BLOCKED" ] && why=" Không tự cập nhật được: $AUTO_BLOCKED."
    echo "Harness có bản mới: $CURRENT chậm $BEHIND commit so với origin/$BRANCH (tag mới nhất $LATEST_TAG). Cập nhật: \`mehcli self-update\`.$why"
  fi
}

do_check() {
  local quiet="${1:-}"
  if [ ! -d "$UP/.git" ]; then
    [ -n "$quiet" ] || echo "Harness tại $UP không phải git clone; không kiểm tra được bản mới."
    return 0
  fi
  mkdir -p "$CACHE_DIR"
  if ! mkdir "$LOCK" 2>/dev/null; then
    # another check is running; a lock older than 10 minutes is stale
    if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +10 2>/dev/null)" ]; then rmdir "$LOCK" 2>/dev/null || true; fi
    mkdir "$LOCK" 2>/dev/null || return 0
  fi
  local rc=0
  refresh "$quiet" || rc=$?
  rmdir "$LOCK" 2>/dev/null || true
  return "$rc"
}

refresh() {
  local quiet="${1:-}"
  load_cache
  local prev_from="$UPDATED_FROM" prev_to="$UPDATED_TO"
  FETCH_OK=1
  g fetch --tags --quiet origin 2>/dev/null || FETCH_OK=0
  CURRENT="$(g describe --tags --always 2>/dev/null || echo unknown)"
  CURRENT_TAG="$(g describe --tags --abbrev=0 2>/dev/null || echo "")"
  LATEST_TAG="$(g tag --list 'v*' --sort=-v:refname | head -1)"
  BRANCH="$(g symbolic-ref --short -q HEAD || echo "")"
  BEHIND=0
  if [ -n "$BRANCH" ] && g rev-parse -q --verify '@{u}' >/dev/null 2>&1; then
    BEHIND="$(g rev-list --count 'HEAD..@{u}')"
  fi
  DIRTY="$(g status --porcelain --untracked-files=no | wc -l | tr -d ' ')"
  AUTO_BLOCKED="" UPDATED_FROM="$prev_from" UPDATED_TO="$prev_to"

  if [ -f "$AUTO_FLAG" ] && [ "$BEHIND" -gt 0 ]; then
    if [ "$BRANCH" != "$ALLOWED_BRANCH" ]; then
      AUTO_BLOCKED="đang ở branch $BRANCH, chỉ tự cập nhật trên $ALLOWED_BRANCH"
    elif [ "$DIRTY" -gt 0 ]; then
      AUTO_BLOCKED="$UP có $DIRTY file đang sửa"
    elif g pull --ff-only --quiet 2>/dev/null; then
      UPDATED_FROM="$CURRENT"
      CURRENT="$(g describe --tags --always 2>/dev/null || echo unknown)"
      CURRENT_TAG="$(g describe --tags --abbrev=0 2>/dev/null || echo "")"
      UPDATED_TO="$CURRENT" BEHIND=0
    else
      AUTO_BLOCKED="git pull --ff-only thất bại (lịch sử đã rẽ nhánh)"
    fi
  fi
  CHECKED_AT="$(date +%s)"
  write_cache

  [ -n "$quiet" ] && return 0
  [ "$FETCH_OK" = 1 ] || echo "Cảnh báo: không fetch được origin, kết quả dựa trên dữ liệu cục bộ."
  local msg
  msg="$(message)"
  if [ -n "$msg" ]; then
    echo "$msg"
    UPDATED_FROM="" UPDATED_TO=""; write_cache  # shown once
  else
    echo "Harness $CURRENT đã mới nhất (branch ${BRANCH:-detached}, tag mới nhất ${LATEST_TAG:-không có})."
  fi
}

do_notify() {
  [ "${MEH_UPDATE_CHECK:-1}" = "0" ] && return 0
  load_cache
  local now age
  now="$(date +%s)"
  age=$(( now - ${CHECKED_AT:-0} ))
  if [ "$age" -ge "$INTERVAL" ]; then
    ( nohup "$SCRIPT_DIR/update-check.sh" check --quiet >/dev/null 2>&1 & ) || true
  fi
  [ -f "$CACHE" ] || return 0
  local msg
  msg="$(message)"
  if [ -n "$msg" ]; then
    echo "HARNESS UPDATE: $msg"
    if [ -n "$UPDATED_TO" ]; then UPDATED_FROM="" UPDATED_TO=""; write_cache; fi
  fi
}

do_auto() {
  case "${1:-status}" in
    on)  mkdir -p "$CONF_DIR"; : > "$AUTO_FLAG"; echo "auto-update: on (chỉ trên branch $ALLOWED_BRANCH, cây làm việc sạch)" ;;
    off) rm -f "$AUTO_FLAG"; echo "auto-update: off" ;;
    status) if [ -f "$AUTO_FLAG" ]; then echo "auto-update: on"; else echo "auto-update: off"; fi ;;
    *) usage 1 ;;
  esac
}

case "${1:-}" in
  check)  shift; do_check "$( [ "${1:-}" = "--quiet" ] && echo quiet || true )" ;;
  notify) do_notify || true ;;
  auto)   shift; do_auto "${1:-status}" ;;
  -h|--help|"") usage 0 ;;
  *) usage 1 ;;
esac
exit 0

#!/usr/bin/env bash
#
# Load-reproduction harness for the frontend suite (APRAS-86).
#
# Owns both sides of the reproduction: the CPU side-car that starves the
# workers, and the vitest invocation that runs under it. Every load parameter
# is a literal below, so a run can be reproduced from this file alone and
# nothing about the load has to be carried in prose.
#
#   level A (gate)        12 hogs, 1 suite instance,  --max-workers=16
#   level B (diagnostic)  24 hogs, 2 suite instances, --max-workers=16
#
# Level B is never a gate: at that oversubscription, tests unrelated to any
# given diff are starved out by the machine, so a green bar is unreachable and
# a red one measures the host rather than the change.
#
# Usage:  scripts/load-test.sh [a|b]      (npm run test:load / test:load:max)

set -o pipefail

LEVEL="$(printf '%s' "${1:-a}" | tr '[:upper:]' '[:lower:]')"

# ---- pinned load levels -----------------------------------------------------
TARGET_PATH="src/features/user-administration"
MAX_WORKERS=16

case "$LEVEL" in
  a) HOG_COUNT=12; SUITE_COUNT=1 ;;
  b) HOG_COUNT=24; SUITE_COUNT=2 ;;
  *)
    echo "usage: $(basename "$0") [a|b]" >&2
    exit 2
    ;;
esac

FRONTEND_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="${LOAD_TEST_LOG_DIR:-$FRONTEND_DIR/.load-test-logs}"
mkdir -p "$LOG_DIR"

# ---- cleanup ----------------------------------------------------------------
# PIDs are collected into arrays as the children are spawned. zsh/bash
# `jobs -p` is empty in a non-interactive script, and relying on it once left
# 12 `yes` processes running after the script exited, which silently poisoned
# every measurement taken afterwards. The arrays are the only reliable handle.
HOG_PIDS=()
SUITE_PIDS=()

cleanup() {
  local pid
  for pid in ${SUITE_PIDS[@]+"${SUITE_PIDS[@]}"}; do
    kill "$pid" 2>/dev/null
  done
  for pid in ${HOG_PIDS[@]+"${HOG_PIDS[@]}"}; do
    kill "$pid" 2>/dev/null
  done
  wait 2>/dev/null
}
trap cleanup EXIT INT TERM

# ---- report the host, since 12 hogs on 8 cores is not 12 hogs on 16 ---------
CORES="$(sysctl -n hw.physicalcpu 2>/dev/null || nproc 2>/dev/null || echo '?')"
echo "== load-test level ${LEVEL}: ${HOG_COUNT} hogs, ${SUITE_COUNT} suite instance(s)"
echo "== vitest: run ${TARGET_PATH} --pool=threads --max-workers=${MAX_WORKERS}"
echo "== physical cores: ${CORES}"
echo "== logs: ${LOG_DIR}"

# ---- the side-car -----------------------------------------------------------
for _hog in $(seq 1 "$HOG_COUNT"); do
  yes >/dev/null 2>&1 &
  HOG_PIDS+=("$!")
done
echo "== hogs up: ${#HOG_PIDS[@]}"

# ---- the suites -------------------------------------------------------------
STAMP="$(date +%Y%m%d-%H%M%S)-$$"
LOGS=()
for instance in $(seq 1 "$SUITE_COUNT"); do
  log="${LOG_DIR}/level-${LEVEL}-${STAMP}-suite${instance}.log"
  LOGS+=("$log")
  (
    cd "$FRONTEND_DIR" || exit 1
    npx vitest run "$TARGET_PATH" --pool=threads --max-workers="$MAX_WORKERS"
  ) >"$log" 2>&1 &
  SUITE_PIDS+=("$!")
done

status=0
for pid in "${SUITE_PIDS[@]}"; do
  wait "$pid" || status=1
done
SUITE_PIDS=()

# ---- results ----------------------------------------------------------------
for log in "${LOGS[@]}"; do
  echo
  echo "---- ${log}"
  grep -E '^\s*(Test Files|Tests|Duration)\s' "$log"
  grep -E '^\s*(FAIL|×)\s' "$log" | sort -u
done

exit "$status"

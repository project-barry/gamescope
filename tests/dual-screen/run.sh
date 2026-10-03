#!/bin/bash
# Headless checks for the bottom screen (DUAL-SCREEN.md): window rules,
# focus and drawing, against GAMESCOPE_BOTTOM_SCREEN_SIMULATE.
#
# Needs a gamescope build, Xwayland, python3 with python-xlib, and a Vulkan
# device gamescope accepts (Mesa 25 lavapipe works where /dev/udmabuf exists).
#
# Usage: tests/dual-screen/run.sh [build-dir] [scenario...]
#   build-dir defaults to ./build; scenarios default to all of them.
#   Logs and frames go to $OUT (default: a new temporary directory).
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
BUILD="$(cd "${1:-build}" && pwd)"; shift || true
OUT="${OUT:-$(mktemp -d)}"
mkdir -p "$OUT"
SCENARIOS=("$@")
(( ${#SCENARIOS[@]} )) || SCENARIOS=(melonds azahar cemu property_wins disabled stress png touch)

# gamescope starts its child through gamescopereaper, found on PATH.
export PATH="$BUILD/src:$PATH"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-$(mktemp -d)}"
# The AYN Thor's bottom panel: 1080x1240, turned one step back.
export GAMESCOPE_BOTTOM_SCREEN_SIMULATE=1080x1240@3

rc=0
for s in "${SCENARIOS[@]}"; do
  log="$OUT/$s.log"
  rm -f "$log" "$OUT/$s.png"
  (
    [[ $s == disabled ]] && export GAMESCOPE_BOTTOM_SCREEN_TITLES=
    GS_LOG="$log" GAMESCOPE_BOTTOM_SCREEN_SIMULATE_PNG="$OUT/$s.png" \
      timeout 120 "$BUILD/src/gamescope" --backend headless -W 1280 -H 800 --xwayland-count 1 -- \
      python3 "$HERE/bottomtest.py" "$s" >"$log" 2>&1
    echo "gamescope exit: $?" >>"$log"
  )
  grep -E '^(PASS|FAIL|RESULT)|gamescope exit|Assertion|Segmentation|terminate called' "$log"
  grep -q "RESULT $s: PASS" "$log" || rc=1
done
echo "logs and frames: $OUT"
exit $rc

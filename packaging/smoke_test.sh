#!/usr/bin/env bash
# Check a packaged Linux app without a screen: the example pavements are next
# to it, Qt's X11/Wayland plugins find every library, the app stays up with its
# single engine worker, and it writes the calculation memorial to the user's
# log folder. CI runs it on each package.
# Usage: packaging/smoke_test.sh <beam_calculator executable or its link>
set -euo pipefail
shopt -s nullglob

exe="$(readlink -f "$1")"
internal="$(dirname "$exe")/_internal"
examples="$(dirname "$exe")/exemplos"
logs="${XDG_STATE_HOME:-$HOME/.local/state}/beam_calculator/log"

# Arquivo › Abrir exemplo… opens this folder
if [[ ! -f "$examples/template.pavement.yaml" ]]; then
    echo "No example pavements in $examples" >&2
    exit 1
fi

# The offscreen run below never loads the desktop plugins: check them with ldd
plugins=("$internal"/PySide6/Qt/plugins/platforms/libq{xcb,wayland}*.so)
missing="$(LD_LIBRARY_PATH="$internal" ldd "${plugins[@]}" | awk '/not found/ {print $1}' | sort -u)"
if [[ -n "$missing" ]]; then
    echo "Libraries missing for the desktop plugins: $missing" >&2
    exit 1
fi

QT_QPA_PLATFORM=offscreen "$1" &
app=$!
sleep 20
if ! kill -0 "$app" 2>/dev/null; then
    echo "The app exited during startup" >&2
    exit 1
fi

# The window, the engine worker and multiprocessing's resource tracker; a worker
# that opened another window would spawn workers of its own
pids=()
for proc in /proc/[0-9]*; do
    if [[ "$(readlink "$proc/exe" 2>/dev/null)" == "$exe" ]]; then
        pids+=("${proc#/proc/}")
    fi
done
kill "${pids[@]}" 2>/dev/null || true
if (( ${#pids[@]} < 2 || ${#pids[@]} > 3 )); then
    echo "Expected the window and its engine worker, found ${#pids[@]} processes" >&2
    exit 1
fi

logs_written=("$logs"/beam_calculator_*.log)
if (( ${#logs_written[@]} == 0 )); then
    echo "No calculation memorial in $logs" >&2
    exit 1
fi
echo "OK: ${#pids[@]} processes, memorial in $logs"

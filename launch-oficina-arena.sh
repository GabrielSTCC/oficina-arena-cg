#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

export SDL_VIDEO_WAYLAND_WMCLASS="${SDL_VIDEO_WAYLAND_WMCLASS:-oficina-arena}"
export SDL_VIDEO_X11_WMCLASS="${SDL_VIDEO_X11_WMCLASS:-oficina-arena}"

PY=".venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="python3"
fi

exec "$PY" main.py

#!/usr/bin/env python3
"""Oficina Arena — aplicação 3D (Computação Gráfica)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# PRIME offload: sem isso o GLX do notebook híbrido escolhe a Intel integrada.
# setdefault respeita override (ex.: __GLX_VENDOR_LIBRARY_NAME=mesa).
if any(Path(p).exists() for p in ("/usr/lib/libGLX_nvidia.so.0", "/usr/lib64/libGLX_nvidia.so.0")):
    os.environ.setdefault("__NV_PRIME_RENDER_OFFLOAD", "1")
    os.environ.setdefault("__GLX_VENDOR_LIBRARY_NAME", "nvidia")

import OpenGL

OpenGL.ERROR_CHECKING = False

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.application import Application
from gfx.hud import AppState


def main() -> None:
    parser = argparse.ArgumentParser(description="Oficina Arena 3D — Computação Gráfica")
    parser.add_argument("--screenshot", type=Path, default=None, help="Salva PNG e encerra")
    parser.add_argument("--frames", type=int, default=30, help="Frames antes do screenshot")
    parser.add_argument("--cam", choices=("orbital", "planta", "seguir"), default=None)
    parser.add_argument("--seed", type=int, default=None, help="Seed opcional (padrão: aleatória)")
    parser.add_argument("--sim", action="store_true", help="Inicia direto na partida em andamento")
    parser.add_argument("--fast-turns", type=int, default=0, help="Avança N turnos antes de renderizar")
    parser.add_argument("--at-base", action="store_true", help="Foca câmera na base (0,0)")
    parser.add_argument(
        "--state",
        choices=(
            "tutorial",
            "menu",
            "config",
            "modo",
            "robo",
            "moeda",
            "moeda_cara",
            "moeda_coroa",
            "jogo",
            "vitoria",
        ),
        default=None,
        help="Abre diretamente em um estado específico da UI",
    )
    args = parser.parse_args()

    init_state = AppState.TUTORIAL
    if args.state == "menu":
        init_state = AppState.MENU_PRINCIPAL
    elif args.sim or args.fast_turns > 0 or args.state in ("jogo", "vitoria"):
        init_state = AppState.EM_JOGO

    app = Application(seed=args.seed, initial_state=init_state)

    if args.state == "tutorial":
        app.state = AppState.TUTORIAL
    elif args.state == "config":
        app._execute_ui_action("menu_config")
    elif args.state == "robo":
        app._enter_robot_select()
    elif args.state == "modo":
        app._confirm_robot_select()
    elif args.state == "moeda":
        app._enter_coin_choice()
    elif args.state in ("moeda_cara", "moeda_coroa"):
        app._enter_coin_choice()
        res = "cara" if args.state == "moeda_cara" else "coroa"
        app._start_coin_toss("cara", forced_result=res)
        app.coin.update(app.coin.toss_duration + 0.05)
        app.state = AppState.MOEDA_RESULTADO
        app.hud.mark_dirty()

    if args.sim or args.fast_turns > 0 or args.state == "vitoria":
        app.bridge.start_from_workshop(app.workshop, seed=args.seed, new_random_map=False)
        app._snap_robots_to_bases()
    if args.state == "vitoria":
        from core.partida import ResultadoPartida

        app.bridge.last_result = ResultadoPartida.VITORIA_ALFA
        app.bridge.running = False
        app._seen_result = ResultadoPartida.VITORIA_ALFA
        app._enter_victory(app.actor_alfa, is_alfa=True)
    last_events: list[tuple[str, int, bool, str]] = []
    for _ in range(max(0, args.fast_turns)):
        app.bridge.accum = app.bridge.turn_interval
        app.bridge.update(0.0, app.workshop)
        ev = app.bridge.pop_step_events()
        if ev:
            last_events = ev
        app.bridge.mirror_minerios_to_scene(app.workshop)
    if args.fast_turns > 0:
        cells = app.bridge.robot_cells()
        app.actor_alfa.snap_to(cells["Alfa"], yaw_deg=45.0, on_base=app._is_base_cell(cells["Alfa"]))
        app.actor_beta.snap_to(cells["Beta"], yaw_deg=225.0, on_base=app._is_base_cell(cells["Beta"]))
        for who, delta_bat, is_trap, ev_txt in last_events:
            target = app.actor_alfa if who == "Alfa" else app.actor_beta
            target.trigger_step_feedback(delta_bat, is_trap=is_trap, event_text=ev_txt)
        app.bridge.accum = -5.0
    if args.at_base:
        from scene.catalog import cell_to_world

        app.actor_alfa.snap_to((0, 0), yaw_deg=135.0, on_base=True)
        app.camera.target = cell_to_world(0, 0)
    if args.cam:
        from gfx.camera import CameraMode

        modes = {
            "orbital": CameraMode.ORBITAL,
            "planta": CameraMode.PLANTA,
            "seguir": CameraMode.SEGUIR,
        }
        app.camera.set_mode(modes[args.cam])
    app.run(
        screenshot_path=args.screenshot,
        max_frames=args.frames if args.screenshot is not None else None,
    )


if __name__ == "__main__":
    main()

"""Loop GLFW: Menus (Principal, Configurações, Modos), Moeda 3D, P1/P2/COM e render Phong+HUD."""

from __future__ import annotations

import random
import time
from pathlib import Path

import glfw
import glm
import numpy as np
from OpenGL.GL import (
    GL_BLEND,
    GL_COLOR_BUFFER_BIT,
    GL_CULL_FACE,
    GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST,
    GL_FALSE,
    GL_FRONT,
    GL_ONE_MINUS_SRC_ALPHA,
    GL_RGB,
    GL_SRC_ALPHA,
    GL_TEXTURE0,
    GL_TEXTURE2,
    GL_TEXTURE4,
    GL_TEXTURE_2D,
    GL_TRUE,
    GL_UNSIGNED_BYTE,
    glActiveTexture,
    glBindTexture,
    glBlendFunc,
    glClear,
    glClearColor,
    glCullFace,
    glDepthMask,
    glDisable,
    glEnable,
    glReadPixels,
    glViewport,
)
from PIL import Image

import audio.music as music
from audio.sfx import play_voice, stop_voice
from gfx.camera import Camera, CameraMode
from gfx.hud import AppState, HudOverlay
from gfx.mesh import MAT_BASE_ALFA, MAT_BASE_BETA, Material
from gfx.mesh_loader import DOWNLOADED_ROBOTS
from gfx.postprocess import PostProcess
from gfx.shader import Shader
from gfx.shadow_map import ShadowMap
from scene.catalog import CellKind, ROBOT_ALFA, ROBOT_BETA, cell_to_world
from scene.coin_actor import CoinActor
from scene.placeable import Placeable
from scene.robot_actor import RobotActor
from scene.robot_models import RobotModel, load_robot_models
from scene.workshop import GRID_H, GRID_W, HOLO_HEIGHT, Workshop
import world  # noqa: F401 — registra path de config/core/ia
from core.partida import ResultadoPartida
from world.bridge import GameMode, WorldBridge

_FOG_COLOR = glm.vec3(0.02, 0.03, 0.045)
_SKY_AMBIENT = glm.vec3(0.09, 0.12, 0.18)
_GROUND_AMBIENT = glm.vec3(0.03, 0.04, 0.06)
_DIR_LIGHT_DIR = glm.vec3(-0.35, -1.0, 0.42)
_DIR_LIGHT_COLOR = glm.vec3(0.44, 0.50, 0.62)
_HOLO_COLOR = glm.vec3(0.18, 0.86, 1.0)

ROOT = Path(__file__).resolve().parents[1]
_FOCUS_ROBOT = "robo3"
_MAT_NEUTRAL = Material(glm.vec3(1.0, 1.0, 1.0), glm.vec3(0.22, 0.24, 0.28), 44.0)
_BASE_ALFA_CELL = (0, 0)


class Application:
    def __init__(self, *, seed: int | None = None, initial_state: AppState = AppState.TUTORIAL) -> None:
        music.init()
        if not glfw.init():
            raise RuntimeError("Falha ao iniciar GLFW")
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        self.win = glfw.create_window(1280, 720, "OCAM — Oficina Cosy da Arena de Mineração", None, None)
        if not self.win:
            glfw.terminate()
            raise RuntimeError("Falha ao criar janela")
        glfw.make_context_current(self.win)
        self._apply_window_icon()
        glfw.set_key_callback(self.win, self._on_key)
        glfw.set_cursor_pos_callback(self.win, self._on_cursor)
        glfw.set_mouse_button_callback(self.win, self._on_mouse)
        glfw.set_scroll_callback(self.win, self._on_scroll)
        glfw.set_framebuffer_size_callback(self.win, self._on_resize)

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glClearColor(float(_FOG_COLOR.x), float(_FOG_COLOR.y), float(_FOG_COLOR.z), 1.0)

        shader_dir = ROOT / "gfx" / "shaders"
        self.shader = Shader(shader_dir / "phong.vert", shader_dir / "phong.frag")
        self.hologram = Shader(shader_dir / "hologram.vert", shader_dir / "hologram.frag")
        self.depth_shader = Shader(shader_dir / "depth.vert", shader_dir / "depth.frag")
        self.shadow = ShadowMap(2048)
        fb_w, fb_h = glfw.get_framebuffer_size(self.win)
        self.post = PostProcess(shader_dir, max(fb_w, 1), max(fb_h, 1))
        self.hud = HudOverlay(shader_dir, max(fb_w, 1), max(fb_h, 1))
        self.workshop = Workshop(ROOT / "assets" / "models")
        self.camera = Camera(self.workshop.grid_w, self.workshop.grid_h)
        self.bridge = WorldBridge()
        self.coin = CoinActor(
            center_pos=glm.vec3(self.workshop.grid_w * 0.5, 1.45, self.workshop.grid_h * 0.5)
        )
        self.state: AppState = initial_state
        self._coin_result_timer: float = 0.0
        self._last_title: str = ""

        self.hover_cell = (0, 0)
        self.drag_orbit = False
        self.drag_pan = False
        self.drag_volume = False
        self.last_x = 0.0
        self.last_y = 0.0
        self.hud.volume = music.get_volume()
        music.set_volume(self.hud.volume)
        self.follow_alfa = True
        self.robot_keys = list(DOWNLOADED_ROBOTS.keys())
        self.test_idx = self.robot_keys.index(_FOCUS_ROBOT) if _FOCUS_ROBOT in self.robot_keys else 0
        self.solo_test = False
        self.robot_models: list[RobotModel] = load_robot_models()
        self.selected_robot_idx = 0
        self._victory_actor: RobotActor | None = None
        self._last_dance_key: str | None = None
        self._seen_result = None
        focus = _FOCUS_ROBOT if _FOCUS_ROBOT in self.workshop.meshes else "robo"
        focus_mesh = self.workshop.meshes[focus]
        focus_parts = self.workshop.robot_parts.get(focus, [])
        mid = (self.workshop.grid_w // 2, self.workshop.grid_h // 2)
        self.actor_alfa = RobotActor(
            Placeable(
                item=ROBOT_ALFA,
                mesh=focus_mesh,
                cell=_BASE_ALFA_CELL,
                material=_MAT_NEUTRAL,
                locked=True,
                parts=list(focus_parts),
            ),
            step_duration=self.bridge.turn_interval,
            base_kd=glm.vec3(0.68, 0.80, 0.90),
        )
        self.actor_beta = RobotActor(
            Placeable(
                item=ROBOT_BETA,
                mesh=focus_mesh,
                cell=self._base_beta_cell,
                material=_MAT_NEUTRAL,
                locked=True,
                parts=list(focus_parts),
            ),
            step_duration=self.bridge.turn_interval,
            base_kd=glm.vec3(0.88, 0.72, 0.62),
        )
        if self.robot_models:
            self.actor_alfa.set_model(self.robot_models[0])
            self.actor_beta.set_model(self.robot_models[min(1, len(self.robot_models) - 1)])
        self.hud.robo_nomes = [m.nome for m in self.robot_models] or ["Robo 3", "Robo 5"]
        self._seed_bases()
        self.bridge.seed_workshop_preview(self.workshop, seed=seed)
        self._snap_robots_to_bases()
        self.showcase: list[RobotActor] = self._build_showcase()
        self.workshop.begin_ghost((1, 1))
        self.camera.set_mode(CameraMode.ORBITAL)
        self._sync_camera_to_grid()
        self.camera.target = cell_to_world(*mid)
        self.camera.pitch = 40.0
        w, h = glfw.get_framebuffer_size(self.win)
        self.camera.aspect = max(w, 1) / max(h, 1)

    @property
    def _base_beta_cell(self) -> tuple[int, int]:
        return (self.workshop.grid_w - 1, self.workshop.grid_h - 1)

    def _grid_scale(self) -> float:
        return max(self.workshop.grid_w / float(GRID_W), self.workshop.grid_h / float(GRID_H))

    def _sync_camera_to_grid(self) -> None:
        self.camera.grid_w = self.workshop.grid_w
        self.camera.grid_h = self.workshop.grid_h
        self.camera.distance = 16.5 * self._grid_scale()

    def _snap_robots_to_bases(self) -> None:
        self.actor_alfa.stop_dance()
        self.actor_beta.stop_dance()
        self.actor_alfa.snap_to(_BASE_ALFA_CELL, yaw_deg=45.0, on_base=True)
        self.actor_beta.snap_to(self._base_beta_cell, yaw_deg=225.0, on_base=True)

    def _build_showcase(self) -> list[RobotActor]:
        actors: list[RobotActor] = []
        mid = (self.workshop.grid_w // 2, self.workshop.grid_h // 2)
        focus = _FOCUS_ROBOT if _FOCUS_ROBOT in self.workshop.meshes else "robo"
        mesh = self.workshop.meshes[focus]
        for i, model in enumerate(self.robot_models):
            cell = (mid[0] + (-1 if i == 0 else 1), mid[1])
            actor = RobotActor(
                Placeable(
                    item=ROBOT_ALFA if i == 0 else ROBOT_BETA,
                    mesh=mesh,
                    cell=cell,
                    material=_MAT_NEUTRAL,
                    locked=True,
                ),
                base_kd=glm.vec3(0.75, 0.78, 0.82),
            )
            actor.set_model(model)
            actor.snap_to(cell, yaw_deg=180.0, on_base=False)
            # offset visual X para ±1.3 do centro
            cx = self.workshop.grid_w * 0.5 + (-1.3 if i == 0 else 1.3)
            cz = self.workshop.grid_h * 0.5
            actor._visual = glm.vec3(cx, 0.0, cz)
            actor._from = glm.vec3(actor._visual)
            actor._to = glm.vec3(actor._visual)
            actors.append(actor)
        return actors

    def _clear_stage_props(self) -> None:
        """Remove minérios/paredes/armadilhas, mantendo só as bases (vitrine/vitória)."""
        keep = [o for o in self.workshop.objects if o.item.cell_kind == CellKind.BASE and o.locked]
        self.workshop.objects = keep
        self.workshop.occupancy = {o.cell: o for o in keep}
        self.workshop._cell_map_dirty = True

    def _play_selected_robot_voice(self) -> None:
        if not self.robot_models:
            return
        idx = self.selected_robot_idx % len(self.robot_models)
        key = self.robot_models[idx].key
        play_voice(ROOT / "assets" / "audio" / "voice" / f"{key}.mp3")

    def _enter_robot_select(self) -> None:
        self.bridge.pause(self.workshop)
        self._clear_stage_props()
        self.state = AppState.SELECAO_ROBO
        self.hud.selected_idx = self.selected_robot_idx
        self.hud.robo_nomes = [m.nome for m in self.robot_models]
        self.hud.mark_dirty()
        gw, gh = self.workshop.grid_w, self.workshop.grid_h
        self.camera.set_mode(CameraMode.ORBITAL)
        self.camera.target = glm.vec3(gw * 0.5, 0.85, gh * 0.5)
        self.camera.distance = 7.0
        self.camera.pitch = 8.0
        self.camera.yaw = 18.0
        self._play_selected_robot_voice()

    def _confirm_robot_select(self) -> None:
        stop_voice()
        if not self.robot_models:
            self.state = AppState.MENU_MODO
            self.hud.selected_idx = 0
            return
        idx = self.selected_robot_idx % len(self.robot_models)
        chosen = self.robot_models[idx]
        other = self.robot_models[(idx + 1) % len(self.robot_models)]
        self.actor_alfa.set_model(chosen)
        self.actor_beta.set_model(other)
        self.bridge.seed_workshop_preview(self.workshop)
        self._snap_robots_to_bases()
        self.state = AppState.MENU_MODO
        self.hud.selected_idx = 0
        self.hud.mark_dirty()
        self._sync_camera_to_grid()
        self.camera.target = cell_to_world(self.workshop.grid_w // 2, self.workshop.grid_h // 2)
        self.camera.pitch = 40.0

    def _enter_victory(self, winner: RobotActor, *, is_alfa: bool) -> None:
        self.state = AppState.VITORIA
        self._victory_actor = winner
        self._clear_stage_props()
        mid = (self.workshop.grid_w // 2, self.workshop.grid_h // 2)
        winner.snap_to(mid, yaw_deg=0.0, on_base=False)
        # ancora visual no centro geométrico da grade
        cx, cz = self.workshop.grid_w * 0.5, self.workshop.grid_h * 0.5
        winner._visual = glm.vec3(cx, 0.0, cz)
        winner._from = glm.vec3(winner._visual)
        winner._to = glm.vec3(winner._visual)
        if winner.dances:
            pool = [d for d in winner.dances if d.music_key != self._last_dance_key]
            if not pool:
                pool = list(winner.dances)
            entry = random.choice(pool)
            self._last_dance_key = entry.music_key
            winner.start_dance(entry.clip)
            music.play_loop(entry.music_path)
        self.hud.vitoria_is_alfa = is_alfa
        self.hud.vitoria_nome = winner.model_nome or winner.model_key
        self.hud.mark_dirty()
        self.camera.set_mode(CameraMode.ORBITAL)
        self.camera.target = glm.vec3(cx, 0.95, cz)
        self.camera.distance = 6.2
        self.camera.pitch = 12.0
        self.camera.yaw = 25.0

    def _leave_victory(self) -> None:
        music.stop()
        if self._victory_actor is not None:
            self._victory_actor.stop_dance()
        self._victory_actor = None
        self._snap_robots_to_bases()
        if self.bridge.has_next_round():
            self._execute_ui_action("jogo_prox_round")
        else:
            self._execute_ui_action("jogo_nova_serie")

    def _is_base_cell(self, cell: tuple[int, int]) -> bool:
        obj = self.workshop.occupancy.get(cell)
        if obj is not None and obj.item.cell_kind == CellKind.BASE:
            return True
        return cell in {_BASE_ALFA_CELL, self._base_beta_cell}

    # ------------------------------------------------------------------
    # Transições de Menu, Moeda 3D e Início de Partida
    # ------------------------------------------------------------------

    def _enter_main_menu(self) -> None:
        self.bridge.pause(self.workshop)
        self.state = AppState.MENU_PRINCIPAL
        self._last_dance_key = None
        self.hud.selected_idx = 0
        self.hud.mark_dirty()
        self.camera.set_mode(CameraMode.ORBITAL)
        self._sync_camera_to_grid()
        self.camera.target = cell_to_world(self.workshop.grid_w // 2, self.workshop.grid_h // 2)
        self.camera.pitch = 40.0

    def _enter_coin_choice(self) -> None:
        self.bridge.pause(self.workshop)
        self.bridge.seed_workshop_preview(self.workshop)
        self._snap_robots_to_bases()
        gw, gh = self.workshop.grid_w, self.workshop.grid_h
        self.coin.base_pos = glm.vec3(gw * 0.5, 1.45, gh * 0.5)
        self.coin.reset_for_choice()
        self.state = AppState.MOEDA_ESCOLHA
        self.hud.selected_idx = 0
        self.hud.mark_dirty()
        self.camera.set_mode(CameraMode.ORBITAL)
        self.camera.target = glm.vec3(gw * 0.5, 1.85, gh * 0.5)
        self.camera.yaw = 0.0
        self.camera.pitch = 56.0
        self.camera.distance = 4.6

    def _start_coin_toss(self, chosen_side: str, forced_result: str | None = None) -> None:
        self.coin.start_toss(chosen_side, forced_result=forced_result)
        self.state = AppState.MOEDA_GIRANDO
        self.hud.mark_dirty()

    def _begin_match_from_coin(self) -> None:
        self.bridge.starter = self.coin.winner_starter
        self.bridge.start_from_workshop(self.workshop, new_random_map=False)
        self._seen_result = None
        self._snap_robots_to_bases()
        self.state = AppState.EM_JOGO
        self.hud.mark_dirty()
        self.camera.set_mode(CameraMode.ORBITAL)
        self._sync_camera_to_grid()
        self.camera.target = cell_to_world(self.workshop.grid_w // 2, self.workshop.grid_h // 2)
        self.camera.yaw = 32.0
        self.camera.pitch = 42.0

    def _apply_window_icon(self) -> None:
        """Define o ícone da janela (barra de título / taskbar)."""
        icon_dir = ROOT / "assets" / "icons"
        paths = [icon_dir / f"app_icon_{s}.png" for s in (16, 32, 48, 64, 128, 256)]
        paths.append(icon_dir / "app_icon.png")
        images = []
        for p in paths:
            if not p.is_file():
                continue
            try:
                images.append(Image.open(p).convert("RGBA"))
            except Exception:
                pass
        if not images:
            return
        try:
            glfw.set_window_icon(self.win, len(images), images)
        except Exception:
            pass

    def _sync_window_maximized(self) -> None:
        maximized = bool(glfw.get_window_attrib(self.win, glfw.MAXIMIZED))
        if maximized != self.hud.window_maximized:
            self.hud.window_maximized = maximized
            self.hud.mark_dirty()

    def _toggle_maximize(self) -> None:
        if glfw.get_window_attrib(self.win, glfw.MAXIMIZED):
            glfw.restore_window(self.win)
        else:
            glfw.maximize_window(self.win)
        self._sync_window_maximized()

    def _set_volume(self, v: float) -> None:
        music.set_volume(v)
        self.hud.volume = music.get_volume()
        self.hud.mark_dirty()

    def _apply_volume_at_x(self, mx: float) -> None:
        v = self.hud.volume_from_x(mx)
        if v is not None:
            self._set_volume(v)

    def _execute_ui_action(self, action_id: str) -> None:
        if action_id == "win_close":
            glfw.set_window_should_close(self.win, True)
            return
        if action_id == "win_min":
            glfw.iconify_window(self.win)
            return
        if action_id == "win_max":
            self._toggle_maximize()
            return
        if action_id == "vol_down":
            self._set_volume(self.hud.volume - 0.1)
            return
        if action_id == "vol_up":
            self._set_volume(self.hud.volume + 0.1)
            return
        if action_id == "vol_bar":
            self._apply_volume_at_x(self.last_x)
            self.drag_volume = True
            return
        if action_id == "tutorial_continuar":
            self._enter_main_menu()
        elif action_id == "menu_tutorial":
            self.state = AppState.TUTORIAL
            self.hud.selected_idx = 0
        elif action_id == "menu_iniciar":
            self._enter_robot_select()
        elif action_id == "menu_config":
            self.state = AppState.MENU_CONFIG
            self.hud.selected_idx = 0
        elif action_id == "menu_sair":
            glfw.set_window_should_close(self.win, True)
        elif action_id.startswith("robo_sel:"):
            self.selected_robot_idx = int(action_id.split(":")[1])
            self.hud.selected_idx = self.selected_robot_idx
            self._play_selected_robot_voice()
        elif action_id == "robo_confirmar":
            self._confirm_robot_select()
        elif action_id == "robo_voltar":
            stop_voice()
            self._enter_main_menu()
        elif action_id.startswith("cfg:") and action_id.count(":") == 2:
            _, campo, delta_s = action_id.split(":")
            self.bridge.cfg.ajustar(campo, int(delta_s))
            self.bridge.seed_workshop_preview(self.workshop)
            self._snap_robots_to_bases()
            self._sync_camera_to_grid()
        elif action_id == "cfg_padrao":
            self.bridge.cfg.restaurar_padroes()
            self.bridge.seed_workshop_preview(self.workshop)
            self._snap_robots_to_bases()
            self._sync_camera_to_grid()
        elif action_id == "cfg_voltar":
            self.state = AppState.MENU_PRINCIPAL
            self.hud.selected_idx = 2
        elif action_id == "modo_com_com":
            self.bridge.mode = GameMode.COM_VS_COM
            self.bridge.reset_series()
            self._enter_coin_choice()
        elif action_id == "modo_p1_com":
            self.bridge.mode = GameMode.P1_VS_COM
            self.bridge.reset_series()
            self._enter_coin_choice()
        elif action_id == "modo_p1_p2":
            self.bridge.mode = GameMode.P1_VS_P2
            self.bridge.reset_series()
            self._enter_coin_choice()
        elif action_id == "modo_voltar":
            self.state = AppState.MENU_PRINCIPAL
            self.hud.selected_idx = 0
        elif action_id == "moeda_cara":
            self._start_coin_toss("cara")
        elif action_id == "moeda_coroa":
            self._start_coin_toss("coroa")
        elif action_id == "moeda_iniciar":
            self._begin_match_from_coin()
        elif action_id == "jogo_prox_round":
            self.bridge.round_atual += 1
            self._seen_result = None
            self._enter_coin_choice()
        elif action_id == "jogo_nova_serie":
            self.bridge.reset_series()
            self._seen_result = None
            self._enter_coin_choice()
        elif action_id == "jogo_menu":
            self._seen_result = None
            self._enter_main_menu()
        self.hud.mark_dirty()

    def _try_step_robot(self, dx: int, dz: int) -> None:
        """WASD: passo manual do robô Alfa (em P1 vs COM / P1 vs P2 ou modo pausado)."""
        if self.actor_alfa.busy:
            return
        if self.bridge.running:
            self.bridge.step_human("Alfa", dx, dz, self.workshop)
            return
        x, z = self.actor_alfa.placeable.cell
        nx, nz = x + dx, z + dz
        if not (0 <= nx < self.workshop.grid_w and 0 <= nz < self.workshop.grid_h):
            return
        occ = self.workshop.occupancy.get((nx, nz))
        if occ is not None and occ.item.cell_kind == CellKind.PAREDE:
            return
        is_trap = occ is not None and occ.item.cell_kind == CellKind.ARMADILHA
        custo = self.bridge.cfg.custo_passo_armadilha if is_trap else 2
        if self.bridge.partida is not None:
            alfa = self.bridge.partida.alfa
            if alfa.bateria < custo:
                return
            alfa.bateria = max(0, alfa.bateria - custo)
            alfa.posicao = (nx, nz)
            if (nx, nz) == _BASE_ALFA_CELL:
                alfa.bateria = alfa.bateria_maxima
                alfa.carga = 0
                alfa.itens = 0
        self.actor_alfa.trigger_step_feedback(
            -custo,
            is_trap=is_trap,
            event_text=f"ARMADILHA (-{custo} bat)" if is_trap else "",
        )
        self.actor_alfa.update(0.0, (nx, nz), on_base=self._is_base_cell((nx, nz)))
        self.camera.target = cell_to_world(nx, nz)

    def _try_step_beta(self, dx: int, dz: int) -> None:
        """Setas direcionais: passo manual do robô Beta (P2 no modo P1 vs P2)."""
        if self.actor_beta.busy:
            return
        if self.bridge.running and self.bridge.mode == GameMode.P1_VS_P2:
            self.bridge.step_human("Beta", dx, dz, self.workshop)

    def _apply_robot_test(self, idx: int) -> None:
        """Troca o modelo do Alfa (5–8); carrega partes texturizadas sob demanda."""
        if not self.robot_keys:
            return
        self.test_idx = idx % len(self.robot_keys)
        key = self.robot_keys[self.test_idx]
        if not self.workshop.robot_parts.get(key):
            from gfx.mesh_loader import load_downloaded_robot_parts

            parts = load_downloaded_robot_parts(key, target_height=1.8)
            self.workshop.robot_parts[key] = parts
            if parts:
                self.workshop.meshes[key] = parts[0][0]
        mesh = self.workshop.meshes.get(key)
        parts = self.workshop.robot_parts.get(key, [])
        if mesh is not None:
            self.actor_alfa.placeable.mesh = mesh
            self.actor_alfa.placeable.parts = list(parts)
            self.actor_alfa.placeable.material = _MAT_NEUTRAL
        self.camera.target = cell_to_world(*self.actor_alfa.placeable.cell)

    def _seed_bases(self) -> None:
        from scene.catalog import CATALOG

        base_item = next(i for i in CATALOG if i.id == "base")
        for cell, mat in ((_BASE_ALFA_CELL, MAT_BASE_ALFA), (self._base_beta_cell, MAT_BASE_BETA)):
            p = Placeable(
                item=base_item,
                mesh=self.workshop.meshes["base"],
                cell=cell,
                material=mat,
                locked=True,
            )
            self.workshop.objects.append(p)
            self.workshop.occupancy[cell] = p

    def save_screenshot(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        w, h = glfw.get_framebuffer_size(self.win)
        raw = glReadPixels(0, 0, w, h, GL_RGB, GL_UNSIGNED_BYTE)
        arr = np.frombuffer(raw, dtype=np.uint8).reshape((h, w, 3))
        img = Image.fromarray(np.flipud(arr), "RGB")
        img.save(path)
        print(f"Screenshot salvo em {path}")

    def _on_resize(self, _win, w: int, h: int) -> None:
        w, h = max(w, 1), max(h, 1)
        glViewport(0, 0, w, h)
        self.camera.aspect = w / h
        if hasattr(self, "post"):
            self.post.resize(w, h)
        if hasattr(self, "hud"):
            self.hud.resize(w, h)

    def _on_menu_key(self, key: int) -> None:
        if self.state == AppState.TUTORIAL:
            if key in (glfw.KEY_ENTER, glfw.KEY_KP_ENTER, glfw.KEY_SPACE):
                self._execute_ui_action("tutorial_continuar")
            elif key == glfw.KEY_ESCAPE:
                self._execute_ui_action("tutorial_continuar")
            self.hud.mark_dirty()
            return

        if self.state == AppState.MENU_PRINCIPAL:
            if key == glfw.KEY_UP:
                self.hud.selected_idx = (self.hud.selected_idx - 1) % 4
            elif key == glfw.KEY_DOWN:
                self.hud.selected_idx = (self.hud.selected_idx + 1) % 4
            elif key in (glfw.KEY_ENTER, glfw.KEY_KP_ENTER, glfw.KEY_SPACE):
                acts = ["menu_iniciar", "menu_tutorial", "menu_config", "menu_sair"]
                self._execute_ui_action(acts[self.hud.selected_idx % 4])
            elif key == glfw.KEY_ESCAPE:
                glfw.set_window_should_close(self.win, True)
            self.hud.mark_dirty()
            return

        if self.state == AppState.MENU_CONFIG:
            from gfx.hud import CONFIG_ROWS

            n_rows = len(CONFIG_ROWS)
            n_opts = n_rows + 2
            row = self.hud.selected_idx % n_opts
            if key == glfw.KEY_UP:
                self.hud.selected_idx = (self.hud.selected_idx - 1) % n_opts
            elif key == glfw.KEY_DOWN:
                self.hud.selected_idx = (self.hud.selected_idx + 1) % n_opts
            elif key == glfw.KEY_LEFT and row < n_rows:
                campo, passo = CONFIG_ROWS[row][1], CONFIG_ROWS[row][2]
                self._execute_ui_action(f"cfg:{campo}:{-passo}")
            elif key == glfw.KEY_RIGHT and row < n_rows:
                campo, passo = CONFIG_ROWS[row][1], CONFIG_ROWS[row][2]
                self._execute_ui_action(f"cfg:{campo}:{passo}")
            elif key in (glfw.KEY_ENTER, glfw.KEY_KP_ENTER, glfw.KEY_SPACE):
                if row == n_rows:
                    self._execute_ui_action("cfg_padrao")
                elif row == n_rows + 1:
                    self._execute_ui_action("cfg_voltar")
                elif row < n_rows:
                    campo, passo = CONFIG_ROWS[row][1], CONFIG_ROWS[row][2]
                    self._execute_ui_action(f"cfg:{campo}:{passo}")
            elif key == glfw.KEY_ESCAPE:
                self._execute_ui_action("cfg_voltar")
            self.hud.mark_dirty()
            return

        if self.state == AppState.SELECAO_ROBO:
            n = max(1, len(self.robot_models))
            if key in (glfw.KEY_LEFT, glfw.KEY_UP):
                self.selected_robot_idx = (self.selected_robot_idx - 1) % n
                self.hud.selected_idx = self.selected_robot_idx
                self._play_selected_robot_voice()
            elif key in (glfw.KEY_RIGHT, glfw.KEY_DOWN):
                self.selected_robot_idx = (self.selected_robot_idx + 1) % n
                self.hud.selected_idx = self.selected_robot_idx
                self._play_selected_robot_voice()
            elif key in (glfw.KEY_ENTER, glfw.KEY_KP_ENTER, glfw.KEY_SPACE):
                self._execute_ui_action("robo_confirmar")
            elif key == glfw.KEY_ESCAPE:
                self._execute_ui_action("robo_voltar")
            self.hud.mark_dirty()
            return

        if self.state == AppState.MENU_MODO:
            if key == glfw.KEY_UP:
                self.hud.selected_idx = (self.hud.selected_idx - 1) % 4
            elif key == glfw.KEY_DOWN:
                self.hud.selected_idx = (self.hud.selected_idx + 1) % 4
            elif key in (glfw.KEY_ENTER, glfw.KEY_KP_ENTER, glfw.KEY_SPACE):
                acts = ["modo_com_com", "modo_p1_com", "modo_p1_p2", "modo_voltar"]
                self._execute_ui_action(acts[self.hud.selected_idx % 4])
            elif key == glfw.KEY_ESCAPE:
                self._execute_ui_action("modo_voltar")
            self.hud.mark_dirty()
            return

        if self.state == AppState.VITORIA:
            if key in (glfw.KEY_ENTER, glfw.KEY_KP_ENTER, glfw.KEY_SPACE):
                self._leave_victory()
            elif key == glfw.KEY_ESCAPE:
                music.stop()
                if self._victory_actor is not None:
                    self._victory_actor.stop_dance()
                self._victory_actor = None
                self._enter_main_menu()
            self.hud.mark_dirty()
            return

        if self.state == AppState.MOEDA_ESCOLHA:
            if key in (glfw.KEY_LEFT, glfw.KEY_1):
                self.hud.selected_idx = 0
                if key == glfw.KEY_1:
                    self._execute_ui_action("moeda_cara")
            elif key in (glfw.KEY_RIGHT, glfw.KEY_2):
                self.hud.selected_idx = 1
                if key == glfw.KEY_2:
                    self._execute_ui_action("moeda_coroa")
            elif key in (glfw.KEY_ENTER, glfw.KEY_KP_ENTER, glfw.KEY_SPACE):
                act = "moeda_cara" if (self.hud.selected_idx % 2 == 0) else "moeda_coroa"
                self._execute_ui_action(act)
            elif key == glfw.KEY_ESCAPE:
                self.state = AppState.MENU_MODO
            self.hud.mark_dirty()
            return

        if self.state == AppState.MOEDA_RESULTADO:
            if key in (glfw.KEY_ENTER, glfw.KEY_KP_ENTER, glfw.KEY_SPACE):
                self._execute_ui_action("moeda_iniciar")
            elif key == glfw.KEY_ESCAPE:
                self._enter_main_menu()

    def _on_key(self, _win, key, _sc, action, mods) -> None:
        if action not in (glfw.PRESS, glfw.REPEAT):
            return
        if action == glfw.PRESS and (mods & glfw.MOD_ALT):
            if key == glfw.KEY_F4:
                glfw.set_window_should_close(self.win, True)
                return
            if key == glfw.KEY_F9:
                glfw.iconify_window(self.win)
                return
            if key == glfw.KEY_F10:
                self._toggle_maximize()
                return
        if key == glfw.KEY_F12 and action == glfw.PRESS:
            ts = int(time.time())
            self.save_screenshot(ROOT / "docs" / "screenshots" / f"capture_{ts}.png")
            return

        if self.state != AppState.EM_JOGO:
            self._on_menu_key(key)
            return

        # --- Controles durante EM_JOGO ---
        if key == glfw.KEY_ESCAPE or key == glfw.KEY_M:
            if self.workshop.ghost and key == glfw.KEY_ESCAPE and not self.bridge.running:
                self.workshop.cancel_ghost()
            else:
                self._enter_main_menu()
        elif key in (glfw.KEY_ENTER, glfw.KEY_KP_ENTER) and self.bridge.last_result is not None:
            if self.bridge.has_next_round():
                self._execute_ui_action("jogo_prox_round")
            else:
                self._execute_ui_action("jogo_nova_serie")
        elif key == glfw.KEY_C:
            self.camera.cycle()
        elif key == glfw.KEY_1:
            self.camera.set_mode(CameraMode.PLANTA)
        elif key == glfw.KEY_2:
            self.camera.set_mode(CameraMode.ORBITAL)
        elif key == glfw.KEY_3:
            self.camera.set_mode(CameraMode.SEGUIR)
        elif key in (glfw.KEY_SPACE, glfw.KEY_P):
            was_finished = self.bridge.last_result is not None
            was_turn_zero = self.bridge.partida is not None and self.bridge.partida.turno == 0 and not self.bridge.running
            self.bridge.toggle(self.workshop)
            if was_finished or was_turn_zero:
                self._snap_robots_to_bases()
        elif key == glfw.KEY_R:
            self.bridge.start_from_workshop(self.workshop, new_random_map=True)
            self._snap_robots_to_bases()
        elif key == glfw.KEY_TAB:
            self.follow_alfa = not self.follow_alfa
        elif key in (glfw.KEY_PERIOD, glfw.KEY_RIGHT_BRACKET):
            self.workshop.select_next(1)
        elif key in (glfw.KEY_COMMA, glfw.KEY_LEFT_BRACKET):
            self.workshop.select_next(-1)
        elif key == glfw.KEY_Q:
            self.workshop.rotate_ghost(-15)
        elif key == glfw.KEY_E:
            self.workshop.rotate_ghost(15)
        elif key in (glfw.KEY_EQUAL, glfw.KEY_KP_ADD):
            self.workshop.scale_ghost(1.1)
        elif key in (glfw.KEY_MINUS, glfw.KEY_KP_SUBTRACT):
            self.workshop.scale_ghost(1 / 1.1)
        elif key in (glfw.KEY_ENTER, glfw.KEY_KP_ENTER):
            self.workshop.confirm_ghost()
        elif key in (glfw.KEY_BACKSPACE, glfw.KEY_DELETE):
            if self.workshop.editing:
                self.workshop.remove_at(self.hover_cell)
        elif key == glfw.KEY_G:
            self.workshop.begin_ghost(self.hover_cell)
        elif key == glfw.KEY_T:
            self._apply_robot_test(self.test_idx + 1)
        elif key == glfw.KEY_Y:
            self.solo_test = not self.solo_test
        elif key in (glfw.KEY_5, glfw.KEY_6, glfw.KEY_7, glfw.KEY_8):
            self._apply_robot_test(key - glfw.KEY_5)
        # P1 (Alfa): W / A / S / D
        elif key == glfw.KEY_W:
            self._try_step_robot(0, -1)
        elif key == glfw.KEY_S:
            self._try_step_robot(0, 1)
        elif key == glfw.KEY_A:
            self._try_step_robot(-1, 0)
        elif key == glfw.KEY_D:
            self._try_step_robot(1, 0)
        # P2 (Beta no modo P1 vs P2): Setas Direcionais
        elif key == glfw.KEY_UP:
            self._try_step_beta(0, -1)
        elif key == glfw.KEY_DOWN:
            self._try_step_beta(0, 1)
        elif key == glfw.KEY_LEFT:
            self._try_step_beta(-1, 0)
        elif key == glfw.KEY_RIGHT:
            self._try_step_beta(1, 0)

    def _on_cursor(self, _win, x: float, y: float) -> None:
        self.hud.update_hover(x, y)
        dx, dy = x - self.last_x, y - self.last_y
        if self.drag_volume and self.state == AppState.MENU_PRINCIPAL:
            self._apply_volume_at_x(x)
        elif self.state == AppState.EM_JOGO:
            if self.drag_orbit:
                self.camera.orbit(dx, dy)
            elif self.drag_pan:
                self.camera.pan(dx, dy)
            elif self.workshop.editing:
                cell = self._pick_cell(x, y)
                if cell:
                    self.hover_cell = cell
                    self.workshop.update_ghost_cell(cell)
        self.last_x, self.last_y = x, y

    def _on_mouse(self, _win, button, action, _mods) -> None:
        pressed = action == glfw.PRESS
        if button == glfw.MOUSE_BUTTON_LEFT and not pressed:
            self.drag_volume = False
        if button == glfw.MOUSE_BUTTON_LEFT and pressed:
            hit = self.hud.hit_test(self.last_x, self.last_y)
            if hit is not None:
                self._execute_ui_action(hit)
                return
        if self.state != AppState.EM_JOGO:
            return
        if button == glfw.MOUSE_BUTTON_RIGHT:
            self.drag_orbit = pressed
        elif button == glfw.MOUSE_BUTTON_MIDDLE:
            self.drag_pan = pressed
        elif button == glfw.MOUSE_BUTTON_LEFT:
            if pressed and (_mods & glfw.MOD_SHIFT):
                self.drag_pan = True
            elif not pressed:
                self.drag_pan = False
            elif pressed and self.workshop.editing:
                self.workshop.confirm_ghost()
                self.workshop.begin_ghost(self.hover_cell)

    def _on_scroll(self, _win, _x, y: float) -> None:
        if self.state == AppState.EM_JOGO:
            self.camera.zoom(y)

    def _pick_cell(self, mx: float, my: float) -> tuple[int, int] | None:
        """Ray no plano Y=0 a partir da câmera (aproximação por projeção inversa)."""
        w, h = glfw.get_window_size(self.win)
        if w <= 0 or h <= 0:
            return None
        view, proj, eye = self.camera.view_proj()
        ndc_x = (2.0 * mx / w) - 1.0
        ndc_y = 1.0 - (2.0 * my / h)
        inv = glm.inverse(proj * view)
        near = inv * glm.vec4(ndc_x, ndc_y, -1.0, 1.0)
        far = inv * glm.vec4(ndc_x, ndc_y, 1.0, 1.0)
        near /= near.w
        far /= far.w
        dir = glm.normalize(glm.vec3(far) - glm.vec3(near))
        origin = glm.vec3(near)
        if abs(dir.y) < 1e-6:
            return None
        t = -origin.y / dir.y
        if t < 0:
            return None
        hit = origin + dir * t
        cx, cy = int(hit.x), int(hit.z)
        if 0 <= cx < self.workshop.grid_w and 0 <= cy < self.workshop.grid_h:
            return cx, cy
        return None

    def _apply_lights(self, eye: glm.vec3, now_t: float) -> None:
        self.shader.set_float("uTime", now_t)
        self.shader.set_vec3("uSkyAmbient", _SKY_AMBIENT)
        self.shader.set_vec3("uGroundAmbient", _GROUND_AMBIENT)
        self.shader.set_vec2("uGridSize", float(self.workshop.grid_w), float(self.workshop.grid_h))
        self.shader.set_vec3("uDirLightDir", _DIR_LIGHT_DIR)
        self.shader.set_vec3("uDirLightColor", _DIR_LIGHT_COLOR)
        points = self.workshop.point_lights(eye)
        self.shader.set_int("uNumPoints", len(points))
        for i in range(16):
            if i < len(points):
                pos, col = points[i]
                self.shader.set_vec3(f"uPointPos[{i}]", pos)
                self.shader.set_vec3(f"uPointColor[{i}]", col)
            else:
                self.shader.set_vec3(f"uPointPos[{i}]", glm.vec3(0))
                self.shader.set_vec3(f"uPointColor[{i}]", glm.vec3(0))
        self.shader.set_vec3("uFogColor", _FOG_COLOR)
        self.shader.set_float("uFogStart", 20.0)
        self.shader.set_float("uFogEnd", 48.0)
        self.shader.set_float("uBloomThreshold", 1.15)
        self.shader.set_float("uSpecScale", 0.25)

    def _update_title(self) -> None:
        hud = self.bridge.hud_line()
        title = f"Oficina | {hud} | M menu · P sim · R novo"
        if title != self._last_title:
            self._last_title = title
            glfw.set_window_title(self.win, title)

    def run(
        self,
        *,
        screenshot_path: Path | None = None,
        max_frames: int | None = None,
    ) -> None:
        last = time.perf_counter()
        frame_idx = 0
        while not glfw.window_should_close(self.win):
            now = time.perf_counter()
            dt = now - last
            last = now
            glfw.poll_events()
            fb_w, fb_h = glfw.get_framebuffer_size(self.win)
            if fb_w > 0 and fb_h > 0 and (fb_w != self.post.width or fb_h != self.post.height):
                self._on_resize(self.win, fb_w, fb_h)

            if self.state in (
                AppState.TUTORIAL,
                AppState.MENU_PRINCIPAL,
                AppState.MENU_CONFIG,
                AppState.MENU_MODO,
            ):
                self.camera.yaw = (self.camera.yaw + dt * 9.0) % 360.0
            elif self.state == AppState.SELECAO_ROBO:
                for i, sc in enumerate(self.showcase):
                    sc.update(dt, None, on_base=False)
                    if i == (self.selected_robot_idx % max(1, len(self.showcase))):
                        sc._yaw = (sc._yaw + dt * 55.0) % 360.0
            elif self.state == AppState.VITORIA:
                self.camera.yaw = (self.camera.yaw + dt * 22.0) % 360.0
                if self._victory_actor is not None:
                    self._victory_actor.update(dt, None, on_base=False)
            elif self.state in (AppState.MOEDA_ESCOLHA, AppState.MOEDA_GIRANDO, AppState.MOEDA_RESULTADO):
                finished_toss = self.coin.update(dt)
                if finished_toss and self.state == AppState.MOEDA_GIRANDO:
                    self.state = AppState.MOEDA_RESULTADO
                    self._coin_result_timer = 0.0
                    self.hud.mark_dirty()
                elif self.state == AppState.MOEDA_RESULTADO and screenshot_path is None:
                    self._coin_result_timer += dt
                    if self._coin_result_timer >= 2.2:
                        self._begin_match_from_coin()
            elif self.state == AppState.EM_JOGO:
                self.bridge.update(dt, self.workshop)
                for who, delta_bat, is_trap, ev_txt in self.bridge.pop_step_events():
                    target_actor = self.actor_alfa if who == "Alfa" else self.actor_beta
                    target_actor.trigger_step_feedback(delta_bat, is_trap=is_trap, event_text=ev_txt)
                self.bridge.mirror_minerios_to_scene(self.workshop)
                res = self.bridge.last_result
                if res is not None and res is not self._seen_result:
                    self._seen_result = res
                    if res == ResultadoPartida.VITORIA_ALFA:
                        self._enter_victory(self.actor_alfa, is_alfa=True)
                    elif res == ResultadoPartida.VITORIA_BETA:
                        self._enter_victory(self.actor_beta, is_alfa=False)

            cells = self.bridge.robot_cells()
            if self.state == AppState.EM_JOGO and self.bridge.running:
                ca, cb = cells["Alfa"], cells["Beta"]
                self.actor_alfa.update(dt, ca, on_base=self._is_base_cell(ca))
                self.actor_beta.update(dt, cb, on_base=self._is_base_cell(cb))
            elif self.state not in (AppState.SELECAO_ROBO, AppState.VITORIA):
                ca = self.actor_alfa.placeable.cell
                cb = self.actor_beta.placeable.cell
                self.actor_alfa.update(dt, None, on_base=self._is_base_cell(ca))
                self.actor_beta.update(dt, None, on_base=self._is_base_cell(cb))

            follow = (
                (cells["Alfa"] if self.follow_alfa else cells["Beta"])
                if self.bridge.running
                else (self.actor_alfa.placeable.cell if self.follow_alfa else self.actor_beta.placeable.cell)
            )
            self.camera.follow_pos = cell_to_world(*follow) + glm.vec3(0, 0.4, 0)
            self.camera.grid_w = self.workshop.grid_w
            self.camera.grid_h = self.workshop.grid_h

            view, proj, eye = self.camera.view_proj()
            gw, gh = self.workshop.grid_w, self.workshop.grid_h
            light_center = glm.vec3(gw * 0.5, 0.0, gh * 0.5)
            _lv, _lp, light_vp = self.shadow.light_matrices(
                _DIR_LIGHT_DIR, center=light_center, radius=13.5 * self._grid_scale()
            )

            show_coin = self.state in (
                AppState.MOEDA_ESCOLHA,
                AppState.MOEDA_GIRANDO,
                AppState.MOEDA_RESULTADO,
            )

            # --- Pass 1: shadow depth ---
            self.shadow.bind()
            glViewport(0, 0, self.shadow.size, self.shadow.size)
            glClear(GL_DEPTH_BUFFER_BIT)
            glEnable(GL_CULL_FACE)
            glCullFace(GL_FRONT)
            self.depth_shader.use()
            self.depth_shader.set_mat4("uLightVP", light_vp)
            self.workshop.draw_depth_casters(self.depth_shader)
            if self.state == AppState.SELECAO_ROBO:
                for sc in self.showcase:
                    sc.draw_depth_pass(self.depth_shader)
            elif self.state == AppState.VITORIA:
                if self._victory_actor is not None:
                    self._victory_actor.draw_depth_pass(self.depth_shader)
            else:
                self.actor_alfa.draw_depth_pass(self.depth_shader)
                self.actor_beta.draw_depth_pass(self.depth_shader)
            if show_coin:
                self.coin.draw_depth_pass(self.depth_shader)
            glDisable(GL_CULL_FACE)
            self.shadow.unbind()

            # --- Pass 2: scene → FBO (com Phong+ + sombras + cell map + fog) ---
            glT = float(glfw.get_time())
            self.post.begin_scene()
            self.shader.use()
            self.shader.set_mat4("uView", view)
            self.shader.set_mat4("uProj", proj)
            self.shader.set_vec3("uViewPos", eye)
            self.shader.set_mat4("uLightVP", light_vp)
            self.shader.set_int("uUseShadows", 1)
            glActiveTexture(GL_TEXTURE2)
            glBindTexture(GL_TEXTURE_2D, self.shadow.depth_tex)
            self.shader.set_int("uShadowMap", 2)

            self.workshop._rebuild_cell_map_if_needed()
            glActiveTexture(GL_TEXTURE4)
            glBindTexture(GL_TEXTURE_2D, self.workshop.cell_map_tex)
            self.shader.set_int("uCellMap", 4)
            glActiveTexture(GL_TEXTURE0)
            self._apply_lights(eye, glT)

            self.workshop.draw_static(self.shader, eye)
            self.workshop.draw_objects(self.shader)
            self.workshop.draw_forcefield_hardware(self.shader)
            if self.state == AppState.SELECAO_ROBO:
                for sc in self.showcase:
                    sc.draw(self.shader)
            elif self.state == AppState.VITORIA:
                if self._victory_actor is not None:
                    self._victory_actor.draw(self.shader)
            else:
                self.actor_alfa.draw(self.shader)
                self.actor_beta.draw(self.shader)
            if show_coin:
                self.coin.draw(self.shader)

            # --- Pass 2b: decals no piso (anéis de base + brilho sob minérios + rotas A*) ---
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glDepthMask(GL_FALSE)
            alfa_path, beta_path = self.bridge.robot_paths()
            self.workshop.draw_decals(self.shader, glT, alfa_path, beta_path)

            # --- Pass 2c: volumes holográficos conectados (depthMask off) ---
            self.hologram.use()
            self.hologram.set_mat4("uView", view)
            self.hologram.set_mat4("uProj", proj)
            self.hologram.set_vec3("uViewPos", eye)
            self.hologram.set_float("u_time", glT)
            self.hologram.set_vec3("u_color", _HOLO_COLOR)
            self.hologram.set_float("u_height", HOLO_HEIGHT)
            self.workshop.draw_hologram_walls(self.hologram)
            glDepthMask(GL_TRUE)

            if self.state == AppState.EM_JOGO and self.workshop.editing and screenshot_path is None:
                self.shader.use()
                self.shader.set_mat4("uView", view)
                self.shader.set_mat4("uProj", proj)
                self.shader.set_vec3("uViewPos", eye)
                self.workshop.draw_ghost(self.shader)

            # --- Pass 3: bloom + ACES + vinheta ---
            self.post.end_and_bloom(strength=0.34, exposure=1.02, blur_passes=2)

            # --- Pass 4: Menus Interativos / Moeda / HUD de Partida ---
            self.hud.draw(
                glT,
                self.state,
                self.bridge,
                self.actor_alfa,
                self.actor_beta,
                self.coin,
                view,
                proj,
            )

            self._update_title()
            frame_idx += 1
            if max_frames is not None and frame_idx >= max_frames:
                if screenshot_path is not None:
                    self.save_screenshot(screenshot_path)
                glfw.swap_buffers(self.win)
                break
            glfw.swap_buffers(self.win)

        glfw.terminate()

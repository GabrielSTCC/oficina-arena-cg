"""Loop GLFW: input, edição do catálogo e render Phong."""

from __future__ import annotations

import time
from pathlib import Path

import glfw
import glm
from OpenGL.GL import (
    GL_BLEND,
    GL_COLOR_BUFFER_BIT,
    GL_CULL_FACE,
    GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST,
    GL_FALSE,
    GL_FRONT,
    GL_ONE_MINUS_SRC_ALPHA,
    GL_SRC_ALPHA,
    GL_TEXTURE0,
    GL_TEXTURE2,
    GL_TEXTURE_2D,
    GL_TRUE,
    glActiveTexture,
    glBindTexture,
    glBlendFunc,
    glClear,
    glClearColor,
    glCullFace,
    glDepthMask,
    glDisable,
    glEnable,
    glViewport,
)

from gfx.anim_clip import load_anim_clip
from gfx.camera import Camera, CameraMode
from gfx.mesh import Material
from gfx.mesh_loader import DOWNLOADED_ROBOTS
from gfx.postprocess import PostProcess
from gfx.shader import Shader
from gfx.shadow_map import ShadowMap
from scene.catalog import ROBOT_ALFA, ROBOT_BETA, cell_to_world
from scene.placeable import Placeable
from scene.robot_actor import RobotActor
from scene.workshop import GRID_H, GRID_W, Workshop
from world.bridge import WorldBridge

_FOG_COLOR = glm.vec3(0.02, 0.02, 0.03)
_DIR_LIGHT_DIR = glm.vec3(-0.4, -1.0, -0.3)
_DIR_LIGHT_COLOR = glm.vec3(0.72, 0.70, 0.65)
_HOLO_COLOR = glm.vec3(0.2, 0.8, 1.0)

ROOT = Path(__file__).resolve().parents[1]
# Por enquanto: Robô 3 + clips Mixamo (Andar_pra_frente / Stop_Walking)
_FOCUS_ROBOT = "robo3"
_MAT_NEUTRAL = Material(glm.vec3(1.0, 1.0, 1.0), glm.vec3(0.18, 0.18, 0.18), 36.0)
_CLIPS_DIR = ROOT / "assets" / "models" / "robo3_clips"


class Application:
    def __init__(self) -> None:
        if not glfw.init():
            raise RuntimeError("Falha ao iniciar GLFW")
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        self.win = glfw.create_window(1280, 720, "Oficina Arena — CG", None, None)
        if not self.win:
            glfw.terminate()
            raise RuntimeError("Falha ao criar janela")
        glfw.make_context_current(self.win)
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
        self.workshop = Workshop(ROOT / "assets" / "models")
        self.camera = Camera(GRID_W, GRID_H)
        self.bridge = WorldBridge()
        self.hover_cell = (0, 0)
        self.drag_orbit = False
        self.drag_pan = False
        self.last_x = 0.0
        self.last_y = 0.0
        self.follow_alfa = True
        self.robot_keys = list(DOWNLOADED_ROBOTS.keys())
        self.test_idx = self.robot_keys.index(_FOCUS_ROBOT) if _FOCUS_ROBOT in self.robot_keys else 0
        self.solo_test = True
        focus = _FOCUS_ROBOT if _FOCUS_ROBOT in self.workshop.meshes else "robo"
        focus_mesh = self.workshop.meshes[focus]
        focus_parts = self.workshop.robot_parts.get(focus, [])
        walk_clip = load_anim_clip(_CLIPS_DIR / "walk.npz", in_place=True)
        idle_clip = load_anim_clip(_CLIPS_DIR / "idle.npz", in_place=True)
        mid = (GRID_W // 2, GRID_H // 2)
        self.actor_alfa = RobotActor(
            Placeable(
                item=ROBOT_ALFA,
                mesh=focus_mesh,
                cell=mid,
                material=_MAT_NEUTRAL,
                locked=True,
                parts=list(focus_parts),
            ),
            step_duration=self.bridge.turn_interval,
            walk_clip=walk_clip,
            idle_clip=idle_clip,
        )
        self.actor_beta = RobotActor(
            Placeable(
                item=ROBOT_BETA,
                mesh=focus_mesh,
                cell=(GRID_W - 1, GRID_H - 1),
                material=_MAT_NEUTRAL,
                locked=True,
                parts=list(focus_parts),
            ),
            step_duration=self.bridge.turn_interval,
            walk_clip=walk_clip,
            idle_clip=idle_clip,
        )
        # Por enquanto: só o mecha do Blender (sem vitrine colorida)
        self.showcase: list[RobotActor] = []
        self._seed_bases()
        # Preview da arena (parede/minério/armadilha) com materiais do catálogo
        self.bridge.seed_workshop_preview(self.workshop, seed=42)
        self.workshop.begin_ghost((1, 1))
        self.camera.set_mode(CameraMode.ORBITAL)
        self.camera.target = cell_to_world(*mid)
        self.camera.distance = 16.0
        self.camera.pitch = 40.0
        w, h = glfw.get_framebuffer_size(self.win)
        self.camera.aspect = max(w, 1) / max(h, 1)

    def _try_step_robot(self, dx: int, dz: int) -> None:
        """WASD: um passo na grade (só fora da simulação, se a célula estiver livre)."""
        if self.bridge.running or self.actor_alfa.busy:
            return
        x, z = self.actor_alfa.placeable.cell
        nx, nz = x + dx, z + dz
        if not (0 <= nx < GRID_W and 0 <= nz < GRID_H):
            return
        if (nx, nz) in self.workshop.occupancy:
            return
        self.actor_alfa.update(0.0, (nx, nz))
        self.camera.target = cell_to_world(nx, nz)

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
        for cell in ((0, 0), (GRID_W - 1, GRID_H - 1)):
            p = Placeable(
                item=base_item,
                mesh=self.workshop.meshes["base"],
                cell=cell,
                locked=True,
            )
            self.workshop.objects.append(p)
            self.workshop.occupancy[cell] = p

    def _on_resize(self, _win, w: int, h: int) -> None:
        w, h = max(w, 1), max(h, 1)
        glViewport(0, 0, w, h)
        self.camera.aspect = w / h
        if hasattr(self, "post"):
            self.post.resize(w, h)

    def _on_key(self, _win, key, _sc, action, _mods) -> None:
        if action not in (glfw.PRESS, glfw.REPEAT):
            return
        if key == glfw.KEY_ESCAPE:
            if self.workshop.ghost:
                self.workshop.cancel_ghost()
            else:
                glfw.set_window_should_close(self.win, True)
        elif key == glfw.KEY_C:
            self.camera.cycle()
        elif key == glfw.KEY_1:
            self.camera.set_mode(CameraMode.PLANTA)
        elif key == glfw.KEY_2:
            self.camera.set_mode(CameraMode.ORBITAL)
        elif key == glfw.KEY_3:
            self.camera.set_mode(CameraMode.SEGUIR)
        elif key in (glfw.KEY_SPACE, glfw.KEY_P):
            self.bridge.toggle(self.workshop)
        elif key == glfw.KEY_R:
            self.bridge.start_from_workshop(self.workshop)
        elif key == glfw.KEY_TAB:
            self.follow_alfa = not self.follow_alfa
        elif key in (glfw.KEY_RIGHT, glfw.KEY_PERIOD, glfw.KEY_RIGHT_BRACKET):
            self.workshop.select_next(1)
        elif key in (glfw.KEY_LEFT, glfw.KEY_COMMA, glfw.KEY_LEFT_BRACKET):
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
        elif key == glfw.KEY_W:
            self._try_step_robot(0, -1)
        elif key == glfw.KEY_S:
            self._try_step_robot(0, 1)
        elif key == glfw.KEY_A:
            self._try_step_robot(-1, 0)
        elif key == glfw.KEY_D:
            self._try_step_robot(1, 0)

    def _on_cursor(self, _win, x: float, y: float) -> None:
        dx, dy = x - self.last_x, y - self.last_y
        if self.drag_orbit:
            self.camera.orbit(dx, dy)
        elif self.drag_pan:
            self.camera.pan(dx, dy)
        self.last_x, self.last_y = x, y
        if not self.drag_orbit and not self.drag_pan:
            cell = self._pick_cell(x, y)
            if cell:
                self.hover_cell = cell
                if self.workshop.editing:
                    self.workshop.update_ghost_cell(cell)

    def _on_mouse(self, _win, button, action, _mods) -> None:
        pressed = action == glfw.PRESS
        if button == glfw.MOUSE_BUTTON_RIGHT:
            self.drag_orbit = pressed
        elif button == glfw.MOUSE_BUTTON_MIDDLE:
            self.drag_pan = pressed
        elif button == glfw.MOUSE_BUTTON_LEFT:
            # Shift+esquerdo = pan; esquerdo sozinho = colocar objeto
            if pressed and (_mods & glfw.MOD_SHIFT):
                self.drag_pan = True
            elif not pressed:
                self.drag_pan = False
            elif pressed and self.workshop.editing:
                self.workshop.confirm_ghost()
                self.workshop.begin_ghost(self.hover_cell)

    def _on_scroll(self, _win, _x, y: float) -> None:
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
        if 0 <= cx < GRID_W and 0 <= cy < GRID_H:
            return cx, cy
        return None

    def _apply_lights(self, eye: glm.vec3) -> None:
        self.shader.set_vec3("uDirLightDir", _DIR_LIGHT_DIR)
        self.shader.set_vec3("uDirLightColor", _DIR_LIGHT_COLOR)
        points = self.workshop.point_lights(eye)
        self.shader.set_int("uNumPoints", len(points))
        for i in range(8):
            if i < len(points):
                pos, col = points[i]
                self.shader.set_vec3(f"uPointPos[{i}]", pos)
                self.shader.set_vec3(f"uPointColor[{i}]", col)
            else:
                self.shader.set_vec3(f"uPointPos[{i}]", glm.vec3(0))
                self.shader.set_vec3(f"uPointColor[{i}]", glm.vec3(0))
        self.shader.set_vec3("uFogColor", _FOG_COLOR)
        self.shader.set_float("uFogStart", 12.0)
        self.shader.set_float("uFogEnd", 28.0)
        self.shader.set_float("uBloomThreshold", 1.2)
        self.shader.set_float("uSpecScale", 0.22)

    def _update_title(self) -> None:
        hud = self.bridge.hud_line()
        glfw.set_window_title(self.win, f"Oficina | {hud} | P sim · R reinicia")

    def run(self) -> None:
        last = time.perf_counter()
        while not glfw.window_should_close(self.win):
            now = time.perf_counter()
            dt = now - last
            last = now
            glfw.poll_events()
            self.bridge.update(dt, self.workshop)
            self.bridge.mirror_minerios_to_scene(self.workshop)

            cells = self.bridge.robot_cells()
            show_match = self.bridge.partida is not None
            if self.bridge.running:
                self.actor_alfa.update(dt, cells["Alfa"])
                self.actor_beta.update(dt, cells["Beta"])
            else:
                self.actor_alfa.update(dt, None)
                if show_match:
                    self.actor_beta.update(dt, None)
            follow = (
                cells["Alfa"]
                if self.bridge.running and self.follow_alfa
                else self.actor_alfa.placeable.cell
            )
            self.camera.follow_pos = cell_to_world(*follow) + glm.vec3(0, 0.4, 0)

            view, proj, eye = self.camera.view_proj()
            light_center = glm.vec3(GRID_W * 0.5, 0.0, GRID_H * 0.5)
            _lv, _lp, light_vp = self.shadow.light_matrices(
                _DIR_LIGHT_DIR, center=light_center, radius=14.0
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
            self.actor_alfa.draw_depth_pass(self.depth_shader)
            if show_match:
                self.actor_beta.draw_depth_pass(self.depth_shader)
            glDisable(GL_CULL_FACE)
            self.shadow.unbind()

            # --- Pass 2: scene → FBO (com Phong + sombras + fog) ---
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
            glActiveTexture(GL_TEXTURE0)
            self._apply_lights(eye)

            self.workshop.draw_static(self.shader)
            self.workshop.draw_objects(self.shader)
            self.workshop.draw_forcefield_hardware(self.shader)
            self.actor_alfa.draw(self.shader)
            if show_match:
                self.actor_beta.draw(self.shader)

            # Volumes holográficos depois de todos os opacos (depthMask off)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glDepthMask(GL_FALSE)
            self.hologram.use()
            self.hologram.set_mat4("uView", view)
            self.hologram.set_mat4("uProj", proj)
            self.hologram.set_vec3("uViewPos", eye)
            self.hologram.set_float("u_time", float(glfw.get_time()))
            self.hologram.set_vec3("u_color", _HOLO_COLOR)
            self.workshop.draw_hologram_walls(self.hologram)
            glDepthMask(GL_TRUE)

            if self.workshop.editing:
                self.shader.use()
                self.shader.set_mat4("uView", view)
                self.shader.set_mat4("uProj", proj)
                self.shader.set_vec3("uViewPos", eye)
                self.workshop.draw_ghost(self.shader)

            # --- Pass 3: bloom + composite ---
            self.post.end_and_bloom(strength=0.35, exposure=1.8, blur_passes=2)

            self._update_title()
            glfw.swap_buffers(self.win)

        glfw.terminate()

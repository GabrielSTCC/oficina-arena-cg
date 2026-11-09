"""Robô: passo entre células + clips Mixamo (walk/idle/kneel/dança) + feedback de dano."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import glm

from gfx.anim_clip import AnimClip
from gfx.mesh import Material, Mesh
from gfx.shader import Shader
from scene.catalog import cell_to_world
from scene.placeable import Placeable, draw_depth, draw_textured

if TYPE_CHECKING:
    from scene.robot_models import DanceEntry, RobotModel

# Altura do topo da plataforma Base2 para o robô não afundar no pedestal
_BASE_PAD_Y = 0.14
_DAMAGE_DURATION = 0.95


def _smooth(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


@dataclass
class RobotActor:
    """Interpolação entre células; animação Mixamo no passo, ajoelhar na base e dano em armadilha."""

    placeable: Placeable
    step_duration: float = 0.35
    walk_clip: AnimClip | None = None
    idle_clip: AnimClip | None = None
    kneel_clip: AnimClip | None = None
    kneel_duration: float = 0.50
    base_kd: glm.vec3 = field(default_factory=lambda: glm.vec3(0.72, 0.74, 0.78))
    model_key: str = ""
    model_nome: str = ""
    dances: list[DanceEntry] = field(default_factory=list)

    _from: glm.vec3 = field(default_factory=lambda: glm.vec3(0))
    _to: glm.vec3 = field(default_factory=lambda: glm.vec3(0))
    _visual: glm.vec3 = field(default_factory=lambda: glm.vec3(0))
    _prev_cell: tuple[int, int] = (0, 0)
    _t: float = 1.0
    _yaw: float = 0.0
    _moving: bool = False
    _kneel_t: float = 0.0
    _on_base: bool = False
    _anim_mesh: Mesh | None = field(default=None, repr=False)
    _anim_key: tuple[int, int] = (-1, -1)
    _active_clip: AnimClip | None = field(default=None, repr=False)
    _clip_mat: Material = field(
        default_factory=lambda: Material(
            glm.vec3(0.72, 0.74, 0.78), glm.vec3(0.2, 0.2, 0.22), shininess=40.0
        )
    )
    _dance_clip: AnimClip | None = field(default=None, repr=False)
    _dance_t: float = 0.0

    # Feedback visual de gasto de bateria e dano em armadilha
    damage_timer: float = 0.0
    popup_timer: float = 0.0
    last_delta_bat: int = 0
    last_is_trap: bool = False
    last_event_text: str = ""

    def __post_init__(self) -> None:
        cell = self.placeable.cell
        self._prev_cell = cell
        self._visual = cell_to_world(*cell)
        self._from = glm.vec3(self._visual)
        self._to = glm.vec3(self._visual)
        self._clip_mat.kd = glm.vec3(self.base_kd)
        for clip in (self.idle_clip, self.walk_clip, self.kneel_clip):
            if clip is not None:
                clip.preload_meshes()
        rest = self.idle_clip or self.walk_clip or self.kneel_clip
        if rest is not None:
            self._push_frame(rest, 0)

    def set_model(self, model: RobotModel) -> None:
        """Troca clips/materiais do robô (seleção de personagem)."""
        self.model_key = model.key
        self.model_nome = model.nome
        self.walk_clip = model.walk
        self.idle_clip = model.idle
        self.kneel_clip = model.kneel
        self.dances = list(model.dances)
        self.stop_dance()
        self._pose_rest()

    @property
    def busy(self) -> bool:
        return self._t < 1.0

    def snap_to(
        self,
        cell: tuple[int, int],
        yaw_deg: float = 0.0,
        *,
        on_base: bool = True,
    ) -> None:
        """Posiciona o robô imediatamente na célula (ex.: início/reinício de partida na base)."""
        target_y = _BASE_PAD_Y if on_base else 0.0
        pos = cell_to_world(*cell) + glm.vec3(0.0, target_y, 0.0)
        self.placeable.cell = cell
        self._prev_cell = cell
        self._visual = glm.vec3(pos)
        self._from = glm.vec3(pos)
        self._to = glm.vec3(pos)
        self._t = 1.0
        self._yaw = yaw_deg
        self._moving = False
        self._on_base = on_base
        self._kneel_t = 0.0
        self.damage_timer = 0.0
        self.popup_timer = 0.0
        self.last_delta_bat = 0
        self.last_is_trap = False
        self.last_event_text = ""
        if self._dance_clip is None:
            self._pose_rest()

    def start_dance(self, clip: AnimClip) -> None:
        self._dance_clip = clip
        self._dance_t = 0.0
        self._moving = False
        self._t = 1.0
        self._push_frame(clip, 0)

    def stop_dance(self) -> None:
        self._dance_clip = None
        self._dance_t = 0.0
        self._pose_rest()

    def trigger_step_feedback(
        self,
        delta_bat: int,
        is_trap: bool = False,
        event_text: str = "",
    ) -> None:
        """Ativa indicador de gasto de bateria (-2 ou -4) e flash/tremor se for armadilha."""
        self.last_delta_bat = int(delta_bat)
        self.last_is_trap = bool(is_trap)
        self.last_event_text = event_text
        self.popup_timer = 1.25 if is_trap else 0.80
        if is_trap:
            self.damage_timer = _DAMAGE_DURATION

    def _push_frame(self, clip: AnimClip, frame: int) -> None:
        frame = max(0, min(int(frame), clip.n_frames - 1))
        key = (id(clip), frame)
        if key == self._anim_key and self._anim_mesh is not None:
            return
        self._anim_mesh = clip.frame_mesh(frame)
        self._anim_key = key
        self._active_clip = clip

    def _pose_rest(self) -> None:
        rest = self.idle_clip or self.walk_clip
        if rest is None:
            return
        self._push_frame(rest, 0)

    def update(
        self,
        dt: float,
        cell: tuple[int, int] | None = None,
        *,
        on_base: bool = False,
    ) -> None:
        if self.damage_timer > 0.0:
            self.damage_timer = max(0.0, self.damage_timer - dt)
        if self.popup_timer > 0.0:
            self.popup_timer = max(0.0, self.popup_timer - dt)

        if self._dance_clip is not None:
            self._dance_t += dt
            # clips de dança vêm subsampleados (fps baixo); 3x fica legível na vitória
            fps = max(1.0, float(self._dance_clip.fps)) * 3.0
            fi = int(self._dance_t * fps) % self._dance_clip.n_frames
            self._push_frame(self._dance_clip, fi)
            return

        target_y = _BASE_PAD_Y if on_base else 0.0
        if cell is not None and cell != self._prev_cell:
            self._from = glm.vec3(self._visual)
            self._to = cell_to_world(*cell) + glm.vec3(0.0, target_y, 0.0)
            d = self._to - self._from
            if abs(float(d.x)) + abs(float(d.z)) > 1e-4:
                self._yaw = math.degrees(math.atan2(float(d.x), float(d.z)))
            self._t = 0.0
            self._prev_cell = cell
            self.placeable.cell = cell
            self._kneel_t = 0.0

        self._on_base = on_base

        if self._t < 1.0:
            self._t = min(1.0, self._t + dt / max(self.step_duration, 1e-3))
            u = _smooth(self._t)
            self._visual = self._from + (self._to - self._from) * u
            self._moving = True
            if self.walk_clip is not None:
                fi = int(self._t * self.walk_clip.n_frames) % self.walk_clip.n_frames
                self._push_frame(self.walk_clip, fi)
            if self._t >= 1.0:
                if on_base and self.kneel_clip is not None:
                    self._kneel_t = 0.0
                    self._push_frame(self.kneel_clip, 0)
                else:
                    self._pose_rest()
        else:
            self._visual = cell_to_world(*self._prev_cell) + glm.vec3(0.0, target_y, 0.0)
            was_moving = self._moving
            self._moving = False
            if on_base and self.kneel_clip is not None:
                self._kneel_t = min(1.0, self._kneel_t + dt / max(self.kneel_duration, 1e-3))
                fi = int(round(self._kneel_t * (self.kneel_clip.n_frames - 1)))
                self._push_frame(self.kneel_clip, fi)
            else:
                if was_moving or self._kneel_t > 0.0:
                    self._kneel_t = 0.0
                    self._pose_rest()

    def _model(self) -> glm.mat4:
        pos = glm.vec3(self._visual)
        if self.damage_timer > 0.0:
            strength = self.damage_timer / _DAMAGE_DURATION
            shake_x = 0.13 * strength * math.sin(self.damage_timer * 62.0)
            shake_z = 0.10 * strength * math.cos(self.damage_timer * 48.0)
            shake_y = 0.06 * strength * abs(math.sin(self.damage_timer * 35.0))
            pos = pos + glm.vec3(shake_x, shake_y, shake_z)
        m = glm.translate(glm.mat4(1.0), pos)
        m = glm.rotate(m, glm.radians(self._yaw), glm.vec3(0, 1, 0))
        m = glm.scale(m, glm.vec3(self.placeable.scale))
        return m

    def _draw_clip(self, shader: Shader, depth: bool = False) -> None:
        if self._anim_mesh is None or self._active_clip is None:
            return
        m = self._model()
        clip = self._active_clip
        tint = None
        if not depth and self.damage_timer > 0.0:
            pulse = 0.55 + 0.45 * abs(math.sin(self.damage_timer * 28.0))
            tint = glm.mix(glm.vec3(1.0), glm.vec3(1.0, 0.18, 0.12), pulse)

        ranges = clip.ranges or [(0, int(clip.idx.size))]
        mats = clip.materials or [self._clip_mat]
        for i, (first, count) in enumerate(ranges):
            if count <= 0:
                continue
            if depth:
                draw_depth(shader, self._anim_mesh, m, index_range=(first, count))
            else:
                mat = mats[i] if i < len(mats) else self._clip_mat
                draw_textured(
                    shader,
                    self._anim_mesh,
                    m,
                    mat,
                    tint=tint,
                    index_range=(first, count),
                )

    def draw(self, shader: Shader) -> None:
        if self._anim_mesh is not None and self._active_clip is not None:
            self._draw_clip(shader, depth=False)
            return

        assert self.placeable.material is not None
        tint = glm.vec3(1.0, 0.2, 0.15) if self.damage_timer > 0.0 else None
        m = self._model()
        if self.placeable.parts:
            for mesh, mat in self.placeable.parts:
                draw_textured(shader, mesh, m, mat, tint=tint)
        else:
            draw_textured(shader, self.placeable.mesh, m, self.placeable.material, tint=tint)

    def draw_depth_pass(self, shader: Shader) -> None:
        if self._anim_mesh is not None and self._active_clip is not None:
            self._draw_clip(shader, depth=True)
            return
        m = self._model()
        if self.placeable.parts:
            for mesh, _mat in self.placeable.parts:
                draw_depth(shader, mesh, m)
        else:
            draw_depth(shader, self.placeable.mesh, m)

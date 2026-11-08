"""Robô: passo entre células + clips Mixamo (walk/idle) sem balanço procedural."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import glm

import numpy as np

from gfx.anim_clip import AnimClip
from gfx.mesh import Material, Mesh
from gfx.shader import Shader
from scene.catalog import cell_to_world
from scene.placeable import Placeable, draw_depth, draw_textured


def _smooth(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


@dataclass
class RobotActor:
    """Interpolação entre células; animação Mixamo só durante o passo (WASD/sim)."""

    placeable: Placeable
    step_duration: float = 0.35
    walk_clip: AnimClip | None = None
    idle_clip: AnimClip | None = None  # pose de descanso = frame 0 (não loopa sozinho)

    _from: glm.vec3 = field(default_factory=lambda: glm.vec3(0))
    _to: glm.vec3 = field(default_factory=lambda: glm.vec3(0))
    _visual: glm.vec3 = field(default_factory=lambda: glm.vec3(0))
    _prev_cell: tuple[int, int] = (0, 0)
    _t: float = 1.0
    _yaw: float = 0.0
    _moving: bool = False
    _anim_mesh: Mesh | None = field(default=None, repr=False)
    _anim_frame: int = -1
    _clip_mat: Material = field(
        default_factory=lambda: Material(
            glm.vec3(0.72, 0.74, 0.78), glm.vec3(0.2, 0.2, 0.22), shininess=40.0
        )
    )

    def __post_init__(self) -> None:
        cell = self.placeable.cell
        self._prev_cell = cell
        self._visual = cell_to_world(*cell)
        self._from = glm.vec3(self._visual)
        self._to = glm.vec3(self._visual)
        # Pose inicial estática (frame 0 do idle ou walk) — sem animar até WASD
        rest = self.idle_clip or self.walk_clip
        if rest is not None:
            self._anim_mesh = Mesh(rest.interleaved(0), rest.idx.astype(np.uint32), dynamic=True)
            self._anim_frame = 0

    @property
    def busy(self) -> bool:
        return self._t < 1.0

    def _push_frame(self, clip: AnimClip, frame: int) -> None:
        if self._anim_mesh is None:
            return
        frame = int(frame) % clip.n_frames
        if frame == self._anim_frame:
            return
        self._anim_mesh.update_vertices(clip.interleaved(frame))
        self._anim_frame = frame

    def _pose_rest(self) -> None:
        rest = self.idle_clip or self.walk_clip
        if rest is None:
            return
        self._anim_frame = -1
        self._push_frame(rest, 0)

    def update(self, dt: float, cell: tuple[int, int] | None = None) -> None:
        if cell is not None and cell != self._prev_cell:
            self._from = glm.vec3(self._visual)
            self._to = cell_to_world(*cell)
            d = self._to - self._from
            if abs(float(d.x)) + abs(float(d.z)) > 1e-4:
                self._yaw = math.degrees(math.atan2(float(d.x), float(d.z)))
            self._t = 0.0
            self._prev_cell = cell
            self.placeable.cell = cell

        if self._t < 1.0:
            self._t = min(1.0, self._t + dt / max(self.step_duration, 1e-3))
            u = _smooth(self._t)
            self._visual = self._from + (self._to - self._from) * u
            self._moving = True
            if self.walk_clip is not None:
                fi = int(self._t * self.walk_clip.n_frames) % self.walk_clip.n_frames
                self._push_frame(self.walk_clip, fi)
            if self._t >= 1.0:
                self._pose_rest()
        else:
            self._visual = cell_to_world(*self._prev_cell)
            was_moving = self._moving
            self._moving = False
            if was_moving:
                self._pose_rest()

    def _model(self) -> glm.mat4:
        m = glm.translate(glm.mat4(1.0), self._visual)
        m = glm.rotate(m, glm.radians(self._yaw), glm.vec3(0, 1, 0))
        m = glm.scale(m, glm.vec3(self.placeable.scale))
        return m

    def draw(self, shader: Shader) -> None:
        m = self._model()

        if self._anim_mesh is not None and (self.walk_clip or self.idle_clip):
            draw_textured(shader, self._anim_mesh, m, self._clip_mat)
            return

        assert self.placeable.material is not None
        if self.placeable.parts:
            for mesh, mat in self.placeable.parts:
                draw_textured(shader, mesh, m, mat)
        else:
            draw_textured(shader, self.placeable.mesh, m, self.placeable.material)

    def draw_depth_pass(self, shader: Shader) -> None:
        m = self._model()
        if self._anim_mesh is not None and (self.walk_clip or self.idle_clip):
            draw_depth(shader, self._anim_mesh, m)
            return
        if self.placeable.parts:
            for mesh, _mat in self.placeable.parts:
                draw_depth(shader, mesh, m)
        else:
            draw_depth(shader, self.placeable.mesh, m)

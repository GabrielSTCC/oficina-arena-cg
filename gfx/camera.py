"""Três modos de câmera: planta, orbital e seguir robô."""

from __future__ import annotations

from enum import Enum, auto

import glm


class CameraMode(Enum):
    PLANTA = auto()
    ORBITAL = auto()
    SEGUIR = auto()


class Camera:
    def __init__(self, grid_w: int = 15, grid_h: int = 9) -> None:
        self.grid_w = grid_w
        self.grid_h = grid_h
        self.mode = CameraMode.ORBITAL
        self.yaw = 40.0
        self.pitch = 50.0
        self.distance = 18.0
        self.ortho_zoom = 1.0
        self.target = glm.vec3(grid_w * 0.5, 0.0, grid_h * 0.5)
        self.follow_pos = glm.vec3(0.5, 0.5, 0.5)
        self.aspect = 16 / 9

    def cycle(self) -> None:
        order = [CameraMode.PLANTA, CameraMode.ORBITAL, CameraMode.SEGUIR]
        self.mode = order[(order.index(self.mode) + 1) % len(order)]

    def set_mode(self, mode: CameraMode) -> None:
        self.mode = mode

    def orbit(self, dx: float, dy: float) -> None:
        """Gira em torno do alvo (qualquer modo exceto SEGUIR força orbital)."""
        if self.mode == CameraMode.SEGUIR:
            return
        if self.mode == CameraMode.PLANTA:
            self.mode = CameraMode.ORBITAL
        self.yaw += dx * 0.25
        self.pitch = max(8.0, min(85.0, self.pitch + dy * 0.25))

    def pan(self, dx: float, dy: float) -> None:
        """Arrasta o alvo no plano XZ (visão atual)."""
        if self.mode == CameraMode.SEGUIR:
            return
        sens = 0.02 * (self.distance / 18.0)
        if self.mode == CameraMode.PLANTA:
            sens = 0.03 * self.ortho_zoom
            # planta: x tela → x mundo, y tela → -z mundo
            self.target.x -= dx * sens
            self.target.z -= dy * sens
        else:
            yaw_r = glm.radians(self.yaw)
            right = glm.vec3(glm.cos(yaw_r), 0.0, -glm.sin(yaw_r))
            forward = glm.vec3(glm.sin(yaw_r), 0.0, glm.cos(yaw_r))
            self.target += right * (-dx * sens) + forward * (dy * sens)
        self.target.x = max(-2.0, min(self.grid_w + 2.0, float(self.target.x)))
        self.target.z = max(-2.0, min(self.grid_h + 2.0, float(self.target.z)))

    def zoom(self, delta: float) -> None:
        if self.mode == CameraMode.PLANTA:
            self.ortho_zoom = max(0.4, min(2.5, self.ortho_zoom - delta * 0.1))
        else:
            self.distance = max(4.0, min(45.0, self.distance - delta))

    def view_proj(self) -> tuple[glm.mat4, glm.mat4, glm.vec3]:
        center = self.target
        if self.mode == CameraMode.PLANTA:
            eye = center + glm.vec3(0.0, 22.0, 0.01)
            view = glm.lookAt(eye, center, glm.vec3(0, 0, -1))
            half_w = self.grid_w * 0.55 * self.ortho_zoom
            half_h = half_w / self.aspect
            proj = glm.ortho(-half_w, half_w, -half_h, half_h, 0.1, 80.0)
            return view, proj, eye

        if self.mode == CameraMode.SEGUIR:
            eye = self.follow_pos + glm.vec3(-2.5, 2.2, -2.5)
            view = glm.lookAt(eye, self.follow_pos + glm.vec3(0, 0.5, 0), glm.vec3(0, 1, 0))
            proj = glm.perspective(glm.radians(55.0), self.aspect, 0.1, 100.0)
            return view, proj, eye

        yaw_r = glm.radians(self.yaw)
        pitch_r = glm.radians(self.pitch)
        offset = glm.vec3(
            self.distance * glm.cos(pitch_r) * glm.sin(yaw_r),
            self.distance * glm.sin(pitch_r),
            self.distance * glm.cos(pitch_r) * glm.cos(yaw_r),
        )
        eye = center + offset
        view = glm.lookAt(eye, center, glm.vec3(0, 1, 0))
        proj = glm.perspective(glm.radians(50.0), self.aspect, 0.1, 100.0)
        return view, proj, eye

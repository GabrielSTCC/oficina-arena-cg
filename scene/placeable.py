"""Objeto da cena com transformação e vínculo à grade."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

import glm
from OpenGL.GL import (
    GL_TEXTURE0,
    GL_TEXTURE1,
    GL_TEXTURE3,
    GL_TEXTURE_2D,
    glActiveTexture,
    glBindTexture,
)

from gfx.mesh import Material, Mesh
from gfx.shader import Shader
from scene.catalog import CatalogItem, CellKind, cell_to_world

ORE_HOVER_Y = 0.50
ORE_BOB_AMP = 0.07
ORE_BOB_HZ = 2.0


def draw_textured(
    shader: Shader,
    mesh: Mesh,
    model: glm.mat4,
    mat: Material,
    *,
    alpha: float = 1.0,
    tint: glm.vec3 | None = None,
    floor_mode: int = 0,
    index_range: tuple[int, int] | None = None,
) -> None:
    normal = glm.mat3(glm.transpose(glm.inverse(model)))
    kd = tint if tint is not None else mat.kd
    use_tex = 1 if mat.texture_id is not None and tint is None else 0
    use_nmap = 1 if mat.normal_id is not None and tint is None else 0
    use_emap = 1 if mat.emissive_id is not None and tint is None else 0
    shader.set_mat4("uModel", model)
    shader.set_mat3("uNormalMat", normal)
    shader.set_vec3("uKd", kd)
    shader.set_vec3("uKs", mat.ks)
    shader.set_vec3("uEmissive", mat.emissive if tint is None else glm.vec3(0.0))
    shader.set_float("uShininess", mat.shininess)
    shader.set_float("uAlpha", alpha)
    shader.set_int("uUseTexture", use_tex)
    shader.set_int("uUseNormalMap", use_nmap)
    shader.set_int("uUseEmissiveMap", use_emap)
    shader.set_float("uPulseHz", mat.pulse_hz if tint is None else 0.0)
    shader.set_int("uAlphaTex", 1 if (mat.alpha_tex and use_tex) else 0)
    shader.set_float("uTriplanarScale", mat.triplanar_scale if tint is None else 0.0)
    shader.set_int("uFloorMode", floor_mode)
    if use_tex:
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, mat.texture_id)
        shader.set_int("uTexture", 0)
    if use_nmap:
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D, mat.normal_id)
        shader.set_int("uNormalMap", 1)
    if use_emap:
        glActiveTexture(GL_TEXTURE3)
        glBindTexture(GL_TEXTURE_2D, mat.emissive_id)
        shader.set_int("uEmissiveMap", 3)
    glActiveTexture(GL_TEXTURE0)
    if index_range is not None:
        mesh.draw_range(index_range[0], index_range[1])
    else:
        mesh.draw()


def draw_depth(
    shader: Shader,
    mesh: Mesh,
    model: glm.mat4,
    *,
    index_range: tuple[int, int] | None = None,
) -> None:
    shader.set_mat4("uModel", model)
    if index_range is not None:
        mesh.draw_range(index_range[0], index_range[1])
    else:
        mesh.draw()


def draw_hologram(shader: Shader, mesh: Mesh, model: glm.mat4) -> None:
    """Desenha malha com o shader de campo de forças (só MVP + normal)."""
    normal = glm.mat3(glm.transpose(glm.inverse(model)))
    shader.set_mat4("uModel", model)
    shader.set_mat3("uNormalMat", normal)
    mesh.draw()


@dataclass
class Placeable:
    item: CatalogItem
    mesh: Mesh
    cell: tuple[int, int]
    yaw_deg: float = 0.0
    scale: float = 1.0
    material: Material | None = None
    locked: bool = False
    parts: list[tuple[Mesh, Material]] = field(default_factory=list)
    ore_tipo: str | None = None
    ore_valor: int | None = None
    user_placed: bool = False

    def __post_init__(self) -> None:
        if self.material is None:
            self.material = self.item.material
        if self.scale == 1.0:
            self.scale = self.item.default_scale

    def model_matrix(self, override_cell: tuple[int, int] | None = None) -> glm.mat4:
        cx, cy = override_cell or self.cell
        pos = cell_to_world(cx, cy)
        if self.item.cell_kind == CellKind.MINERIO:
            phase = (cx * 1.7 + cy * 2.3) * 0.37
            bob = ORE_BOB_AMP * math.sin(time.perf_counter() * ORE_BOB_HZ + phase)
            pos = pos + glm.vec3(0.0, ORE_HOVER_Y + bob, 0.0)
        m = glm.translate(glm.mat4(1.0), pos)
        m = glm.rotate(m, glm.radians(self.yaw_deg), glm.vec3(0, 1, 0))
        m = glm.scale(m, glm.vec3(self.scale))
        return m

    def draw(
        self,
        shader: Shader,
        alpha: float = 1.0,
        tint: glm.vec3 | None = None,
        override_cell: tuple[int, int] | None = None,
    ) -> None:
        assert self.material is not None
        model = self.model_matrix(override_cell)
        if self.parts:
            for mesh, mat in self.parts:
                draw_textured(shader, mesh, model, mat, alpha=alpha, tint=tint)
            return
        draw_textured(shader, self.mesh, model, self.material, alpha=alpha, tint=tint)

    def draw_depth_pass(self, shader: Shader, override_cell: tuple[int, int] | None = None) -> None:
        model = self.model_matrix(override_cell)
        if self.parts:
            for mesh, _mat in self.parts:
                draw_depth(shader, mesh, model)
            return
        draw_depth(shader, self.mesh, model)

    def draw_hologram_pass(self, shader: Shader) -> None:
        model = self.model_matrix()
        if self.parts:
            for mesh, _mat in self.parts:
                draw_hologram(shader, mesh, model)
            return
        draw_hologram(shader, self.mesh, model)


@dataclass
class Ghost:
    item: CatalogItem
    mesh: Mesh
    cell: tuple[int, int] = (0, 0)
    yaw_deg: float = 0.0
    scale: float = 1.0
    allowed: bool = True
    parts: list[tuple[Mesh, Material]] = field(default_factory=list)

    def as_placeable(self) -> Placeable:
        return Placeable(
            item=self.item,
            mesh=self.mesh,
            cell=self.cell,
            yaw_deg=self.yaw_deg,
            scale=self.scale,
            parts=list(self.parts),
        )

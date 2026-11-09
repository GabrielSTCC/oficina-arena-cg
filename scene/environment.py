"""Hangar fechado em torno da arena 15×9 (chão externo, borda, paredes, janela, teto)."""

from __future__ import annotations

import glm
from OpenGL.GL import GL_BACK, GL_CULL_FACE, glCullFace, glDisable, glEnable

from gfx.mesh import (
    MAT_CHAO,
    MAT_CONCRETO,
    MAT_HAZARD,
    MAT_JANELA,
    MAT_METAL_ESC,
    MAT_PAINEL,
    Material,
)
from gfx.primitives import make_box, make_floor, make_wall_quad
from gfx.shader import Shader
from scene.placeable import draw_depth, draw_textured

_MAT_NEON_TRIM = Material(
    glm.vec3(0.15, 0.78, 1.0),
    glm.vec3(0.3, 0.35, 0.4),
    48.0,
    emissive=glm.vec3(0.35, 1.35, 1.85),
)
_MAT_CEIL_LIGHT = Material(
    glm.vec3(0.85, 0.92, 1.0),
    glm.vec3(0.2, 0.2, 0.25),
    24.0,
    emissive=glm.vec3(1.35, 1.55, 1.85),
)
_MAT_DARK_STRUCT = Material(
    glm.vec3(0.10, 0.12, 0.15),
    glm.vec3(0.30, 0.33, 0.38),
    52.0,
    triplanar_scale=0.5,
)


class HangarEnvironment:
    """Constrói e desenha o hangar sci-fi ao redor do tabuleiro."""

    def __init__(self, grid_w: int = 15, grid_h: int = 9) -> None:
        self.grid_w = float(grid_w)
        self.grid_h = float(grid_h)
        self.cx = self.grid_w * 0.5
        self.cz = self.grid_h * 0.5

        # Dimensões internas do hangar (margem ao redor da arena 15×9)
        self.room_w = 30.0
        self.room_d = 22.0
        self.room_h = 8.2
        self.floor_y = -0.14

        # 1. Piso da arena (+3 mm vs topo da plataforma em Y=0) + degrau metálico
        self.arena_floor = make_floor(
            self.grid_w, self.grid_h, y=0.003, uv_repeat=(self.grid_w, self.grid_h)
        )
        self.platform_base = make_box(
            self.grid_w + 0.56, 0.14, self.grid_h + 0.56, uv_scale=0.5, y0=-0.14
        )

        # 2. Chão externo (−3 mm vs base da plataforma em floor_y) — evita z-fight
        self.outer_floor = make_floor(
            self.room_w,
            self.room_d,
            y=self.floor_y - 0.003,
            uv_repeat=(self.room_w * 0.28, self.room_d * 0.28),
        )
        # Teto (normal para baixo)
        self.ceiling = make_floor(
            self.room_w,
            self.room_d,
            y=self.room_h,
            uv_repeat=(self.room_w * 0.22, self.room_d * 0.22),
            normal_up=False,
        )

        # 3. Paredes do hangar (normais para dentro → dollhouse culling automático)
        self.wall_ns = make_wall_quad(
            self.room_w, self.room_h - self.floor_y, uv_repeat=(self.room_w / 3.0, 2.0)
        )
        self.wall_ew = make_wall_quad(
            self.room_d, self.room_h - self.floor_y, uv_repeat=(self.room_d / 3.0, 2.0)
        )
        # Janela industrial alta na parede norte (Z menor, alinhada com _DIR_LIGHT_DIR)
        self.window_quad = make_wall_quad(9.0, 2.6, uv_repeat=(1.0, 1.0))

        # 4. Borda da arena: mureta metálica baixa + faixa de perigo + filete neon + postes
        curb_h = 0.28
        curb_t = 0.24
        self.curb_ns = make_box(self.grid_w + curb_t * 2, curb_h, curb_t, uv_scale=0.6)
        self.curb_ew = make_box(curb_t, curb_h, self.grid_h, uv_scale=0.6)
        self.hazard_ns = make_box(
            self.grid_w + 0.08, 0.025, curb_t * 0.78, uv_scale=0.75, y0=curb_h
        )
        self.hazard_ew = make_box(
            curb_t * 0.78, 0.025, self.grid_h - 0.08, uv_scale=0.75, y0=curb_h
        )
        self.trim_ns = make_box(self.grid_w, 0.04, 0.03, y0=0.14)
        self.trim_ew = make_box(0.03, 0.04, self.grid_h, y0=0.14)
        self.corner_post = make_box(0.36, 0.48, 0.36, uv_scale=0.8)
        self.corner_cap = make_box(0.24, 0.06, 0.24, y0=0.48)

        # 5. Pilares estruturais nas paredes do hangar + vigas/luminárias no teto
        self.hangar_pillar = make_box(0.55, self.room_h - self.floor_y, 0.55, y0=self.floor_y)
        self.ceiling_beam = make_box(0.35, 0.28, self.room_d - 0.4, y0=self.room_h - 0.30)
        self.light_strip = make_box(3.4, 0.07, 0.32, y0=self.room_h - 0.34)

    def ceiling_lights(self) -> list[tuple[glm.vec3, glm.vec3]]:
        """Luzes pontuais frias do teto + reforço azulado vindo da janela norte."""
        y = self.room_h - 0.55
        col = glm.vec3(0.45, 0.56, 0.72) * 0.52
        win_col = glm.vec3(0.42, 0.62, 0.95) * 0.50
        return [
            (glm.vec3(self.cx - 4.2, y, self.cz - 2.4), col),
            (glm.vec3(self.cx + 4.2, y, self.cz - 2.4), col),
            (glm.vec3(self.cx - 4.2, y, self.cz + 2.4), col),
            (glm.vec3(self.cx + 4.2, y, self.cz + 2.4), col),
            (glm.vec3(self.cx, 3.8, self.cz - self.room_d * 0.5 + 1.8), win_col),
        ]

    def _curb_transforms(self) -> list[tuple]:
        w, h = self.grid_w, self.grid_h
        cx, cz = self.cx, self.cz
        off = 0.12
        items = [
            (self.curb_ns, glm.translate(glm.mat4(1), glm.vec3(cx, 0.0, -off)), MAT_METAL_ESC),
            (self.curb_ns, glm.translate(glm.mat4(1), glm.vec3(cx, 0.0, h + off)), MAT_METAL_ESC),
            (self.curb_ew, glm.translate(glm.mat4(1), glm.vec3(-off, 0.0, cz)), MAT_METAL_ESC),
            (self.curb_ew, glm.translate(glm.mat4(1), glm.vec3(w + off, 0.0, cz)), MAT_METAL_ESC),
            (self.hazard_ns, glm.translate(glm.mat4(1), glm.vec3(cx, 0.0, -off)), MAT_HAZARD),
            (self.hazard_ns, glm.translate(glm.mat4(1), glm.vec3(cx, 0.0, h + off)), MAT_HAZARD),
            (self.hazard_ew, glm.translate(glm.mat4(1), glm.vec3(-off, 0.0, cz)), MAT_HAZARD),
            (self.hazard_ew, glm.translate(glm.mat4(1), glm.vec3(w + off, 0.0, cz)), MAT_HAZARD),
            (self.trim_ns, glm.translate(glm.mat4(1), glm.vec3(cx, 0.0, 0.01)), _MAT_NEON_TRIM),
            (self.trim_ns, glm.translate(glm.mat4(1), glm.vec3(cx, 0.0, h - 0.01)), _MAT_NEON_TRIM),
            (self.trim_ew, glm.translate(glm.mat4(1), glm.vec3(0.01, 0.0, cz)), _MAT_NEON_TRIM),
            (self.trim_ew, glm.translate(glm.mat4(1), glm.vec3(w - 0.01, 0.0, cz)), _MAT_NEON_TRIM),
        ]
        for px in (-off, w + off):
            for pz in (-off, h + off):
                m = glm.translate(glm.mat4(1), glm.vec3(px, 0.0, pz))
                items.append((self.corner_post, m, _MAT_DARK_STRUCT))
                items.append((self.corner_cap, m, _MAT_NEON_TRIM))
        return items

    def draw(self, shader: Shader, eye_pos: glm.vec3 | None = None) -> None:
        cx, cz = self.cx, self.cz
        center_m = glm.translate(glm.mat4(1), glm.vec3(cx, 0.0, cz))

        # 1. Piso da arena com grade tática, variação por célula e cell map AO
        draw_textured(shader, self.arena_floor, center_m, MAT_CHAO, floor_mode=1)
        draw_textured(shader, self.platform_base, center_m, _MAT_DARK_STRUCT)

        # 2. Chão externo de concreto
        draw_textured(shader, self.outer_floor, center_m, MAT_CONCRETO)

        # 3. Borda da arena (mureta + hazard + neon + postes de canto)
        for mesh, model, mat in self._curb_transforms():
            draw_textured(shader, mesh, model, mat)

        # 4. Paredes e teto do hangar com backface culling (dollhouse quando câmera sai)
        hw, hd = self.room_w * 0.5, self.room_d * 0.5
        glEnable(GL_CULL_FACE)
        glCullFace(GL_BACK)

        # Parede Norte (Z = cz - hd, normal +Z para dentro)
        m_n = glm.translate(glm.mat4(1), glm.vec3(cx, self.floor_y, cz - hd))
        draw_textured(shader, self.wall_ns, m_n, MAT_PAINEL)

        # Janela industrial na parede norte
        m_win = glm.translate(glm.mat4(1), glm.vec3(cx, 2.6, cz - hd + 0.03))
        draw_textured(shader, self.window_quad, m_win, MAT_JANELA)

        # Parede Sul (Z = cz + hd, normal -Z)
        m_s = glm.translate(glm.mat4(1), glm.vec3(cx, self.floor_y, cz + hd))
        m_s = glm.rotate(m_s, glm.radians(180.0), glm.vec3(0, 1, 0))
        draw_textured(shader, self.wall_ns, m_s, MAT_PAINEL)

        # Parede Oeste (X = cx - hw, normal +X)
        m_w = glm.translate(glm.mat4(1), glm.vec3(cx - hw, self.floor_y, cz))
        m_w = glm.rotate(m_w, glm.radians(90.0), glm.vec3(0, 1, 0))
        draw_textured(shader, self.wall_ew, m_w, MAT_PAINEL)

        # Parede Leste (X = cx + hw, normal -X)
        m_e = glm.translate(glm.mat4(1), glm.vec3(cx + hw, self.floor_y, cz))
        m_e = glm.rotate(m_e, glm.radians(-90.0), glm.vec3(0, 1, 0))
        draw_textured(shader, self.wall_ew, m_e, MAT_PAINEL)

        # Teto (normal -Y)
        draw_textured(shader, self.ceiling, center_m, _MAT_DARK_STRUCT)
        glDisable(GL_CULL_FACE)

        # 5. Pilares (só nas paredes que não estão entre a câmera e o centro)
        ey_z = float(eye_pos.z) if eye_pos is not None else cz
        ey_y = float(eye_pos.y) if eye_pos is not None else 3.0
        for dx in (-11.0, -4.5, 4.5, 11.0):
            if ey_z > cz - hd + 0.5:  # parede norte visível por dentro
                mp = glm.translate(glm.mat4(1), glm.vec3(cx + dx, 0.0, cz - hd + 0.28))
                draw_textured(shader, self.hangar_pillar, mp, _MAT_DARK_STRUCT)
            if ey_z < cz + hd - 0.5:  # parede sul visível por dentro
                mp = glm.translate(glm.mat4(1), glm.vec3(cx + dx, 0.0, cz + hd - 0.28))
                draw_textured(shader, self.hangar_pillar, mp, _MAT_DARK_STRUCT)

        # Vigas e faixas luminosas do teto: só quando a câmera está abaixo do teto
        if ey_y < self.room_h - 0.4:
            for dx in (-6.0, 0.0, 6.0):
                mb = glm.translate(glm.mat4(1), glm.vec3(cx + dx, 0.0, cz))
                draw_textured(shader, self.ceiling_beam, mb, _MAT_DARK_STRUCT)
            for dx in (-4.2, 4.2):
                for dz in (-2.8, 2.8):
                    ml = glm.translate(glm.mat4(1), glm.vec3(cx + dx, 0.0, cz + dz))
                    draw_textured(shader, self.light_strip, ml, _MAT_CEIL_LIGHT)

    def draw_depth(self, shader: Shader) -> None:
        """Borda e postes projetam sombra no piso da arena."""
        for mesh, model, mat in self._curb_transforms():
            if mat is _MAT_NEON_TRIM:
                continue
            draw_depth(shader, mesh, model)

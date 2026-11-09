"""Malha GPU (VAO/VBO/EBO) e material associado."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from OpenGL.GL import (
    GL_ARRAY_BUFFER,
    GL_ELEMENT_ARRAY_BUFFER,
    GL_FLOAT,
    GL_STATIC_DRAW,
    GL_TRIANGLES,
    GL_UNSIGNED_INT,
    glBindBuffer,
    glBindVertexArray,
    glBufferData,
    glDrawElements,
    glEnableVertexAttribArray,
    glGenBuffers,
    glGenVertexArrays,
    glVertexAttribPointer,
)
import glm


@dataclass
class Material:
    kd: glm.vec3
    ks: glm.vec3 = None  # type: ignore[assignment]
    shininess: float = 32.0
    texture_id: int | None = None
    normal_id: int | None = None
    emissive: glm.vec3 = None  # type: ignore[assignment]
    emissive_id: int | None = None
    pulse_hz: float = 0.0
    alpha_tex: bool = False
    triplanar_scale: float = 0.0  # >0: mapeamento em 2 etapas (caixa/triplanar) em world space

    def __post_init__(self) -> None:
        if self.ks is None:
            self.ks = glm.vec3(0.15, 0.15, 0.15)
        if self.emissive is None:
            self.emissive = glm.vec3(0.0, 0.0, 0.0)


# Materiais pré-definidos (madeira / metal / fosco / emissivo / ambiente hangar)
MAT_MADEIRA = Material(glm.vec3(0.95, 0.88, 0.80), glm.vec3(0.07, 0.06, 0.05), 10.0)
MAT_METAL = Material(glm.vec3(0.75, 0.78, 0.84), glm.vec3(0.38, 0.40, 0.44), 56.0)
MAT_METAL_ESC = Material(glm.vec3(0.78, 0.82, 0.88), glm.vec3(0.42, 0.45, 0.50), 64.0, triplanar_scale=0.5)
MAT_HAZARD = Material(glm.vec3(1.0, 1.0, 1.0), glm.vec3(0.22, 0.22, 0.22), 28.0, triplanar_scale=0.65)
MAT_CONCRETO = Material(glm.vec3(0.92, 0.95, 1.0), glm.vec3(0.12, 0.13, 0.15), 18.0)
MAT_PAINEL = Material(
    glm.vec3(1.0, 1.0, 1.0),
    glm.vec3(0.28, 0.32, 0.38),
    42.0,
    emissive=glm.vec3(0.55, 0.85, 1.05),
)
MAT_JANELA = Material(
    glm.vec3(1.0, 1.0, 1.0),
    glm.vec3(0.45, 0.50, 0.60),
    72.0,
    emissive=glm.vec3(1.35, 1.55, 1.85),
)
MAT_BASE = Material(glm.vec3(1.0, 1.0, 1.0), glm.vec3(0.38, 0.42, 0.48), 56.0, emissive=glm.vec3(0.2, 0.75, 1.0))
MAT_BASE_ALFA = Material(glm.vec3(0.88, 0.96, 1.05), glm.vec3(0.42, 0.48, 0.55), 64.0, emissive=glm.vec3(0.20, 0.85, 1.25))
MAT_BASE_BETA = Material(glm.vec3(1.05, 0.90, 0.84), glm.vec3(0.48, 0.38, 0.32), 64.0, emissive=glm.vec3(1.25, 0.38, 0.14))
MAT_FOSCO = Material(glm.vec3(0.32, 0.68, 0.38), glm.vec3(0.04, 0.04, 0.04), 6.0)
MAT_ABAJUR = Material(
    glm.vec3(0.95, 0.82, 0.62),
    glm.vec3(0.06, 0.06, 0.05),
    8.0,
    emissive=glm.vec3(0.55, 0.42, 0.22),
)
MAT_LUMINARIA = Material(
    glm.vec3(0.82, 0.86, 0.92),
    glm.vec3(0.38, 0.40, 0.45),
    52.0,
    emissive=glm.vec3(0.45, 0.55, 0.65),
)
MAT_MINERIO = Material(glm.vec3(1.0, 1.0, 1.0), glm.vec3(0.35, 0.30, 0.16), 44.0, emissive=glm.vec3(0.65, 0.45, 0.12))
MAT_DIAMANTE = Material(glm.vec3(1.25, 1.45, 1.65), glm.vec3(0.55, 0.60, 0.70), 88.0, emissive=glm.vec3(0.38, 0.82, 1.35))
MAT_OURO = Material(glm.vec3(1.0, 1.0, 1.0), glm.vec3(0.45, 0.36, 0.14), 60.0, emissive=glm.vec3(0.82, 0.56, 0.10))
MAT_PRATA = Material(glm.vec3(1.0, 1.0, 1.0), glm.vec3(0.45, 0.48, 0.54), 68.0, emissive=glm.vec3(0.48, 0.54, 0.68))
MAT_RUBI = Material(glm.vec3(0.95, 0.16, 0.28), glm.vec3(0.55, 0.22, 0.28), 76.0, emissive=glm.vec3(1.15, 0.14, 0.26))
MAT_BRONZE = Material(glm.vec3(0.82, 0.46, 0.22), glm.vec3(0.38, 0.22, 0.12), 44.0, emissive=glm.vec3(0.62, 0.28, 0.10))
MAT_ARMADILHA = Material(
    glm.vec3(1.0, 1.0, 1.0),
    glm.vec3(0.28, 0.22, 0.20),
    32.0,
    emissive=glm.vec3(1.35, 0.25, 0.08),
    pulse_hz=1.8,
)
MAT_PAREDE = Material(glm.vec3(1.0, 1.0, 1.0), glm.vec3(0.28, 0.30, 0.34), 48.0)
MAT_CHAO = Material(glm.vec3(1.0, 1.0, 1.0), glm.vec3(0.36, 0.38, 0.42), 64.0)
MAT_ALFA = Material(glm.vec3(0.28, 0.55, 0.95), glm.vec3(0.22, 0.24, 0.3), 40.0)
MAT_BETA = Material(glm.vec3(0.92, 0.35, 0.28), glm.vec3(0.25, 0.16, 0.14), 40.0)


class Mesh:
    """Interleaved pos(3) + normal(3) + uv(2)."""

    def __init__(self, vertices: np.ndarray, indices: np.ndarray, *, dynamic: bool = False) -> None:
        from OpenGL.GL import GL_DYNAMIC_DRAW

        self.count = int(indices.size)
        self.vao = glGenVertexArrays(1)
        self.vbo = glGenBuffers(1)
        ebo = glGenBuffers(1)
        usage = GL_DYNAMIC_DRAW if dynamic else GL_STATIC_DRAW
        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, usage)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
        stride = 8 * 4
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, False, stride, None)
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 3, GL_FLOAT, False, stride, ctypes_c(3 * 4))
        glEnableVertexAttribArray(2)
        glVertexAttribPointer(2, 2, GL_FLOAT, False, stride, ctypes_c(6 * 4))
        glBindVertexArray(0)
        self._dynamic = dynamic

    def update_vertices(self, vertices: np.ndarray) -> None:
        """Atualiza VBO (clips de animação)."""
        from OpenGL.GL import glBufferSubData

        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferSubData(GL_ARRAY_BUFFER, 0, vertices.nbytes, vertices)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def draw(self) -> None:
        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, self.count, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)

    def draw_range(self, first: int, count: int) -> None:
        """Desenha um subintervalo do EBO (first/count em índices, não triângulos)."""
        import ctypes

        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, int(count), GL_UNSIGNED_INT, ctypes.c_void_p(int(first) * 4))
        glBindVertexArray(0)


def ctypes_c(offset: int):
    import ctypes

    return ctypes.c_void_p(offset)

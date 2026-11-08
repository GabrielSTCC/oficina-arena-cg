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

    def __post_init__(self) -> None:
        if self.ks is None:
            self.ks = glm.vec3(0.15, 0.15, 0.15)
        if self.emissive is None:
            self.emissive = glm.vec3(0.0, 0.0, 0.0)


# Materiais pré-definidos (madeira / metal / fosco / emissivo leve)
MAT_MADEIRA = Material(glm.vec3(0.55, 0.35, 0.18), glm.vec3(0.08, 0.08, 0.08), 8.0)
MAT_METAL = Material(glm.vec3(0.55, 0.58, 0.62), glm.vec3(0.28, 0.28, 0.28), 48.0)
MAT_BASE = Material(glm.vec3(1.0, 1.0, 1.0), glm.vec3(0.18, 0.18, 0.18), 40.0)
MAT_FOSCO = Material(glm.vec3(0.25, 0.55, 0.28), glm.vec3(0.04, 0.04, 0.04), 4.0)
MAT_MINERIO = Material(glm.vec3(1.0, 1.0, 1.0), glm.vec3(0.3, 0.28, 0.15), 40.0, emissive=glm.vec3(0.55, 0.4, 0.1))
MAT_DIAMANTE = Material(glm.vec3(1.0, 1.0, 1.0), glm.vec3(0.35, 0.35, 0.4), 72.0, emissive=glm.vec3(0.25, 0.55, 0.9))
MAT_OURO = Material(glm.vec3(1.0, 1.0, 1.0), glm.vec3(0.32, 0.26, 0.12), 48.0, emissive=glm.vec3(0.7, 0.48, 0.08))
MAT_PRATA = Material(glm.vec3(1.0, 1.0, 1.0), glm.vec3(0.3, 0.3, 0.35), 56.0, emissive=glm.vec3(0.4, 0.45, 0.55))
MAT_RUBI = Material(glm.vec3(0.95, 0.25, 0.35), glm.vec3(0.28, 0.1, 0.12), 48.0, emissive=glm.vec3(0.7, 0.08, 0.15))
MAT_BRONZE = Material(glm.vec3(0.75, 0.45, 0.25), glm.vec3(0.22, 0.14, 0.08), 32.0, emissive=glm.vec3(0.45, 0.22, 0.08))
MAT_ARMADILHA = Material(glm.vec3(0.85, 0.22, 0.12), glm.vec3(0.18, 0.06, 0.04), 20.0, emissive=glm.vec3(0.85, 0.12, 0.06))
MAT_PAREDE = Material(glm.vec3(1.0, 1.0, 1.0), glm.vec3(0.28, 0.28, 0.30), 48.0)
MAT_CHAO = Material(glm.vec3(1.0, 1.0, 1.0), glm.vec3(0.35, 0.35, 0.38), 64.0)
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
        from OpenGL.GL import GL_DYNAMIC_DRAW, glBufferSubData

        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferSubData(GL_ARRAY_BUFFER, 0, vertices.nbytes, vertices)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def draw(self) -> None:
        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, self.count, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)


def ctypes_c(offset: int):
    import ctypes

    return ctypes.c_void_p(offset)

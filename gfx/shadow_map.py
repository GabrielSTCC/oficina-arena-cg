"""Shadow map: FBO de profundidade + matriz luz ortográfica."""

from __future__ import annotations

import glm
from OpenGL.GL import (
    GL_CLAMP_TO_BORDER,
    GL_DEPTH_ATTACHMENT,
    GL_DEPTH_COMPONENT,
    GL_DEPTH_COMPONENT24,
    GL_FLOAT,
    GL_FRAMEBUFFER,
    GL_FRAMEBUFFER_COMPLETE,
    GL_LINEAR,
    GL_NONE,
    GL_TEXTURE_2D,
    GL_TEXTURE_BORDER_COLOR,
    GL_TEXTURE_MAG_FILTER,
    GL_TEXTURE_MIN_FILTER,
    GL_TEXTURE_WRAP_S,
    GL_TEXTURE_WRAP_T,
    glBindFramebuffer,
    glBindTexture,
    glCheckFramebufferStatus,
    glDrawBuffer,
    glFramebufferTexture2D,
    glGenFramebuffers,
    glGenTextures,
    glReadBuffer,
    glTexImage2D,
    glTexParameterfv,
    glTexParameteri,
)


class ShadowMap:
    def __init__(self, size: int = 2048) -> None:
        self.size = size
        self.depth_tex = int(glGenTextures(1))
        glBindTexture(GL_TEXTURE_2D, self.depth_tex)
        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_DEPTH_COMPONENT24,
            size,
            size,
            0,
            GL_DEPTH_COMPONENT,
            GL_FLOAT,
            None,
        )
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_BORDER)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_BORDER)
        border = (1.0, 1.0, 1.0, 1.0)
        glTexParameterfv(GL_TEXTURE_2D, GL_TEXTURE_BORDER_COLOR, border)

        self.fbo = int(glGenFramebuffers(1))
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
        glFramebufferTexture2D(
            GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, self.depth_tex, 0
        )
        glDrawBuffer(GL_NONE)
        glReadBuffer(GL_NONE)
        status = glCheckFramebufferStatus(GL_FRAMEBUFFER)
        if status != GL_FRAMEBUFFER_COMPLETE:
            raise RuntimeError(f"Shadow FBO incompleto: {status}")
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

    def bind(self) -> None:
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)

    @staticmethod
    def unbind() -> None:
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

    @staticmethod
    def light_matrices(
        light_dir: glm.vec3,
        *,
        center: glm.vec3,
        radius: float = 12.0,
        near: float = 1.0,
        far: float = 40.0,
    ) -> tuple[glm.mat4, glm.mat4, glm.mat4]:
        """Retorna (light_view, light_proj, light_vp) para luz direcional."""
        d = glm.normalize(light_dir)
        # câmera da luz: atrás do centro, olhando na direção da luz
        eye = center - d * (radius * 1.4)
        up = glm.vec3(0.0, 1.0, 0.0)
        if abs(glm.dot(d, up)) > 0.95:
            up = glm.vec3(0.0, 0.0, 1.0)
        view = glm.lookAt(eye, center, up)
        proj = glm.ortho(-radius, radius, -radius, radius, near, far)
        return view, proj, proj * view

"""Post-process: FBO MRT (cena HDR + bright) + blur + Exposure tone map + gamma."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from OpenGL.GL import (
    GL_ARRAY_BUFFER,
    GL_CLAMP_TO_EDGE,
    GL_COLOR_ATTACHMENT0,
    GL_COLOR_ATTACHMENT1,
    GL_COLOR_BUFFER_BIT,
    GL_DEPTH_ATTACHMENT,
    GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_COMPONENT,
    GL_DEPTH_COMPONENT24,
    GL_DEPTH_TEST,
    GL_FLOAT,
    GL_FRAMEBUFFER,
    GL_FRAMEBUFFER_COMPLETE,
    GL_LINEAR,
    GL_RGBA,
    GL_RGBA16F,
    GL_STATIC_DRAW,
    GL_TEXTURE0,
    GL_TEXTURE1,
    GL_TEXTURE_2D,
    GL_TEXTURE_MAG_FILTER,
    GL_TEXTURE_MIN_FILTER,
    GL_TEXTURE_WRAP_S,
    GL_TEXTURE_WRAP_T,
    GL_TRIANGLES,
    GL_UNSIGNED_BYTE,
    glActiveTexture,
    glBindBuffer,
    glBindFramebuffer,
    glBindTexture,
    glBindVertexArray,
    glBufferData,
    glCheckFramebufferStatus,
    glClear,
    glDisable,
    glDrawArrays,
    glDrawBuffers,
    glEnable,
    glEnableVertexAttribArray,
    glFramebufferTexture2D,
    glGenBuffers,
    glGenFramebuffers,
    glGenTextures,
    glGenVertexArrays,
    glTexImage2D,
    glTexParameteri,
    glUniform2f,
    glVertexAttribPointer,
    glViewport,
)

from gfx.shader import Shader


def _make_color_tex(w: int, h: int) -> int:
    tid = int(glGenTextures(1))
    glBindTexture(GL_TEXTURE_2D, tid)
    try:
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA16F, w, h, 0, GL_RGBA, GL_FLOAT, None)
    except Exception:
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    return tid


def _make_depth_tex(w: int, h: int) -> int:
    tid = int(glGenTextures(1))
    glBindTexture(GL_TEXTURE_2D, tid)
    glTexImage2D(
        GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT24, w, h, 0, GL_DEPTH_COMPONENT, GL_FLOAT, None
    )
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    return tid


def _fbo_single(tex: int) -> int:
    fbo = int(glGenFramebuffers(1))
    glBindFramebuffer(GL_FRAMEBUFFER, fbo)
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, tex, 0)
    if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
        raise RuntimeError("Postprocess FBO incompleto")
    glBindFramebuffer(GL_FRAMEBUFFER, 0)
    return fbo


class PostProcess:
    def __init__(self, shader_dir: Path, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.blur_shader = Shader(shader_dir / "fullscreen.vert", shader_dir / "blur.frag")
        self.composite_shader = Shader(shader_dir / "fullscreen.vert", shader_dir / "composite.frag")
        self._quad_vao = self._make_quad()
        self.scene_tex = 0
        self.scene_depth = 0
        self.scene_fbo = 0
        self.bright_tex = 0
        self.blur_tex_a = 0
        self.blur_fbo_a = 0
        self.blur_tex_b = 0
        self.blur_fbo_b = 0
        self.resize(width, height)

    @staticmethod
    def _make_quad() -> int:
        verts = np.array(
            [
                -1.0, -1.0, 0.0, 0.0,
                 1.0, -1.0, 1.0, 0.0,
                 1.0,  1.0, 1.0, 1.0,
                -1.0, -1.0, 0.0, 0.0,
                 1.0,  1.0, 1.0, 1.0,
                -1.0,  1.0, 0.0, 1.0,
            ],
            dtype=np.float32,
        )
        vao = int(glGenVertexArrays(1))
        vbo = int(glGenBuffers(1))
        glBindVertexArray(vao)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, verts.nbytes, verts, GL_STATIC_DRAW)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, False, 16, None)
        glEnableVertexAttribArray(1)
        import ctypes

        glVertexAttribPointer(1, 2, GL_FLOAT, False, 16, ctypes.c_void_p(8))
        glBindVertexArray(0)
        return vao

    def resize(self, width: int, height: int) -> None:
        self.width = max(1, width)
        self.height = max(1, height)
        self.scene_tex = _make_color_tex(self.width, self.height)
        self.bright_tex = _make_color_tex(self.width, self.height)
        self.scene_depth = _make_depth_tex(self.width, self.height)

        self.scene_fbo = int(glGenFramebuffers(1))
        glBindFramebuffer(GL_FRAMEBUFFER, self.scene_fbo)
        glFramebufferTexture2D(
            GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.scene_tex, 0
        )
        glFramebufferTexture2D(
            GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT1, GL_TEXTURE_2D, self.bright_tex, 0
        )
        glFramebufferTexture2D(
            GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, self.scene_depth, 0
        )
        glDrawBuffers(2, [GL_COLOR_ATTACHMENT0, GL_COLOR_ATTACHMENT1])
        if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
            raise RuntimeError("Scene MRT FBO incompleto")
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        self.blur_tex_a = _make_color_tex(self.width, self.height)
        self.blur_fbo_a = _fbo_single(self.blur_tex_a)
        self.blur_tex_b = _make_color_tex(self.width, self.height)
        self.blur_fbo_b = _fbo_single(self.blur_tex_b)

    def begin_scene(self) -> None:
        glBindFramebuffer(GL_FRAMEBUFFER, self.scene_fbo)
        glDrawBuffers(2, [GL_COLOR_ATTACHMENT0, GL_COLOR_ATTACHMENT1])
        glViewport(0, 0, self.width, self.height)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glEnable(GL_DEPTH_TEST)

    def end_and_bloom(
        self,
        *,
        strength: float = 0.35,
        exposure: float = 1.8,
        blur_passes: int = 2,
    ) -> None:
        """Blur do RT1 (bright do Phong) + Exposure tone map + gamma."""
        glDisable(GL_DEPTH_TEST)

        src = self.bright_tex
        texel_x = 1.0 / self.width
        texel_y = 1.0 / self.height
        for _ in range(blur_passes):
            glBindFramebuffer(GL_FRAMEBUFFER, self.blur_fbo_a)
            glDrawBuffers(1, [GL_COLOR_ATTACHMENT0])
            glClear(GL_COLOR_BUFFER_BIT)
            self.blur_shader.use()
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, src)
            self.blur_shader.set_int("uTex", 0)
            glUniform2f(self.blur_shader.loc("uDirection"), 1.0, 0.0)
            glUniform2f(self.blur_shader.loc("uTexelSize"), texel_x, texel_y)
            self._draw_quad()

            glBindFramebuffer(GL_FRAMEBUFFER, self.blur_fbo_b)
            glClear(GL_COLOR_BUFFER_BIT)
            glBindTexture(GL_TEXTURE_2D, self.blur_tex_a)
            glUniform2f(self.blur_shader.loc("uDirection"), 0.0, 1.0)
            self._draw_quad()
            src = self.blur_tex_b

        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        glViewport(0, 0, self.width, self.height)
        glClear(GL_COLOR_BUFFER_BIT)
        self.composite_shader.use()
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.scene_tex)
        self.composite_shader.set_int("uScene", 0)
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D, src)
        self.composite_shader.set_int("uBloom", 1)
        self.composite_shader.set_float("uStrength", strength)
        self.composite_shader.set_float("uExposure", exposure)
        self._draw_quad()
        glActiveTexture(GL_TEXTURE0)
        glEnable(GL_DEPTH_TEST)

    def _draw_quad(self) -> None:
        glBindVertexArray(self._quad_vao)
        glDrawArrays(GL_TRIANGLES, 0, 6)
        glBindVertexArray(0)

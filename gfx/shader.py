"""Compilação e uso de programas GLSL."""

from __future__ import annotations

from pathlib import Path

from OpenGL.GL import (
    GL_FRAGMENT_SHADER,
    GL_VERTEX_SHADER,
    glAttachShader,
    glCompileShader,
    glCreateProgram,
    glCreateShader,
    glDeleteShader,
    glGetProgramInfoLog,
    glGetProgramiv,
    glGetShaderInfoLog,
    glGetShaderiv,
    glGetUniformLocation,
    glLinkProgram,
    glShaderSource,
    glUseProgram,
    GL_COMPILE_STATUS,
    GL_LINK_STATUS,
    GL_TRUE,
)
import glm


class Shader:
    def __init__(self, vert_path: Path, frag_path: Path) -> None:
        vs = self._compile(vert_path.read_text(encoding="utf-8"), GL_VERTEX_SHADER)
        fs = self._compile(frag_path.read_text(encoding="utf-8"), GL_FRAGMENT_SHADER)
        self.program = glCreateProgram()
        glAttachShader(self.program, vs)
        glAttachShader(self.program, fs)
        glLinkProgram(self.program)
        if glGetProgramiv(self.program, GL_LINK_STATUS) != GL_TRUE:
            raise RuntimeError(glGetProgramInfoLog(self.program).decode())
        glDeleteShader(vs)
        glDeleteShader(fs)
        self._locs: dict[str, int] = {}

    @staticmethod
    def _compile(source: str, kind: int) -> int:
        sid = glCreateShader(kind)
        glShaderSource(sid, source)
        glCompileShader(sid)
        if glGetShaderiv(sid, GL_COMPILE_STATUS) != GL_TRUE:
            raise RuntimeError(glGetShaderInfoLog(sid).decode())
        return sid

    def use(self) -> None:
        glUseProgram(self.program)

    def loc(self, name: str) -> int:
        if name not in self._locs:
            self._locs[name] = glGetUniformLocation(self.program, name)
        return self._locs[name]

    def set_mat4(self, name: str, m: glm.mat4) -> None:
        from OpenGL.GL import glUniformMatrix4fv

        glUniformMatrix4fv(self.loc(name), 1, False, glm.value_ptr(m))

    def set_mat3(self, name: str, m: glm.mat3) -> None:
        from OpenGL.GL import glUniformMatrix3fv

        glUniformMatrix3fv(self.loc(name), 1, False, glm.value_ptr(m))

    def set_vec3(self, name: str, v: glm.vec3) -> None:
        from OpenGL.GL import glUniform3f

        glUniform3f(self.loc(name), float(v.x), float(v.y), float(v.z))

    def set_float(self, name: str, v: float) -> None:
        from OpenGL.GL import glUniform1f

        glUniform1f(self.loc(name), float(v))

    def set_int(self, name: str, v: int) -> None:
        from OpenGL.GL import glUniform1i

        glUniform1i(self.loc(name), int(v))

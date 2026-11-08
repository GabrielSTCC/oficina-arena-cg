"""Carrega imagem → textura OpenGL 2D."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from OpenGL.GL import (
    GL_LINEAR,
    GL_LINEAR_MIPMAP_LINEAR,
    GL_REPEAT,
    GL_RGB,
    GL_RGBA,
    GL_TEXTURE_2D,
    GL_TEXTURE_MAG_FILTER,
    GL_TEXTURE_MIN_FILTER,
    GL_TEXTURE_WRAP_S,
    GL_TEXTURE_WRAP_T,
    GL_UNSIGNED_BYTE,
    glBindTexture,
    glGenerateMipmap,
    glGenTextures,
    glTexImage2D,
    glTexParameteri,
)
from PIL import Image

_CACHE: dict[str, int] = {}


def load_texture(path: Path) -> int | None:
    if not path.is_file():
        return None
    key = str(path.resolve())
    if key in _CACHE:
        return _CACHE[key]
    # glTF/PNG: origem top-left; OpenGL: bottom-left
    img = Image.open(path).convert("RGBA").transpose(Image.FLIP_TOP_BOTTOM)
    data = np.asarray(img, dtype=np.uint8)
    h, w = data.shape[:2]
    tid = int(glGenTextures(1))
    glBindTexture(GL_TEXTURE_2D, tid)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
    glGenerateMipmap(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, 0)
    _CACHE[key] = tid
    return tid

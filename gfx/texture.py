"""Carrega imagem → textura OpenGL 2D e texturas de dados (cell map)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from OpenGL.GL import (
    GL_CLAMP_TO_EDGE,
    GL_LINEAR,
    GL_LINEAR_MIPMAP_LINEAR,
    GL_RED,
    GL_REPEAT,
    GL_R8,
    GL_RGBA,
    GL_TEXTURE_2D,
    GL_TEXTURE_MAG_FILTER,
    GL_TEXTURE_MIN_FILTER,
    GL_TEXTURE_WRAP_S,
    GL_TEXTURE_WRAP_T,
    GL_UNPACK_ALIGNMENT,
    GL_UNSIGNED_BYTE,
    glBindTexture,
    glGenerateMipmap,
    glGenTextures,
    glPixelStorei,
    glTexImage2D,
    glTexParameterf,
    glTexParameteri,
    glTexSubImage2D,
)
from PIL import Image

_CACHE: dict[tuple[str, int | None, int], int] = {}

# Constantes de filtro anisotrópico (EXT_texture_filter_anisotropic)
GL_TEXTURE_MAX_ANISOTROPY_EXT = 0x84FE
GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT = 0x84FF


def _apply_anisotropy(aniso: float) -> None:
    if aniso <= 1.0:
        return
    try:
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAX_ANISOTROPY_EXT, float(aniso))
    except Exception:
        pass


def load_texture(
    path: Path,
    *,
    max_size: int | None = 1024,
    wrap: int = GL_REPEAT,
    aniso: float = 8.0,
) -> int | None:
    if not path.is_file():
        return None
    key = (str(path.resolve()), max_size, int(wrap))
    if key in _CACHE:
        return _CACHE[key]
    # glTF/PNG: origem top-left; OpenGL: bottom-left
    img = Image.open(path).convert("RGBA")
    if max_size is not None and (img.width > max_size or img.height > max_size):
        scale = min(max_size / img.width, max_size / img.height)
        nw = max(1, int(round(img.width * scale)))
        nh = max(1, int(round(img.height * scale)))
        img = img.resize((nw, nh), Image.LANCZOS)
    img = img.transpose(Image.FLIP_TOP_BOTTOM)
    data = np.asarray(img, dtype=np.uint8)
    h, w = data.shape[:2]
    tid = int(glGenTextures(1))
    glBindTexture(GL_TEXTURE_2D, tid)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, wrap)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, wrap)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    _apply_anisotropy(aniso)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
    glGenerateMipmap(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, 0)
    _CACHE[key] = tid
    return tid


def make_data_texture_rgba(arr: np.ndarray) -> int:
    """Cria textura RGBA8 2D (ex.: cell map 15×9: R=wallAO, G=trap, B=alfa, A=beta)."""
    h, w = arr.shape[:2]
    data = np.ascontiguousarray(np.clip(arr, 0, 255).astype(np.uint8))
    tid = int(glGenTextures(1))
    glBindTexture(GL_TEXTURE_2D, tid)
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
    glBindTexture(GL_TEXTURE_2D, 0)
    return tid


def update_data_texture_rgba(tid: int, arr: np.ndarray) -> None:
    """Atualiza textura RGBA8 (realoca se o tamanho mudou, ex.: arena redimensionada)."""
    h, w = arr.shape[:2]
    data = np.ascontiguousarray(np.clip(arr, 0, 255).astype(np.uint8))
    glBindTexture(GL_TEXTURE_2D, tid)
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
    glBindTexture(GL_TEXTURE_2D, 0)

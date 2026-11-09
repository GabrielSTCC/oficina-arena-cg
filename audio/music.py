"""Música de fundo via pygame.mixer (falha silenciosa se áudio indisponível)."""

from __future__ import annotations

from pathlib import Path

_ok = False
_volume = 0.8


def init() -> None:
    global _ok
    try:
        import pygame

        pygame.mixer.init()
        _ok = True
        set_volume(_volume)
        # canais para música + fala
        try:
            from audio import sfx

            sfx.init()
        except Exception:
            pass
    except Exception:
        _ok = False


def get_volume() -> float:
    return float(_volume)


def set_volume(v: float) -> None:
    global _volume
    _volume = max(0.0, min(1.0, float(v)))
    if not _ok:
        return
    try:
        import pygame

        pygame.mixer.music.set_volume(_volume)
    except Exception:
        pass


def play_loop(path: Path | str) -> None:
    if not _ok:
        return
    p = Path(path)
    if not p.is_file():
        return
    try:
        import pygame

        pygame.mixer.music.load(str(p))
        pygame.mixer.music.set_volume(_volume)
        pygame.mixer.music.play(loops=-1)
    except Exception:
        pass


def stop() -> None:
    if not _ok:
        return
    try:
        import pygame

        pygame.mixer.music.stop()
    except Exception:
        pass

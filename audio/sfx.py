"""Efeitos one-shot (fala dos robôs) via pygame.mixer.Sound."""

from __future__ import annotations

from pathlib import Path

from audio.music import get_volume

_ok = False
_channel = None
_cache: dict[str, object] = {}


def init() -> None:
    global _ok, _channel
    try:
        import pygame

        if pygame.mixer.get_init() is None:
            pygame.mixer.init()
        _channel = pygame.mixer.Channel(1)
        _ok = True
    except Exception:
        _ok = False
        _channel = None


def stop_voice() -> None:
    if not _ok or _channel is None:
        return
    try:
        _channel.stop()
    except Exception:
        pass


def play_voice(path: Path | str) -> None:
    """Toca um áudio one-shot; para a fala anterior."""
    if not _ok or _channel is None:
        return
    p = Path(path)
    if not p.is_file():
        return
    try:
        import pygame

        key = str(p.resolve())
        snd = _cache.get(key)
        if snd is None:
            snd = pygame.mixer.Sound(key)
            _cache[key] = snd
        snd.set_volume(get_volume())
        _channel.stop()
        _channel.play(snd)
    except Exception:
        pass

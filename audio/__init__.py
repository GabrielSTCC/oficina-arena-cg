"""Áudio da Oficina Arena (música da dança de vitória)."""

from audio.music import get_volume, init, play_loop, set_volume, stop
from audio.sfx import play_voice, stop_voice

__all__ = [
    "init",
    "play_loop",
    "stop",
    "get_volume",
    "set_volume",
    "play_voice",
    "stop_voice",
]

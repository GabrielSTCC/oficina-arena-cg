"""Catálogo de modelos de robô (clips Mixamo texturizados)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from gfx.anim_clip import AnimClip, load_anim_clip

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "assets" / "models"
AUDIO_DIR = ROOT / "assets" / "audio"

# (arquivo_clip, chave_musica) por robô
_DANCES: dict[str, list[tuple[str, str]]] = {
    "robo3": [("dance1", "salsa"), ("dance2", "opaganastar")],
    "robo5": [("dance1", "hiphop"), ("dance2", "salsa")],
}


@dataclass
class DanceEntry:
    clip: AnimClip
    music_key: str

    @property
    def music_path(self) -> Path:
        return AUDIO_DIR / f"{self.music_key}.mp3"


@dataclass
class RobotModel:
    key: str
    nome: str
    walk: AnimClip | None = None
    idle: AnimClip | None = None
    kneel: AnimClip | None = None
    dances: list[DanceEntry] = field(default_factory=list)


def _load_dir(key: str, nome: str) -> RobotModel | None:
    d = MODELS_DIR / f"{key}_clips"
    if not (d / "walk.npz").is_file():
        return None
    walk = load_anim_clip(d / "walk.npz", in_place=True)
    idle = load_anim_clip(d / "idle.npz", in_place=True) or walk
    kneel = load_anim_clip(d / "kneel.npz", in_place=True)
    dances: list[DanceEntry] = []
    for clip_name, music_key in _DANCES.get(key, []):
        clip = load_anim_clip(d / f"{clip_name}.npz", in_place=True)
        if clip is not None:
            dances.append(DanceEntry(clip=clip, music_key=music_key))
    # Preload só locomotion (danças sob demanda)
    for clip in (walk, idle, kneel):
        if clip is not None:
            clip.preload_meshes()
    return RobotModel(key=key, nome=nome, walk=walk, idle=idle, kneel=kneel, dances=dances)


def load_robot_models() -> list[RobotModel]:
    """Carrega Robo 3 e Robo 5 se os clips existirem."""
    out: list[RobotModel] = []
    for key, nome in (("robo3", "Robo 3"), ("robo5", "Robo 5")):
        m = _load_dir(key, nome)
        if m is not None:
            out.append(m)
    return out

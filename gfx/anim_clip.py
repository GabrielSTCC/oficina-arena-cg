"""Clips de animação vertex (Mixamo exportados p/ .npz)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from gfx.mesh import Mesh


@dataclass
class AnimClip:
    pos: np.ndarray  # (F, V, 3)
    nrm: np.ndarray  # (F, V, 3)
    idx: np.ndarray  # (T,)
    name: str = ""

    @property
    def n_frames(self) -> int:
        return int(self.pos.shape[0])

    @property
    def n_verts(self) -> int:
        return int(self.pos.shape[1])

    def interleaved(self, frame: int) -> np.ndarray:
        f = int(frame) % self.n_frames
        p = self.pos[f]
        n = self.nrm[f]
        uv = np.zeros((self.n_verts, 2), dtype=np.float32)
        return np.concatenate([p, n, uv], axis=1).astype(np.float32).ravel()

    def make_mesh(self, frame: int = 0) -> Mesh:
        return Mesh(self.interleaved(frame), self.idx.astype(np.uint32))

    def make_in_place(self) -> None:
        """Remove deslocamento XZ do root (Mixamo); o WASD cuida da distância na grade."""
        pos = self.pos
        # ancora no centro XZ do frame 0
        c0x = float(pos[0, :, 0].mean())
        c0z = float(pos[0, :, 2].mean())
        for f in range(self.n_frames):
            pos[f, :, 0] -= float(pos[f, :, 0].mean()) - c0x
            pos[f, :, 2] -= float(pos[f, :, 2].mean()) - c0z


def load_anim_clip(path: Path, *, in_place: bool = False) -> AnimClip | None:
    if not path.is_file():
        return None
    data = np.load(path)
    name = ""
    if "action" in data:
        raw = data["action"]
        name = str(raw) if np.ndim(raw) == 0 else str(raw.item() if hasattr(raw, "item") else raw)
    clip = AnimClip(
        pos=np.asarray(data["pos"], dtype=np.float32).copy(),
        nrm=np.asarray(data["nrm"], dtype=np.float32),
        idx=np.asarray(data["idx"], dtype=np.uint32),
        name=name,
    )
    if in_place:
        clip.make_in_place()
    return clip

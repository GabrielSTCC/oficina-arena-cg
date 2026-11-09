"""Clips de animação vertex (Mixamo exportados p/ .npz)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import glm
import numpy as np

from gfx.mesh import Material, Mesh
from gfx.texture import load_texture


@dataclass
class AnimClip:
    pos: np.ndarray  # (F, V, 3)
    nrm: np.ndarray  # (F, V, 3)
    idx: np.ndarray  # (T,)
    uv: np.ndarray | None = None  # (V, 2)
    ranges: list[tuple[int, int]] = field(default_factory=list)  # (first, count) em índices
    materials: list[Material] = field(default_factory=list)
    fps: float = 24.0
    name: str = ""
    _frame_meshes: dict[int, Mesh] = field(default_factory=dict, repr=False)

    @property
    def n_frames(self) -> int:
        return int(self.pos.shape[0])

    @property
    def n_verts(self) -> int:
        return int(self.pos.shape[1])

    def interleaved(self, frame: int) -> np.ndarray:
        f = int(frame) % self.n_frames
        out = np.empty((self.n_verts, 8), dtype=np.float32)
        out[:, 0:3] = self.pos[f]
        out[:, 3:6] = self.nrm[f]
        if self.uv is not None and self.uv.shape[0] == self.n_verts:
            out[:, 6:8] = self.uv
        else:
            out[:, 6:8] = 0.0
        return out.ravel()

    def frame_mesh(self, frame: int = 0) -> Mesh:
        """Retorna VAO/VBO estático em cache na GPU para o frame solicitado."""
        f = int(frame) % self.n_frames
        mesh = self._frame_meshes.get(f)
        if mesh is None:
            mesh = Mesh(self.interleaved(f), self.idx.astype(np.uint32))
            self._frame_meshes[f] = mesh
        return mesh

    def preload_meshes(self) -> None:
        """Pré-carrega todos os frames do clip na GPU uma única vez."""
        idx_u32 = self.idx.astype(np.uint32)
        for f in range(self.n_frames):
            if f not in self._frame_meshes:
                self._frame_meshes[f] = Mesh(self.interleaved(f), idx_u32)

    def make_mesh(self, frame: int = 0) -> Mesh:
        return self.frame_mesh(frame)

    def make_in_place(self) -> None:
        """Centraliza XZ em cada frame (Mixamo root motion); o jogo posiciona o ator."""
        pos = self.pos
        for f in range(self.n_frames):
            pos[f, :, 0] -= float(pos[f, :, 0].mean())
            pos[f, :, 2] -= float(pos[f, :, 2].mean())
            # garante contato com o chão
            pos[f, :, 1] -= float(pos[f, :, 1].min())


def load_anim_clip(path: Path, *, in_place: bool = False) -> AnimClip | None:
    if not path.is_file():
        return None
    data = np.load(path, allow_pickle=True)
    name = ""
    if "action" in data:
        raw = data["action"]
        name = str(raw) if np.ndim(raw) == 0 else str(raw.item() if hasattr(raw, "item") else raw)
    fps = 24.0
    if "fps" in data:
        fps = float(np.asarray(data["fps"]).reshape(-1)[0])

    uv = None
    if "uv" in data:
        uv = np.asarray(data["uv"], dtype=np.float32)

    ranges: list[tuple[int, int]] = []
    materials: list[Material] = []
    tex_dir = path.parent / "textures"
    if "mat_ranges" in data:
        mr = np.asarray(data["mat_ranges"], dtype=np.int32)
        kd = np.asarray(data["mat_kd"], dtype=np.float32) if "mat_kd" in data else None
        tex_names = data["mat_tex"] if "mat_tex" in data else None
        for i in range(mr.shape[0]):
            first, count = int(mr[i, 0]), int(mr[i, 1])
            ranges.append((first, count))
            color = glm.vec3(0.72, 0.74, 0.78)
            if kd is not None and i < kd.shape[0]:
                color = glm.vec3(float(kd[i, 0]), float(kd[i, 1]), float(kd[i, 2]))
            mat = Material(color, glm.vec3(0.22, 0.24, 0.28), shininess=40.0)
            if tex_names is not None and i < len(tex_names):
                tname = str(tex_names[i])
                if tname and tname != "None":
                    tid = load_texture(tex_dir / tname, max_size=1024)
                    if tid is not None:
                        mat.texture_id = tid
                        mat.kd = glm.vec3(1.0, 1.0, 1.0)
            materials.append(mat)
    else:
        ranges = [(0, int(np.asarray(data["idx"]).size))]
        materials = [Material(glm.vec3(0.72, 0.74, 0.78), glm.vec3(0.22, 0.24, 0.28), 40.0)]

    clip = AnimClip(
        pos=np.asarray(data["pos"], dtype=np.float32).copy(),
        nrm=np.asarray(data["nrm"], dtype=np.float32),
        idx=np.asarray(data["idx"], dtype=np.uint32),
        uv=uv,
        ranges=ranges,
        materials=materials,
        fps=fps,
        name=name,
    )
    if in_place:
        clip.make_in_place()
    return clip

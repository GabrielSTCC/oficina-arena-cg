"""Ator 3D da Moeda de 1 Euro para o sorteio de Cara ou Coroa antes da partida."""

from __future__ import annotations

import json
import math
import random
import struct
from pathlib import Path

import glm
import numpy as np

from gfx.mesh import Material, Mesh
from gfx.mesh_loader import EURO_COIN_GLTF
from gfx.primitives import make_box
from gfx.shader import Shader
from gfx.texture import load_texture
from scene.placeable import draw_depth, draw_textured


def _load_euro_coin_mesh(gltf_path: Path, diameter: float = 2.05) -> tuple[Mesh, Material]:
    """Carrega scene.gltf da moeda Euro centralizada no plano XZ (+Y = Cara/Águia, -Y = Coroa/1 Euro)."""
    if not gltf_path.is_file():
        mat = Material(glm.vec3(0.95, 0.82, 0.35), glm.vec3(0.65), 64.0)
        return make_box(diameter, 0.16, diameter), mat

    folder = gltf_path.parent
    doc = json.loads(gltf_path.read_text(encoding="utf-8"))
    blob = (folder / doc["buffers"][0]["uri"]).read_bytes()

    def read_acc(index: int) -> np.ndarray:
        acc = doc["accessors"][index]
        view = doc["bufferViews"][acc["bufferView"]]
        offset = int(view.get("byteOffset", 0)) + int(acc.get("byteOffset", 0))
        count = int(acc["count"])
        ctype = int(acc["componentType"])
        typ = acc["type"]
        ncomp = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[typ]
        fmt = {5121: "B", 5123: "H", 5125: "I", 5126: "f"}[ctype]
        stride = int(view.get("byteStride", 0)) or (struct.calcsize(fmt) * ncomp)
        dtype = np.float32 if fmt == "f" else np.uint32
        out = np.empty((count, ncomp), dtype=dtype)
        for i in range(count):
            out[i] = struct.unpack_from(fmt * ncomp, blob, offset + i * stride)
        return out

    prim = doc["meshes"][0]["primitives"][0]
    attrs = prim["attributes"]
    pos = read_acc(attrs["POSITION"]).astype(np.float32)
    nrm = read_acc(attrs["NORMAL"]).astype(np.float32)
    uv = read_acc(attrs["TEXCOORD_0"]).astype(np.float32)
    # glTF tem origem UV no topo-esquerdo; load_texture faz FLIP_TOP_BOTTOM (origem OpenGL baixo-esquerdo)
    uv[:, 1] = 1.0 - uv[:, 1]
    idx = read_acc(prim["indices"]).astype(np.uint32).reshape(-1)

    mins = pos.min(axis=0)
    maxs = pos.max(axis=0)
    center = (mins + maxs) * 0.5
    span = float(max(maxs[0] - mins[0], maxs[1] - mins[1], 1e-6))
    scale = diameter / span

    cx = (pos[:, 0] - center[0]) * scale
    cy = (pos[:, 1] - center[1]) * scale
    cz = (pos[:, 2] - center[2]) * scale * 1.45

    # Orienta a moeda no plano XZ com a face -Z original (Cara/Águia) apontando para +Y
    # e rotaciona 90° no plano para que a Águia e o número "1 EURO" fiquem em pé para a câmera.
    new_pos = np.stack([cy, -cz, cx], axis=1).astype(np.float32)
    new_nrm = np.stack([nrm[:, 1], -nrm[:, 2], nrm[:, 0]], axis=1).astype(np.float32)
    nl = np.linalg.norm(new_nrm, axis=1, keepdims=True)
    new_nrm = new_nrm / np.maximum(nl, 1e-8)

    verts = np.empty((len(new_pos), 8), dtype=np.float32)
    verts[:, 0:3] = new_pos
    verts[:, 3:6] = new_nrm
    verts[:, 6:8] = uv

    tex_path = folder / doc["images"][0]["uri"]
    tex_id = load_texture(tex_path, max_size=1024)
    mat = Material(
        glm.vec3(1.10, 1.04, 0.92),
        glm.vec3(0.72, 0.65, 0.45),
        64.0,
        texture_id=tex_id,
        emissive=glm.vec3(0.08, 0.07, 0.05),
    )
    return Mesh(verts.ravel(), idx), mat


class CoinActor:
    """Controla a exibição e a física de lançamento da moeda 3D (Cara ou Coroa)."""

    def __init__(self, center_pos: glm.vec3 = glm.vec3(7.5, 1.65, 4.5)) -> None:
        self.mesh, self.material = _load_euro_coin_mesh(EURO_COIN_GLTF, diameter=2.05)
        self.base_pos = glm.vec3(center_pos)
        self.pos = glm.vec3(center_pos)
        self.rot_x_deg = 28.0
        self.rot_y_deg = 0.0
        self.rot_z_deg = 0.0
        self.mode = "idle"  # "idle" | "tossing" | "landed"
        self.timer = 0.0
        self.toss_duration = 1.65
        self.chosen_side = "cara"   # escolha do jogador 1 ("cara" ou "coroa")
        self.result_side = "cara"   # lado sorteado ("cara" ou "coroa")
        self._target_rot_x = 0.0

    @property
    def winner_starter(self) -> str:
        """Retorna quem inicia a partida ('Alfa' se acertou a moeda, senão 'Beta')."""
        return "Alfa" if self.result_side == self.chosen_side else "Beta"

    def reset_for_choice(self) -> None:
        self.mode = "idle"
        self.timer = 0.0
        self.pos = glm.vec3(self.base_pos) + glm.vec3(0.0, 0.40, 0.0)
        self.rot_x_deg = 32.0
        self.rot_y_deg = 0.0
        self.rot_z_deg = 0.0

    def start_toss(self, chosen_side: str, forced_result: str | None = None) -> str:
        """Inicia o lançamento físico 3D da moeda para o alto."""
        self.chosen_side = chosen_side.lower()
        self.result_side = (
            forced_result.lower()
            if forced_result is not None
            else random.choice(("cara", "coroa"))
        )
        self.mode = "tossing"
        self.timer = 0.0
        # 6 voltas completas (2160°); +0° termina com +Y (Cara/Águia) para cima, +180° termina com -Y (Coroa/1 Euro) para cima
        extra = 0.0 if self.result_side == "cara" else 180.0
        # Inclinação de +26° na chegada para a câmera em +Z enxergar a face de frente com nitidez
        self._target_rot_x = 6.0 * 360.0 + extra + 26.0
        return self.result_side

    def update(self, dt: float) -> bool:
        """Atualiza animação da moeda; retorna True no instante em que o lançamento termina."""
        self.timer += dt
        if self.mode == "idle":
            bob = 0.12 * math.sin(self.timer * 2.6)
            self.pos = glm.vec3(self.base_pos) + glm.vec3(0.0, 0.40 + bob, 0.0)
            self.rot_y_deg = (self.timer * 50.0) % 360.0
            self.rot_x_deg = 35.0 + 25.0 * math.sin(self.timer * 1.6)
            self.rot_z_deg = 10.0 * math.cos(self.timer * 1.1)
            return False

        if self.mode == "tossing":
            t = min(1.0, self.timer / max(self.toss_duration, 1e-3))
            arc = 3.0 * 4.0 * t * (1.0 - t)
            ease = 1.0 - pow(1.0 - t, 3.0)
            self.pos = glm.vec3(self.base_pos) + glm.vec3(0.0, 0.25 + arc, 0.0)
            self.rot_x_deg = ease * self._target_rot_x
            self.rot_y_deg = (1.0 - ease) * 360.0
            self.rot_z_deg = math.sin(t * math.pi * 4.0) * 14.0 * (1.0 - t)
            if t >= 1.0:
                self.mode = "landed"
                self.timer = 0.0
                return True
            return False

        # landed: pousada exibindo a face vencedora
        self.pos = glm.vec3(self.base_pos) + glm.vec3(0.0, 0.28 + 0.03 * math.sin(self.timer * 3.0), 0.0)
        return False

    def model_matrix(self) -> glm.mat4:
        m = glm.translate(glm.mat4(1.0), self.pos)
        m = glm.rotate(m, glm.radians(self.rot_y_deg), glm.vec3(0, 1, 0))
        m = glm.rotate(m, glm.radians(self.rot_x_deg), glm.vec3(1, 0, 0))
        m = glm.rotate(m, glm.radians(self.rot_z_deg), glm.vec3(0, 0, 1))
        return m

    def draw(self, shader: Shader) -> None:
        draw_textured(shader, self.mesh, self.model_matrix(), self.material)

    def draw_depth_pass(self, shader: Shader) -> None:
        draw_depth(shader, self.mesh, self.model_matrix())

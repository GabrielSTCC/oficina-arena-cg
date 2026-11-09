"""Carrega Wavefront OBJ (v/vn/vt + f) para Mesh GPU."""

from __future__ import annotations

from pathlib import Path

import glm
import numpy as np

from gfx.mesh import Material, Mesh
from gfx.primitives import make_box
from gfx.texture import load_texture

ROOT = Path(__file__).resolve().parents[1]
GLTF_DIR = ROOT / "assets" / "gltf"
BASE2_GLTF = GLTF_DIR / "Base2" / "scene.gltf"
SCIFI_WALL_GLTF = GLTF_DIR / "sci-fi_wall" / "scene.gltf"
EURO_COIN_GLTF = GLTF_DIR / "Moeda" / "euro" / "scene.gltf"
MINERIOS_DIR = GLTF_DIR / "Minerios"
ORE_GLTFS: dict[str, Path] = {
    "diamante": MINERIOS_DIR / "diamante" / "scene.gltf",
    "ouro": MINERIOS_DIR / "ouro" / "scene.gltf",
    "prata": MINERIOS_DIR / "prata" / "scene.gltf",
}
# OBJ debug opcional (teclas T/5–8); ausente no clone padrão — vira placeholder
ROBOS_DIR = ROOT / "assets" / "robots_obj"
# tipos da arena → chave de malha (rubi/bronze reusam diamante/prata)
ORE_MESH_FOR_TIPO: dict[str, str] = {
    "diamante": "diamante",
    "ouro": "ouro",
    "prata": "prata",
    "rubi": "diamante",
    "bronze": "prata",
}

DOWNLOADED_ROBOTS: dict[str, Path] = {
    "robo1": ROBOS_DIR / "Robo 1" / "78508.obj",
    "robo2": ROBOS_DIR / "Robo 2" / "78364.obj",
    "robo3": ROBOS_DIR / "77938" / "77938.obj",
    "robo4": ROBOS_DIR / "Robo 4" / "78413.obj",
}

MeshPart = tuple[Mesh, Material]


def _parse_mtl(mtl_path: Path, tex_dir: Path) -> dict[str, Material]:
    mats: dict[str, Material] = {}
    cur: str | None = None
    kd = glm.vec3(0.8, 0.8, 0.8)
    ks = glm.vec3(0.2, 0.2, 0.2)
    shin = 32.0
    tex: int | None = None

    def flush() -> None:
        nonlocal cur, kd, ks, shin, tex
        if cur is None:
            return
        m = Material(glm.vec3(kd), glm.vec3(ks), shin)
        m.texture_id = tex
        mats[cur] = m

    if not mtl_path.is_file():
        return mats
    with mtl_path.open(encoding="utf-8", errors="ignore") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line[0] == "#":
                continue
            parts = line.split()
            tag = parts[0]
            if tag == "newmtl" and len(parts) >= 2:
                flush()
                cur = parts[1]
                kd = glm.vec3(0.8, 0.8, 0.8)
                ks = glm.vec3(0.2, 0.2, 0.2)
                shin = 32.0
                tex = None
            elif tag == "Kd" and len(parts) >= 4:
                kd = glm.vec3(float(parts[1]), float(parts[2]), float(parts[3]))
            elif tag == "Ks" and len(parts) >= 4:
                ks = glm.vec3(float(parts[1]), float(parts[2]), float(parts[3]))
            elif tag == "Ns" and len(parts) >= 2:
                shin = max(1.0, float(parts[1]) * 0.1)
            elif tag == "map_Kd" and len(parts) >= 2:
                name = Path(parts[-1].replace("\\", "/")).name
                tid = load_texture(tex_dir / name)
                if tid is not None:
                    tex = tid
                    kd = glm.vec3(1.0, 1.0, 1.0)
    flush()
    return mats


def _faces_to_mesh(
    pos: np.ndarray,
    nrm: np.ndarray | None,
    uv: np.ndarray | None,
    faces: list[list[tuple[int, int, int]]],
) -> Mesh:
    out: list[float] = []
    idx: list[int] = []
    for tri in faces:
        p0 = pos[tri[0][0]]
        p1 = pos[tri[1][0]]
        p2 = pos[tri[2][0]]
        fn = np.cross(p1 - p0, p2 - p0)
        fl = float(np.linalg.norm(fn))
        fn = fn / fl if fl > 1e-8 else np.array([0.0, 1.0, 0.0], dtype=np.float32)
        for vi, ti, ni in tri:
            p = pos[vi]
            n = nrm[ni] if nrm is not None and 0 <= ni < len(nrm) else fn
            t = uv[ti] if uv is not None and 0 <= ti < len(uv) else (0.0, 0.0)
            idx.append(len(out) // 8)
            out.extend(
                [
                    float(p[0]),
                    float(p[1]),
                    float(p[2]),
                    float(n[0]),
                    float(n[1]),
                    float(n[2]),
                    float(t[0]),
                    float(t[1]),
                ]
            )
    return Mesh(np.asarray(out, dtype=np.float32), np.asarray(idx, dtype=np.uint32))


def load_obj_parts(
    path: Path,
    *,
    z_up: bool = True,
    normalize: bool = False,
    target_height: float = 0.95,
    tex_dir: Path | None = None,
) -> list[MeshPart]:
    """OBJ com usemtl → lista (mesh, material); texturas em tex_dir ou ./textures."""
    if not path.is_file():
        return [(make_box(0.7, 0.7, 0.7), Material(glm.vec3(0.7)))]

    positions: list[list[float]] = []
    normals: list[list[float]] = []
    uvs: list[list[float]] = []
    groups: dict[str, list[list[tuple[int, int, int]]]] = {"default": []}
    cur = "default"
    mtl_file: Path | None = None

    with path.open(encoding="utf-8", errors="ignore") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line[0] == "#":
                continue
            parts = line.split()
            tag = parts[0]
            if tag == "mtllib" and len(parts) >= 2:
                mtl_file = path.parent / parts[1]
            elif tag == "usemtl" and len(parts) >= 2:
                cur = parts[1]
                groups.setdefault(cur, [])
            elif tag == "v" and len(parts) >= 4:
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                positions.append([x, z, -y] if z_up else [x, y, z])
            elif tag == "vn" and len(parts) >= 4:
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                normals.append([x, z, -y] if z_up else [x, y, z])
            elif tag == "vt" and len(parts) >= 2:
                uvs.append([float(parts[1]), float(parts[2]) if len(parts) > 2 else 0.0])
            elif tag == "f" and len(parts) >= 4:
                verts: list[tuple[int, int, int]] = []
                for token in parts[1:]:
                    bits = token.split("/")
                    vi = int(bits[0])
                    vi = vi - 1 if vi > 0 else len(positions) + vi
                    ti = -1
                    ni = -1
                    if len(bits) > 1 and bits[1]:
                        ti = int(bits[1])
                        ti = ti - 1 if ti > 0 else len(uvs) + ti
                    if len(bits) > 2 and bits[2]:
                        ni = int(bits[2])
                        ni = ni - 1 if ni > 0 else len(normals) + ni
                    verts.append((vi, ti, ni))
                for i in range(1, len(verts) - 1):
                    groups[cur].append([verts[0], verts[i], verts[i + 1]])

    if not positions or not any(groups.values()):
        return [(make_box(0.7, 0.7, 0.7), Material(glm.vec3(0.7)))]

    pos = np.asarray(positions, dtype=np.float32)
    if normalize:
        mins = pos.min(axis=0)
        maxs = pos.max(axis=0)
        center = (mins + maxs) * 0.5
        height = float(maxs[1] - mins[1])
        span = float((maxs - mins).max())
        scale = target_height / height if height > 1e-6 else target_height / max(span, 1e-6)
        pos[:, 0] = (pos[:, 0] - center[0]) * scale
        pos[:, 2] = (pos[:, 2] - center[2]) * scale
        pos[:, 1] = (pos[:, 1] - mins[1]) * scale

    nrm = np.asarray(normals, dtype=np.float32) if normals else None
    uv = np.asarray(uvs, dtype=np.float32) if uvs else None
    tdir = tex_dir or (path.parent / "textures")
    if mtl_file is None or not mtl_file.is_file():
        # OBJ antigo aponta p/ scene1.mtl; cai no .mtl irmão do .obj
        cand = path.with_suffix(".mtl")
        if cand.is_file():
            mtl_file = cand
        else:
            found = list(path.parent.glob("*.mtl"))
            mtl_file = found[0] if found else None
    mats = _parse_mtl(mtl_file, tdir) if mtl_file else {}

    result: list[MeshPart] = []
    for name, faces in groups.items():
        if not faces:
            continue
        mat = mats.get(name, Material(glm.vec3(0.75, 0.75, 0.78), shininess=40.0))
        result.append((_faces_to_mesh(pos, nrm, uv, faces), mat))
    return result


def load_obj(
    path: Path,
    *,
    z_up: bool = True,
    normalize: bool = False,
    target_height: float = 0.95,
) -> Mesh:
    parts = load_obj_parts(path, z_up=z_up, normalize=normalize, target_height=target_height)
    return parts[0][0]


def load_catalog_mesh(models_dir: Path, name: str, fallback_size=(0.8, 0.8, 0.8)) -> Mesh:
    path = models_dir / f"{name}.obj"
    if path.is_file():
        return load_obj(path, z_up=True, normalize=False)
    sx, sy, sz = fallback_size
    return make_box(sx, sy, sz)


def load_downloaded_robot(key: str, target_height: float = 0.95) -> Mesh:
    path = DOWNLOADED_ROBOTS.get(key)
    if path is None or not path.is_file():
        return make_box(0.5, 0.75, 0.5)
    return load_obj(path, z_up=True, normalize=True, target_height=target_height)


def load_downloaded_robot_parts(key: str, target_height: float = 0.95) -> list[MeshPart]:
    path = DOWNLOADED_ROBOTS.get(key)
    if path is None or not path.is_file():
        return [(make_box(0.5, 0.75, 0.5), Material(glm.vec3(0.7)))]
    return load_obj_parts(path, z_up=True, normalize=True, target_height=target_height)

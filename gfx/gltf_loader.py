"""Loader mínimo glTF 2.0 (meshes estáticas + baseColor) p/ warehouse."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import glm
import numpy as np

from gfx.mesh import Material, Mesh
from gfx.texture import load_texture

GltfPart = tuple[Mesh, Material, str]


def _read_accessor(doc: dict, blob: bytes, index: int) -> np.ndarray:
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
        o = offset + i * stride
        out[i] = struct.unpack_from(fmt * ncomp, blob, o)
    return out


def _node_local(n: dict) -> glm.mat4:
    if "matrix" in n:
        return glm.mat4(*n["matrix"])
    t = glm.translate(glm.mat4(1), glm.vec3(*(n.get("translation", [0, 0, 0]))))
    r = glm.mat4(1)
    if "rotation" in n:
        qx, qy, qz, qw = n["rotation"]
        r = glm.mat4_cast(glm.quat(qw, qx, qy, qz))
    s = n.get("scale", [1, 1, 1])
    return t * r * glm.scale(glm.mat4(1), glm.vec3(*s))


def _world_mats(doc: dict) -> dict[int, glm.mat4]:
    nodes = doc["nodes"]
    local = {i: _node_local(n) for i, n in enumerate(nodes)}
    children = {i: list(n.get("children", [])) for i, n in enumerate(nodes)}
    world: dict[int, glm.mat4] = {}

    def walk(i: int, parent: glm.mat4) -> None:
        w = parent * local[i]
        world[i] = w
        for c in children[i]:
            walk(c, w)

    for r in doc["scenes"][doc.get("scene", 0)]["nodes"]:
        walk(r, glm.mat4(1))
    return world


def _np_mat4(M: glm.mat4) -> np.ndarray:
    return np.column_stack(
        [
            [M[c].x, M[c].y, M[c].z, M[c].w]
            for c in range(4)
        ]
    ).astype(np.float32)


def _material(doc: dict, folder: Path, index: int | None) -> Material:
    kd = glm.vec3(0.7, 0.7, 0.7)
    tex_id = None
    emissive = glm.vec3(0.0)
    if index is None:
        return Material(kd)
    mat = doc["materials"][index]
    pbr = mat.get("pbrMetallicRoughness", {})
    if "baseColorFactor" in pbr:
        c = pbr["baseColorFactor"]
        kd = glm.vec3(c[0], c[1], c[2])
    if "baseColorTexture" in pbr:
        tex = doc["textures"][pbr["baseColorTexture"]["index"]]
        img = doc["images"][tex["source"]]
        tex_id = load_texture(folder / img["uri"])
        kd = glm.vec3(1.0, 1.0, 1.0)
    em = mat.get("emissiveFactor")
    if em and sum(em) > 0.01:
        strength = 1.0
        ext = mat.get("extensions", {}).get("KHR_materials_emissive_strength", {})
        if "emissiveStrength" in ext:
            strength = float(ext["emissiveStrength"])
        emissive = glm.vec3(em[0], em[1], em[2]) * strength
    m = Material(kd, shininess=24.0, emissive=emissive)
    m.texture_id = tex_id
    return m


def load_gltf_parts(
    path: Path,
    *,
    fit_xz: float | None = None,
    fit_y: float | None = None,
) -> tuple[list[GltfPart], glm.vec3, glm.vec3]:
    folder = path.parent
    doc = json.loads(path.read_text(encoding="utf-8"))
    blob = (folder / doc["buffers"][0]["uri"]).read_bytes()
    worlds = _world_mats(doc)
    staged: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, Material, str]] = []
    mins = np.array([1e9, 1e9, 1e9], dtype=np.float32)
    maxs = np.array([-1e9, -1e9, -1e9], dtype=np.float32)

    for ni, node in enumerate(doc["nodes"]):
        if "mesh" not in node:
            continue
        mesh_def = doc["meshes"][node["mesh"]]
        Mm = _np_mat4(worlds[ni])
        N3 = Mm[:3, :3]
        for prim in mesh_def["primitives"]:
            attrs = prim["attributes"]
            pos = _read_accessor(doc, blob, attrs["POSITION"]).astype(np.float32)
            nrm = (
                _read_accessor(doc, blob, attrs["NORMAL"]).astype(np.float32)
                if "NORMAL" in attrs
                else np.tile(np.array([[0.0, 1.0, 0.0]], np.float32), (len(pos), 1))
            )
            uv = (
                _read_accessor(doc, blob, attrs["TEXCOORD_0"]).astype(np.float32)
                if "TEXCOORD_0" in attrs
                else np.zeros((len(pos), 2), np.float32)
            )
            idx = _read_accessor(doc, blob, prim["indices"]).astype(np.uint32).reshape(-1)

            hp = np.concatenate([pos, np.ones((len(pos), 1), np.float32)], axis=1)
            wp = (Mm @ hp.T).T[:, :3]
            wn = (N3 @ nrm.T).T
            lens = np.linalg.norm(wn, axis=1, keepdims=True)
            wn = wn / np.maximum(lens, 1e-8)

            mins = np.minimum(mins, wp.min(axis=0))
            maxs = np.maximum(maxs, wp.max(axis=0))
            mat = _material(doc, folder, prim.get("material"))
            staged.append((wp, wn, uv, idx, mat, mesh_def.get("name", "part")))

    if fit_xz is not None and staged:
        span = float(max(maxs[0] - mins[0], maxs[2] - mins[2], 1e-6))
        scale = fit_xz / span
        center = (mins + maxs) * 0.5
        y0 = float(mins[1])
        mins = np.array([1e9, 1e9, 1e9], dtype=np.float32)
        maxs = np.array([-1e9, -1e9, -1e9], dtype=np.float32)
        scaled: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, Material, str]] = []
        for wp, wn, uv, idx, mat, name in staged:
            wp = wp.copy()
            wp[:, 0] = (wp[:, 0] - center[0]) * scale
            wp[:, 2] = (wp[:, 2] - center[2]) * scale
            wp[:, 1] = (wp[:, 1] - y0) * scale
            mins = np.minimum(mins, wp.min(axis=0))
            maxs = np.maximum(maxs, wp.max(axis=0))
            scaled.append((wp, wn, uv, idx, mat, name))
        staged = scaled

    if fit_y is not None and staged:
        h = float(maxs[1] - mins[1])
        if h > 1e-6:
            sy = fit_y / h
            mins = np.array([1e9, 1e9, 1e9], dtype=np.float32)
            maxs = np.array([-1e9, -1e9, -1e9], dtype=np.float32)
            tall: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, Material, str]] = []
            for wp, wn, uv, idx, mat, name in staged:
                wp = wp.copy()
                wp[:, 1] *= sy
                mins = np.minimum(mins, wp.min(axis=0))
                maxs = np.maximum(maxs, wp.max(axis=0))
                tall.append((wp, wn, uv, idx, mat, name))
            staged = tall

    parts: list[GltfPart] = []
    for wp, wn, uv, idx, mat, name in staged:
        verts = np.empty((len(wp), 8), dtype=np.float32)
        verts[:, 0:3] = wp
        verts[:, 3:6] = wn
        verts[:, 6:8] = uv
        parts.append((Mesh(verts.ravel(), idx), mat, name))

    return parts, glm.vec3(*mins.tolist()), glm.vec3(*maxs.tolist())

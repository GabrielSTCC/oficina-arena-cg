"""
Exporta clips Mixamo (Andar_pra_frente + Stop_Walking) p/ OpenGL.

Gera assets/models/robo3_clips/walk.npz e idle.npz
(posições/normais por frame, UVs+indices compartilhados, altura ~1.8).

Uso:
  blender -b assets/blender/robot3_mixamo_anims.blend --python assets/blender/mixamo/export_opengl_clips.py
"""

from __future__ import annotations

import os
import sys

import bpy
import numpy as np
from mathutils import Vector

BLEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.abspath(os.path.join(BLEND_DIR, "..", "models", "robo3_clips"))

CLIPS = {
    "walk": ("Andar_pra_frente", 5),  # step frames
    "idle": ("Stop_Walking", 20),
}

TARGET_HEIGHT = 1.8


def _armature():
    for o in bpy.data.objects:
        if o.type == "ARMATURE":
            return o
    return None


def _mesh_obj():
    for o in bpy.data.objects:
        if o.type == "MESH":
            return o
    return None


def _set_action(arm, name: str) -> bpy.types.Action | None:
    act = bpy.data.actions.get(name)
    if act is None:
        return None
    if arm.animation_data is None:
        arm.animation_data_create()
    arm.animation_data.action = act
    return act


def _sample_frame(obj, depsgraph) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Retorna pos (V,3), nrm (V,3), idx (T,) — malha indexada (sem UV)."""
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()
    mesh.calc_loop_triangles()
    mw = eval_obj.matrix_world
    n3 = mw.to_3x3()

    n_v = len(mesh.vertices)
    local = np.empty(n_v * 3, np.float32)
    mesh.vertices.foreach_get("co", local)
    local = local.reshape(n_v, 3)
    # aplica matrix_world
    ones = np.ones((n_v, 1), np.float32)
    hp = np.concatenate([local, ones], axis=1)
    Mm = np.array(mw, dtype=np.float32).reshape(4, 4)
    # mathutils Matrix is row-major when converted to np.array
    positions = (hp @ Mm.T)[:, :3].astype(np.float32)

    ln = np.empty(n_v * 3, np.float32)
    mesh.vertices.foreach_get("normal", ln)
    ln = ln.reshape(n_v, 3)
    N = np.array(n3, dtype=np.float32).reshape(3, 3)
    normals = (ln @ N.T).astype(np.float32)
    lens = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = normals / np.maximum(lens, 1e-8)

    n_t = len(mesh.loop_triangles)
    indices = np.empty(n_t * 3, np.int32)
    mesh.loop_triangles.foreach_get("vertices", indices)
    indices = indices.astype(np.uint32)

    eval_obj.to_mesh_clear()
    return positions, normals, indices


def _normalize(pos: np.ndarray, nrm: np.ndarray, ref: dict | None) -> tuple[np.ndarray, np.ndarray, dict]:
    """Y-up: Blender já é Z-up → troca p/ Y-up; escala p/ TARGET_HEIGHT."""
    # Blender Z-up → OpenGL Y-up: (x,y,z) -> (x,z,-y)
    p = np.empty_like(pos)
    p[:, 0] = pos[:, 0]
    p[:, 1] = pos[:, 2]
    p[:, 2] = -pos[:, 1]
    n = np.empty_like(nrm)
    n[:, 0] = nrm[:, 0]
    n[:, 1] = nrm[:, 2]
    n[:, 2] = -nrm[:, 1]

    if ref is None:
        mins = p.min(axis=0)
        maxs = p.max(axis=0)
        center = (mins + maxs) * 0.5
        height = float(maxs[1] - mins[1])
        scale = TARGET_HEIGHT / height if height > 1e-6 else 1.0
        ref = {"center": center, "mins_y": float(mins[1]), "scale": scale}

    c = ref["center"]
    s = ref["scale"]
    my = ref["mins_y"]
    p2 = np.empty_like(p)
    p2[:, 0] = (p[:, 0] - c[0]) * s
    p2[:, 2] = (p[:, 2] - c[2]) * s
    p2[:, 1] = (p[:, 1] - my) * s
    return p2, n, ref


def export_clip(name: str, action_name: str, step: int) -> None:
    arm = _armature()
    obj = _mesh_obj()
    if arm is None or obj is None:
        raise RuntimeError("Armature/mesh não encontrados")
    act = _set_action(arm, action_name)
    if act is None:
        print(f"SKIP {name}: action {action_name} ausente")
        return

    scene = bpy.context.scene
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    frames = list(range(f0, f1 + 1, max(1, step)))
    if frames[-1] != f1:
        frames.append(f1)

    pos_frames = []
    nrm_frames = []
    idx0 = None
    ref = None
    depsgraph = bpy.context.evaluated_depsgraph_get()

    for i, f in enumerate(frames):
        scene.frame_set(f)
        depsgraph.update()
        pos, nrm, idx = _sample_frame(obj, depsgraph)
        pos, nrm, ref = _normalize(pos, nrm, ref)
        pos_frames.append(pos)
        nrm_frames.append(nrm)
        if i == 0:
            idx0 = idx
        print(f"  {name} frame {f} ({i+1}/{len(frames)}) verts={len(pos)}")

    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f"{name}.npz")
    np.savez_compressed(
        out,
        pos=np.stack(pos_frames, axis=0),
        nrm=np.stack(nrm_frames, axis=0),
        idx=idx0,
        frames=np.asarray(frames, np.int32),
        action=np.asarray(action_name),
    )
    mb = (pos_frames[0].nbytes * len(pos_frames) * 2) / (1024 * 1024)
    print(f"WROTE {out} V={pos_frames[0].shape[0]} F={len(frames)} ~{mb:.1f}MB raw")


def main() -> None:
    for name, (action, step) in CLIPS.items():
        print(f"=== {name} / {action} step={step}")
        export_clip(name, action, step)
    print("DONE", OUT_DIR)


if __name__ == "__main__":
    main()

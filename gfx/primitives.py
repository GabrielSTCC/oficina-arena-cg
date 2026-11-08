"""Primitivas low-poly (caixa) usadas como placeholder e para o galpão."""

from __future__ import annotations

import numpy as np

from gfx.mesh import Mesh


def make_box(sx: float, sy: float, sz: float, *, uv_scale: float = 1.0) -> Mesh:
    """Caixa centrada em XZ, base em y=0, topo em y=sy."""
    hx, hz = sx * 0.5, sz * 0.5
    # UV proporcional ao tamanho da face (tile em paredes longas)
    u_x, u_z, u_y = sx * uv_scale, sz * uv_scale, sy * uv_scale
    faces = [
        # +Y
        ([(-hx, sy, -hz), (hx, sy, -hz), (hx, sy, hz), (-hx, sy, hz)], (0, 1, 0), [(0, 0), (u_x, 0), (u_x, u_z), (0, u_z)]),
        # -Y
        ([(-hx, 0, hz), (hx, 0, hz), (hx, 0, -hz), (-hx, 0, -hz)], (0, -1, 0), [(0, 0), (u_x, 0), (u_x, u_z), (0, u_z)]),
        # +Z
        ([(-hx, 0, hz), (-hx, sy, hz), (hx, sy, hz), (hx, 0, hz)], (0, 0, 1), [(0, 0), (0, u_y), (u_x, u_y), (u_x, 0)]),
        # -Z
        ([(hx, 0, -hz), (hx, sy, -hz), (-hx, sy, -hz), (-hx, 0, -hz)], (0, 0, -1), [(0, 0), (0, u_y), (u_x, u_y), (u_x, 0)]),
        # +X
        ([(hx, 0, hz), (hx, sy, hz), (hx, sy, -hz), (hx, 0, -hz)], (1, 0, 0), [(0, 0), (0, u_y), (u_z, u_y), (u_z, 0)]),
        # -X
        ([(-hx, 0, -hz), (-hx, sy, -hz), (-hx, sy, hz), (-hx, 0, hz)], (-1, 0, 0), [(0, 0), (0, u_y), (u_z, u_y), (u_z, 0)]),
    ]
    verts: list[float] = []
    inds: list[int] = []
    for corners, n, uvs in faces:
        base = len(verts) // 8
        for (x, y, z), (u, v) in zip(corners, uvs):
            verts.extend([x, y, z, *n, u, v])
        inds.extend([base, base + 1, base + 2, base, base + 2, base + 3])
    return Mesh(np.asarray(verts, np.float32), np.asarray(inds, np.uint32))


def make_floor(
    width: float,
    depth: float,
    y: float = 0.0,
    *,
    uv_repeat: tuple[float, float] = (1.0, 1.0),
) -> Mesh:
    hw, hd = width * 0.5, depth * 0.5
    ru, rv = uv_repeat
    verts = np.asarray(
        [
            -hw, y, -hd, 0, 1, 0, 0, 0,
            hw, y, -hd, 0, 1, 0, ru, 0,
            hw, y, hd, 0, 1, 0, ru, rv,
            -hw, y, hd, 0, 1, 0, 0, rv,
        ],
        np.float32,
    )
    inds = np.asarray([0, 1, 2, 0, 2, 3], np.uint32)
    return Mesh(verts, inds)

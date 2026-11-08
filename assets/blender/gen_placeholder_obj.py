"""Gera OBJs placeholder sem Blender (fallback)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "models"


def write_box(path: Path, sx: float, sy: float, sz: float) -> None:
    """Caixa com base em y=0, centro xz, normals e UVs (OpenGL Y-up)."""
    hx, hz = sx / 2, sz / 2
    # 8 corners
    v = [
        (-hx, 0, -hz),
        (hx, 0, -hz),
        (hx, 0, hz),
        (-hx, 0, hz),
        (-hx, sy, -hz),
        (hx, sy, -hz),
        (hx, sy, hz),
        (-hx, sy, hz),
    ]
    # faces: (verts idx 1-based, normal)
    faces = [
        ([5, 6, 7, 8], (0, 1, 0)),
        ([1, 4, 3, 2], (0, -1, 0)),
        ([4, 8, 7, 3], (0, 0, 1)),
        ([2, 6, 5, 1], (0, 0, -1)),
        ([2, 3, 7, 6], (1, 0, 0)),
        ([1, 5, 8, 4], (-1, 0, 0)),
    ]
    lines = ["# placeholder oficina-arena", "mtllib none"]
    for x, y, z in v:
        lines.append(f"v {x:.4f} {y:.4f} {z:.4f}")
    lines += ["vt 0 0", "vt 1 0", "vt 1 1", "vt 0 1"]
    for i, (_, n) in enumerate(faces):
        lines.append(f"vn {n[0]} {n[1]} {n[2]}")
    for fi, (idxs, _) in enumerate(faces):
        ni = fi + 1
        # triangulate
        a, b, c, d = idxs
        lines.append(f"f {a}/1/{ni} {b}/2/{ni} {c}/3/{ni}")
        lines.append(f"f {a}/1/{ni} {c}/3/{ni} {d}/4/{ni}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


SIZES = {
    "bancada": (0.9, 0.55, 0.55),
    "cadeira": (0.45, 0.7, 0.45),
    "luminaria": (0.25, 1.2, 0.25),
    "abajur": (0.3, 0.6, 0.3),
    "planta": (0.35, 0.7, 0.35),
    "minerio": (0.4, 0.35, 0.4),
    "estante": (0.95, 1.4, 0.35),
    "base": (0.85, 0.25, 0.85),
    "robo": (0.5, 0.75, 0.5),
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, size in SIZES.items():
        write_box(OUT / f"{name}.obj", *size)
        print("wrote", name)


if __name__ == "__main__":
    main()

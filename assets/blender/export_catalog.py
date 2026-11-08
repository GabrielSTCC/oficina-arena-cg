"""Gera malhas low-poly do catálogo e exporta OBJ (rodar no Blender).

blender --background --python assets/blender/export_catalog.py
"""

from __future__ import annotations

from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "models"
BLEND_OUT = ROOT / "assets" / "blender" / "catalog.blend"
OUT.mkdir(parents=True, exist_ok=True)


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.meshes:
        bpy.data.meshes.remove(block)


def export_obj(obj: bpy.types.Object, name: str) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    path = OUT / f"{name}.obj"
    bpy.ops.wm.obj_export(
        filepath=str(path),
        export_selected_objects=True,
        export_normals=True,
        export_uv=True,
        export_materials=False,
        forward_axis="NEGATIVE_Y",
        up_axis="Z",
    )


def box(name: str, size, loc=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    # base em z=0: sobe metade da altura
    h = size[2]
    obj.location.z = h * 0.5
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    return obj


def build_all() -> None:
    clear_scene()
    # Blender Z-up aqui; export mapeia para OpenGL Y-up via -Y forward / Z up
    specs = {
        "bancada": ((0.9, 0.5, 0.55),),
        "cadeira": ((0.4, 0.4, 0.7),),
        "luminaria": ((0.2, 0.2, 1.2),),
        "abajur": ((0.28, 0.28, 0.55),),
        "planta": ((0.3, 0.3, 0.65),),
        "minerio": ((0.35, 0.35, 0.3),),
        "estante": ((0.9, 0.3, 1.3),),
        "base": ((0.8, 0.8, 0.2),),
        "robo": ((0.45, 0.45, 0.7),),
    }
    created = []
    for name, (scale,) in specs.items():
        # size tuple is (x, y, z) in Blender
        obj = box(name, scale)
        created.append((obj, name))

    for obj, name in created:
        export_obj(obj, name)

    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_OUT))
    print(f"Exported {len(created)} OBJs to {OUT}")


if __name__ == "__main__":
    build_all()

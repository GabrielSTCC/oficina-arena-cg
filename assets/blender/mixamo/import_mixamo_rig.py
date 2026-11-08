"""Importa FBX do Mixamo (With Skin) e salva robot3_mixamo.blend.

Uso:
  1. Baixe do Mixamo como robo3_mixamo_rigged.fbx nesta pasta
  2. blender --python import_mixamo_rig.py
"""

from __future__ import annotations

from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
FBX = HERE / "robo3_mixamo_rigged.fbx"
OUT = HERE.parent / "robot3_mixamo.blend"


def main() -> None:
    if not FBX.is_file():
        raise SystemExit(
            f"Arquivo não encontrado: {FBX}\n"
            "Baixe do Mixamo (FBX With Skin) com esse nome nesta pasta."
        )

    # Cena limpa
    bpy.ops.wm.read_factory_settings(use_empty=True)

    bpy.ops.import_scene.fbx(
        filepath=str(FBX),
        automatic_bone_orientation=True,
        use_anim=True,
    )

    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    print("armatures", [a.name for a in arms])
    print("meshes", [m.name for m in meshes])
    for m in meshes:
        print(
            " ",
            m.name,
            "parent=",
            m.parent.name if m.parent else None,
            "groups=",
            len(m.vertex_groups),
            "mods=",
            [mod.type for mod in m.modifiers],
        )

    bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
    print("SAVED", OUT)


if __name__ == "__main__":
    main()

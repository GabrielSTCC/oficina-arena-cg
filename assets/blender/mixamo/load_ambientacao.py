"""
Importa a ambientação warehouse (glTF) na cena do Robo 3 e inicia o WASD.
"""

from __future__ import annotations

import os
import sys

import bpy
from mathutils import Vector

GLTF = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "..",
        "..",
        "modelos3D",
        "Ambientação",
        "warehouse",
        "scene.gltf",
    )
)
_FALLBACK = (
    "/home/gabriel/Documents/Faculdade/Computação Grafica/"
    "modelos3D/Ambientação/warehouse/scene.gltf"
)

ROOT_NAME = "Ambientacao_Warehouse"


def _gltf_path() -> str:
    if os.path.isfile(GLTF):
        return GLTF
    return _FALLBACK


def _tex_dir() -> str:
    return os.path.join(os.path.dirname(_gltf_path()), "textures")


def _scene_bounds(objects) -> tuple[Vector, Vector] | None:
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    found = False
    for o in objects:
        if o.type != "MESH":
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            mins.x = min(mins.x, w.x)
            mins.y = min(mins.y, w.y)
            mins.z = min(mins.z, w.z)
            maxs.x = max(maxs.x, w.x)
            maxs.y = max(maxs.y, w.y)
            maxs.z = max(maxs.z, w.z)
            found = True
    return (mins, maxs) if found else None


def import_warehouse() -> bpy.types.Object:
    root = bpy.data.objects.get(ROOT_NAME)
    if root is not None:
        return root

    path = _gltf_path()
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Ambientação não encontrada: {path}")

    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    imported = [o for o in bpy.data.objects if o not in before]

    root = bpy.data.objects.new(ROOT_NAME, None)
    bpy.context.collection.objects.link(root)
    for o in imported:
        if o.parent is None:
            o.parent = root

    plane = bpy.data.objects.get("Terreno_Plano")
    if plane is not None:
        bpy.data.objects.remove(plane, do_unlink=True)

    return root


_ROBOT_TEX = (
    "/home/gabriel/Documents/Faculdade/Computação Grafica/"
    "modelos3D/Robos/Robo 3/textures"
)


def _resolve_disk(img: bpy.types.Image, search_dirs: list[str]) -> str | None:
    candidates = [
        os.path.basename(img.filepath or ""),
        img.name,
        img.name.split(".")[0] + os.path.splitext(img.name)[-1],
    ]
    # blinn10SG_baseColor.jpeg.003 -> blinn10SG_baseColor.jpeg
    base = img.name
    while base and base[-1].isdigit():
        # strip .001 style via rsplit
        break
    stem = img.name
    if ".jpeg." in stem or ".jpg." in stem or ".png." in stem:
        stem = stem.rsplit(".", 1)[0]  # remove .001
        candidates.insert(0, stem)

    for folder in search_dirs:
        for name in candidates:
            if not name:
                continue
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                return path
            # tenta .jpg/.jpeg/.png
            root, _ = os.path.splitext(name)
            for ext in (".jpeg", ".jpg", ".png"):
                path = os.path.join(folder, root + ext)
                if os.path.isfile(path):
                    return path
    return None


def _fix_textures() -> None:
    """Recarrega texturas do warehouse + robô (paths quebrados no .blend)."""
    search = [_tex_dir(), _ROBOT_TEX]
    fixed = 0
    for img in bpy.data.images:
        disk = _resolve_disk(img, search)
        if disk is None:
            continue
        try:
            if img.packed_file:
                img.unpack(method="REMOVE")
        except Exception:
            pass
        img.source = "FILE"
        img.filepath = disk
        img.reload()
        if img.size[0] > 0:
            fixed += 1
    print(f"texturas recarregadas: {fixed}/{len(bpy.data.images)}")

    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        base_img = None
        for node in mat.node_tree.nodes:
            if node.type != "TEX_IMAGE" or node.image is None:
                continue
            nlow = (node.image.name or "").lower()
            if "basecolor" in nlow or "albedo" in nlow or "diffuse" in nlow:
                base_img = node.image
                break
            if base_img is None:
                base_img = node.image
        if base_img is None or base_img.size[0] <= 0:
            low = mat.name.lower()
            if "metal" in low:
                mat.diffuse_color = (0.45, 0.45, 0.48, 1.0)
            elif "emissive" in low:
                mat.diffuse_color = (0.95, 0.9, 0.55, 1.0)
            continue
        w, h = int(base_img.size[0]), int(base_img.size[1])
        if w <= 0 or h <= 0:
            continue
        px = base_img.pixels
        i = (h // 2 * w + w // 2) * 4
        if i + 3 < len(px):
            mat.diffuse_color = (px[i], px[i + 1], px[i + 2], 1.0)


def place_robot_in_warehouse(arm: bpy.types.Object, root: bpy.types.Object) -> None:
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    env = [o for o in meshes if not (o.parent and o.parent.type == "ARMATURE")]
    bounds = _scene_bounds(env)
    if bounds is None:
        return
    mins, maxs = bounds
    center = (mins + maxs) * 0.5
    floor_z = mins.z

    arm.location.x = center.x
    arm.location.y = center.y
    min_z = None
    for c in arm.children:
        if c.type != "MESH":
            continue
        for corner in c.bound_box:
            z = (c.matrix_world @ Vector(corner)).z
            min_z = z if min_z is None else min(min_z, z)
    if min_z is not None:
        arm.location.z += floor_z - min_z
    else:
        arm.location.z = floor_z


def _setup_viewport(context) -> None:
    """Material Preview = texturas reais; leve o bastante p/ o warehouse."""
    for area in context.screen.areas:
        if area.type != "VIEW_3D":
            continue
        for space in area.spaces:
            if space.type != "VIEW_3D":
                continue
            space.shading.type = "SOLID"
            space.shading.light = "STUDIO"
            space.shading.color_type = "TEXTURE"
            space.overlay.show_floor = False
            space.overlay.show_ortho_grid = False
            space.overlay.show_bones = False
            space.overlay.show_axis_x = False
            space.overlay.show_axis_y = False
            space.overlay.show_axis_z = False
            space.overlay.show_cursor = False
            space.overlay.show_relationship_lines = False
        break


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)

    import wasd_control as wasd

    root = import_warehouse()
    arm = wasd._find_armature()
    if arm is None:
        raise RuntimeError("Armature do robô não encontrada")

    place_robot_in_warehouse(arm, root)
    _fix_textures()
    _setup_viewport(bpy.context)

    arm.show_in_front = False
    arm.data.display_type = "STICK"
    for bone in arm.data.bones:
        bone.hide = True

    # seleciona armature (painel N + ops precisam de active ARMATURE)
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm

    import robot_control_panel as panel

    try:
        panel.unregister()
    except Exception:
        pass
    panel.register()

    wasd.register()
    bpy.context.scene["oficina_has_ambientacao"] = True
    bpy.ops.mixamo.wasd_drive("INVOKE_DEFAULT")


if __name__ == "__main__":
    main()

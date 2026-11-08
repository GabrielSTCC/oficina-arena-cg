"""
Gera uma Armature bípede mecânica ("Robot_Rig") e vincula à Mesh selecionada.

=============================================================================
COMO USAR
=============================================================================
1. Abra o .blend do robô no Blender.
2. Se o robô tiver vários objetos Mesh, junte-os antes (Ctrl+J) ou selecione
   a malha principal já unificada.
3. Selecione a Mesh do robô (Object Mode).
4. Scripting → Text Editor → Open → este arquivo → Run Script.
5. A Armature "Robot_Rig" fica na base (pés) da malha, com "In Front" ligado.
6. Parent = Empty Groups (ARMATURE_NAME) + Assign rígido automático:
   cada vértice recebe peso 1.0 no osso mais próximo (sem borracha).

=============================================================================
AJUSTE MANUAL (opcional, para refinar uma peça)
=============================================================================
1. Mesh → Edit Mode → selecione os vértices da peça.
2. Vertex Groups → escolha o osso (ex. LowerArm.L) → Weight 1.0 → Assign.
3. Remova esses vértices dos outros grupos se precisar (Remove).
4. Pose Mode na armature para testar.

=============================================================================
"""

from __future__ import annotations

import bpy
from mathutils import Vector, Matrix


RIG_NAME = "Robot_Rig"
AUTO_RIGID_WEIGHTS = True  # peso 1.0 no osso mais próximo (mecânico)


def _world_bbox(obj: bpy.types.Object) -> tuple[Vector, Vector, Vector]:
    """Retorna (min, max, center) do bound_box em world space."""
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs = [c.x for c in corners]
    ys = [c.y for c in corners]
    zs = [c.z for c in corners]
    mn = Vector((min(xs), min(ys), min(zs)))
    mx = Vector((max(xs), max(ys), max(zs)))
    return mn, mx, (mn + mx) * 0.5


def _remove_existing_rig() -> None:
    """Remove armature anterior com o mesmo nome (script idempotente)."""
    existing = bpy.data.objects.get(RIG_NAME)
    if existing is None:
        return
    for obj in list(bpy.data.objects):
        if obj.parent == existing:
            mw = obj.matrix_world.copy()
            obj.parent = None
            obj.matrix_world = mw
            for mod in list(obj.modifiers):
                if mod.type == "ARMATURE" and mod.object == existing:
                    obj.modifiers.remove(mod)
    arm_data = existing.data
    bpy.data.objects.remove(existing, do_unlink=True)
    if arm_data is not None and arm_data.users == 0:
        bpy.data.armatures.remove(arm_data)


def _add_bone(
    edit_bones,
    name: str,
    head: Vector,
    tail: Vector,
    parent=None,
    connect: bool = False,
):
    bone = edit_bones.new(name)
    bone.head = head
    bone.tail = tail
    if parent is not None:
        bone.parent = parent
        bone.use_connect = connect
    return bone


def _dist_point_to_segment(p: Vector, a: Vector, b: Vector) -> float:
    ab = b - a
    den = ab.length_squared
    if den < 1e-12:
        return (p - a).length
    t = max(0.0, min(1.0, (p - a).dot(ab) / den))
    return (p - (a + ab * t)).length


def _assign_nearest_bone_rigid(mesh_obj: bpy.types.Object, arm_obj: bpy.types.Object) -> None:
    """Cada vértice → peso 1.0 no osso mais próximo (movimento rígido, sem blend)."""
    # limpa pesos antigos
    for vg in mesh_obj.vertex_groups:
        mesh_obj.vertex_groups.remove(vg)
    for bone in arm_obj.data.bones:
        mesh_obj.vertex_groups.new(name=bone.name)

    # segmentos dos ossos em world space
    segments: list[tuple[str, Vector, Vector]] = []
    for bone in arm_obj.data.bones:
        head_w = arm_obj.matrix_world @ bone.head_local
        tail_w = arm_obj.matrix_world @ bone.tail_local
        segments.append((bone.name, head_w, tail_w))

    groups = {g.name: g for g in mesh_obj.vertex_groups}
    mw = mesh_obj.matrix_world
    for vi, vert in enumerate(mesh_obj.data.vertices):
        pw = mw @ vert.co
        best_name = segments[0][0]
        best_d = 1e30
        for name, a, b in segments:
            d = _dist_point_to_segment(pw, a, b)
            if d < best_d:
                best_d = d
                best_name = name
        groups[best_name].add([vi], 1.0, "REPLACE")


def _stand_mesh_upright(mesh_obj: bpy.types.Object) -> None:
    """Bakes matrix_world into verts, puts longest axis on +Z, feet on Z=0."""
    mw = mesh_obj.matrix_world.copy()
    for v in mesh_obj.data.vertices:
        v.co = mw @ v.co
    mesh_obj.data.update()
    mesh_obj.matrix_world = Matrix.Identity(4)

    xs = [v.co.x for v in mesh_obj.data.vertices]
    ys = [v.co.y for v in mesh_obj.data.vertices]
    zs = [v.co.z for v in mesh_obj.data.vertices]
    sx, sy, sz = max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)

    # Longest → +Z (corrige robô “caído” no chão)
    if sy >= sx and sy >= sz:
        for v in mesh_obj.data.vertices:
            x, y, z = v.co
            v.co = Vector((x, -z, y))
    elif sx >= sy and sx >= sz:
        for v in mesh_obj.data.vertices:
            x, y, z = v.co
            v.co = Vector((z, y, -x))
    mesh_obj.data.update()

    xs = [v.co.x for v in mesh_obj.data.vertices]
    ys = [v.co.y for v in mesh_obj.data.vertices]
    zs = [v.co.z for v in mesh_obj.data.vertices]
    off = Vector(((min(xs) + max(xs)) * 0.5, (min(ys) + max(ys)) * 0.5, min(zs)))
    for v in mesh_obj.data.vertices:
        v.co -= off
    mesh_obj.data.update()
    bpy.context.view_layer.update()


def create_robot_rig() -> bpy.types.Object:
    # --- 1) Validação -------------------------------------------------------
    mesh_obj = bpy.context.view_layer.objects.active
    if mesh_obj is None or mesh_obj.type != "MESH":
        raise RuntimeError(
            "Selecione um objeto Mesh (o robô) antes de rodar o script. "
            "Object Mode → clique na malha → Run Script."
        )

    # Endireita malha (eixo longo = +Z, pés no chão) antes do bbox
    _stand_mesh_upright(mesh_obj)

    # --- 2) Bbox / proporções -----------------------------------------------
    mn, mx, _center = _world_bbox(mesh_obj)
    size = mx - mn
    height = max(float(size.z), 1e-4)
    width = max(float(size.x), height * 0.2)
    depth = max(float(size.y), height * 0.15)

    h = height
    # ombros/quadril proporcionais à largura real
    shoulder_x = width * 0.32
    hip_x = width * 0.14

    # Origem da armature = centro dos pés (chão), não o centro do volume
    foot_center = Vector(( (mn.x + mx.x) * 0.5, (mn.y + mx.y) * 0.5, mn.z ))

    # --- 3) Armature na base ------------------------------------------------
    _remove_existing_rig()

    arm_data = bpy.data.armatures.new(RIG_NAME)
    arm_obj = bpy.data.objects.new(RIG_NAME, arm_data)
    bpy.context.collection.objects.link(arm_obj)
    arm_obj.matrix_world = Matrix.Translation(foot_center)
    arm_obj.show_in_front = True
    arm_data.display_type = "OCTAHEDRAL"

    # --- 4) Edit Mode — hierarquia (local Z = altura a partir dos pés) ------
    bpy.ops.object.select_all(action="DESELECT")
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones
    for b in list(eb):
        eb.remove(b)

    # Alturas relativas (bípede mais natural)
    z_foot = 0.0
    z_ankle = 0.04 * h
    z_knee = 0.28 * h
    z_hip = 0.52 * h
    z_chest = 0.78 * h
    z_neck = 0.88 * h
    z_head = 1.00 * h
    y_off = depth * 0.02  # leve offset frontal

    root = _add_bone(
        eb, "Root",
        Vector((0.0, y_off, z_hip - 0.04 * h)),
        Vector((0.0, y_off, z_hip)),
    )
    spine = _add_bone(
        eb, "Spine",
        root.tail.copy(),
        Vector((0.0, y_off, z_chest)),
        parent=root, connect=True,
    )
    # Cabeça ligada na ponta da Spine (sem “osso flutuante”)
    _add_bone(
        eb, "Head",
        spine.tail.copy(),
        Vector((0.0, y_off, z_head)),
        parent=spine, connect=True,
    )

    # Ombros saem da Spine e conectam os braços (cadeia contínua)
    sh_l = _add_bone(
        eb, "Shoulder.L",
        spine.tail.copy(),
        Vector((shoulder_x, y_off, z_chest)),
        parent=spine, connect=False,
    )
    ual = _add_bone(
        eb, "UpperArm.L",
        sh_l.tail.copy(),
        Vector((shoulder_x + 0.18 * h, y_off, z_chest - 0.02 * h)),
        parent=sh_l, connect=True,
    )
    _add_bone(
        eb, "LowerArm.L",
        ual.tail.copy(),
        ual.tail + Vector((0.16 * h, 0.0, -0.03 * h)),
        parent=ual, connect=True,
    )
    sh_r = _add_bone(
        eb, "Shoulder.R",
        spine.tail.copy(),
        Vector((-shoulder_x, y_off, z_chest)),
        parent=spine, connect=False,
    )
    uar = _add_bone(
        eb, "UpperArm.R",
        sh_r.tail.copy(),
        Vector((-shoulder_x - 0.18 * h, y_off, z_chest - 0.02 * h)),
        parent=sh_r, connect=True,
    )
    _add_bone(
        eb, "LowerArm.R",
        uar.tail.copy(),
        uar.tail + Vector((-0.16 * h, 0.0, -0.03 * h)),
        parent=uar, connect=True,
    )

    # Pernas: coxa ligada ao Root (offset), joelho conectado
    thl = _add_bone(
        eb, "Thigh.L",
        Vector((hip_x, y_off, z_hip)),
        Vector((hip_x, y_off, z_knee)),
        parent=root, connect=False,
    )
    _add_bone(
        eb, "Calf.L",
        thl.tail.copy(),
        Vector((hip_x, y_off, z_ankle)),
        parent=thl, connect=True,
    )
    thr = _add_bone(
        eb, "Thigh.R",
        Vector((-hip_x, y_off, z_hip)),
        Vector((-hip_x, y_off, z_knee)),
        parent=root, connect=False,
    )
    _add_bone(
        eb, "Calf.R",
        thr.tail.copy(),
        Vector((-hip_x, y_off, z_ankle)),
        parent=thr, connect=True,
    )

    bpy.ops.object.mode_set(mode="OBJECT")

    # --- 5) Parent mecânico SEM tombear a malha -----------------------------
    # parent_set(ARMATURE_NAME) às vezes aplica uma matrix_local rotacionada
    # e o robô “cai” de novo. Parentamos à mão preservando matrix_world.
    mw_mesh = mesh_obj.matrix_world.copy()
    mesh_obj.parent = arm_obj
    mesh_obj.matrix_parent_inverse = arm_obj.matrix_world.inverted()
    mesh_obj.matrix_world = mw_mesh  # restaura pose em pé

    # Modifier Armature (deformação por Vertex Groups)
    for mod in list(mesh_obj.modifiers):
        if mod.type == "ARMATURE":
            mesh_obj.modifiers.remove(mod)
    arm_mod = mesh_obj.modifiers.new(name="Armature", type="ARMATURE")
    arm_mod.object = arm_obj
    arm_mod.use_vertex_groups = True

    for bone in arm_obj.data.bones:
        if bone.name not in mesh_obj.vertex_groups:
            mesh_obj.vertex_groups.new(name=bone.name)

    if AUTO_RIGID_WEIGHTS:
        print("[create_robot_rig] Assign rígido por osso mais próximo…")
        _assign_nearest_bone_rigid(mesh_obj, arm_obj)

    bpy.ops.object.select_all(action="DESELECT")
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    # Entra em Pose Mode já com um braço levantado — prova visual da ligação
    bpy.ops.object.mode_set(mode="POSE")
    if "UpperArm.L" in arm_obj.pose.bones:
        b = arm_obj.pose.bones["UpperArm.L"]
        b.rotation_mode = "XYZ"
        b.rotation_euler[1] = 0.9  # levanta o braço L
    bpy.context.view_layer.update()

    _mn, _mx, _ = _world_bbox(mesh_obj)
    print(
        f"[create_robot_rig] OK — '{RIG_NAME}' ligado à malha "
        f"(parent+modifier+pesos). world_size="
        f"({(_mx-_mn).x:.1f},{(_mx-_mn).y:.1f},{(_mx-_mn).z:.1f}). "
        f"Pose Mode: selecione um osso → R para girar a armadura."
    )
    return arm_obj


if __name__ == "__main__":
    create_robot_rig()

"""
Painel N-Panel "Controle Robô" — move a Armature relativa à câmera da viewport.

Uso: Text Editor → Open este arquivo → Run Script
Viewport → N → aba "Controle Robô"
"""

from __future__ import annotations

import bpy
from mathutils import Vector

STEP = 0.5  # unidades por clique


def _active_armature(context) -> bpy.types.Object | None:
    obj = context.active_object
    if obj is not None and obj.type == "ARMATURE":
        return obj
    return None


def _armature_poll(context) -> bool:
    return _active_armature(context) is not None


def _view_rv3d(context):
    for area in context.screen.areas:
        if area.type != "VIEW_3D":
            continue
        for space in area.spaces:
            if space.type == "VIEW_3D":
                return space.region_3d
    return None


def _flat(v: Vector) -> Vector:
    out = Vector((v.x, v.y, 0.0))
    if out.length > 1e-8:
        out.normalize()
    return out


def _camera_basis(rv3d) -> tuple[Vector, Vector]:
    q = rv3d.view_rotation
    forward = _flat(q @ Vector((0.0, 0.0, -1.0)))
    right = _flat(q @ Vector((1.0, 0.0, 0.0)))
    if forward.length < 1e-8:
        forward = Vector((0.0, 1.0, 0.0))
    if right.length < 1e-8:
        right = Vector((1.0, 0.0, 0.0))
    return forward, right


def _move_camera_relative(context, fwd: float, strafe: float) -> None:
    arm = _active_armature(context)
    if arm is None:
        return
    rv3d = _view_rv3d(context)
    if rv3d is None:
        return
    cam_f, cam_r = _camera_basis(rv3d)
    move = cam_f * fwd + cam_r * strafe
    move.z = 0.0
    if move.length < 1e-8:
        return
    move.normalize()
    arm.location += move * STEP


class ROBO_OT_move_forward(bpy.types.Operator):
    bl_idname = "robo.move_forward"
    bl_label = "Frente"
    bl_description = "Move na frente da câmera da viewport"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return _armature_poll(context)

    def execute(self, context):
        _move_camera_relative(context, 1.0, 0.0)
        return {"FINISHED"}


class ROBO_OT_move_back(bpy.types.Operator):
    bl_idname = "robo.move_back"
    bl_label = "Trás"
    bl_description = "Move para trás relativo à câmera"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return _armature_poll(context)

    def execute(self, context):
        _move_camera_relative(context, -1.0, 0.0)
        return {"FINISHED"}


class ROBO_OT_move_left(bpy.types.Operator):
    bl_idname = "robo.move_left"
    bl_label = "Esquerda"
    bl_description = "Move para a esquerda da câmera"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return _armature_poll(context)

    def execute(self, context):
        _move_camera_relative(context, 0.0, -1.0)
        return {"FINISHED"}


class ROBO_OT_move_right(bpy.types.Operator):
    bl_idname = "robo.move_right"
    bl_label = "Direita"
    bl_description = "Move para a direita da câmera"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return _armature_poll(context)

    def execute(self, context):
        _move_camera_relative(context, 0.0, 1.0)
        return {"FINISHED"}


class ROBO_PT_controle(bpy.types.Panel):
    bl_label = "Movimento"
    bl_idname = "ROBO_PT_controle"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Controle Robô"

    @classmethod
    def poll(cls, context):
        return _armature_poll(context)

    def draw(self, context):
        layout = self.layout
        arm = _active_armature(context)

        layout.label(text=arm.name if arm else "—")

        col = layout.column(align=True)
        col.scale_y = 1.2
        col.operator("robo.move_forward", text="Frente", icon="TRIA_UP")

        row = col.row(align=True)
        row.operator("robo.move_left", text="Esquerda", icon="TRIA_LEFT")
        row.operator("robo.move_right", text="Direita", icon="TRIA_RIGHT")

        col.operator("robo.move_back", text="Trás", icon="TRIA_DOWN")

        layout.separator()
        layout.label(text=f"Passo: {STEP} u (câmera)", icon="INFO")


classes = (
    ROBO_OT_move_forward,
    ROBO_OT_move_back,
    ROBO_OT_move_left,
    ROBO_OT_move_right,
    ROBO_PT_controle,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    try:
        unregister()
    except Exception:
        pass
    register()
    print("Controle Robô: painel registrado (N → Controle Robô)")

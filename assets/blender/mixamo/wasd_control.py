"""
Controle WASD relativo à câmera da viewport + giro antes de andar.

W/S — frente/trás da câmera (chão XY)
A/D — esquerda/direita da câmera
Se o rumo mudar bastante: anima giro (Right_Turn) e só então anda.
Shift — correr | Esc — sair
"""

from __future__ import annotations

import math
import time

import bpy
from mathutils import Matrix, Vector

ANIM = {
    "walk_f": "Andar_pra_frente",
    "walk_b": "Running_Backward",
    "run_f": "Run_Forward",
    "run_b": "Running_Backward",
    "stop": "Stop_Walking",
    "turn": "Right_Turn",
    "turn_run": "Running_To_Turn",
}

WALK_SPEED = 8.0
RUN_SPEED = 16.0
WALK_ANIM_FPS = 36.0
RUN_ANIM_FPS = 48.0
TURN_ANIM_FPS = 36.0
TURN_SPEED = 4.0  # rad/s enquanto gira
TURN_THRESHOLD = math.radians(35.0)
TURN_DONE = math.radians(5.0)
_INPLACE_DONE: set[str] = set()


def _find_armature() -> bpy.types.Object | None:
    for obj in bpy.context.scene.objects:
        if obj.type == "ARMATURE":
            return obj
    return None


def _iter_fcurves(action: bpy.types.Action):
    if getattr(action, "is_action_legacy", False) and hasattr(action, "fcurves"):
        yield from action.fcurves
        return
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                yield from bag.fcurves


def _make_action_in_place(action: bpy.types.Action) -> None:
    if action.name in _INPLACE_DONE:
        return
    for fc in list(_iter_fcurves(action)):
        path = fc.data_path or ""
        if "Hips" not in path or ".location" not in path:
            continue
        if fc.array_index not in (0, 1):
            continue
        if not fc.keyframe_points:
            continue
        v = fc.keyframe_points[0].co[1]
        for kp in fc.keyframe_points:
            kp.co[1] = v
            kp.handle_left[1] = v
            kp.handle_right[1] = v
        fc.update()
    _INPLACE_DONE.add(action.name)


def _set_action(arm: bpy.types.Object, name: str) -> None:
    action = bpy.data.actions.get(name)
    if action is None:
        return
    _make_action_in_place(action)
    if arm.animation_data is None:
        arm.animation_data_create()
    if arm.animation_data.action != action:
        arm.animation_data.action = action
        scene = bpy.context.scene
        scene.frame_start = int(action.frame_range[0])
        scene.frame_end = int(action.frame_range[1])
        scene.frame_current = int(action.frame_range[0])


def _hips_world(arm: bpy.types.Object) -> Vector:
    loc = arm.matrix_world.to_translation().copy()
    loc.z += 1.0
    return loc


def _ensure_flat_ground(context) -> bpy.types.Object:
    name = "Terreno_Plano"
    ground = bpy.data.objects.get(name)
    if ground is None:
        bpy.ops.mesh.primitive_plane_add(size=40.0, location=(0.0, 0.0, 0.0))
        ground = context.view_layer.objects.active
        ground.name = name
        if ground.data:
            ground.data.name = name

    ground.location = (0.0, 0.0, 0.0)
    ground.rotation_euler = (0.0, 0.0, 0.0)
    ground.scale = (1.0, 1.0, 1.0)
    ground.hide_render = False
    ground.hide_viewport = False

    mat = bpy.data.materials.get("Terreno_Mat")
    if mat is None:
        mat = bpy.data.materials.new("Terreno_Mat")
    mat.diffuse_color = (0.28, 0.30, 0.32, 1.0)
    if ground.data.materials:
        ground.data.materials[0] = mat
    else:
        ground.data.materials.append(mat)

    for area in context.screen.areas:
        if area.type != "VIEW_3D":
            continue
        for space in area.spaces:
            if space.type != "VIEW_3D":
                continue
            space.shading.type = "SOLID"
            space.shading.light = "STUDIO"
            space.shading.color_type = "MATERIAL"
            space.overlay.show_floor = False
            space.overlay.show_ortho_grid = False
            space.overlay.show_axis_x = False
            space.overlay.show_axis_y = False
            space.overlay.show_axis_z = False
            space.overlay.show_relationship_lines = False
            space.overlay.show_bones = False
            space.overlay.show_cursor = False
        break

    return ground


def _place_robot_on_ground(arm: bpy.types.Object) -> None:
    min_z = None
    for c in arm.children:
        if c.type != "MESH":
            continue
        for corner in c.bound_box:
            z = (c.matrix_world @ Vector(corner)).z
            min_z = z if min_z is None else min(min_z, z)
    if min_z is not None:
        arm.location.z -= min_z


def _focus_camera_on_robot(context, arm: bpy.types.Object) -> None:
    center = _hips_world(arm)
    height = 2.0
    for c in arm.children:
        if c.type == "MESH":
            zs = [(c.matrix_world @ Vector(corner)).z for corner in c.bound_box]
            height = max(zs) - min(zs)
            break

    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    for c in arm.children:
        c.select_set(True)
    context.view_layer.objects.active = arm
    context.scene.cursor.location = center

    for area in context.screen.areas:
        if area.type != "VIEW_3D":
            continue
        for space in area.spaces:
            if space.type != "VIEW_3D":
                continue
            space.lock_object = None
            space.region_3d.view_location = center.copy()
            space.region_3d.view_distance = max(height * 2.5, 3.0)
            space.region_3d.view_perspective = "PERSP"
        break


def _robot_forward(arm: bpy.types.Object) -> Vector:
    """Frente visual Mixamo (X=+90°: +Z local no chão)."""
    direction = arm.matrix_world.to_quaternion() @ Vector((0.0, 0.0, 1.0))
    direction.z = 0.0
    if direction.length > 1e-8:
        direction.normalize()
    return direction


def _robot_right(arm: bpy.types.Object) -> Vector:
    direction = arm.matrix_world.to_quaternion() @ Vector((-1.0, 0.0, 0.0))
    direction.z = 0.0
    if direction.length > 1e-8:
        direction.normalize()
    return direction


def _flat(v: Vector) -> Vector:
    out = Vector((v.x, v.y, 0.0))
    if out.length > 1e-8:
        out.normalize()
    return out


def _camera_basis(rv3d) -> tuple[Vector, Vector]:
    """Frente e direita da viewport no plano XY."""
    q = rv3d.view_rotation
    forward = _flat(q @ Vector((0.0, 0.0, -1.0)))
    right = _flat(q @ Vector((1.0, 0.0, 0.0)))
    if forward.length < 1e-8:
        forward = Vector((0.0, 1.0, 0.0))
    if right.length < 1e-8:
        right = Vector((1.0, 0.0, 0.0))
    return forward, right


def _camera_move_vector(rv3d, fwd_axis: float, str_axis: float) -> Vector | None:
    if fwd_axis == 0.0 and str_axis == 0.0:
        return None
    if rv3d is None:
        return None
    cam_f, cam_r = _camera_basis(rv3d)
    move = cam_f * fwd_axis + cam_r * str_axis
    move.z = 0.0
    length = move.length
    if length < 1e-8:
        return None
    if length > 1.0:
        move /= length
    return move


def _signed_yaw(from_dir: Vector, to_dir: Vector) -> float:
    """Ângulo assinado no plano XY (rad): positivo = anti-horário."""
    a = _flat(from_dir)
    b = _flat(to_dir)
    if a.length < 1e-8 or b.length < 1e-8:
        return 0.0
    return math.atan2(a.x * b.y - a.y * b.x, a.x * b.x + a.y * b.y)


def _yaw_armature(arm: bpy.types.Object, angle: float) -> None:
    pivot = arm.matrix_world.to_translation().copy()
    R = Matrix.Rotation(angle, 4, "Z")
    T = Matrix.Translation(pivot)
    arm.matrix_world = T @ R @ T.inverted() @ arm.matrix_world


def _advance_anim(scene, arm, anim_frame: float, dt: float, fps: float) -> float:
    action = arm.animation_data.action if arm.animation_data else None
    if action is None:
        return anim_frame
    f0 = float(action.frame_range[0])
    f1 = float(action.frame_range[1])
    length = max(f1 - f0, 1.0)
    anim_frame += dt * fps
    while anim_frame > f1:
        anim_frame -= length
    fi = int(anim_frame)
    scene.frame_set(fi, subframe=anim_frame - fi)
    return anim_frame


class MIXAMO_OT_wasd(bpy.types.Operator):
    bl_idname = "mixamo.wasd_drive"
    bl_label = "Mixamo WASD Drive"
    bl_options = {"REGISTER"}

    _timer = None
    _keys: set[str]
    _shift: bool
    _last_anim: str
    _arm_name: str
    _rv3d = None
    _mode: str
    _desired: Vector | None

    def invoke(self, context, event):
        arm = _find_armature()
        if arm is None:
            self.report({"ERROR"}, "Nenhuma Armature na cena.")
            return {"CANCELLED"}

        self._keys = set()
        self._shift = False
        self._last_anim = ""
        self._arm_name = arm.name
        self._rv3d = None
        self._mode = "idle"
        self._desired = None

        bpy.ops.object.mode_set(mode="OBJECT")
        arm.show_in_front = False
        arm.data.display_type = "STICK"
        for bone in arm.data.bones:
            bone.hide = True

        has_env = bool(context.scene.get("oficina_has_ambientacao")) or (
            bpy.data.objects.get("Ambientacao_Warehouse") is not None
        )
        if not has_env:
            _ensure_flat_ground(context)
            _place_robot_on_ground(arm)
        else:
            for area in context.screen.areas:
                if area.type != "VIEW_3D":
                    continue
                for space in area.spaces:
                    if space.type != "VIEW_3D":
                        continue
                    space.shading.type = "SOLID"
                    space.shading.light = "STUDIO"
                    space.shading.color_type = "TEXTURE"
                    space.overlay.show_bones = False
                    space.overlay.show_floor = False
                break

        for aname in ANIM.values():
            act = bpy.data.actions.get(aname)
            if act:
                _make_action_in_place(act)

        self._anim_frame = 0.0
        self._last_time = time.perf_counter()
        _set_action(arm, ANIM["stop"])
        self._last_anim = ANIM["stop"]
        _focus_camera_on_robot(context, arm)

        for area in context.screen.areas:
            if area.type != "VIEW_3D":
                continue
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    self._rv3d = space.region_3d
                    break
            break

        wm = context.window_manager
        self._timer = wm.event_timer_add(1 / 120, window=context.window)
        wm.modal_handler_add(self)
        msg = (
            "Warehouse — WASD câmera+giro, Shift corre, Esc sai"
            if has_env
            else "Terreno — WASD câmera+giro, Shift corre, Esc sai"
        )
        self.report({"INFO"}, msg)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        arm = bpy.data.objects.get(self._arm_name)
        if arm is None:
            return self._finish(context, cancelled=True)

        if event.type in {"W", "A", "S", "D"}:
            if event.value in {"PRESS", "REPEAT"}:
                self._keys.add(event.type)
            elif event.value == "RELEASE":
                self._keys.discard(event.type)
            return {"RUNNING_MODAL"}

        if event.type in {"LEFT_SHIFT", "RIGHT_SHIFT"}:
            self._shift = event.value != "RELEASE"
            return {"RUNNING_MODAL"}

        if event.type == "ESC" and event.value == "PRESS":
            return self._finish(context)

        if event.type == "TIMER":
            self._tick(context, arm)
            return {"RUNNING_MODAL"}

        return {"PASS_THROUGH"}

    def _play(self, arm: bpy.types.Object, anim: str) -> None:
        if anim != self._last_anim and bpy.data.actions.get(anim):
            _set_action(arm, anim)
            self._last_anim = anim
            self._anim_frame = float(int(bpy.data.actions[anim].frame_range[0]))

    def _tick(self, context, arm: bpy.types.Object) -> None:
        now = time.perf_counter()
        dt = now - self._last_time
        self._last_time = now
        if dt <= 0.0 or dt > 0.1:
            dt = 1 / 60

        scene = context.scene
        running = self._shift
        fwd_axis = float(("W" in self._keys) - ("S" in self._keys))
        str_axis = float(("D" in self._keys) - ("A" in self._keys))
        desired = _camera_move_vector(self._rv3d, fwd_axis, str_axis)
        if desired is None:
            # fallback se não houver view: eixos do robô
            if fwd_axis != 0.0 or str_axis != 0.0:
                desired = _robot_forward(arm) * fwd_axis + _robot_right(arm) * str_axis
                if desired.length > 1e-8:
                    desired.normalize()
                else:
                    desired = None

        if desired is None:
            self._mode = "idle"
            self._desired = None
            self._play(arm, ANIM["stop"])
            self._anim_frame = _advance_anim(
                scene, arm, self._anim_frame, dt, WALK_ANIM_FPS
            )
            self._follow_cam(dt, arm)
            return

        self._desired = desired.copy()
        facing = _robot_forward(arm)
        yaw_delta = _signed_yaw(facing, desired)

        # decide estado
        if self._mode == "idle":
            if abs(yaw_delta) >= TURN_THRESHOLD:
                self._mode = "turning"
            else:
                self._mode = "moving"
        elif self._mode == "moving":
            if abs(yaw_delta) >= TURN_THRESHOLD:
                self._mode = "turning"
        # turning continua até alinhar

        if self._mode == "turning":
            turn_anim = ANIM["turn_run"] if running else ANIM["turn"]
            if not bpy.data.actions.get(turn_anim):
                turn_anim = ANIM["turn"]
            self._play(arm, turn_anim)
            self._anim_frame = _advance_anim(
                scene, arm, self._anim_frame, dt, TURN_ANIM_FPS
            )

            step = max(-TURN_SPEED * dt, min(TURN_SPEED * dt, yaw_delta))
            _yaw_armature(arm, step)

            facing = _robot_forward(arm)
            yaw_delta = _signed_yaw(facing, desired)
            if abs(yaw_delta) < TURN_DONE:
                self._mode = "moving"
            self._follow_cam(dt, arm)
            return

        # moving: translada na direção da câmera; anim frente/trás vs facing
        along = facing.dot(desired)
        if along >= 0.0:
            anim = ANIM["run_f"] if running else ANIM["walk_f"]
        else:
            anim = ANIM["run_b"] if running else ANIM["walk_b"]
        self._play(arm, anim)
        self._anim_frame = _advance_anim(
            scene,
            arm,
            self._anim_frame,
            dt,
            RUN_ANIM_FPS if running else WALK_ANIM_FPS,
        )

        speed = RUN_SPEED if running else WALK_SPEED
        arm.location += desired * (speed * dt)
        self._follow_cam(dt, arm)

    def _follow_cam(self, dt: float, arm: bpy.types.Object) -> None:
        if self._rv3d is None:
            return
        target = _hips_world(arm)
        cur = self._rv3d.view_location
        self._rv3d.view_location = cur.lerp(target, min(1.0, dt * 10.0))

    def _finish(self, context, cancelled: bool = False):
        wm = context.window_manager
        if self._timer:
            wm.event_timer_remove(self._timer)
            self._timer = None
        self.report({"INFO"}, "WASD desligado")
        return {"CANCELLED"} if cancelled else {"FINISHED"}


classes = (MIXAMO_OT_wasd,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
    bpy.ops.mixamo.wasd_drive("INVOKE_DEFAULT")

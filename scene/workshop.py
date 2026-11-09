"""Galpão fechado + grade de objetos posicionados."""

from __future__ import annotations

import math
import random
import time
from pathlib import Path

import glm
import numpy as np

from gfx.gltf_loader import load_gltf_parts
from gfx.mesh import (
    MAT_ABAJUR,
    MAT_ARMADILHA,
    MAT_BASE,
    MAT_BASE_ALFA,
    MAT_BASE_BETA,
    MAT_BRONZE,
    MAT_CHAO,
    MAT_CONCRETO,
    MAT_DIAMANTE,
    MAT_FOSCO,
    MAT_HAZARD,
    MAT_JANELA,
    MAT_LUMINARIA,
    MAT_MADEIRA,
    MAT_METAL,
    MAT_METAL_ESC,
    MAT_MINERIO,
    MAT_OURO,
    MAT_PAINEL,
    MAT_PAREDE,
    MAT_PRATA,
    MAT_RUBI,
    Material,
    Mesh,
)
from gfx.mesh_loader import (
    BASE2_GLTF,
    DOWNLOADED_ROBOTS,
    ORE_GLTFS,
    ORE_MESH_FOR_TIPO,
    SCIFI_WALL_GLTF,
    load_catalog_mesh,
    load_downloaded_robot,
    load_downloaded_robot_parts,
)
from gfx.primitives import make_box, make_decal_quad
from gfx.shader import Shader
from gfx.texture import (
    load_texture,
    make_data_texture_rgba,
    update_data_texture_rgba,
)
from scene.catalog import CATALOG, CatalogItem, CellKind, cell_to_world
from scene.environment import HangarEnvironment
from scene.placeable import Ghost, Placeable, draw_depth, draw_hologram, draw_textured


GRID_W = 15
GRID_H = 9
WALL_H = 3.0
HOLO_HEIGHT = 1.2
_HOLO_THICK = 0.24
_MAT_EMITTER = Material(
    glm.vec3(0.22, 0.25, 0.30),
    glm.vec3(0.38, 0.42, 0.48),
    56.0,
    triplanar_scale=0.8,
)
_MAT_EMITTER_GLOW = Material(
    glm.vec3(0.2, 0.85, 1.0),
    glm.vec3(0.3, 0.35, 0.4),
    48.0,
    emissive=glm.vec3(0.35, 1.35, 1.85),
)
_MAT_DECAL_ALFA = Material(
    glm.vec3(0.20, 0.88, 1.0),
    glm.vec3(0.05),
    8.0,
    emissive=glm.vec3(0.35, 1.45, 1.95),
    alpha_tex=True,
)
_MAT_DECAL_BETA = Material(
    glm.vec3(1.0, 0.38, 0.14),
    glm.vec3(0.05),
    8.0,
    emissive=glm.vec3(1.85, 0.52, 0.16),
    alpha_tex=True,
)
_MAT_DECAL_ORE = Material(
    glm.vec3(1.0, 1.0, 1.0),
    glm.vec3(0.05),
    8.0,
    emissive=glm.vec3(1.0, 0.8, 0.3),
    alpha_tex=True,
)
_ORTHO = ((1, 0), (-1, 0), (0, 1), (0, -1))


class Workshop:
    def __init__(self, models_dir: Path) -> None:
        self.models_dir = models_dir
        self.meshes: dict[str, Mesh] = {}
        self.catalog_parts: dict[str, list[tuple[Mesh, Material]]] = {}
        self.robot_parts: dict[str, list[tuple[Mesh, Material]]] = {}
        for item in CATALOG:
            sizes = {
                "bancada": (0.9, 0.55, 0.55),
                "cadeira": (0.45, 0.7, 0.45),
                "luminaria": (0.25, 1.2, 0.25),
                "abajur": (0.3, 0.6, 0.3),
                "planta": (0.35, 0.7, 0.35),
                "minerio": (0.4, 0.35, 0.4),
                "estante": (0.95, 1.4, 0.35),
                "armadilha": (0.78, 0.08, 0.78),
                "base": (0.85, 0.25, 0.85),
            }
            if item.id == "base" and BASE2_GLTF.is_file():
                parts, _, _ = load_gltf_parts(BASE2_GLTF, fit_xz=1.2, fit_y=0.32)
                mesh, mat, _ = parts[0]
                self.meshes[item.id] = mesh
                if mat.texture_id is not None:
                    for bmat in (MAT_BASE, MAT_BASE_ALFA, MAT_BASE_BETA):
                        bmat.texture_id = mat.texture_id
                MAT_BASE.emissive = glm.vec3(0.25, 0.85, 1.15)
                MAT_BASE.ks = glm.vec3(0.45, 0.5, 0.55)
                MAT_BASE.shininess = 64.0
            elif item.id == "estante" and SCIFI_WALL_GLTF.is_file():
                parts, _, _ = load_gltf_parts(SCIFI_WALL_GLTF, fit_xz=1.06, fit_y=1.4)
                wall_parts: list[tuple[Mesh, Material]] = []
                for m, mat, _ in parts:
                    if mat.shininess < 48.0:
                        mat.shininess = 48.0
                    if float(glm.length(mat.ks)) < 0.25:
                        mat.ks = glm.vec3(0.3, 0.3, 0.32)
                    wall_parts.append((m, mat))
                self.catalog_parts["estante"] = wall_parts
                self.meshes[item.id] = parts[0][0]
            elif item.id == "armadilha":
                # Placa baixa com UV 0..1 na face superior (sem repetição quebrada)
                self.meshes[item.id] = make_box(0.82, 0.07, 0.82, uv_scale=1.0 / 0.82)
            elif item.id == "minerio":
                self.meshes[item.id] = load_catalog_mesh(
                    models_dir, item.id, sizes.get(item.id, (0.4, 0.35, 0.4))
                )
            else:
                self.meshes[item.id] = load_catalog_mesh(
                    models_dir, item.id, sizes.get(item.id, (0.7, 0.7, 0.7))
                )
        self.ore_materials = {
            "diamante": MAT_DIAMANTE,
            "ouro": MAT_OURO,
            "prata": MAT_PRATA,
            "rubi": MAT_RUBI,
            "bronze": MAT_BRONZE,
        }
        self._load_ore_meshes()

        focus = "robo3"
        clips_dir = Path(__file__).resolve().parents[1] / "assets" / "models" / "robo3_clips"
        has_clips = (clips_dir / "walk.npz").is_file()
        for key in DOWNLOADED_ROBOTS:
            if has_clips:
                self.meshes[key] = make_box(0.5, 1.8, 0.5)
                self.robot_parts[key] = []
            elif key == focus:
                parts = load_downloaded_robot_parts(key, target_height=1.8)
                self.robot_parts[key] = parts
                self.meshes[key] = parts[0][0]
            else:
                self.meshes[key] = load_downloaded_robot(key, target_height=1.8)
                self.robot_parts[key] = []
        self.meshes["robo"] = self.meshes.get(focus) or next(iter(self.meshes.values()))

        self._bind_env_textures(models_dir.parent / "textures")

        # Hangar fechado (substitui o piso/muro isolado); cache por tamanho da arena
        self.grid_w = GRID_W
        self.grid_h = GRID_H
        self._hangars: dict[tuple[int, int], HangarEnvironment] = {}
        self.hangar = HangarEnvironment(self.grid_w, self.grid_h)
        self._hangars[(self.grid_w, self.grid_h)] = self.hangar

        # Geometria unitária para paredes holográficas conectadas e trilhos emissores
        self.holo_unit = make_box(1.0, HOLO_HEIGHT, 1.0, y0=0.05)
        self.rail_unit = make_box(1.0, 0.08, 1.0, y0=0.0)
        self.rail_glow = make_box(1.0, 0.02, 1.0, y0=0.08)
        self.pillar_base = make_box(0.42, 0.11, 0.42, y0=0.0)
        self.force_pillar = make_box(0.20, HOLO_HEIGHT + 0.08, 0.20, y0=0.0)
        self.pillar_cap = make_box(0.26, 0.04, 0.26, y0=HOLO_HEIGHT + 0.08)

        # Decals no piso (anéis de base + brilho sob minérios)
        self.base_decal_mesh = make_decal_quad(1.48, y=0.012)
        self.ore_decal_mesh = make_decal_quad(0.96, y=0.006)

        self.env_parts: list[tuple[Mesh, Material]] = []
        self.env_model = glm.mat4(1.0)
        self.env_center = glm.vec3(self.grid_w * 0.5, 0.0, self.grid_h * 0.5)

        self.objects: list[Placeable] = []
        self.occupancy: dict[tuple[int, int], Placeable] = {}
        self.catalog_index = 0
        self.ghost: Ghost | None = None
        self.editing = True

        # Cell map (RGBA8) para AO de paredes e halos no shader do piso
        self._cell_map_arr = np.zeros((self.grid_h, self.grid_w, 4), dtype=np.uint8)
        self.cell_map_tex = make_data_texture_rgba(self._cell_map_arr)
        self._cell_map_dirty = True
        self._cached_walls: set[tuple[int, int]] = set()
        self._cached_segs: list[tuple[tuple[int, int], tuple[int, int]]] = []
        self._cached_isolates: list[tuple[int, int]] = []
        self._cached_pillars: list[tuple[int, int]] = []

    def _load_ore_meshes(self) -> None:
        """Malhas glTF diamante/ouro/prata (atlas + UV)."""
        for key, path in ORE_GLTFS.items():
            if not path.is_file():
                continue
            parts, _, _ = load_gltf_parts(path, fit_xz=0.85)
            if not parts:
                continue
            mesh, mat, _ = parts[0]
            self.meshes[key] = mesh
            dst = self.ore_materials[key]
            if mat.texture_id is not None:
                dst.texture_id = mat.texture_id
                if key in ("ouro", "prata"):
                    dst.kd = glm.vec3(1.0, 1.0, 1.0)
        # Prata é neutra (cinza claro), ótima para tingir bronze sem apagar a cor;
        # rubi fica sem a textura azul do diamante para preservar o vermelho rubi vivo.
        if MAT_PRATA.texture_id is not None:
            MAT_BRONZE.texture_id = MAT_PRATA.texture_id
        if MAT_OURO.texture_id is not None:
            MAT_MINERIO.texture_id = MAT_OURO.texture_id
            self.meshes["minerio"] = self.meshes.get("ouro", self.meshes["minerio"])

    @staticmethod
    def _bind_env_textures(tex_dir: Path) -> None:
        """Carrega texturas da arena, do hangar e dos materiais procedurais."""
        t_chao = load_texture(tex_dir / "chao.png", max_size=1024)
        t_chao_n = load_texture(tex_dir / "chao_normal.png", max_size=1024)
        if t_chao is not None:
            MAT_CHAO.texture_id = t_chao
            MAT_CHAO.kd = glm.vec3(0.54, 0.58, 0.65)
            MAT_PAREDE.texture_id = t_chao
            MAT_PAREDE.kd = glm.vec3(0.60, 0.64, 0.70)
        if t_chao_n is not None:
            MAT_CHAO.normal_id = t_chao_n

        t_base = load_texture(tex_dir / "base.png", max_size=1024)
        if t_base is not None:
            for bmat in (MAT_BASE, MAT_BASE_ALFA, MAT_BASE_BETA):
                if bmat.texture_id is None:
                    bmat.texture_id = t_base

        # Hangar: concreto, painéis sci-fi, hazard, metal escovado, janela
        t_conc = load_texture(tex_dir / "concreto.png", max_size=1024)
        t_conc_n = load_texture(tex_dir / "concreto_normal.png", max_size=1024)
        if t_conc is not None:
            MAT_CONCRETO.texture_id = t_conc
            MAT_CONCRETO.kd = glm.vec3(0.46, 0.50, 0.58)
        if t_conc_n is not None:
            MAT_CONCRETO.normal_id = t_conc_n

        t_pan = load_texture(tex_dir / "painel.png", max_size=1024)
        t_pan_n = load_texture(tex_dir / "painel_normal.png", max_size=1024)
        t_pan_e = load_texture(tex_dir / "painel_emissive.png", max_size=1024)
        if t_pan is not None:
            MAT_PAINEL.texture_id = t_pan
            MAT_PAINEL.kd = glm.vec3(0.62, 0.66, 0.74)
        if t_pan_n is not None:
            MAT_PAINEL.normal_id = t_pan_n
        if t_pan_e is not None:
            MAT_PAINEL.emissive_id = t_pan_e

        t_haz = load_texture(tex_dir / "hazard.png", max_size=512)
        if t_haz is not None:
            MAT_HAZARD.texture_id = t_haz

        t_met = load_texture(tex_dir / "metal_escovado.png", max_size=512)
        if t_met is not None:
            MAT_METAL_ESC.texture_id = t_met
            MAT_METAL.texture_id = t_met
            MAT_LUMINARIA.texture_id = t_met
            _MAT_EMITTER.texture_id = t_met

        t_win = load_texture(tex_dir / "janela.png", max_size=1024)
        t_win_e = load_texture(tex_dir / "janela_emissive.png", max_size=1024)
        if t_win is not None:
            MAT_JANELA.texture_id = t_win
        if t_win_e is not None:
            MAT_JANELA.emissive_id = t_win_e

        # Armadilha: grelha + emissivo pulsante + normal map
        t_arm = load_texture(tex_dir / "armadilha.png", max_size=512)
        t_arm_e = load_texture(tex_dir / "armadilha_emissive.png", max_size=512)
        t_arm_n = load_texture(tex_dir / "armadilha_normal.png", max_size=512)
        if t_arm is not None:
            MAT_ARMADILHA.texture_id = t_arm
            MAT_ARMADILHA.kd = glm.vec3(1.0, 1.0, 1.0)
        if t_arm_e is not None:
            MAT_ARMADILHA.emissive_id = t_arm_e
        if t_arm_n is not None:
            MAT_ARMADILHA.normal_id = t_arm_n

        # Materiais de catálogo (madeira e tecido/fosco procedurais)
        t_mad = load_texture(tex_dir / "madeira.png", max_size=512)
        if t_mad is not None:
            MAT_MADEIRA.texture_id = t_mad
            MAT_MADEIRA.triplanar_scale = 0.9
        t_fos = load_texture(tex_dir / "fosco.png", max_size=512)
        if t_fos is not None:
            MAT_FOSCO.texture_id = t_fos
            MAT_FOSCO.triplanar_scale = 1.2
            MAT_ABAJUR.texture_id = t_fos
            MAT_ABAJUR.triplanar_scale = 1.2

        # Decals RGBA
        t_ring = load_texture(tex_dir / "anel_base.png", max_size=512)
        if t_ring is not None:
            _MAT_DECAL_ALFA.texture_id = t_ring
            _MAT_DECAL_BETA.texture_id = t_ring
        t_glow = load_texture(tex_dir / "brilho.png", max_size=256)
        if t_glow is not None:
            _MAT_DECAL_ORE.texture_id = t_glow

        for mat, name in (
            (MAT_MINERIO, "minerio.png"),
            (MAT_DIAMANTE, "diamante.png"),
            (MAT_OURO, "ouro.png"),
            (MAT_PRATA, "prata.png"),
        ):
            if mat.texture_id is not None:
                continue
            tid = load_texture(tex_dir / name, max_size=1024)
            if tid is not None:
                mat.texture_id = tid
                mat.kd = glm.vec3(1.0, 1.0, 1.0)

    def resize_grid(self, w: int, h: int) -> None:
        """Troca o tamanho da grade: hangar (com cache), cell map e base Beta."""
        w, h = max(1, int(w)), max(1, int(h))
        if w == self.grid_w and h == self.grid_h:
            return
        self.grid_w, self.grid_h = w, h
        key = (w, h)
        if key not in self._hangars:
            self._hangars[key] = HangarEnvironment(w, h)
        self.hangar = self._hangars[key]
        self.env_center = glm.vec3(w * 0.5, 0.0, h * 0.5)

        # Move base Beta (objeto locked com MAT_BASE_BETA) para o canto oposto
        new_beta = (w - 1, h - 1)
        for o in self.objects:
            if o.item.cell_kind != CellKind.BASE or not o.locked:
                continue
            if o.material is MAT_BASE_BETA or (o.cell != (0, 0) and o.material is not MAT_BASE_ALFA):
                old = o.cell
                if old != new_beta:
                    self.occupancy.pop(old, None)
                    o.cell = new_beta
                    self.occupancy[new_beta] = o
                break
        self._cell_map_dirty = True

    def _rebuild_cell_map_if_needed(self) -> None:
        if not self._cell_map_dirty:
            return
        arr = np.zeros((self.grid_h, self.grid_w, 4), dtype=np.uint8)
        for (x, z), obj in self.occupancy.items():
            if not (0 <= x < self.grid_w and 0 <= z < self.grid_h):
                continue
            kind = obj.item.cell_kind
            if kind == CellKind.PAREDE:
                arr[z, x, 0] = 255
            elif kind == CellKind.ARMADILHA:
                arr[z, x, 1] = 255
            elif kind == CellKind.BASE:
                if (x, z) == (0, 0) or obj.material is MAT_BASE_ALFA:
                    arr[z, x, 2] = 255
                else:
                    arr[z, x, 3] = 255
        self._cell_map_arr = arr
        update_data_texture_rgba(self.cell_map_tex, arr)
        walls = self._wall_cells()
        self._cached_walls = walls
        self._cached_segs, self._cached_isolates = self._wall_segments_and_isolates(walls)
        self._cached_pillars = self._pillar_cells(walls)
        self._cell_map_dirty = False

    def current_item(self) -> CatalogItem:
        return CATALOG[self.catalog_index]

    def select_next(self, delta: int = 1) -> None:
        if delta:
            self.catalog_index = (self.catalog_index + delta) % len(CATALOG)
        self._refresh_ghost_item()

    def select_index(self, index: int) -> None:
        self.catalog_index = index % len(CATALOG)
        self._refresh_ghost_item()

    def _parts_for(self, item_id: str) -> list[tuple[Mesh, Material]]:
        return list(self.catalog_parts.get(item_id, []))

    def _refresh_ghost_item(self) -> None:
        if not self.ghost:
            return
        item = self.current_item()
        self.ghost.item = item
        self.ghost.mesh = self.meshes[item.id]
        self.ghost.parts = self._parts_for(item.id)
        self.ghost.scale = item.default_scale
        self.ghost.yaw_deg = 0.0
        self.ghost.allowed = self.can_place(item, self.ghost.cell)

    def begin_ghost(self, cell: tuple[int, int]) -> None:
        item = self.current_item()
        self.ghost = Ghost(
            item=item,
            mesh=self.meshes[item.id],
            cell=cell,
            scale=item.default_scale,
            allowed=self.can_place(item, cell),
            parts=self._parts_for(item.id),
        )

    def update_ghost_cell(self, cell: tuple[int, int]) -> None:
        if not self.ghost:
            self.begin_ghost(cell)
            return
        self.ghost.cell = cell
        self.ghost.allowed = self.can_place(self.ghost.item, cell)

    def can_place(self, item: CatalogItem, cell: tuple[int, int]) -> bool:
        x, y = cell
        if not (0 <= x < self.grid_w and 0 <= y < self.grid_h):
            return False
        if cell in self.occupancy:
            return False
        return True

    def confirm_ghost(self) -> bool:
        if not self.ghost or not self.ghost.allowed or not self.editing:
            return False
        p = self.ghost.as_placeable()
        p.user_placed = True
        if p.item.cell_kind == CellKind.MINERIO:
            tipo, valor = random.choice(
                [("bronze", 10), ("prata", 25), ("ouro", 50), ("rubi", 80), ("diamante", 120)]
            )
            p.ore_tipo = tipo
            p.ore_valor = valor
            mesh_key = ORE_MESH_FOR_TIPO.get(tipo, "ouro")
            p.mesh = self.meshes.get(mesh_key) or self.meshes["minerio"]
            p.material = self.ore_materials.get(tipo, MAT_MINERIO)
        self.objects.append(p)
        self.occupancy[p.cell] = p
        self.ghost = None
        self._cell_map_dirty = True
        return True

    def has_user_placed_objects(self) -> bool:
        return any(o.user_placed for o in self.objects)

    def cancel_ghost(self) -> None:
        self.ghost = None

    def remove_at(self, cell: tuple[int, int]) -> None:
        p = self.occupancy.pop(cell, None)
        if p and not p.locked:
            self.objects = [o for o in self.objects if o is not p]
            self._cell_map_dirty = True
        elif p and p.locked:
            self.occupancy[cell] = p

    def rotate_ghost(self, delta_deg: float) -> None:
        if self.ghost and self.ghost.item.can_rotate:
            self.ghost.yaw_deg = (self.ghost.yaw_deg + delta_deg) % 360

    def scale_ghost(self, factor: float) -> None:
        if self.ghost and self.ghost.item.can_scale:
            self.ghost.scale = max(0.4, min(1.8, self.ghost.scale * factor))

    def _ore_color_for(self, mat: Material | None) -> glm.vec3:
        ore_colors = {
            id(MAT_OURO): glm.vec3(1.2, 0.85, 0.25),
            id(MAT_DIAMANTE): glm.vec3(0.35, 0.78, 1.35),
            id(MAT_PRATA): glm.vec3(0.85, 0.92, 1.15),
            id(MAT_RUBI): glm.vec3(1.35, 0.22, 0.38),
            id(MAT_BRONZE): glm.vec3(1.05, 0.55, 0.24),
            id(MAT_MINERIO): glm.vec3(1.1, 0.8, 0.35),
        }
        return ore_colors.get(id(mat or MAT_MINERIO), glm.vec3(1.1, 0.8, 0.35))

    def point_lights(
        self, camera_pos: glm.vec3 | None = None
    ) -> list[tuple[glm.vec3, glm.vec3]]:
        """Até 16 luzes (teto do hangar + luminárias, bases, armadilhas e minérios)."""
        now = time.perf_counter()
        pulse = 0.65 + 0.35 * math.sin(now * 1.8 * math.tau)
        lights: list[tuple[glm.vec3, glm.vec3]] = list(self.hangar.ceiling_lights())
        obj_lights: list[tuple[glm.vec3, glm.vec3]] = []
        for o in self.objects:
            kind = o.item.cell_kind
            pos = cell_to_world(*o.cell)
            if o.item.emits_light:
                obj_lights.append((pos + glm.vec3(0, 1.1 * o.scale, 0), glm.vec3(1.05, 0.92, 0.72) * 0.65))
            elif kind == CellKind.BASE:
                if o.cell == (0, 0) or o.material is MAT_BASE_ALFA:
                    col = glm.vec3(0.22, 0.88, 1.25) * 0.65
                else:
                    col = glm.vec3(1.25, 0.42, 0.16) * 0.65
                obj_lights.append((pos + glm.vec3(0, 0.6, 0), col))
            elif kind == CellKind.ARMADILHA:
                obj_lights.append((pos + glm.vec3(0, 0.4, 0), glm.vec3(1.25, 0.20, 0.08) * 0.48 * pulse))
            elif kind == CellKind.MINERIO:
                col = self._ore_color_for(o.material)
                obj_lights.append((pos + glm.vec3(0, 0.7, 0), col * 0.42))
        if camera_pos is not None and len(lights) + len(obj_lights) > 16:
            obj_lights.sort(key=lambda lc: float(glm.length(lc[0] - camera_pos)))
        lights.extend(obj_lights)
        return lights[:16]

    def sync_walls_to_kinds(self) -> dict[str, set[tuple[int, int]]]:
        """Extrai conjuntos lógicos a partir dos objetos colocados."""
        paredes: set[tuple[int, int]] = set()
        minerios: set[tuple[int, int]] = set()
        armadilhas: set[tuple[int, int]] = set()
        for cell, obj in self.occupancy.items():
            kind = obj.item.cell_kind
            if kind == CellKind.PAREDE:
                paredes.add(cell)
            elif kind == CellKind.MINERIO:
                minerios.add(cell)
            elif kind == CellKind.ARMADILHA:
                armadilhas.add(cell)
        return {"paredes": paredes, "minerios": minerios, "armadilhas": armadilhas}

    def _item_by_id(self, item_id: str) -> CatalogItem:
        return next(i for i in CATALOG if i.id == item_id)

    def _place_seed(self, item: CatalogItem, cell: tuple[int, int]) -> None:
        if cell in self.occupancy:
            return
        p = Placeable(
            item=item,
            mesh=self.meshes[item.id],
            cell=cell,
            material=item.material,
            scale=item.default_scale,
            locked=False,
            parts=self._parts_for(item.id),
        )
        self.objects.append(p)
        self.occupancy[cell] = p

    def seed_from_arena(self, arena) -> None:
        """Espelha paredes/minérios/armadilhas da arena na cena (não mexe nas bases)."""
        self.resize_grid(arena.largura, arena.altura)
        keep: list[Placeable] = []
        new_occ: dict[tuple[int, int], Placeable] = {}
        for o in self.objects:
            if o.item.cell_kind == CellKind.BASE and o.locked:
                keep.append(o)
                new_occ[o.cell] = o
        self.objects = keep
        self.occupancy = new_occ

        parede = self._item_by_id("estante")
        minerio = self._item_by_id("minerio")
        armadilha = self._item_by_id("armadilha")
        for cell in arena.paredes:
            self._place_seed(parede, cell)
        for cell in arena.armadilhas:
            self._place_seed(armadilha, cell)
        for cell, ore in arena.minerios.items():
            mesh_key = ORE_MESH_FOR_TIPO.get(ore.tipo, "ouro")
            mesh = self.meshes.get(mesh_key) or self.meshes["minerio"]
            mat = self.ore_materials.get(ore.tipo, MAT_MINERIO)
            if cell in self.occupancy:
                continue
            p = Placeable(
                item=minerio,
                mesh=mesh,
                cell=cell,
                material=mat,
                scale=minerio.default_scale,
                locked=False,
                ore_tipo=ore.tipo,
                ore_valor=ore.valor,
                user_placed=False,
            )
            self.objects.append(p)
            self.occupancy[cell] = p
        self._cell_map_dirty = True

    def draw_static(self, shader: Shader, eye_pos: glm.vec3 | None = None) -> None:
        self._rebuild_cell_map_if_needed()
        self.hangar.draw(shader, eye_pos)

    # ------------------------------------------------------------------
    # Auto-tiling de paredes holográficas (segmentos conectados + pilares)
    # ------------------------------------------------------------------

    def _wall_cells(self) -> set[tuple[int, int]]:
        return {o.cell for o in self.objects if o.item.cell_kind == CellKind.PAREDE}

    @staticmethod
    def _wall_segments_and_isolates(
        walls: set[tuple[int, int]],
    ) -> tuple[list[tuple[tuple[int, int], tuple[int, int]]], list[tuple[int, int]]]:
        """Pares de células vizinhas ortogonais (E e S) + células sem vizinhos."""
        segs: list[tuple[tuple[int, int], tuple[int, int]]] = []
        isolates: list[tuple[int, int]] = []
        for x, z in walls:
            if (x + 1, z) in walls:
                segs.append(((x, z), (x + 1, z)))
            if (x, z + 1) in walls:
                segs.append(((x, z), (x, z + 1)))
            has_nbr = any((x + dx, z + dz) in walls for dx, dz in _ORTHO)
            if not has_nbr:
                isolates.append((x, z))
        return segs, isolates

    def _pillar_cells(self, walls: set[tuple[int, int]]) -> list[tuple[int, int]]:
        """Pilares em células isoladas, pontas soltas, cantos em L e junções T/X."""
        out: list[tuple[int, int]] = []
        for x, z in walls:
            nbrs = [(x + dx, z + dz) for dx, dz in _ORTHO if (x + dx, z + dz) in walls]
            n = len(nbrs)
            if n <= 1 or n >= 3:
                out.append((x, z))
            elif n == 2:
                (ax, az), (bx, bz) = nbrs
                if not ((ax == bx == x) or (az == bz == z)):
                    out.append((x, z))
        return out

    @staticmethod
    def _box_transform(cx: float, cz: float, sx: float, sz: float, yaw_deg: float = 0.0) -> glm.mat4:
        m = glm.translate(glm.mat4(1.0), glm.vec3(cx, 0.0, cz))
        if yaw_deg:
            m = glm.rotate(m, glm.radians(yaw_deg), glm.vec3(0, 1, 0))
        return glm.scale(m, glm.vec3(sx, 1.0, sz))

    @staticmethod
    def _cell_model(cell: tuple[int, int], yaw_deg: float = 0.0) -> glm.mat4:
        m = glm.translate(glm.mat4(1.0), cell_to_world(*cell))
        if yaw_deg:
            m = glm.rotate(m, glm.radians(yaw_deg), glm.vec3(0, 1, 0))
        return m

    def draw_objects(self, shader: Shader) -> None:
        """Opacos da cena (paredes PAREDE saem como trilhos + hologramas conectados)."""
        for o in self.objects:
            if o.item.cell_kind == CellKind.PAREDE:
                continue
            o.draw(shader)

    def _isolate_yaw(self, cell: tuple[int, int], walls: set[tuple[int, int]]) -> float:
        obj = self.occupancy.get(cell)
        if obj and obj.yaw_deg:
            return obj.yaw_deg
        x, z = cell
        if (x, z - 2) in walls or (x, z + 2) in walls:
            return 90.0
        if (x - 2, z) in walls or (x + 2, z) in walls:
            return 0.0
        return 90.0 if ((x * 3 + z * 5) % 2 == 1) else 0.0

    def draw_forcefield_hardware(self, shader: Shader) -> None:
        """Trilhos emissores contínuos + pilares/nós nos cantos e pontas."""
        self._rebuild_cell_map_if_needed()
        walls = self._cached_walls
        segs, isolates = self._cached_segs, self._cached_isolates
        rail_w = 0.34
        glow_w = 0.10

        for (x0, z0), (x1, z1) in segs:
            mx = (x0 + x1) * 0.5 + 0.5
            mz = (z0 + z1) * 0.5 + 0.5
            if x1 != x0:  # segmento horizontal (Leste-Oeste)
                m_rail = self._box_transform(mx, mz, 1.08, rail_w)
                m_glow = self._box_transform(mx, mz, 1.04, glow_w)
            else:  # segmento vertical (Norte-Sul)
                m_rail = self._box_transform(mx, mz, rail_w, 1.08)
                m_glow = self._box_transform(mx, mz, glow_w, 1.04)
            draw_textured(shader, self.rail_unit, m_rail, _MAT_EMITTER)
            draw_textured(shader, self.rail_glow, m_glow, _MAT_EMITTER_GLOW)

        for cell in isolates:
            yaw = self._isolate_yaw(cell, walls)
            cx, cz = cell[0] + 0.5, cell[1] + 0.5
            draw_textured(shader, self.rail_unit, self._box_transform(cx, cz, 0.86, rail_w, yaw), _MAT_EMITTER)
            draw_textured(shader, self.rail_glow, self._box_transform(cx, cz, 0.80, glow_w, yaw), _MAT_EMITTER_GLOW)

        for cell in self._cached_pillars:
            cm = self._cell_model(cell)
            draw_textured(shader, self.pillar_base, cm, _MAT_EMITTER)
            draw_textured(shader, self.force_pillar, cm, _MAT_EMITTER)
            draw_textured(shader, self.pillar_cap, cm, _MAT_EMITTER_GLOW)

    def draw_hologram_walls(self, shader: Shader) -> None:
        """Campos de força contínuos entre células vizinhas + painéis para células isoladas."""
        self._rebuild_cell_map_if_needed()
        walls = self._cached_walls
        segs, isolates = self._cached_segs, self._cached_isolates
        for (x0, z0), (x1, z1) in segs:
            mx = (x0 + x1) * 0.5 + 0.5
            mz = (z0 + z1) * 0.5 + 0.5
            if x1 != x0:
                m = self._box_transform(mx, mz, 1.02, _HOLO_THICK)
            else:
                m = self._box_transform(mx, mz, _HOLO_THICK, 1.02)
            draw_hologram(shader, self.holo_unit, m)
        for cell in isolates:
            yaw = self._isolate_yaw(cell, walls)
            cx, cz = cell[0] + 0.5, cell[1] + 0.5
            draw_hologram(shader, self.holo_unit, self._box_transform(cx, cz, 0.82, _HOLO_THICK, yaw))

    def draw_decals(
        self,
        shader: Shader,
        now: float,
        alfa_path: list[tuple[int, int]] | None = None,
        beta_path: list[tuple[int, int]] | None = None,
    ) -> None:
        """Anéis luminosos nas bases, brilho sob minérios e marcadores da rota calculada."""
        for o in self.objects:
            kind = o.item.cell_kind
            pos = cell_to_world(*o.cell)
            if kind == CellKind.BASE:
                is_alfa = o.cell == (0, 0) or o.material is MAT_BASE_ALFA
                mat = _MAT_DECAL_ALFA if is_alfa else _MAT_DECAL_BETA
                ang = now * 22.0 * (1.0 if is_alfa else -1.0)
                m = glm.translate(glm.mat4(1.0), pos)
                m = glm.rotate(m, glm.radians(ang), glm.vec3(0, 1, 0))
                draw_textured(shader, self.base_decal_mesh, m, mat, alpha=0.88)
            elif kind == CellKind.MINERIO:
                col = self._ore_color_for(o.material)
                _MAT_DECAL_ORE.kd = col
                _MAT_DECAL_ORE.emissive = col * 1.15
                phase = (o.cell[0] * 1.7 + o.cell[1] * 2.3) * 0.37
                s = 0.88 + 0.10 * math.sin(now * 2.0 + phase)
                m = glm.translate(glm.mat4(1.0), pos)
                m = glm.scale(m, glm.vec3(s, 1.0, s))
                draw_textured(shader, self.ore_decal_mesh, m, _MAT_DECAL_ORE, alpha=0.72)

        for path, col in (
            (alfa_path, glm.vec3(0.18, 0.90, 1.0)),
            (beta_path, glm.vec3(1.0, 0.45, 0.16)),
        ):
            if not path:
                continue
            _MAT_DECAL_ORE.kd = col
            _MAT_DECAL_ORE.emissive = col * 1.35
            for idx, cell in enumerate(path):
                pos = cell_to_world(*cell) + glm.vec3(0.0, 0.008, 0.0)
                s = 0.34 if idx < len(path) - 1 else 0.52
                m = glm.translate(glm.mat4(1.0), pos)
                m = glm.scale(m, glm.vec3(s, 1.0, s))
                draw_textured(shader, self.ore_decal_mesh, m, _MAT_DECAL_ORE, alpha=0.58)

    def draw_depth_casters(self, shader: Shader) -> None:
        """Geometria que projeta sombra (borda do hangar, objetos, trilhos e pilares)."""
        self._rebuild_cell_map_if_needed()
        self.hangar.draw_depth(shader)
        for o in self.objects:
            if o.item.cell_kind == CellKind.PAREDE:
                continue
            o.draw_depth_pass(shader)
        segs, isolates = self._cached_segs, self._cached_isolates
        rail_w = 0.34
        for (x0, z0), (x1, z1) in segs:
            mx = (x0 + x1) * 0.5 + 0.5
            mz = (z0 + z1) * 0.5 + 0.5
            m_rail = (
                self._box_transform(mx, mz, 1.08, rail_w)
                if x1 != x0
                else self._box_transform(mx, mz, rail_w, 1.08)
            )
            draw_depth(shader, self.rail_unit, m_rail)
        for cell in isolates:
            cx, cz = cell[0] + 0.5, cell[1] + 0.5
            draw_depth(shader, self.rail_unit, self._box_transform(cx, cz, 0.86, rail_w))
        for cell in self._cached_pillars:
            draw_depth(shader, self.force_pillar, self._cell_model(cell))

    def draw_ghost(self, shader: Shader) -> None:
        if not self.ghost:
            return
        tint = glm.vec3(0.2, 0.9, 0.3) if self.ghost.allowed else glm.vec3(0.95, 0.2, 0.2)
        p = self.ghost.as_placeable()
        p.draw(shader, alpha=0.55, tint=tint)

"""Galpão fechado + grade de objetos posicionados."""

from __future__ import annotations

from pathlib import Path

import glm

from gfx.gltf_loader import load_gltf_parts
from gfx.mesh import (
    MAT_BASE,
    MAT_BRONZE,
    MAT_CHAO,
    MAT_DIAMANTE,
    MAT_MINERIO,
    MAT_OURO,
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
    WAREHOUSE_GLTF,
    load_catalog_mesh,
    load_downloaded_robot,
    load_downloaded_robot_parts,
)
from gfx.primitives import make_box, make_floor
from gfx.shader import Shader
from gfx.texture import load_texture
from scene.catalog import CATALOG, CatalogItem, CellKind, cell_to_world
from scene.placeable import Ghost, Placeable, draw_depth, draw_hologram, draw_textured


GRID_W = 15
GRID_H = 9
WALL_H = 3.0
_HOLO_THICK = 0.36  # ~36% da largura da célula
_MAT_EMITTER = Material(
    glm.vec3(0.07, 0.08, 0.09),
    glm.vec3(0.12, 0.12, 0.14),
    24.0,
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
                "armadilha": (0.7, 0.12, 0.7),
                "base": (0.85, 0.25, 0.85),
            }
            if item.id == "base" and BASE2_GLTF.is_file():
                # Base2 albedo é atlas — malha glTF + emissive (cyan)
                parts, _, _ = load_gltf_parts(BASE2_GLTF, fit_xz=1.2, fit_y=0.32)
                mesh, mat, _ = parts[0]
                self.meshes[item.id] = mesh
                if mat.texture_id is not None:
                    MAT_BASE.texture_id = mat.texture_id
                    MAT_BASE.kd = glm.vec3(1.0, 1.0, 1.0)
                MAT_BASE.emissive = glm.vec3(mat.emissive)
                MAT_BASE.ks = glm.vec3(0.45, 0.5, 0.55)
                MAT_BASE.shininess = 64.0
            elif item.id == "estante" and SCIFI_WALL_GLTF.is_file():
                # 1.06: cobre a célula + leve overlap para unir painéis vizinhos
                parts, _, _ = load_gltf_parts(SCIFI_WALL_GLTF, fit_xz=1.06, fit_y=1.4)
                wall_parts: list[tuple[Mesh, Material]] = []
                for m, mat, _ in parts:
                    # highlight metálico concentrado (Dark Sci-Fi)
                    if mat.shininess < 48.0:
                        mat.shininess = 48.0
                    if float(glm.length(mat.ks)) < 0.25:
                        mat.ks = glm.vec3(0.3, 0.3, 0.32)
                    wall_parts.append((m, mat))
                self.catalog_parts["estante"] = wall_parts
                self.meshes[item.id] = parts[0][0]
            elif item.id == "minerio":
                # placeholder; malhas tipadas em _load_ore_meshes
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
        # Robô 3: clips Mixamo no OpenGL; OBJ texturizado só se não houver walk.npz
        focus = "robo3"
        clips_dir = Path(__file__).resolve().parents[1] / "assets" / "models" / "robo3_clips"
        has_clips = (clips_dir / "walk.npz").is_file()
        for key in DOWNLOADED_ROBOTS:
            if has_clips:
                # clips Mixamo no Actor; não carrega OBJs pesados no boot
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
        # UV tile ~1 por célula no chão; paredes com escala por metro
        self.floor = make_floor(GRID_W + 0.2, GRID_H + 0.2, uv_repeat=(float(GRID_W), float(GRID_H)))
        self.ceiling = make_floor(GRID_W + 0.2, GRID_H + 0.2, WALL_H, uv_repeat=(float(GRID_W), float(GRID_H)))
        self.wall_n = make_box(GRID_W + 0.4, WALL_H, 0.2, uv_scale=0.5)
        self.wall_s = make_box(GRID_W + 0.4, WALL_H, 0.2, uv_scale=0.5)
        self.wall_e = make_box(0.2, WALL_H, GRID_H + 0.4, uv_scale=0.5)
        self.wall_w = make_box(0.2, WALL_H, GRID_H + 0.4, uv_scale=0.5)

        # Hardware do campo de forças (volume holo + base + pilar)
        self.holo_volume = make_box(0.9, 1.5, _HOLO_THICK)
        self.emitter_base = make_box(0.7, 0.12, 0.7)
        self.force_pillar = make_box(0.22, 1.55, 0.22)

        self.env_parts: list[tuple[Mesh, Material]] = []
        self.env_model = glm.mat4(1.0)
        self.env_center = glm.vec3(GRID_W * 0.5, 0.0, GRID_H * 0.5)
        # Por enquanto: sem warehouse (escala/orientação erradas na cena)
        self.use_warehouse = False

        self.objects: list[Placeable] = []
        self.occupancy: dict[tuple[int, int], Placeable] = {}
        self.catalog_index = 0
        self.ghost: Ghost | None = None
        self.editing = True

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
                if key in ("diamante", "ouro", "prata"):
                    dst.kd = glm.vec3(1.0, 1.0, 1.0)
        # rubi/bronze reusam textura da malha correspondente
        if MAT_DIAMANTE.texture_id is not None:
            MAT_RUBI.texture_id = MAT_DIAMANTE.texture_id
        if MAT_PRATA.texture_id is not None:
            MAT_BRONZE.texture_id = MAT_PRATA.texture_id
        if MAT_OURO.texture_id is not None:
            MAT_MINERIO.texture_id = MAT_OURO.texture_id
            self.meshes["minerio"] = self.meshes.get("ouro", self.meshes["minerio"])

    @staticmethod
    def _bind_env_textures(tex_dir: Path) -> None:
        """Chão/parede=chao2 (tile); base=Base2 (atlas + malha)."""
        env = (
            (MAT_CHAO, tex_dir / "chao.png"),
            # sci-fi_wall sem PNG; painel tileável = chao2 (não o atlas Base2)
            (MAT_PAREDE, tex_dir / "chao.png"),
            (MAT_BASE, tex_dir / "base.png"),
        )
        for mat, path in env:
            tid = load_texture(path)
            if tid is None:
                continue
            # Base pode já ter tex/emissive da malha glTF (UVs do atlas)
            if mat is MAT_BASE and mat.texture_id is not None:
                mat.kd = glm.vec3(1.0, 1.0, 1.0)
                continue
            mat.texture_id = tid
            mat.kd = glm.vec3(1.0, 1.0, 1.0)
        nmap = load_texture(tex_dir / "chao_normal.png")
        if nmap is not None:
            MAT_CHAO.normal_id = nmap
        # metal Dark Sci-Fi: highlight concentrado
        MAT_CHAO.ks = glm.vec3(0.35, 0.35, 0.38)
        MAT_CHAO.shininess = 64.0
        MAT_PAREDE.ks = glm.vec3(0.28, 0.28, 0.30)
        MAT_PAREDE.shininess = 48.0
        MAT_PAREDE.emissive = glm.vec3(0.0)  # sem glow da Base2
        for mat, name in (
            (MAT_MINERIO, "minerio.png"),
            (MAT_DIAMANTE, "diamante.png"),
            (MAT_OURO, "ouro.png"),
            (MAT_PRATA, "prata.png"),
        ):
            if mat.texture_id is not None:
                continue
            tid = load_texture(tex_dir / name)
            if tid is not None:
                mat.texture_id = tid
                mat.kd = glm.vec3(1.0, 1.0, 1.0)

    def _load_warehouse(self) -> None:
        if not WAREHOUSE_GLTF.is_file():
            return
        parts, mins, maxs = load_gltf_parts(WAREHOUSE_GLTF)
        if not parts:
            return
        size = maxs - mins
        span = max(float(size.x), float(size.z), 1e-3)
        # encaixa o galpão na grade 15×9, chão em Y=0
        target = float(max(GRID_W, GRID_H)) * 0.95
        scale = target / span
        center = (mins + maxs) * 0.5
        self.env_model = glm.translate(glm.mat4(1), glm.vec3(GRID_W * 0.5, 0.0, GRID_H * 0.5))
        self.env_model = glm.scale(self.env_model, glm.vec3(scale))
        self.env_model = glm.translate(
            self.env_model, glm.vec3(-center.x, -mins.y, -center.z)
        )
        self.env_parts = [(m, mat) for m, mat, _ in parts]
        self.env_center = glm.vec3(GRID_W * 0.5, 0.0, GRID_H * 0.5)
        self.use_warehouse = True

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
        if not (0 <= x < GRID_W and 0 <= y < GRID_H):
            return False
        if cell in self.occupancy:
            return False
        # Bases só nos cantos lógicos se já houver bases do jogo; livres no edit
        if item.cell_kind == CellKind.BASE and cell not in {(0, 0), (GRID_W - 1, GRID_H - 1)}:
            # permite em qualquer célula livre para criatividade, mas preferência nos cantos
            pass
        return True

    def confirm_ghost(self) -> bool:
        if not self.ghost or not self.ghost.allowed or not self.editing:
            return False
        p = self.ghost.as_placeable()
        self.objects.append(p)
        self.occupancy[p.cell] = p
        self.ghost = None
        return True

    def cancel_ghost(self) -> None:
        self.ghost = None

    def remove_at(self, cell: tuple[int, int]) -> None:
        p = self.occupancy.pop(cell, None)
        if p and not p.locked:
            self.objects = [o for o in self.objects if o is not p]

    def rotate_ghost(self, delta_deg: float) -> None:
        if self.ghost and self.ghost.item.can_rotate:
            self.ghost.yaw_deg = (self.ghost.yaw_deg + delta_deg) % 360

    def scale_ghost(self, factor: float) -> None:
        if self.ghost and self.ghost.item.can_scale:
            self.ghost.scale = max(0.4, min(1.8, self.ghost.scale * factor))

    def point_lights(
        self, camera_pos: glm.vec3 | None = None
    ) -> list[tuple[glm.vec3, glm.vec3]]:
        """Até 8 luzes locais (luminárias, minérios, armadilhas, bases)."""
        ore_colors = {
            id(MAT_OURO): glm.vec3(1.2, 0.85, 0.25),
            id(MAT_DIAMANTE): glm.vec3(0.45, 0.75, 1.3),
            id(MAT_PRATA): glm.vec3(0.85, 0.9, 1.1),
            id(MAT_RUBI): glm.vec3(1.3, 0.25, 0.4),
            id(MAT_BRONZE): glm.vec3(1.0, 0.55, 0.25),
            id(MAT_MINERIO): glm.vec3(1.1, 0.8, 0.35),
        }
        lights: list[tuple[glm.vec3, glm.vec3]] = []
        for o in self.objects:
            kind = o.item.cell_kind
            pos = cell_to_world(*o.cell)
            if o.item.emits_light:
                lights.append((pos + glm.vec3(0, 1.1 * o.scale, 0), glm.vec3(1.0, 0.92, 0.75) * 0.45))
            elif kind == CellKind.MINERIO:
                mat = o.material or MAT_MINERIO
                color = ore_colors.get(id(mat), glm.vec3(1.1, 0.8, 0.35))
                lights.append((pos + glm.vec3(0, 0.7, 0), color * 0.45))
            elif kind == CellKind.ARMADILHA:
                lights.append((pos + glm.vec3(0, 0.35, 0), glm.vec3(1.2, 0.2, 0.12) * 0.45))
            elif kind == CellKind.BASE:
                em = MAT_BASE.emissive
                cyan = glm.vec3(0.25, 0.85, 1.0) if glm.length(em) < 0.01 else em * 2.5
                lights.append((pos + glm.vec3(0, 0.5, 0), cyan * 0.45 * 0.55))
        if camera_pos is not None and len(lights) > 8:
            lights.sort(key=lambda lc: float(glm.length(lc[0] - camera_pos)))
        return lights[:8]

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
            )
            self.objects.append(p)
            self.occupancy[cell] = p

    def draw_static(self, shader: Shader) -> None:
        if self.use_warehouse and self.env_parts:
            for mesh, mat in self.env_parts:
                draw_textured(shader, mesh, self.env_model, mat)
            return
        floor_model = glm.translate(glm.mat4(1), glm.vec3(GRID_W * 0.5, 0.0, GRID_H * 0.5))
        draw_textured(shader, self.floor, floor_model, MAT_CHAO)
        wall_h = 0.55
        for mesh, pos in (
            (self.wall_n, glm.vec3(GRID_W * 0.5, 0, -0.1)),
            (self.wall_s, glm.vec3(GRID_W * 0.5, 0, GRID_H + 0.1)),
            (self.wall_w, glm.vec3(-0.1, 0, GRID_H * 0.5)),
            (self.wall_e, glm.vec3(GRID_W + 0.1, 0, GRID_H * 0.5)),
        ):
            model = glm.translate(glm.mat4(1), pos)
            model = glm.scale(model, glm.vec3(1.0, wall_h / WALL_H, 1.0))
            draw_textured(shader, mesh, model, MAT_PAREDE)

    def _wall_cells(self) -> set[tuple[int, int]]:
        return {o.cell for o in self.objects if o.item.cell_kind == CellKind.PAREDE}

    def _pillar_cells(self, walls: set[tuple[int, int]]) -> list[tuple[int, int]]:
        """Pontas soltas e cantos em L (não segmentos retos)."""
        out: list[tuple[int, int]] = []
        for x, z in walls:
            nbrs = [(x + dx, z + dz) for dx, dz in _ORTHO if (x + dx, z + dz) in walls]
            n = len(nbrs)
            if n <= 1:
                out.append((x, z))
                continue
            if n == 2:
                (ax, az), (bx, bz) = nbrs
                # colinear se partilham eixo X ou Z através da célula
                if not ((ax == bx == x) or (az == bz == z)):
                    out.append((x, z))
        return out

    @staticmethod
    def _cell_model(cell: tuple[int, int], yaw_deg: float = 0.0) -> glm.mat4:
        m = glm.translate(glm.mat4(1.0), cell_to_world(*cell))
        if yaw_deg:
            m = glm.rotate(m, glm.radians(yaw_deg), glm.vec3(0, 1, 0))
        return m

    def draw_objects(self, shader: Shader) -> None:
        """Opacos da cena (paredes PAREDE saem no pass holográfico)."""
        for o in self.objects:
            if o.item.cell_kind == CellKind.PAREDE:
                continue
            o.draw(shader)

    def draw_forcefield_hardware(self, shader: Shader) -> None:
        """Bases emissoras + pilares (opacos, depth ligado)."""
        walls = self._wall_cells()
        for o in self.objects:
            if o.item.cell_kind != CellKind.PAREDE:
                continue
            draw_textured(shader, self.emitter_base, self._cell_model(o.cell), _MAT_EMITTER)
        for cell in self._pillar_cells(walls):
            draw_textured(shader, self.force_pillar, self._cell_model(cell), _MAT_EMITTER)

    def draw_hologram_walls(self, shader: Shader) -> None:
        """Volume holográfico espesso (~36% da célula) — pass transparente."""
        for o in self.objects:
            if o.item.cell_kind != CellKind.PAREDE:
                continue
            draw_hologram(shader, self.holo_volume, self._cell_model(o.cell, o.yaw_deg))

    def draw_depth_casters(self, shader: Shader) -> None:
        """Geometria que projeta sombra (sem fantasma nem volume holográfico)."""
        if self.use_warehouse and self.env_parts:
            for mesh, _mat in self.env_parts:
                draw_depth(shader, mesh, self.env_model)
        else:
            wall_h = 0.55
            for mesh, pos in (
                (self.wall_n, glm.vec3(GRID_W * 0.5, 0, -0.1)),
                (self.wall_s, glm.vec3(GRID_W * 0.5, 0, GRID_H + 0.1)),
                (self.wall_w, glm.vec3(-0.1, 0, GRID_H * 0.5)),
                (self.wall_e, glm.vec3(GRID_W + 0.1, 0, GRID_H * 0.5)),
            ):
                model = glm.translate(glm.mat4(1), pos)
                model = glm.scale(model, glm.vec3(1.0, wall_h / WALL_H, 1.0))
                draw_depth(shader, mesh, model)
        for o in self.objects:
            if o.item.cell_kind == CellKind.PAREDE:
                continue
            o.draw_depth_pass(shader)
        walls = self._wall_cells()
        for o in self.objects:
            if o.item.cell_kind != CellKind.PAREDE:
                continue
            draw_depth(shader, self.emitter_base, self._cell_model(o.cell))
        for cell in self._pillar_cells(walls):
            draw_depth(shader, self.force_pillar, self._cell_model(cell))

    def draw_ghost(self, shader: Shader) -> None:
        if not self.ghost:
            return
        tint = glm.vec3(0.2, 0.9, 0.3) if self.ghost.allowed else glm.vec3(0.95, 0.2, 0.2)
        p = self.ghost.as_placeable()
        p.draw(shader, alpha=0.55, tint=tint)

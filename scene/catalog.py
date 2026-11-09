"""Catálogo de objetos posicionáveis e regras de célula."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

import glm

from gfx.mesh import (
    MAT_ABAJUR,
    MAT_ALFA,
    MAT_ARMADILHA,
    MAT_BASE,
    MAT_BETA,
    MAT_FOSCO,
    MAT_LUMINARIA,
    MAT_MADEIRA,
    MAT_METAL,
    MAT_MINERIO,
    MAT_PAREDE,
    Material,
)


class CellKind(Enum):
    LIVRE = auto()
    PAREDE = auto()
    ARMADILHA = auto()
    MINERIO = auto()
    BASE = auto()


@dataclass(frozen=True)
class CatalogItem:
    id: str
    label: str
    cell_kind: CellKind
    material: Material
    can_rotate: bool = True
    can_scale: bool = True
    default_scale: float = 1.0
    emits_light: bool = False
    is_robot: bool = False


CATALOG: list[CatalogItem] = [
    CatalogItem("bancada", "Bancada", CellKind.PAREDE, MAT_MADEIRA),
    CatalogItem("cadeira", "Cadeira", CellKind.LIVRE, MAT_MADEIRA, default_scale=0.9),
    CatalogItem("luminaria", "Luminária", CellKind.LIVRE, MAT_LUMINARIA, emits_light=True),
    CatalogItem("abajur", "Abajur", CellKind.LIVRE, MAT_ABAJUR, emits_light=True, default_scale=0.7),
    CatalogItem("planta", "Planta", CellKind.LIVRE, MAT_FOSCO, default_scale=0.8),
    CatalogItem("minerio", "Minério", CellKind.MINERIO, MAT_MINERIO, default_scale=1.15),
    CatalogItem("estante", "Estante/Parede", CellKind.PAREDE, MAT_PAREDE),
    CatalogItem("armadilha", "Armadilha", CellKind.ARMADILHA, MAT_ARMADILHA, default_scale=0.85, can_scale=False),
    CatalogItem("base", "Base", CellKind.BASE, MAT_BASE, can_scale=False),
]

ROBOT_ALFA = CatalogItem("robo", "Robô Alfa", CellKind.LIVRE, MAT_ALFA, is_robot=True, can_scale=False)
ROBOT_BETA = CatalogItem("robo", "Robô Beta", CellKind.LIVRE, MAT_BETA, is_robot=True, can_scale=False)


def cell_to_world(x: int, y: int) -> glm.vec3:
    """Centro da célula (x,y) no chão Y=0."""
    return glm.vec3(x + 0.5, 0.0, y + 0.5)

"""
Heurísticas admissíveis para busca informada na grade.

A heurística oficial do A* é a distância de Manhattan. A Euclidiana permanece
disponível para comparação experimental (menos informativa em vizinhança-4).
"""

from __future__ import annotations

import math
from collections.abc import Callable

Celula = tuple[int, int]
Heuristica = Callable[[Celula, Celula], float]


def manhattan(a: Celula, b: Celula) -> int:
    """Distância de Manhattan entre duas células.

    Em grade com movimento ortogonal e custo mínimo de aresta 1, esta
    função é admissível e consistente: h(n) ≤ h*(n) e
    |h(n) − h(n')| ≤ c(n, n').

    Args:
        a: Célula origem.
        b: Célula destino (objetivo).

    Returns:
        Soma das diferenças absolutas das coordenadas.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def euclidiana(a: Celula, b: Celula) -> float:
    """Distância Euclidiana (somente para comparação / relatório).

    Também é admissível sob custo mínimo 1, porém subestima mais trajetórias
    forçadas a contornar obstáculos em vizinhança-4, sendo menos informativa.

    Args:
        a: Célula origem.
        b: Célula destino.

    Returns:
        Distância em linha reta.
    """
    return math.hypot(a[0] - b[0], a[1] - b[1])

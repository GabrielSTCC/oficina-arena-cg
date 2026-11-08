"""
Navegação por busca heurística A* na arena.

Formulação: estados = células livres; ações = vizinhos-4; objetivo = alvo;
custo de aresta = 2 em armadilha, 1 caso contrário; h injetável (padrão Manhattan).
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass

from core.arena import Arena, Celula

from ia.heuristicas import Heuristica, manhattan


@dataclass(frozen=True)
class ResultadoBusca:
    """Resultado de uma chamada de busca de caminho.

    Attributes:
        caminho: Sequência de células a partir do sucessor de origem até o destino.
        custo: Custo g acumulado (arestas do grafo de busca).
        nos_expandidos: Quantidade de nós retirados da fronteira.
        alcancavel: False se não há caminho.
    """

    caminho: list[Celula]
    custo: float
    nos_expandidos: int
    alcancavel: bool


def buscar_caminho(
    arena: Arena,
    origem: Celula,
    destino: Celula,
    heuristica: Heuristica = manhattan,
) -> ResultadoBusca:
    """Executa A* com f(n) = g(n) + h(n).

    Args:
        arena: Ambiente com paredes e armadilhas.
        origem: Posição atual do agente.
        destino: Célula objetivo.
        heuristica: Função h(n) admissível (padrão: Manhattan).

    Returns:
        ``ResultadoBusca`` com caminho (sem a origem), custo e nós expandidos.
        Se inalcançável, ``alcancavel`` é False e ``caminho`` é vazio.
    """
    if origem == destino:
        return ResultadoBusca(caminho=[], custo=0, nos_expandidos=0, alcancavel=True)

    if not arena.eh_livre(destino):
        return ResultadoBusca(
            caminho=[], custo=float("inf"), nos_expandidos=0, alcancavel=False
        )

    # Fronteira: (f, contador_desempate, nó)
    fronteira: list[tuple[float, int, Celula]] = []
    contador = 0
    heapq.heappush(fronteira, (heuristica(origem, destino), contador, origem))

    veio_de: dict[Celula, Celula | None] = {origem: None}
    g_score: dict[Celula, float] = {origem: 0.0}
    fechados: set[Celula] = set()
    nos_expandidos = 0

    while fronteira:
        _, _, atual = heapq.heappop(fronteira)
        if atual in fechados:
            continue
        nos_expandidos += 1
        fechados.add(atual)

        if atual == destino:
            caminho = _reconstruir(veio_de, destino)
            return ResultadoBusca(
                caminho=caminho,
                custo=g_score[destino],
                nos_expandidos=nos_expandidos,
                alcancavel=True,
            )

        for vizinho in arena.vizinhos_validos(atual):
            custo_passo = arena.custo_aresta(vizinho)
            tentativo = g_score[atual] + custo_passo
            if tentativo < g_score.get(vizinho, float("inf")):
                veio_de[vizinho] = atual
                g_score[vizinho] = tentativo
                f = tentativo + heuristica(vizinho, destino)
                contador += 1
                heapq.heappush(fronteira, (f, contador, vizinho))

    return ResultadoBusca(
        caminho=[],
        custo=float("inf"),
        nos_expandidos=nos_expandidos,
        alcancavel=False,
    )


def _reconstruir(
    veio_de: dict[Celula, Celula | None], destino: Celula
) -> list[Celula]:
    """Reconstrói o caminho do sucessor da origem até o destino.

    Args:
        veio_de: Mapa de predecessores.
        destino: Nó objetivo alcançado.

    Returns:
        Lista ordenada de células a percorrer (sem a origem).
    """
    caminho: list[Celula] = []
    atual: Celula | None = destino
    while atual is not None and veio_de.get(atual) is not None:
        caminho.append(atual)
        atual = veio_de[atual]
    caminho.reverse()
    return caminho


def custo_bateria(
    arena: Arena,
    origem: Celula,
    destino: Celula,
    custo_normal: int,
    custo_armadilha: int,
) -> float:
    """Bateria gasta para ir de origem até destino pelo caminho do A*."""
    resultado=buscar_caminho(arena, origem, destino)
    if not resultado.alcancavel:
        return float("inf")
    total = 0
    for celula in resultado.caminho:
        if celula in arena.armadilhas:
            total+= custo_armadilha
        else:
            total += custo_normal
    return total
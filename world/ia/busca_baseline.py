"""
Busca de caminho sem heurística (baseline experimental).

BFS trata cada aresta com custo unitário uniforme na topologia, ignorando
o custo assimétrico de armadilhas e sem h(n). Serve para contraste com A*.
"""

from __future__ import annotations

from collections import deque

from core.arena import Arena, Celula

from ia.navegacao import ResultadoBusca


def buscar_caminho_bfs(
    arena: Arena,
    origem: Celula,
    destino: Celula,
) -> ResultadoBusca:
    """Busca em largura (sem heurística) até o destino.

    Args:
        arena: Ambiente corrente.
        origem: Posição inicial.
        destino: Célula objetivo.

    Returns:
        Resultado análogo ao A*, com custo = comprimento do caminho em passos.
    """
    if origem == destino:
        return ResultadoBusca(caminho=[], custo=0, nos_expandidos=0, alcancavel=True)

    if not arena.eh_livre(destino):
        return ResultadoBusca(
            caminho=[], custo=float("inf"), nos_expandidos=0, alcancavel=False
        )

    fila: deque[Celula] = deque([origem])
    veio_de: dict[Celula, Celula | None] = {origem: None}
    nos_expandidos = 0

    while fila:
        atual = fila.popleft()
        nos_expandidos += 1
        if atual == destino:
            caminho: list[Celula] = []
            no: Celula | None = destino
            while no is not None and veio_de.get(no) is not None:
                caminho.append(no)
                no = veio_de[no]
            caminho.reverse()
            return ResultadoBusca(
                caminho=caminho,
                custo=float(len(caminho)),
                nos_expandidos=nos_expandidos,
                alcancavel=True,
            )
        for vizinho in arena.vizinhos_validos(atual):
            if vizinho not in veio_de:
                veio_de[vizinho] = atual
                fila.append(vizinho)

    return ResultadoBusca(
        caminho=[],
        custo=float("inf"),
        nos_expandidos=nos_expandidos,
        alcancavel=False,
    )

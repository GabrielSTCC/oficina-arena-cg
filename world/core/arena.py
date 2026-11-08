"""
Ambiente espacial da arena: geração aleatória e consultas de vizinhança.

Responsabilidade: modelar o mundo discreto (paredes, armadilhas, minérios)
sem embutir lógica de decisão dos agentes.
"""

from __future__ import annotations

import random
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field

import config

Celula = tuple[int, int]


@dataclass(frozen=True)
class Minerio:
    """Minério posicionado em uma célula da arena.

    Attributes:
        tipo: Nome simbólico (diamante, rubi, ouro, prata, bronze).
        valor: Pontuação obtida ao coletar.
    """

    tipo: str
    valor: int


@dataclass
class Arena:
    """Grade retangular com obstáculos e recursos.

    Attributes:
        largura: Número de colunas.
        altura: Número de linhas.
        paredes: Células intransponíveis.
        armadilhas: Células transitáveis com custo dobrado.
        minerios: Mapa posição → minério.
        seed: Semente usada na geração (reprodutibilidade).
    """

    largura: int = config.LARGURA_GRADE
    altura: int = config.ALTURA_GRADE
    paredes: set[Celula] = field(default_factory=set)
    armadilhas: set[Celula] = field(default_factory=set)
    minerios: dict[Celula, Minerio] = field(default_factory=dict)
    seed: int | None = None

    def dentro_limites(self, celula: Celula) -> bool:
        """Verifica se a célula está dentro da grade.

        Args:
            celula: Coordenada (x, y).

        Returns:
            True se a célula é válida geometricamente.
        """
        x, y = celula
        return 0 <= x < self.largura and 0 <= y < self.altura

    def eh_livre(self, celula: Celula) -> bool:
        """Indica se a célula pode ser ocupada por um robô.

        Args:
            celula: Coordenada (x, y).

        Returns:
            True se está nos limites e não é parede.
        """
        return self.dentro_limites(celula) and celula not in self.paredes

    def custo_aresta(self, destino: Celula) -> int:
        """Custo de entrar em ``destino`` no grafo de busca.

        Args:
            destino: Célula de chegada do passo.

        Returns:
            2 se armadilha, 1 caso contrário.
        """
        if destino in self.armadilhas:
            return config.CUSTO_ARESTA_ARMADILHA
        return config.CUSTO_ARESTA_NORMAL

    def vizinhos_validos(self, celula: Celula) -> list[Celula]:
        """Retorna a vizinhança-4 transitável.

        Args:
            celula: Célula de origem.

        Returns:
            Lista de vizinhos ortogonais sem paredes nem fora da grade.
        """
        x, y = celula
        candidatos = ((x, y - 1), (x, y + 1), (x - 1, y), (x + 1, y))
        return [v for v in candidatos if self.eh_livre(v)]

    def remover_minerio(self, celula: Celula) -> Minerio | None:
        """Remove e devolve o minério na célula, se existir.

        Args:
            celula: Posição do minério.

        Returns:
            O minério removido ou None.
        """
        return self.minerios.pop(celula, None)

    def celulas_protegidas(self) -> set[Celula]:
        """Células das bases e duas vizinhas ortogonais de cada uma.

        Returns:
            Conjunto de células que nunca recebem parede/armadilha/minério.
        """
        return {
            config.BASE_ALFA,
            (1, 0),
            (0, 1),
            config.BASE_BETA,
            (config.LARGURA_GRADE - 2, config.ALTURA_GRADE - 1),
            (config.LARGURA_GRADE - 1, config.ALTURA_GRADE - 2),
        }

    def componente_conexa(self, origem: Celula) -> set[Celula]:
        """BFS das células transitáveis alcançáveis a partir de ``origem``.

        Args:
            origem: Célula inicial (em geral uma base).

        Returns:
            Conjunto de células livres na mesma componente; vazio se origem
            não for livre.
        """
        if not self.eh_livre(origem):
            return set()
        visto: set[Celula] = {origem}
        fila: deque[Celula] = deque([origem])
        while fila:
            atual = fila.popleft()
            for vizinho in self.vizinhos_validos(atual):
                if vizinho not in visto:
                    visto.add(vizinho)
                    fila.append(vizinho)
        return visto


def _bases_conectadas(arena: Arena) -> bool:
    """True se Alfa e Beta estão na mesma componente conexa."""
    return config.BASE_BETA in arena.componente_conexa(config.BASE_ALFA)


def gerar_arena(
    largura: int = config.LARGURA_GRADE,
    altura: int = config.ALTURA_GRADE,
    n_paredes: int = config.NUM_PAREDES,
    n_minerios: int = config.NUM_MINERIOS,
    n_armadilhas: int = config.NUM_ARMADILHAS,
    seed: int | None = None,
) -> Arena:
    """Sorteia a arena preservando as células protegidas das bases.

    Garante que as duas bases fiquem na mesma componente conexa e que todo
    minério seja alcançável a partir delas (evita robô isolado sem alvo).

    Args:
        largura: Colunas da grade.
        altura: Linhas da grade.
        n_paredes: Quantidade de paredes.
        n_minerios: Quantidade de minérios.
        n_armadilhas: Quantidade de armadilhas.
        seed: Semente do gerador pseudoaleatório.

    Returns:
        Instância de ``Arena`` preenchida.
    """
    rng = random.Random(seed)
    arena = Arena(largura=largura, altura=altura, seed=seed)
    protegidas = set(arena.celulas_protegidas())
    max_tentativas = 250

    def _sortear_em(candidatos: list[Celula], ocupadas: set[Celula]) -> Celula:
        livres = [c for c in candidatos if c not in ocupadas]
        if not livres:
            raise RuntimeError("sem células livres para colocar elemento")
        return rng.choice(livres)

    # Paredes: regenera até as bases permanecerem conectadas.
    todas = [(x, y) for y in range(altura) for x in range(largura)]
    paredes_ok = False
    for _ in range(max_tentativas):
        arena.paredes.clear()
        ocupadas = set(protegidas)
        for _ in range(n_paredes):
            c = _sortear_em(todas, ocupadas)
            arena.paredes.add(c)
            ocupadas.add(c)
        if _bases_conectadas(arena):
            paredes_ok = True
            break

    if not paredes_ok:
        # Último recurso: menos paredes até conectar (mapa jogável).
        arena.paredes.clear()
        ocupadas = set(protegidas)
        for c in rng.sample(
            [c for c in todas if c not in ocupadas],
            k=min(n_paredes, max(0, largura * altura - len(ocupadas) - 1)),
        ):
            arena.paredes.add(c)
            ocupadas.add(c)
            if not _bases_conectadas(arena):
                arena.paredes.discard(c)
                ocupadas.discard(c)

    ocupadas = set(protegidas) | set(arena.paredes)
    alcancaveis = sorted(arena.componente_conexa(config.BASE_ALFA))

    for _ in range(n_armadilhas):
        c = _sortear_em(alcancaveis, ocupadas)
        arena.armadilhas.add(c)
        ocupadas.add(c)

    tipos = list(config.VALORES_MINERIO.items())
    for _ in range(n_minerios):
        c = _sortear_em(alcancaveis, ocupadas)
        tipo, valor = rng.choice(tipos)
        arena.minerios[c] = Minerio(tipo=tipo, valor=valor)
        ocupadas.add(c)

    return arena


def celulas_livres(arena: Arena) -> Iterable[Celula]:
    """Itera sobre todas as células transitáveis da arena.

    Args:
        arena: Ambiente corrente.

    Yields:
        Coordenadas livres (sem parede).
    """
    for y in range(arena.altura):
        for x in range(arena.largura):
            c = (x, y)
            if arena.eh_livre(c):
                yield c

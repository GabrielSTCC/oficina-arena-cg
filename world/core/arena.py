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

    @property
    def peso(self) -> int:
        """Espaços de carga ocupados (diamante = 2; demais = 1)."""
        return int(config.PESO_MINERIO.get(self.tipo, 1))


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

    @property
    def base_alfa(self) -> Celula:
        return config.BASE_ALFA

    @property
    def base_beta(self) -> Celula:
        return (self.largura - 1, self.altura - 1)

    def dentro_limites(self, celula: Celula) -> bool:
        """Verifica se a célula está dentro da grade."""
        x, y = celula
        return 0 <= x < self.largura and 0 <= y < self.altura

    def eh_livre(self, celula: Celula) -> bool:
        """Indica se a célula pode ser ocupada por um robô."""
        return self.dentro_limites(celula) and celula not in self.paredes

    def custo_aresta(self, destino: Celula) -> int:
        """Custo de entrar em ``destino`` no grafo de busca."""
        if destino in self.armadilhas:
            return config.CUSTO_ARESTA_ARMADILHA
        return config.CUSTO_ARESTA_NORMAL

    def vizinhos_validos(self, celula: Celula) -> list[Celula]:
        """Retorna a vizinhança-4 transitável."""
        x, y = celula
        candidatos = ((x, y - 1), (x, y + 1), (x - 1, y), (x + 1, y))
        return [v for v in candidatos if self.eh_livre(v)]

    def remover_minerio(self, celula: Celula) -> Minerio | None:
        """Remove e devolve o minério na célula, se existir."""
        return self.minerios.pop(celula, None)

    def celulas_protegidas(self) -> set[Celula]:
        """Células das bases e duas vizinhas ortogonais de cada uma."""
        bx, by = self.base_beta
        return {
            self.base_alfa,
            (1, 0),
            (0, 1),
            self.base_beta,
            (bx - 1, by),
            (bx, by - 1),
        }

    def componente_conexa(self, origem: Celula) -> set[Celula]:
        """BFS das células transitáveis alcançáveis a partir de ``origem``."""
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
    return arena.base_beta in arena.componente_conexa(arena.base_alfa)


def _distancias_bfs(arena: Arena, origem: Celula) -> dict[Celula, int]:
    """Distância em passos (BFS) de ``origem`` até cada célula livre alcançável."""
    if not arena.eh_livre(origem):
        return {}
    dist: dict[Celula, int] = {origem: 0}
    fila: deque[Celula] = deque([origem])
    while fila:
        atual = fila.popleft()
        d = dist[atual]
        for vizinho in arena.vizinhos_validos(atual):
            if vizinho not in dist:
                dist[vizinho] = d + 1
                fila.append(vizinho)
    return dist


def _sortear_em(
    rng: random.Random, candidatos: list[Celula], ocupadas: set[Celula]
) -> Celula | None:
    livres = [c for c in candidatos if c not in ocupadas]
    if not livres:
        return None
    return rng.choice(livres)


def _colocar_aleatorio(
    arena: Arena,
    rng: random.Random,
    alcancaveis: list[Celula],
    ocupadas: set[Celula],
    tipo: str,
) -> bool:
    """Coloca 1 minério aleatório; retorna False se a arena estiver lotada."""
    c = _sortear_em(rng, alcancaveis, ocupadas)
    if c is None:
        return False
    arena.minerios[c] = Minerio(tipo=tipo, valor=config.VALORES_MINERIO[tipo])
    ocupadas.add(c)
    return True


def _faixa_perto(largura: int, altura: int) -> tuple[int, int]:
    """Distância BFS mínima e máxima do par perto das bases."""
    k_min = max(4, (largura + altura) // 8)
    raio = max(k_min + 2, (largura + altura) // 5)
    return k_min, raio


def _colocar_perto_par(
    arena: Arena,
    rng: random.Random,
    d_a: dict[Celula, int],
    d_b: dict[Celula, int],
    ocupadas: set[Celula],
    tipo: str,
    k_min: int,
    raio: int,
) -> None:
    """Coloca 1 minério perto de cada base, com a mesma distância BFS ``k``."""
    valor = config.VALORES_MINERIO[tipo]
    candidatos_k = [
        k
        for k in range(k_min, raio + 1)
        if any(d == k and c not in ocupadas for c, d in d_a.items())
        and any(d == k and c not in ocupadas for c, d in d_b.items())
    ]
    def _coloca(dist_map: dict[Celula, int], k: int) -> bool:
        c = _sortear_em(rng, [c for c, d in dist_map.items() if d == k], ocupadas)
        if c is None:
            return False
        arena.minerios[c] = Minerio(tipo=tipo, valor=valor)
        ocupadas.add(c)
        return True

    if candidatos_k:
        k = rng.choice(candidatos_k)
        _coloca(d_a, k)
        _coloca(d_b, k)
        return

    # Fallback: menor k compartilhado ainda >= k_min (mapa lotado)
    comum = {
        d
        for c, d in d_a.items()
        if d >= k_min and c not in ocupadas and any(
            db == d and cb not in ocupadas for cb, db in d_b.items()
        )
    }
    if comum:
        k = min(comum)
        _coloca(d_a, k)
        _coloca(d_b, k)
        return

    # Último recurso: célula livre mais próxima de cada base com d >= k_min
    for dist_map in (d_a, d_b):
        livres = [(d, c) for c, d in dist_map.items() if c not in ocupadas and d >= k_min]
        if not livres:
            continue
        livres.sort()
        d_min = livres[0][0]
        pool = [c for d, c in livres if d == d_min]
        c = rng.choice(pool)
        arena.minerios[c] = Minerio(tipo=tipo, valor=valor)
        ocupadas.add(c)


def _colocar_diamante_meio(
    arena: Arena,
    rng: random.Random,
    d_a: dict[Celula, int],
    d_b: dict[Celula, int],
    ocupadas: set[Celula],
) -> None:
    """Coloca 1 diamante equidistante (|dA-dB|<=1), preferindo o centro da grade."""
    valor = config.VALORES_MINERIO["diamante"]
    cx, cz = (arena.largura - 1) * 0.5, (arena.altura - 1) * 0.5
    equi = [
        c
        for c in d_a
        if c in d_b and c not in ocupadas and abs(d_a[c] - d_b[c]) <= 1 and d_a[c] >= 1
    ]
    if equi:
        equi.sort(key=lambda c: (c[0] - cx) ** 2 + (c[1] - cz) ** 2)
        # entre as mais próximas do centro (top 25% ou no máx. 8), sorteia
        n = max(1, min(8, max(1, len(equi) // 4)))
        c = rng.choice(equi[:n])
        arena.minerios[c] = Minerio(tipo="diamante", valor=valor)
        ocupadas.add(c)
        return

    # Fallback: minimiza |dA-dB| e depois distância ao centro
    livres = [c for c in d_a if c in d_b and c not in ocupadas and d_a[c] >= 1]
    if not livres:
        return
    livres.sort(
        key=lambda c: (
            abs(d_a[c] - d_b[c]),
            (c[0] - cx) ** 2 + (c[1] - cz) ** 2,
        )
    )
    c = livres[0]
    arena.minerios[c] = Minerio(tipo="diamante", valor=valor)
    ocupadas.add(c)


def gerar_arena(
    largura: int = config.LARGURA_GRADE,
    altura: int = config.ALTURA_GRADE,
    n_paredes: int = config.NUM_PAREDES,
    n_armadilhas: int = config.NUM_ARMADILHAS,
    quantidades: dict[str, int] | None = None,
    seed: int | None = None,
) -> Arena:
    """Sorteia a arena preservando as células protegidas das bases.

    ``quantidades`` define a contagem exata por tipo. Diamantes: 1 par perto
    das bases + resto no meio. Rubis: 1 par perto + resto aleatório.
    Ouro/prata/bronze: todos aleatórios. Arena lotada interrompe a colocação.
    """
    qtd = dict(config.MIN_MINERIO if quantidades is None else quantidades)
    rng = random.Random(seed)
    arena = Arena(largura=largura, altura=altura, seed=seed)
    protegidas = set(arena.celulas_protegidas())
    max_tentativas = 250

    # Paredes: regenera até as bases permanecerem conectadas.
    todas = [(x, y) for y in range(altura) for x in range(largura)]
    paredes_ok = False
    for _ in range(max_tentativas):
        arena.paredes.clear()
        ocupadas = set(protegidas)
        ok = True
        for _ in range(n_paredes):
            c = _sortear_em(rng, todas, ocupadas)
            if c is None:
                ok = False
                break
            arena.paredes.add(c)
            ocupadas.add(c)
        if ok and _bases_conectadas(arena):
            paredes_ok = True
            break

    if not paredes_ok:
        arena.paredes.clear()
        ocupadas = set(protegidas)
        livres = [c for c in todas if c not in ocupadas]
        for c in rng.sample(livres, k=min(n_paredes, len(livres))):
            arena.paredes.add(c)
            ocupadas.add(c)
            if not _bases_conectadas(arena):
                arena.paredes.discard(c)
                ocupadas.discard(c)

    ocupadas = set(protegidas) | set(arena.paredes)
    alcancaveis = sorted(arena.componente_conexa(arena.base_alfa))

    for _ in range(n_armadilhas):
        c = _sortear_em(rng, alcancaveis, ocupadas)
        if c is None:
            break
        arena.armadilhas.add(c)
        ocupadas.add(c)

    d_a = _distancias_bfs(arena, arena.base_alfa)
    d_b = _distancias_bfs(arena, arena.base_beta)
    k_min, raio = _faixa_perto(largura, altura)

    # Diamantes: par perto das bases + restantes no meio
    n_dia = max(0, int(qtd.get("diamante", 0)))
    if n_dia >= 2:
        _colocar_perto_par(arena, rng, d_a, d_b, ocupadas, "diamante", k_min, raio)
    while sum(1 for m in arena.minerios.values() if m.tipo == "diamante") < n_dia:
        antes = len(arena.minerios)
        _colocar_diamante_meio(arena, rng, d_a, d_b, ocupadas)
        if len(arena.minerios) == antes:
            break

    # Rubis: par perto + restantes aleatórios
    n_rub = max(0, int(qtd.get("rubi", 0)))
    if n_rub >= 2:
        _colocar_perto_par(arena, rng, d_a, d_b, ocupadas, "rubi", k_min, raio)
    while sum(1 for m in arena.minerios.values() if m.tipo == "rubi") < n_rub:
        if not _colocar_aleatorio(arena, rng, alcancaveis, ocupadas, "rubi"):
            break

    # Ouro / prata / bronze: todos aleatórios
    for tipo in ("ouro", "prata", "bronze"):
        n = max(0, int(qtd.get(tipo, 0)))
        for _ in range(n):
            if not _colocar_aleatorio(arena, rng, alcancaveis, ocupadas, tipo):
                break

    return arena


def celulas_livres(arena: Arena) -> Iterable[Celula]:
    """Itera sobre todas as células transitáveis da arena."""
    for y in range(arena.altura):
        for x in range(arena.largura):
            c = (x, y)
            if arena.eh_livre(c):
                yield c

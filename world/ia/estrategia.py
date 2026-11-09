"""
Estratégia competitiva: Minimax recursivo com poda alfa-beta.

O espaço de ações abstrai a escolha de minério (ou retorno à base), respeitando
o limite de 3 minérios por viagem (CAPACIDADE_CARGA) e a bateria necessária
para percorrer a rota até o minério e retornar à base.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import config
from core.arena import Arena, Celula, Minerio

from ia.heuristicas import manhattan
from ia.navegacao import buscar_caminho, custo_bateria


@dataclass
class ContadoresMinimax:
    """Acumuladores para experimentos de poda."""

    nos_avaliados: int = 0
    podas: int = 0

    def reset(self) -> None:
        """Zera os contadores."""
        self.nos_avaliados = 0
        podas = 0
        self.podas = podas


@dataclass(frozen=True)
class EstadoEstrategico:
    """Estado abstrato para a árvore Minimax (soma zero)."""

    pos_max: Celula
    pos_min: Celula
    pts_max: int
    pts_min: int
    minerios: dict[Celula, Minerio]
    carga_max: int
    carga_min: int
    base_max: Celula
    base_min: Celula
    bat_max: int = config.BATERIA_INICIAL
    bat_min: int = config.BATERIA_INICIAL


@dataclass
class ContextoBusca:
    """Parâmetros compartilhados na recursão Minimax."""

    arena: Arena
    profundidade_max: int = config.PROFUNDIDADE_MINIMAX
    usar_poda: bool = True
    contadores: ContadoresMinimax = field(default_factory=ContadoresMinimax)
    descartados: set[Celula] = field(default_factory=set)
    custo_armadilha: int = config.CUSTO_PASSO_ARMADILHA
    bateria_maxima: int = config.BATERIA_INICIAL
    peso_valor: float = config.PESO_VALOR_MINERIO
    peso_dist: float = config.PESO_VANTAGEM_DISTANCIA
    cache_dist: dict[tuple[Celula, Celula], float] = field(default_factory=dict)
    cache_bat: dict[tuple[Celula, Celula], float] = field(default_factory=dict)


def avaliar(estado: EstadoEstrategico, ctx: ContextoBusca) -> float:
    """Função de avaliação para cortes de profundidade."""
    utilidade = float(estado.pts_max - estado.pts_min)
    if not estado.minerios:
        return utilidade

    melhor_extra = float("-inf")
    for pos, minerio in estado.minerios.items():
        if pos in ctx.descartados:
            continue
        d_max = manhattan(estado.pos_max, pos)
        d_min = manhattan(estado.pos_min, pos)
        extra = (
            ctx.peso_valor * minerio.valor
            + ctx.peso_dist * (d_min - d_max)
        )
        melhor_extra = max(melhor_extra, extra)
    if melhor_extra == float("-inf"):
        return utilidade
    return utilidade + melhor_extra


def _distancia(
    ctx: ContextoBusca,
    origem: Celula,
    destino: Celula,
    ply_restante: int,
) -> float:
    """Estima distância: A* (com cache) nos plies rasos, Manhattan nos profundos."""
    if origem == destino:
        return 0.0
    profundidade_consumida = ctx.profundidade_max - ply_restante
    if profundidade_consumida <= 1:
        chave = (origem, destino)
        if chave in ctx.cache_dist:
            return ctx.cache_dist[chave]
        res = buscar_caminho(ctx.arena, origem, destino)
        val = float(res.custo) if res.alcancavel else float("inf")
        ctx.cache_dist[chave] = val
        return val
    return float(manhattan(origem, destino))


def _gasto_bateria(
    ctx: ContextoBusca,
    origem: Celula,
    destino: Celula,
    ply_restante: int,
) -> float:
    """Custo real de bateria (A* com cache) nos plies rasos, estimativa nos profundos."""
    if origem == destino:
        return 0.0
    profundidade_consumida = ctx.profundidade_max - ply_restante
    if profundidade_consumida <= 1:
        chave = (origem, destino)
        if chave in ctx.cache_bat:
            return ctx.cache_bat[chave]
        val = custo_bateria(
            ctx.arena,
            origem,
            destino,
            config.CUSTO_PASSO_NORMAL,
            ctx.custo_armadilha,
        )
        ctx.cache_bat[chave] = val
        return val
    return float(manhattan(origem, destino) * config.CUSTO_PASSO_NORMAL)


def _acoes(
    estado: EstadoEstrategico,
    maximizando: bool,
    ctx: ContextoBusca,
    ply_restante: int,
) -> list[Celula]:
    """Gera ações candidatas respeitando máximo de 3 minérios e bateria p/ voltar."""
    pos = estado.pos_max if maximizando else estado.pos_min
    base = estado.base_max if maximizando else estado.base_min
    carga = estado.carga_max if maximizando else estado.carga_min
    bat = estado.bat_max if maximizando else estado.bat_min

    if carga >= config.CAPACIDADE_CARGA:
        return [base] if pos != base else []

    candidatos: list[Celula] = []
    for mpos, minerio in estado.minerios.items():
        if mpos in ctx.descartados:
            continue
        if carga + minerio.peso > config.CAPACIDADE_CARGA:
            continue
        ida = _gasto_bateria(ctx, pos, mpos, ply_restante)
        if ida == float("inf"):
            continue
        volta = _gasto_bateria(ctx, mpos, base, ply_restante)
        if bat < ida + volta:
            continue
        candidatos.append(mpos)

    if carga > 0 and pos != base:
        candidatos.append(base)

    if not candidatos and pos != base and (carga > 0 or bat < ctx.bateria_maxima):
        return [base]
    return candidatos


def _aplicar(
    estado: EstadoEstrategico,
    alvo: Celula,
    maximizando: bool,
    ctx: ContextoBusca,
    ply_restante: int,
) -> EstadoEstrategico | None:
    """Aplica a ação abstrata (ir ao alvo e coletar até 3 minérios / descarregar)."""
    if maximizando:
        pos, base = estado.pos_max, estado.base_max
        pts, carga, bat = estado.pts_max, estado.carga_max, estado.bat_max
        pos_inimigo = estado.pos_min
        pts_inimigo, carga_inimigo, bat_inimigo = (
            estado.pts_min,
            estado.carga_min,
            estado.bat_min,
        )
    else:
        pos, base = estado.pos_min, estado.base_min
        pts, carga, bat = estado.pts_min, estado.carga_min, estado.bat_min
        pos_inimigo = estado.pos_max
        pts_inimigo, carga_inimigo, bat_inimigo = (
            estado.pts_max,
            estado.carga_max,
            estado.bat_max,
        )

    dist = _distancia(ctx, pos, alvo, ply_restante)
    if dist == float("inf"):
        return None

    novos_minerios = dict(estado.minerios)
    nova_carga = carga
    novos_pts = pts
    novos_pts_inimigo = pts_inimigo
    nova_carga_inimigo = carga_inimigo

    if alvo == base:
        if carga > 0:
            novos_pts += carga * config.BONUS_ENTREGA
            nova_carga = 0
        nova_pos = base
        nova_bat = ctx.bateria_maxima
    else:
        minerio = novos_minerios.pop(alvo, None)
        if minerio is None:
            return None
        dist_inimigo = _distancia(ctx, pos_inimigo, alvo, ply_restante)
        adversario_chega_antes = (
            dist_inimigo < dist
            and carga_inimigo + minerio.peso <= config.CAPACIDADE_CARGA
        )
        nova_pos = alvo
        gasto = _gasto_bateria(ctx, pos, alvo, ply_restante)
        nova_bat = max(0, int(bat - gasto))
        if adversario_chega_antes:
            novos_pts_inimigo += minerio.valor
            nova_carga_inimigo = min(carga_inimigo + minerio.peso, config.CAPACIDADE_CARGA)
        else:
            novos_pts += minerio.valor
            nova_carga = min(carga + minerio.peso, config.CAPACIDADE_CARGA)

    if maximizando:
        return EstadoEstrategico(
            pos_max=nova_pos,
            pos_min=estado.pos_min,
            pts_max=novos_pts,
            pts_min=novos_pts_inimigo,
            minerios=novos_minerios,
            carga_max=nova_carga,
            carga_min=nova_carga_inimigo,
            base_max=estado.base_max,
            base_min=estado.base_min,
            bat_max=nova_bat,
            bat_min=bat_inimigo,
        )
    return EstadoEstrategico(
        pos_max=estado.pos_max,
        pos_min=nova_pos,
        pts_max=novos_pts_inimigo,
        pts_min=novos_pts,
        minerios=novos_minerios,
        carga_max=nova_carga_inimigo,
        carga_min=nova_carga,
        base_max=estado.base_max,
        base_min=estado.base_min,
        bat_max=bat_inimigo,
        bat_min=nova_bat,
    )


def _minimax(
    estado: EstadoEstrategico,
    profundidade: int,
    alfa: float,
    beta: float,
    maximizando: bool,
    ctx: ContextoBusca,
) -> float:
    """Recursão Minimax com poda alfa-beta."""
    ctx.contadores.nos_avaliados += 1

    if profundidade == 0 or not estado.minerios:
        return avaliar(estado, ctx)

    acoes = _acoes(estado, maximizando, ctx, profundidade)
    if not acoes:
        return avaliar(estado, ctx)

    if maximizando:
        melhor = float("-inf")
        for alvo in acoes:
            filho = _aplicar(estado, alvo, True, ctx, profundidade)
            if filho is None:
                continue
            valor = _minimax(filho, profundidade - 1, alfa, beta, False, ctx)
            melhor = max(melhor, valor)
            if ctx.usar_poda:
                alfa = max(alfa, melhor)
                if alfa >= beta:
                    ctx.contadores.podas += 1
                    break
        return melhor if melhor != float("-inf") else avaliar(estado, ctx)

    melhor = float("inf")
    for alvo in acoes:
        filho = _aplicar(estado, alvo, False, ctx, profundidade)
        if filho is None:
            continue
        valor = _minimax(filho, profundidade - 1, alfa, beta, True, ctx)
        melhor = min(melhor, valor)
        if ctx.usar_poda:
            beta = min(beta, melhor)
            if alfa >= beta:
                ctx.contadores.podas += 1
                break
    return melhor if melhor != float("inf") else avaliar(estado, ctx)


def escolher_alvo(
    arena: Arena,
    pos_agente: Celula,
    pos_inimigo: Celula,
    pts_agente: int,
    pts_inimigo: int,
    carga_agente: int,
    carga_inimigo: int,
    base_agente: Celula,
    base_inimigo: Celula,
    minerios: dict[Celula, Minerio],
    descartados: set[Celula],
    bateria_agente: int,
    custo_armadilha: int,
    bateria_maxima: int = config.BATERIA_INICIAL,
    forcar_base: bool = False,
    profundidade: int = config.PROFUNDIDADE_MINIMAX,
    usar_poda: bool = True,
    contadores: ContadoresMinimax | None = None,
) -> Celula | None:
    """Escolhe o próximo alvo via Minimax com poda alfa-beta."""
    if forcar_base or carga_agente >= config.CAPACIDADE_CARGA:
        if pos_agente != base_agente or carga_agente > 0:
            return base_agente
        descartados.update(minerios.keys())
        return None

    minerios_uteis = {
        p: m for p, m in minerios.items() if p not in descartados
    }
    cache_bat: dict[tuple[Celula, Celula], float] = {}
    # Pré-filtro por rota real A*:
    # 1) Se nem saindo da base com bateria_maxima o robô consegue ir e voltar, descarta já.
    # 2) Só aceita para a viagem atual se a bateria_agente cobrir ida + volta.
    viaveis: dict[Celula, Minerio] = {}
    for pos, minerio in minerios_uteis.items():
        if carga_agente + minerio.peso > config.CAPACIDADE_CARGA:
            continue
        volta = custo_bateria(arena, pos, base_agente, config.CUSTO_PASSO_NORMAL, custo_armadilha)
        cache_bat[(pos, base_agente)] = volta
        ida_base = (
            volta
            if pos_agente == base_agente
            else custo_bateria(arena, base_agente, pos, config.CUSTO_PASSO_NORMAL, custo_armadilha)
        )
        cache_bat[(base_agente, pos)] = ida_base
        if ida_base + volta > bateria_maxima:
            descartados.add(pos)
            continue

        ida = (
            ida_base
            if pos_agente == base_agente
            else custo_bateria(arena, pos_agente, pos, config.CUSTO_PASSO_NORMAL, custo_armadilha)
        )
        cache_bat[(pos_agente, pos)] = ida
        if bateria_agente >= ida + volta:
            viaveis[pos] = minerio
    minerios_uteis = viaveis

    if not minerios_uteis:
        if pos_agente != base_agente:
            # Sem minério útil (sumiu / inalcançável): volta à base em vez de ficar parado.
            return base_agente
        # Já na base: marca o que sobrou como descartado.
        descartados.update(minerios.keys())
        return None

    ctx = ContextoBusca(
        arena=arena,
        profundidade_max=profundidade,
        usar_poda=usar_poda,
        contadores=contadores or ContadoresMinimax(),
        descartados=set(descartados),
        custo_armadilha=custo_armadilha,
        bateria_maxima=bateria_maxima,
        cache_bat=cache_bat,
    )
    ctx.contadores.reset()

    raiz = EstadoEstrategico(
        pos_max=pos_agente,
        pos_min=pos_inimigo,
        pts_max=pts_agente,
        pts_min=pts_inimigo,
        minerios=dict(minerios_uteis),
        carga_max=carga_agente,
        carga_min=carga_inimigo,
        base_max=base_agente,
        base_min=base_inimigo,
        bat_max=bateria_agente,
        bat_min=bateria_maxima,
    )

    melhor_alvo: Celula | None = None
    melhor_valor = float("-inf")
    alfa, beta = float("-inf"), float("inf")

    for alvo in _acoes(raiz, True, ctx, profundidade):
        filho = _aplicar(raiz, alvo, True, ctx, profundidade)
        if filho is None:
            continue
        valor = _minimax(filho, profundidade - 1, alfa, beta, False, ctx)
        if valor > melhor_valor:
            melhor_valor = valor
            melhor_alvo = alvo
        if usar_poda and valor > alfa:
            alfa = valor

    if melhor_alvo is None:
        if pos_agente != base_agente and (carga_agente > 0 or bateria_agente < bateria_maxima):
            return base_agente
        descartados.update(minerios.keys())
        return None
    return melhor_alvo

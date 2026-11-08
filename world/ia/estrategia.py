"""
Estratégia competitiva: Minimax recursivo com poda alfa-beta.

O espaço de ações abstrai a escolha de minério (ou retorno à base). Distâncias
rasas usam A*; nós profundos usam Manhattan para conter o custo de busca.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import config
from core.arena import Arena, Celula, Minerio

from ia.heuristicas import manhattan
from ia.navegacao import buscar_caminho, custo_bateria


@dataclass
class ContadoresMinimax:
    """Acumuladores para experimentos de poda.

    Attributes:
        nos_avaliados: Nós visitados na última chamada.
        podas: Quantidade de cortes alfa-beta realizados.
    """

    nos_avaliados: int = 0
    podas: int = 0

    def reset(self) -> None:
        """Zera os contadores."""
        self.nos_avaliados = 0
        self.podas = 0


@dataclass(frozen=True)
class EstadoEstrategico:
    """Estado abstrato para a árvore Minimax (soma zero).

    Attributes:
        pos_max: Posição do jogador maximizador (agente da vez na raiz).
        pos_min: Posição do adversário.
        pts_max: Pontuação do maximizador.
        pts_min: Pontuação do minimizador.
        minerios: Mapa restante de minérios.
        carga_max: Carga atual do maximizador.
        carga_min: Carga atual do minimizador.
        base_max: Base do maximizador.
        base_min: Base do minimizador.
    """

    pos_max: Celula
    pos_min: Celula
    pts_max: int
    pts_min: int
    minerios: dict[Celula, Minerio]
    carga_max: int
    carga_min: int
    base_max: Celula
    base_min: Celula


@dataclass
class ContextoBusca:
    """Parâmetros compartilhados na recursão Minimax.

    Attributes:
        arena: Topologia (paredes/armadilhas) para A* nos nós rasos.
        profundidade_max: Limite de plies.
        usar_poda: Se False, percorre a árvore completa (experimento).
        contadores: Estatísticas de nós/podas.
        descartados: Células já marcadas como inalcançáveis pelo agente.
        peso_valor: Peso do valor do minério na Eval.
        peso_dist: Peso da vantagem de distância na Eval.
    """

    arena: Arena
    profundidade_max: int = config.PROFUNDIDADE_MINIMAX
    usar_poda: bool = True
    contadores: ContadoresMinimax = field(default_factory=ContadoresMinimax)
    descartados: set[Celula] = field(default_factory=set)
    peso_valor: float = config.PESO_VALOR_MINERIO
    peso_dist: float = config.PESO_VANTAGEM_DISTANCIA


def avaliar(estado: EstadoEstrategico, ctx: ContextoBusca) -> float:
    """Função de avaliação para cortes de profundidade.

    Combina utilidade de soma zero com incentivo a minérios vantajosos:
    valor ponderado + vantagem de distância Manhattan sobre o adversário.

    Args:
        estado: Nó folha / corte.
        ctx: Contexto com pesos.

    Returns:
        Estimativa de utilidade do maximizador.
    """
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
    arena: Arena,
    origem: Celula,
    destino: Celula,
    ply_restante: int,
    profundidade_max: int,
) -> float:
    """Estima distância: A* nos plies rasos, Manhattan nos profundos.

    Args:
        arena: Ambiente.
        origem: Partida.
        destino: Chegada.
        ply_restante: Profundidade ainda disponível na recursão.
        profundidade_max: Limite total configurado.

    Returns:
        Custo estimado; inf se inalcançável no A* raso.
    """
    # Nós rasos: ply próximo da raiz (profundidade já consumida pequena).
    profundidade_consumida = profundidade_max - ply_restante
    if profundidade_consumida <= 1:
        res = buscar_caminho(arena, origem, destino)
        if not res.alcancavel:
            return float("inf")
        return float(res.custo)
    return float(manhattan(origem, destino))


def _acoes(
    estado: EstadoEstrategico,
    maximizando: bool,
    ctx: ContextoBusca,
    ply_restante: int,
) -> list[Celula]:
    """Gera ações candidatas: minérios restantes ou retorno à base.

    Args:
        estado: Estado corrente.
        maximizando: True se é a vez do maximizador.
        ctx: Contexto de busca.
        ply_restante: Plies restantes (para escolha A*/Manhattan).

    Returns:
        Lista de células-alvo candidatas.
    """
    pos = estado.pos_max if maximizando else estado.pos_min
    base = estado.base_max if maximizando else estado.base_min
    carga = estado.carga_max if maximizando else estado.carga_min

    if carga >= config.CAPACIDADE_CARGA:
        return [base]

    candidatos: list[Celula] = []
    for mpos in estado.minerios:
        if mpos in ctx.descartados:
            continue
        dist = _distancia(ctx.arena, pos, mpos, ply_restante, ctx.profundidade_max)
        if dist == float("inf"):
            continue
        candidatos.append(mpos)

    if carga > 0:
        candidatos.append(base)

    if not candidatos and carga > 0:
        return [base]
    return candidatos


def _aplicar(
    estado: EstadoEstrategico,
    alvo: Celula,
    maximizando: bool,
    ctx: ContextoBusca,
    ply_restante: int,
) -> EstadoEstrategico | None:
    """Aplica a ação abstrata (ir ao alvo e coletar / descarregar).

    Se os dois disputam o mesmo minério, quem está estritamente mais perto
    fica com os pontos e a carga. Empate, adversário inalcançável ou
    adversário com carga cheia: o jogador da vez coleta.

    Args:
        estado: Estado pai.
        alvo: Célula escolhida.
        maximizando: Jogador da vez.
        ctx: Contexto.
        ply_restante: Plies restantes.

    Returns:
        Novo estado ou None se a ação for inválida.
    """
    if maximizando:
        pos, base = estado.pos_max, estado.base_max
        pts, carga = estado.pts_max, estado.carga_max
        pos_inimigo = estado.pos_min
        pts_inimigo, carga_inimigo = estado.pts_min, estado.carga_min
    else:
        pos, base = estado.pos_min, estado.base_min
        pts, carga = estado.pts_min, estado.carga_min
        pos_inimigo = estado.pos_max
        pts_inimigo, carga_inimigo = estado.pts_max, estado.carga_max

    dist = _distancia(ctx.arena, pos, alvo, ply_restante, ctx.profundidade_max)
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
    else:
        minerio = novos_minerios.pop(alvo, None)
        if minerio is None:
            return None
        dist_inimigo = _distancia(
            ctx.arena, pos_inimigo, alvo, ply_restante, ctx.profundidade_max
        )
        adversario_chega_antes = (
            dist_inimigo < dist and carga_inimigo < config.CAPACIDADE_CARGA
        )
        nova_pos = alvo
        if adversario_chega_antes:
            novos_pts_inimigo += minerio.valor
            nova_carga_inimigo = min(carga_inimigo + 1, config.CAPACIDADE_CARGA)
        else:
            novos_pts += minerio.valor
            nova_carga = min(carga + 1, config.CAPACIDADE_CARGA)

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
    )


def _minimax(
    estado: EstadoEstrategico,
    profundidade: int,
    alfa: float,
    beta: float,
    maximizando: bool,
    ctx: ContextoBusca,
) -> float:
    """Recursão Minimax com poda alfa-beta opcional.

    Args:
        estado: Nó corrente.
        profundidade: Plies restantes.
        alfa: Melhor valor garantido para MAX.
        beta: Melhor valor garantido para MIN.
        maximizando: Vez de MAX.
        ctx: Contexto compartilhado.

    Returns:
        Valor utilitário do nó.
    """
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
    forcar_base: bool = False,
    profundidade: int = config.PROFUNDIDADE_MINIMAX,
    usar_poda: bool = True,
    contadores: ContadoresMinimax | None = None,
) -> Celula | None:
    """Escolhe o próximo alvo via Minimax com poda alfa-beta.

    Args:
        arena: Ambiente.
        pos_agente: Posição do robô da vez.
        pos_inimigo: Posição do oponente.
        pts_agente: Pontuação do robô da vez.
        pts_inimigo: Pontuação do oponente.
        carga_agente: Carga do robô da vez.
        carga_inimigo: Carga do oponente.
        base_agente: Base do robô da vez.
        base_inimigo: Base do oponente.
        minerios: Minérios restantes.
        descartados: Alvos inalcançáveis.
        bateria_agente: Bateria atual do robô da vez.
        custo_armadilha: Bateria gasta ao pisar em armadilha nesta partida.
        forcar_base: Se True, retorna a base (ex.: Pdescarga).
        profundidade: Profundidade em plies (padrão ≥ 4).
        usar_poda: Ativa poda alfa-beta.
        contadores: Objeto opcional para estatísticas.

    Returns:
        Célula alvo ou None se não há ação útil.
    """
    if forcar_base or carga_agente >= config.CAPACIDADE_CARGA:
        return base_agente

    minerios_uteis = {
        p: m for p, m in minerios.items() if p not in descartados
    }
    # Prioridade: só persegue minério de onde ainda dá para voltar à base.
    viaveis = {}
    for pos, minerio in minerios_uteis.items():
        ida = custo_bateria(arena, pos_agente, pos, config.CUSTO_PASSO_NORMAL, custo_armadilha)
        volta = custo_bateria(arena, pos, base_agente, config.CUSTO_PASSO_NORMAL, custo_armadilha)
        if bateria_agente > ida + volta + 2 * custo_armadilha:
            viaveis[pos] = minerio
    minerios_uteis = viaveis

    if not minerios_uteis:
        if carga_agente > 0 or bateria_agente < config.BATERIA_INICIAL:
            # Volta para descarregar/recarregar e tenta de novo com bateria cheia.
            return base_agente
        # Nem com bateria cheia dá para ir e voltar: desiste desses minérios.
        descartados.update(minerios)
        return None

    ctx = ContextoBusca(
        arena=arena,
        profundidade_max=profundidade,
        usar_poda=usar_poda,
        contadores=contadores or ContadoresMinimax(),
        descartados=set(descartados),
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
    )

    melhor_alvo: Celula | None = None
    melhor_valor = float("-inf")
    alfa, beta = float("-inf"), float("inf")

    for alvo in _acoes(raiz, True, ctx, profundidade):
        filho = _aplicar(raiz, alvo, True, ctx, profundidade)
        if filho is None:
            if alvo != base_agente:
                # Sinaliza inalcançável para o chamador via ausência de filho.
                continue
            continue
        valor = _minimax(filho, profundidade - 1, alfa, beta, False, ctx)
        if valor > melhor_valor:
            melhor_valor = valor
            melhor_alvo = alvo
        if usar_poda and valor > alfa:
            alfa = valor

    if melhor_alvo is None and carga_agente > 0:
        return base_agente
    return melhor_alvo

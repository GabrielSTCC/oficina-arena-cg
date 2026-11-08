"""
Motor da partida: ciclo decidir → navegar → atuar → validar lógica.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

import config
from ia.estrategia import ContadoresMinimax, escolher_alvo
from ia.navegacao import buscar_caminho

from core.agente import Agente
from core.arena import Arena, gerar_arena
from core.config_partida import ConfigPartida


class ResultadoPartida(Enum):
    """Desfecho possível ao terminar a partida."""

    VITORIA_ALFA = auto()
    VITORIA_BETA = auto()
    EMPATE = auto()
    EM_ANDAMENTO = auto()


@dataclass
class Partida:
    """Estado completo de uma partida Arena Bot.

    Attributes:
        arena: Mapa corrente.
        alfa: Robô azul (base 0,0).
        beta: Robô vermelho (base oposta).
        turno: Contador de turnos executados.
        contadores_ia: Estatísticas da última decisão Minimax.
        seed: Semente da arena.
    """

    arena: Arena
    alfa: Agente
    beta: Agente
    turno: int = 0
    contadores_ia: ContadoresMinimax = field(default_factory=ContadoresMinimax)
    seed: int | None = None
    cfg: ConfigPartida = field(default_factory=ConfigPartida)

    @property
    def agentes(self) -> list[Agente]:
        """Lista ordenada [Alfa, Beta]."""
        return [self.alfa, self.beta]

    def agente_da_vez(self) -> Agente:
        """Robô que age neste turno."""
        return self.agentes[self.turno % 2]

    def oponente(self) -> Agente:
        """Robô adversário do da vez."""
        return self.agentes[(self.turno + 1) % 2]

    def terminou(self) -> bool:
        """Verifica condições de fim de partida.

        Encerra quando ambos estão sem bateria, ou quando não restam minérios
        alcançáveis e nenhum robô consegue ainda entregar carga na base.

        Returns:
            True se a partida deve encerrar.
        """
        if self.alfa.bateria <= 0 and self.beta.bateria <= 0:
            return True

        ha_minerio_util = False
        if self.arena.minerios:
            minerios_candidatos = {
                p: m
                for p, m in self.arena.minerios.items()
                if p not in self.alfa.alvos_descartados
                or p not in self.beta.alvos_descartados
            }
            for pos in minerios_candidatos:
                for agente in self.agentes:
                    if agente.bateria <= 0:
                        continue
                    if pos in agente.alvos_descartados:
                        continue
                    res = buscar_caminho(self.arena, agente.posicao, pos)
                    if res.alcancavel:
                        ha_minerio_util = True
                        break
                if ha_minerio_util:
                    break

        if ha_minerio_util:
            return False

        # Sem minérios úteis: ainda há entrega possível?
        for agente in self.agentes:
            if agente.carga <= 0 or agente.bateria <= 0:
                continue
            if agente.posicao == agente.base:
                return False
            res = buscar_caminho(self.arena, agente.posicao, agente.base)
            if res.alcancavel:
                return False
        return True

    def resultado(self) -> ResultadoPartida:
        """Classifica o desfecho com base na pontuação.

        Returns:
            Enum do resultado; ``EM_ANDAMENTO`` se ainda não terminou.
        """
        if not self.terminou():
            return ResultadoPartida.EM_ANDAMENTO
        if self.alfa.pontuacao > self.beta.pontuacao:
            return ResultadoPartida.VITORIA_ALFA
        if self.beta.pontuacao > self.alfa.pontuacao:
            return ResultadoPartida.VITORIA_BETA
        return ResultadoPartida.EMPATE

    def _decidir_alvo(self, agente: Agente, inimigo: Agente) -> None:
        """Atualiza alvo via Minimax quando necessário."""
        alvo_sumiu = (
            agente.alvo is not None
            and agente.alvo != agente.base
            and agente.alvo not in self.arena.minerios
        )
        precisa_voltar = agente.precisa_retornar_base(self.arena)
        indo_para_base = agente.alvo == agente.base

        if (
            agente.alvo is not None
            and not alvo_sumiu
            and agente.caminho
            and (not precisa_voltar or indo_para_base)
        ):
            return

        forcar_base = precisa_voltar
        agente.alvo = escolher_alvo(
            arena=self.arena,
            pos_agente=agente.posicao,
            pos_inimigo=inimigo.posicao,
            pts_agente=agente.pontuacao,
            pts_inimigo=inimigo.pontuacao,
            carga_agente=agente.carga,
            carga_inimigo=inimigo.carga,
            base_agente=agente.base,
            base_inimigo=inimigo.base,
            minerios=self.arena.minerios,
            descartados=agente.alvos_descartados,
            bateria_agente=agente.bateria,
            custo_armadilha=agente.custo_armadilha,
            forcar_base=forcar_base,
            profundidade=config.PROFUNDIDADE_MINIMAX,
            usar_poda=True,
            contadores=self.contadores_ia,
        )
        agente.minimax_nos = self.contadores_ia.nos_avaliados
        agente.minimax_podas = self.contadores_ia.podas

    def _planejar_caminho(self, agente: Agente) -> bool:
        """Calcula A* até o alvo; descarta se inalcançável.

        Args:
            agente: Robô da vez.

        Returns:
            False se o alvo foi descartado e a decisão deve ser refeita.
        """
        if agente.alvo is None:
            return True
        if agente.posicao == agente.alvo:
            agente.caminho = []
            return True

        resultado = buscar_caminho(self.arena, agente.posicao, agente.alvo)
        if not resultado.alcancavel:
            if agente.alvo != agente.base:
                agente.alvos_descartados.add(agente.alvo)
            agente.alvo = None
            agente.caminho = []
            return False

        agente.caminho = list(resultado.caminho)
        agente.caminho_astar = list(resultado.caminho)
        return True

    def executar_turno(self) -> bool:
        """Executa um turno completo do agente da vez.

        Returns:
            True se a partida deve continuar; False se terminou.
        """
        if self.terminou():
            return False

        agente = self.agente_da_vez()
        inimigo = self.oponente()

        if agente.bateria <= 0:
            self.turno += 1
            return not self.terminou()

        # Evita loop infinito em alvos inalcançáveis.
        for _ in range(len(self.arena.minerios) + 3):
            self._decidir_alvo(agente, inimigo)
            if agente.alvo is None:
                break
            if self._planejar_caminho(agente):
                break

        if agente.caminho:
            proxima = agente.caminho.pop(0)
            agente.posicao = proxima
            agente.aplicar_custo_passo(
                self.arena,
                custo_armadilha=self.cfg.custo_passo_armadilha,
            )

        if agente.posicao == agente.base:
            agente.descarregar()
        else:
            if agente.tentar_coletar(self.arena):
                agente.alvo = None
                agente.caminho.clear()

        # Chegou ao alvo sem coletar (ex.: BC negou) → reavalia depois.
        if (
            agente.alvo is not None
            and agente.posicao == agente.alvo
            and agente.alvo != agente.base
        ):
            agente.alvo = None
            agente.caminho.clear()

        self.turno += 1
        return not self.terminou()


def criar_partida(
    seed: int | None = None,
    cfg: ConfigPartida | None = None,
) -> Partida:
    """Instancia arena e dois agentes prontos para jogar.

    Args:
        seed: Semente opcional para reprodutibilidade.
        cfg: Parâmetros de arena/torneio; defaults do enunciado se None.

    Returns:
        ``Partida`` inicializada.
    """
    cfg_uso = (cfg or ConfigPartida()).clonar()
    cfg_uso.normalizar()
    arena = gerar_arena(
        seed=seed,
        n_paredes=cfg_uso.num_paredes,
        n_armadilhas=cfg_uso.num_armadilhas,
        n_minerios=config.NUM_MINERIOS,
    )
    alfa = Agente(
        nome="Alfa",
        posicao=config.BASE_ALFA,
        base=config.BASE_ALFA,
        cor=config.COR_ALFA,
        custo_armadilha=cfg_uso.custo_passo_armadilha,
    )
    beta = Agente(
        nome="Beta",
        posicao=config.BASE_BETA,
        base=config.BASE_BETA,
        cor=config.COR_BETA,
        custo_armadilha=cfg_uso.custo_passo_armadilha,
    )
    return Partida(arena=arena, alfa=alfa, beta=beta, seed=seed, cfg=cfg_uso)

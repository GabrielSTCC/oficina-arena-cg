"""
Motor da partida: ciclo decidir → navegar → atuar → validar lógica.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

import config
from ia.estrategia import ContadoresMinimax, escolher_alvo
from ia.navegacao import buscar_caminho, custo_bateria

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
    """Estado completo de uma partida Arena Bot."""

    arena: Arena
    alfa: Agente
    beta: Agente
    turno: int = 0
    offset_turno: int = 0
    turnos_sem_progresso: int = 0
    contadores_ia: ContadoresMinimax = field(default_factory=ContadoresMinimax)
    seed: int | None = None
    cfg: ConfigPartida = field(default_factory=ConfigPartida)

    @property
    def agentes(self) -> list[Agente]:
        """Lista ordenada [Alfa, Beta]."""
        return [self.alfa, self.beta]

    def definir_primeiro_jogador(self, quem: str) -> None:
        """Define quem joga no turno 0 a partir do sorteio da moeda ('Alfa' ou 'Beta')."""
        self.offset_turno = 1 if quem.lower().startswith("b") else 0

    def agente_da_vez(self) -> Agente:
        """Robô que age neste turno."""
        return self.agentes[(self.turno + self.offset_turno) % 2]

    def oponente(self) -> Agente:
        """Robô adversário do da vez."""
        return self.agentes[(self.turno + self.offset_turno + 1) % 2]

    def _agente_pode_buscar_minerio(self, agente: Agente, pos: tuple[int, int]) -> bool:
        """Verifica se o agente tem bateria para coletar pos agora ou após recarregar na base."""
        if agente.bateria <= 0 or pos in agente.alvos_descartados:
            return False
        if agente.tem_bateria_para_rota(self.arena, pos):
            return True
        if agente.custo_retorno_base(self.arena) > agente.bateria:
            return False
        ida_base = custo_bateria(
            self.arena,
            agente.base,
            pos,
            config.CUSTO_PASSO_NORMAL,
            agente.custo_armadilha,
        )
        volta_base = custo_bateria(
            self.arena,
            pos,
            agente.base,
            config.CUSTO_PASSO_NORMAL,
            agente.custo_armadilha,
        )
        return (ida_base + volta_base) <= agente.bateria_maxima

    def terminou(self) -> bool:
        """Verifica condições de fim de partida."""
        if self.alfa.bateria <= 0 and self.beta.bateria <= 0:
            return True
        if self.turnos_sem_progresso >= 6:
            return True

        ha_minerio_util = False
        if self.arena.minerios:
            for pos in self.arena.minerios:
                for agente in self.agentes:
                    if self._agente_pode_buscar_minerio(agente, pos):
                        ha_minerio_util = True
                        break
                    agente.alvos_descartados.add(pos)
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
        """Classifica o desfecho com base na pontuação."""
        if not self.terminou():
            return ResultadoPartida.EM_ANDAMENTO
        if self.alfa.pontuacao > self.beta.pontuacao:
            return ResultadoPartida.VITORIA_ALFA
        if self.beta.pontuacao > self.alfa.pontuacao:
            return ResultadoPartida.VITORIA_BETA
        return ResultadoPartida.EMPATE

    def _decidir_alvo(self, agente: Agente, inimigo: Agente) -> None:
        """Atualiza alvo via Minimax validando limite de 3 minérios e bateria p/ rota A*."""
        if agente.carga >= config.CAPACIDADE_CARGA:
            agente.alvo = agente.base if agente.posicao != agente.base else None
            return

        alvo_sumiu = (
            agente.alvo is not None
            and agente.alvo != agente.base
            and agente.alvo not in self.arena.minerios
        )
        if alvo_sumiu:
            agente.caminho.clear()
            agente.caminho_astar.clear()
        precisa_voltar = (
            agente.precisa_retornar_base(self.arena)
            if (agente.posicao != agente.base or agente.carga > 0)
            else False
        )
        indo_para_base = agente.alvo == agente.base

        # Mesmo com alvo em andamento, revalida se a bateria restante ainda cobre
        # ir até esse alvo e voltar à base pela rota A*.
        rota_viavel = True
        if agente.alvo is not None and not indo_para_base and not alvo_sumiu:
            rota_viavel = agente.tem_bateria_para_rota(self.arena, agente.alvo)

        if (
            agente.alvo is not None
            and not alvo_sumiu
            and rota_viavel
            and agente.caminho
            and (not precisa_voltar or indo_para_base)
        ):
            return

        forcar_base = precisa_voltar or (agente.carga >= config.CAPACIDADE_CARGA)
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
            bateria_maxima=agente.bateria_maxima,
            forcar_base=forcar_base,
            profundidade=config.PROFUNDIDADE_MINIMAX,
            usar_poda=True,
            contadores=self.contadores_ia,
        )
        agente.minimax_nos = self.contadores_ia.nos_avaliados
        agente.minimax_podas = self.contadores_ia.podas

    def _planejar_caminho(self, agente: Agente) -> bool:
        """Calcula A* até o alvo; descarta se inalcançável."""
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
        """Executa um turno completo do agente da vez."""
        if self.terminou():
            return False

        agente = self.agente_da_vez()
        inimigo = self.oponente()

        if agente.bateria <= 0:
            agente.ultimo_evento = "SEM BATERIA!"
            self.turnos_sem_progresso += 1
            self.turno += 1
            return not self.terminou()

        progresso = False

        # Evita loop infinito em alvos inalcançáveis.
        for _ in range(len(self.arena.minerios) + 3):
            self._decidir_alvo(agente, inimigo)
            if agente.alvo is None:
                agente.caminho.clear()
                agente.caminho_astar.clear()
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
            progresso = True

        if agente.posicao == agente.base:
            carga_antes = agente.carga
            bat_antes = agente.bateria
            agente.descarregar()
            if carga_antes > 0 or bat_antes < agente.bateria_maxima:
                progresso = True
        else:
            if agente.tentar_coletar(self.arena):
                progresso = True
                if agente.carga >= config.CAPACIDADE_CARGA:
                    agente.alvo = agente.base
                    self._planejar_caminho(agente)

        # Chegou ao alvo sem coletar (ex.: BC negou) → reavalia depois.
        if (
            agente.alvo is not None
            and agente.posicao == agente.alvo
            and agente.alvo != agente.base
        ):
            agente.alvos_descartados.add(agente.alvo)
            agente.alvo = None
            agente.caminho.clear()

        if progresso:
            self.turnos_sem_progresso = 0
        else:
            self.turnos_sem_progresso += 1

        self.turno += 1
        return not self.terminou()


def criar_partida(
    seed: int | None = None,
    cfg: ConfigPartida | None = None,
) -> Partida:
    """Instancia arena e dois agentes prontos para jogar nas suas bases."""
    cfg_uso = (cfg or ConfigPartida()).clonar()
    cfg_uso.normalizar()
    arena = gerar_arena(
        seed=seed,
        largura=cfg_uso.largura,
        altura=cfg_uso.altura,
        n_paredes=cfg_uso.num_paredes,
        n_armadilhas=cfg_uso.num_armadilhas,
        quantidades=cfg_uso.quantidades_minerios,
    )
    alfa = Agente(
        nome="Alfa",
        posicao=arena.base_alfa,
        base=arena.base_alfa,
        cor=config.COR_ALFA,
        bateria=cfg_uso.bateria_inicial,
        bateria_maxima=cfg_uso.bateria_inicial,
        custo_armadilha=cfg_uso.custo_passo_armadilha,
    )
    beta = Agente(
        nome="Beta",
        posicao=arena.base_beta,
        base=arena.base_beta,
        cor=config.COR_BETA,
        bateria=cfg_uso.bateria_inicial,
        bateria_maxima=cfg_uso.bateria_inicial,
        custo_armadilha=cfg_uso.custo_passo_armadilha,
    )
    return Partida(arena=arena, alfa=alfa, beta=beta, seed=seed, cfg=cfg_uso)

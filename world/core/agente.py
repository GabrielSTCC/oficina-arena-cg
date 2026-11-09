"""
Modelo do agente robótico: estado interno e interação com a BC.

Classificação sugerida (relatório): agente baseado em utilidade / objetivos,
com modelo interno do mundo e validação lógica antes da coleta.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import config
from ia import conhecimento as kb
from ia.navegacao import custo_bateria

from core.arena import Arena, Celula, Minerio


@dataclass
class Agente:
    """Robô autônomo ou controlado por jogador com bateria, carga (máx 3) e alvo."""

    nome: str
    posicao: Celula
    base: Celula
    cor: tuple[int, int, int]
    bateria: int = config.BATERIA_INICIAL
    bateria_maxima: int = config.BATERIA_INICIAL
    carga: int = 0
    itens: int = 0
    pontuacao: int = 0
    alvo: Celula | None = None
    caminho: list[Celula] = field(default_factory=list)
    caminho_astar: list[Celula] = field(default_factory=list)
    alvos_descartados: set[Celula] = field(default_factory=set)
    bc: kb.BaseConhecimento = field(default_factory=kb.construir_base_padrao)
    custo_armadilha: int = config.CUSTO_PASSO_ARMADILHA
    regras_disparadas: list[str] = field(default_factory=list)
    status_bc: str = "Na base"
    minimax_nos: int = 0
    minimax_podas: int = 0
    ultimo_gasto_bateria: int = 0
    pisou_armadilha: bool = False
    ultimo_evento: str = "Pronto na base"

    def armadilha_adjacente(self, arena: Arena) -> bool:
        """Detecta armadilha em vizinho ortogonal."""
        x, y = self.posicao
        for v in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if v in arena.armadilhas:
                return True
        return False

    def custo_retorno_base(self, arena: Arena, origem: Celula | None = None) -> float:
        """Bateria necessária pelo caminho A* de ``origem`` (ou posição atual) até a base."""
        pos = self.posicao if origem is None else origem
        return custo_bateria(
            arena,
            pos,
            self.base,
            config.CUSTO_PASSO_NORMAL,
            self.custo_armadilha,
        )

    def tem_bateria_para_rota(self, arena: Arena, destino: Celula) -> bool:
        """Verifica se a bateria atual cobre a rota A* até ``destino`` + volta à base."""
        if destino == self.base:
            return self.custo_retorno_base(arena) <= self.bateria
        if self.carga >= config.CAPACIDADE_CARGA:
            return False
        minerio = arena.minerios.get(destino)
        if minerio is not None and self.carga + minerio.peso > config.CAPACIDADE_CARGA:
            return False
        ida = custo_bateria(
            arena,
            self.posicao,
            destino,
            config.CUSTO_PASSO_NORMAL,
            self.custo_armadilha,
        )
        volta = custo_bateria(
            arena,
            destino,
            self.base,
            config.CUSTO_PASSO_NORMAL,
            self.custo_armadilha,
        )
        return self.bateria >= ida + volta

    def fatos_observados(self, arena: Arena) -> set[str]:
        """Lê sensores e devolve símbolos proposicionais observados."""
        sobre_min = self.posicao in arena.minerios
        voltar = self.custo_retorno_base(arena)
        margem = 0 if sobre_min else config.CUSTO_PASSO_NORMAL
        return kb.observar_fatos(
            bateria=self.bateria,
            carga=self.carga,
            capacidade=config.CAPACIDADE_CARGA,
            sobre_minerio=sobre_min,
            armadilha_adjacente=self.armadilha_adjacente(arena),
            limiar_bateria=config.LIMIAR_BATERIA_SEGURA,
            bateria_para_voltar=voltar,
            margem=margem,
        )

    def tentar_coletar(self, arena: Arena) -> bool:
        """Coleta minério somente se a BC derivar ``Acoletar`` (R4) e o peso couber."""
        if self.carga >= config.CAPACIDADE_CARGA:
            self.status_bc = "Carga cheia (3/3)"
            return False

        derivados = self.bc.inferir(self.fatos_observados(arena))
        self.regras_disparadas = [
            self._texto_regra(nome, conclusao) for nome, conclusao in self.bc.ultimo_rastreio
        ]
        if kb.SIMBOLO_ACOLETAR not in derivados:
            self.status_bc = (
                "Sem minério"
                if self.posicao not in arena.minerios
                else "Sem bateria p/ rota"
            )
            return False

        candidato = arena.minerios.get(self.posicao)
        if candidato is None:
            self.status_bc = "Coleta falhou"
            return False
        if self.carga + candidato.peso > config.CAPACIDADE_CARGA:
            self.status_bc = "Sem espaço (diamante ocupa 2)"
            self.ultimo_evento = "Sem espaço p/ diamante"
            return False

        minerio: Minerio = arena.remover_minerio(self.posicao)  # type: ignore[assignment]
        if minerio is None:
            self.status_bc = "Coleta falhou"
            return False
        self.status_bc = "Coleta permitida"
        self.pontuacao += minerio.valor
        self.carga += minerio.peso
        self.itens += 1
        self.ultimo_evento = f"+{minerio.valor} pts ({minerio.tipo}) [{self.carga}/{config.CAPACIDADE_CARGA}]"
        self.alvo = self.base if self.carga >= config.CAPACIDADE_CARGA else None
        self.caminho.clear()
        self.caminho_astar.clear()
        return True

    def descarregar(self) -> None:
        """Entrega carga na base, aplica bônus por item e recarrega bateria."""
        if self.posicao != self.base:
            return
        bat_antes = self.bateria
        itens_entregues = self.itens
        self.bateria = self.bateria_maxima
        self.pisou_armadilha = False
        if itens_entregues > 0:
            bonus = itens_entregues * config.BONUS_ENTREGA
            self.pontuacao += bonus
            self.carga = 0
            self.itens = 0
            self.alvos_descartados.clear()
            self.alvo = None
            self.caminho.clear()
            self.caminho_astar.clear()
            self.ultimo_gasto_bateria = self.bateria - bat_antes
            self.ultimo_evento = f"Entrega +{bonus} pts | Vida 100%"
            self.status_bc = "Descarregou na base"
        elif bat_antes < self.bateria_maxima:
            self.alvos_descartados.clear()
            self.alvo = None
            self.caminho.clear()
            self.caminho_astar.clear()
            self.ultimo_gasto_bateria = self.bateria - bat_antes
            self.ultimo_evento = "Recarregou 100%"
            self.status_bc = "Vida recarregada"

    def executar_passo_manual(
        self,
        arena: Arena,
        destino: Celula,
        custo_armadilha: int | None = None,
    ) -> bool:
        """Executa passo de jogador humano (P1/P2) aplicando dano, coleta (máx 3) e base."""
        if self.bateria <= 0:
            self.ultimo_evento = "SEM VIDA/BATERIA!"
            self.status_bc = "Sem bateria"
            return False
        if not arena.dentro_limites(destino):
            return False
        if destino in arena.paredes:
            return False

        custo_arm = self.custo_armadilha if custo_armadilha is None else int(custo_armadilha)
        self.posicao = destino
        self.caminho.clear()
        self.caminho_astar.clear()
        self.aplicar_custo_passo(arena, custo_armadilha=custo_arm)

        if self.posicao == self.base:
            self.descarregar()
        elif self.posicao in arena.minerios:
            candidato = arena.minerios[self.posicao]
            if self.carga + candidato.peso <= config.CAPACIDADE_CARGA:
                minerio = arena.remover_minerio(self.posicao)
                if minerio is not None:
                    self.pontuacao += minerio.valor
                    self.carga += minerio.peso
                    self.itens += 1
                    self.ultimo_evento = f"+{minerio.valor} pts ({minerio.tipo}) [{self.carga}/{config.CAPACIDADE_CARGA}]"
                    self.status_bc = (
                        "Carga cheia (3/3)"
                        if self.carga >= config.CAPACIDADE_CARGA
                        else "Coletou minério"
                    )
            elif self.carga >= config.CAPACIDADE_CARGA:
                self.ultimo_evento = "Carga cheia (3/3)! Volte a base"
                self.status_bc = "Carga cheia (3/3)"
            else:
                self.ultimo_evento = "Sem espaço p/ diamante"
                self.status_bc = "Sem espaço (diamante ocupa 2)"
        else:
            self.status_bc = (
                "Carga cheia (3/3)"
                if self.carga >= config.CAPACIDADE_CARGA
                else "Em movimento"
            )
        return True

    def _texto_regra(self, nome: str, conclusao: str) -> str:
        """Converte a regra lógica em texto compreensível para o jogador."""
        mapa = {
            "R1_coleta_segura": "Coleta segura",
            "R2_carga_cheia": "Carga cheia",
            "R3_bateria_critica": "Bateria crítica",
            "R4_coletar_se_autorizado": "Coleta autorizada",
            "Pcoleta": "Permite coleta",
            "Pdescarga": "Exige retorno",
            "Acoletar": "Coletar",
        }
        regra = mapa.get(nome, nome)
        conclusao_txt = mapa.get(conclusao, conclusao)
        return f"{regra}: {conclusao_txt}"

    def precisa_retornar_base(self, arena: Arena) -> bool:
        """Consulta a BC para decidir se o retorno à base é obrigatório."""
        derivados = self.bc.inferir(self.fatos_observados(arena))
        self.regras_disparadas = [
            self._texto_regra(nome, conclusao) for nome, conclusao in self.bc.ultimo_rastreio
        ]
        self.status_bc = (
            "Retorno à base"
            if kb.SIMBOLO_PDESCARGA in derivados
            else "Buscando minério"
        )
        return kb.SIMBOLO_PDESCARGA in derivados

    def aplicar_custo_passo(
        self,
        arena: Arena,
        custo_armadilha: int = config.CUSTO_PASSO_ARMADILHA,
    ) -> None:
        """Debita bateria conforme o tipo da célula atual (-2 normal, -custo_armadilha armadilha)."""
        if self.posicao in arena.armadilhas:
            self.bateria = max(0, self.bateria - custo_armadilha)
            self.ultimo_gasto_bateria = -custo_armadilha
            self.pisou_armadilha = True
            self.ultimo_evento = f"ARMADILHA! -{custo_armadilha} BAT"
        else:
            self.bateria = max(0, self.bateria - config.CUSTO_PASSO_NORMAL)
            self.ultimo_gasto_bateria = -config.CUSTO_PASSO_NORMAL
            self.pisou_armadilha = False
            self.ultimo_evento = f"Passo -{config.CUSTO_PASSO_NORMAL} BAT"

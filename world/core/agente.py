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
    """Robô autônomo com bateria, carga e alvo corrente.

    Attributes:
        nome: Identificador (Alfa / Beta).
        posicao: Célula atual.
        base: Célula de descarga/recarga.
        cor: Cor RGB para a interface.
        bateria: Energia restante.
        carga: Quantidade de minérios carregados.
        pontuacao: Pontos acumulados.
        alvo: Destino estratégico atual (minério ou base).
        caminho: Fila de células restantes do A*.
        alvos_descartados: Minérios inalcançáveis já detectados.
        custo_armadilha: Bateria gasta ao pisar em armadilha nesta partida.
        bc: Base de conhecimento proposicional.
    """

    nome: str
    posicao: Celula
    base: Celula
    cor: tuple[int, int, int]
    bateria: int = config.BATERIA_INICIAL
    carga: int = 0
    pontuacao: int = 0
    alvo: Celula | None = None
    caminho: list[Celula] = field(default_factory=list)
    caminho_astar: list[Celula] = field(default_factory=list)
    alvos_descartados: set[Celula] = field(default_factory=set)
    bc: kb.BaseConhecimento = field(default_factory=kb.construir_base_padrao)
    custo_armadilha: int = config.CUSTO_PASSO_ARMADILHA
    regras_disparadas: list[str] = field(default_factory=list)
    status_bc: str = "Sem decisão"
    minimax_nos: int = 0
    minimax_podas: int = 0

    def armadilha_adjacente(self, arena: Arena) -> bool:
        """Detecta armadilha em vizinho ortogonal.

        Args:
            arena: Ambiente corrente.

        Returns:
            True se algum vizinho-4 é armadilha.
        """
        x, y = self.posicao
        for v in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if v in arena.armadilhas:
                return True
        return False

    def fatos_observados(self, arena: Arena) -> set[str]:
        """Lê sensores e devolve símbolos proposicionais observados.

        Args:
            arena: Ambiente corrente.

        Returns:
            Fatos ainda sem inferência.
        """
        return kb.observar_fatos(
            bateria=self.bateria,
            carga=self.carga,
            capacidade=config.CAPACIDADE_CARGA,
            sobre_minerio=self.posicao in arena.minerios,
            armadilha_adjacente=self.armadilha_adjacente(arena),
            limiar_bateria=config.LIMIAR_BATERIA_SEGURA,
            bateria_para_voltar=custo_bateria(arena, self.posicao, self.base, config.CUSTO_PASSO_NORMAL, self.custo_armadilha),
            margem=2 * self.custo_armadilha,
        )

    def tentar_coletar(self, arena: Arena) -> bool:
        """Coleta minério somente se a BC derivar ``Acoletar`` (R4).

        Args:
            arena: Ambiente com minérios.

        Returns:
            True se a coleta ocorreu.
        """
        derivados = self.bc.inferir(self.fatos_observados(arena))
        self.regras_disparadas = [
            self._texto_regra(nome, conclusao) for nome, conclusao in self.bc.ultimo_rastreio
        ]
        if kb.SIMBOLO_ACOLETAR not in derivados:
            self.status_bc = (
                "Sem minério"
                if self.posicao not in arena.minerios
                else "Coleta proibida"
            )
            return False

        minerio: Minerio = arena.remover_minerio(self.posicao)  # type: ignore[assignment]
        if minerio is None:
            self.status_bc = "Coleta falhou"
            return False
        self.status_bc = "Coleta permitida"
        self.pontuacao += minerio.valor
        self.carga += 1
        self.alvo = None
        self.caminho.clear()
        self.caminho_astar.clear()
        return True

    def descarregar(self) -> None:
        """Entrega carga na base, aplica bônus e recarrega bateria."""
        if self.posicao != self.base:
            return
        self.bateria = config.BATERIA_INICIAL
        if self.carga > 0:
            self.pontuacao += self.carga * config.BONUS_ENTREGA
            self.carga = 0
            self.alvos_descartados.clear()
            self.alvo = None
            self.caminho.clear()
            self.caminho_astar.clear()

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
        """Consulta a BC para decidir se o retorno à base é obrigatório.

        Args:
            arena: Ambiente corrente.

        Returns:
            True se ``Pdescarga`` foi inferido.
        """
        derivados = self.bc.inferir(self.fatos_observados(arena))
        self.regras_disparadas = [
            self._texto_regra(nome, conclusao) for nome, conclusao in self.bc.ultimo_rastreio
        ]
        self.status_bc = (
            "Retorno obrigatório"
            if kb.SIMBOLO_PDESCARGA in derivados
            else "Retorno opcional"
        )
        return kb.SIMBOLO_PDESCARGA in derivados

    def aplicar_custo_passo(
        self,
        arena: Arena,
        custo_armadilha: int = config.CUSTO_PASSO_ARMADILHA,
    ) -> None:
        """Debita bateria conforme o tipo da célula atual.

        Args:
            arena: Ambiente corrente.
            custo_armadilha: Gasto de bateria ao entrar em armadilha
                (configurável na tela de Opções; padrão do enunciado = 4).
        """
        if self.posicao in arena.armadilhas:
            self.bateria -= custo_armadilha
        else:
            self.bateria -= config.CUSTO_PASSO_NORMAL

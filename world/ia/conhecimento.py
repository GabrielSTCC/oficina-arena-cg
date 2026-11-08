"""
Base de conhecimento proposicional com encadeamento para frente.

Motor isolado da lógica de atuação: o agente apenas observa fatos e consulta
``inferir``; nenhuma coleta pode ser autorizada por ``if`` espalhado.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

# Símbolos mínimos do enunciado (Tabela 3) + derivados autorais.
SIMBOLO_BALTA = "Balta"
SIMBOLO_CCHEIA = "Ccheia"
SIMBOLO_SMINERIO = "Sminerio"
SIMBOLO_AADJ = "Aadj"
SIMBOLO_PCOLETA = "Pcoleta"
SIMBOLO_PDESCARGA = "Pdescarga"
SIMBOLO_BATERIA_CRITICA = "Bcritica"
SIMBOLO_ACOLETAR = "Acoletar"


@dataclass(frozen=True)
class Regra:
    """Cláusula definida: premissas (literais) ⇒ conclusão.

    Literais negativos são representados como ``("not", simbolo)``.

    Attributes:
        premissas: Conjunto de literais positivos ou ``("not", s)``.
        conclusao: Símbolo derivado quando as premissas valem.
        nome: Identificador legível para rastreamento no relatório.
    """

    premissas: tuple
    conclusao: str
    nome: str = ""

    def aplicavel(self, fatos: set[str]) -> bool:
        """Verifica se todas as premissas são satisfeitas pelos fatos.

        Args:
            fatos: Conjunto de símbolos verdadeiros.

        Returns:
            True se a regra pode disparar.
        """
        for lit in self.premissas:
            if isinstance(lit, tuple) and lit[0] == "not":
                if lit[1] in fatos:
                    return False
            else:
                if lit not in fatos:
                    return False
        return True


@dataclass
class BaseConhecimento:
    """Coleção de regras proposicionais e motor de inferência.

    Attributes:
        regras: Lista ordenada de cláusulas definidas.
        ultimo_rastreio: Histórico da última inferência (regra → conclusão).
        ultimos_observados: Fatos recebidos na última inferência.
    """

    regras: list[Regra] = field(default_factory=list)
    ultimo_rastreio: list[tuple[str, str]] = field(default_factory=list)
    ultimos_observados: set[str] = field(default_factory=set)

    def adicionar_regra(self, regra: Regra) -> None:
        """Inclui uma regra na base.

        Args:
            regra: Cláusula definida a registrar.
        """
        self.regras.append(regra)

    def inferir(self, fatos_observados: Iterable[str]) -> set[str]:
        """Encadeamento para frente até ponto fixo.

        Usa uma fila de fatos novos (estrutura adequada a expansão monotônica)
        em vez de recursão profunda, preservando rastreabilidade.

        Args:
            fatos_observados: Fatos sensoriados no instante atual.

        Returns:
            União dos fatos observados e dos fatos derivados.
        """
        fatos: set[str] = set(fatos_observados)
        self.ultimo_rastreio = []
        self.ultimos_observados = set(fatos_observados)
        mudou = True
        while mudou:
            mudou = False
            for regra in self.regras:
                if regra.conclusao in fatos:
                    continue
                if regra.aplicavel(fatos):
                    fatos.add(regra.conclusao)
                    self.ultimo_rastreio.append(
                        (regra.nome or regra.conclusao, regra.conclusao)
                    )
                    mudou = True
        return fatos


def construir_base_padrao() -> BaseConhecimento:
    """Monta a BC com as duas regras obrigatórias e duas autorais.

    Regras:
        1. Balta ∧ ¬Ccheia ⇒ Pcoleta
        2. Ccheia ⇒ Pdescarga
        3. Bcritica ⇒ Pdescarga (bateria insuficiente para retorno seguro)
        4. Sminerio ∧ Pcoleta ⇒ Acoletar (só coleta sobre minério e com
           coleta autorizada; encadeia a partir da R1)

    Returns:
        Base configurada e pronta para uso.
    """
    bc = BaseConhecimento()
    bc.adicionar_regra(
        Regra(
            premissas=(SIMBOLO_BALTA, ("not", SIMBOLO_CCHEIA)),
            conclusao=SIMBOLO_PCOLETA,
            nome="R1_coleta_segura",
        )
    )
    bc.adicionar_regra(
        Regra(
            premissas=(SIMBOLO_CCHEIA,),
            conclusao=SIMBOLO_PDESCARGA,
            nome="R2_carga_cheia",
        )
    )
    bc.adicionar_regra(
        Regra(
            premissas=(SIMBOLO_BATERIA_CRITICA,),
            conclusao=SIMBOLO_PDESCARGA,
            nome="R3_bateria_critica",
        )
    )
    bc.adicionar_regra(
        Regra(
            premissas=(SIMBOLO_SMINERIO, SIMBOLO_PCOLETA),
            conclusao=SIMBOLO_ACOLETAR,
            nome="R4_coletar_se_autorizado",
        )
    )
    return bc


def observar_fatos(
    *,
    bateria: int,
    carga: int,
    capacidade: int,
    sobre_minerio: bool,
    armadilha_adjacente: bool,
    limiar_bateria: int,
    bateria_para_voltar: float,
    margem: int,
) -> set[str]:
    """Traduz leituras sensoriais nos símbolos proposicionais.

    Args:
        bateria: Nível atual de bateria.
        carga: Itens carregados.
        capacidade: Capacidade máxima.
        sobre_minerio: Robô está sobre célula com minério.
        armadilha_adjacente: Existe armadilha em vizinho-4.
        limiar_bateria: Limiar de segurança (> limiar ⇒ Balta).
        bateria_para_voltar: Bateria gasta no caminho real (A*) até a base.
        margem: Folga de segurança somada ao custo da volta.

    Returns:
        Conjunto de fatos observados (ainda sem derivados).
    """
    fatos: set[str] = set()
    if bateria > limiar_bateria:
        fatos.add(SIMBOLO_BALTA)
    if carga >= capacidade:
        fatos.add(SIMBOLO_CCHEIA)
    if sobre_minerio:
        fatos.add(SIMBOLO_SMINERIO)
    if armadilha_adjacente:
        fatos.add(SIMBOLO_AADJ)
        
    # Bateria não cobre o caminho real de volta à base mais a margem.
    if bateria <= bateria_para_voltar + margem:
        fatos.add(SIMBOLO_BATERIA_CRITICA)
    return fatos

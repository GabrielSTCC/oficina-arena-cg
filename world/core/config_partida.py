"""
Configuração mutável de partida / torneio (editável na tela de Configurações).

Os defaults espelham o enunciado do PP01; o usuário pode alterar no menu.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import config

_TIPOS_ORE = ("diamante", "rubi", "ouro", "prata", "bronze")
# Ordem de corte quando a soma de minérios não cabe na grade
_CORTE_ORE = ("bronze", "prata", "ouro", "rubi", "diamante")


def _padrao_ore(tipo: str) -> int:
    return int(config.MIN_MINERIO[tipo])


@dataclass
class ConfigPartida:
    """Parâmetros de arena, vida e torneio ajustáveis pela interface."""

    num_rounds: int = 1
    num_paredes: int = config.NUM_PAREDES
    num_armadilhas: int = config.NUM_ARMADILHAS
    custo_passo_armadilha: int = config.CUSTO_PASSO_ARMADILHA
    bateria_inicial: int = config.BATERIA_INICIAL
    tamanho_idx: int = 0
    num_diamante: int = field(default_factory=lambda: _padrao_ore("diamante"))
    num_rubi: int = field(default_factory=lambda: _padrao_ore("rubi"))
    num_ouro: int = field(default_factory=lambda: _padrao_ore("ouro"))
    num_prata: int = field(default_factory=lambda: _padrao_ore("prata"))
    num_bronze: int = field(default_factory=lambda: _padrao_ore("bronze"))

    # Limites da UI
    MIN_ROUNDS: int = 1
    MAX_ROUNDS: int = 30
    MIN_PAREDES: int = 0
    MAX_PAREDES: int = 150
    MIN_ARMADILHAS: int = 0
    MAX_ARMADILHAS: int = 80
    MIN_DANO_ARMADILHA: int = 1
    MAX_DANO_ARMADILHA: int = 20
    MIN_BATERIA: int = 20
    MAX_BATERIA: int = 300

    @property
    def largura(self) -> int:
        return config.TAMANHOS_ARENA[self.tamanho_idx][0]

    @property
    def altura(self) -> int:
        return config.TAMANHOS_ARENA[self.tamanho_idx][1]

    @property
    def quantidades_minerios(self) -> dict[str, int]:
        return {
            "diamante": self.num_diamante,
            "rubi": self.num_rubi,
            "ouro": self.num_ouro,
            "prata": self.num_prata,
            "bronze": self.num_bronze,
        }

    def bateria_recomendada(self) -> int:
        """Bateria mínima para ida+volta ao canto oposto com margem."""
        d = (self.largura - 1) + (self.altura - 1)
        bruto = 2 * d * config.CUSTO_PASSO_NORMAL * config.MARGEM_BATERIA
        return int(math.ceil(bruto / 10.0) * 10)

    def min_minerio(self, tipo: str) -> int:
        """Mínimo do tipo escalado pela área da arena (piso = MIN_MINERIO)."""
        base = int(config.MIN_MINERIO[tipo])
        area_base = config.LARGURA_GRADE * config.ALTURA_GRADE
        area = self.largura * self.altura
        return max(base, int(math.ceil(base * area / area_base)))

    def clonar(self) -> ConfigPartida:
        """Cria cópia independente dos valores atuais."""
        return ConfigPartida(
            num_rounds=self.num_rounds,
            num_paredes=self.num_paredes,
            num_armadilhas=self.num_armadilhas,
            custo_passo_armadilha=self.custo_passo_armadilha,
            bateria_inicial=self.bateria_inicial,
            tamanho_idx=self.tamanho_idx,
            num_diamante=self.num_diamante,
            num_rubi=self.num_rubi,
            num_ouro=self.num_ouro,
            num_prata=self.num_prata,
            num_bronze=self.num_bronze,
        )

    def __post_init__(self) -> None:
        self.normalizar()

    def restaurar_padroes(self) -> None:
        """Volta todos os campos aos defaults."""
        self.num_rounds = 1
        self.num_paredes = config.NUM_PAREDES
        self.num_armadilhas = config.NUM_ARMADILHAS
        self.custo_passo_armadilha = config.CUSTO_PASSO_ARMADILHA
        self.bateria_inicial = config.BATERIA_INICIAL
        self.tamanho_idx = 0
        for tipo in _TIPOS_ORE:
            setattr(self, f"num_{tipo}", _padrao_ore(tipo))
        self.normalizar()

    def normalizar(self) -> None:
        """Clamp, bateria >= recomendada, corte de minérios e espaço livre."""
        n_tam = len(config.TAMANHOS_ARENA)
        self.tamanho_idx = max(0, min(n_tam - 1, self.tamanho_idx))
        self.num_rounds = max(self.MIN_ROUNDS, min(self.MAX_ROUNDS, self.num_rounds))
        self.num_paredes = max(self.MIN_PAREDES, min(self.MAX_PAREDES, self.num_paredes))
        self.num_armadilhas = max(
            self.MIN_ARMADILHAS, min(self.MAX_ARMADILHAS, self.num_armadilhas)
        )
        self.custo_passo_armadilha = max(
            self.MIN_DANO_ARMADILHA,
            min(self.MAX_DANO_ARMADILHA, self.custo_passo_armadilha),
        )
        rec = self.bateria_recomendada()
        self.bateria_inicial = max(
            rec,
            max(self.MIN_BATERIA, min(self.MAX_BATERIA, self.bateria_inicial)),
        )

        for tipo in _TIPOS_ORE:
            campo = f"num_{tipo}"
            lo = self.min_minerio(tipo)
            hi = int(config.MAX_MINERIO[tipo])
            setattr(self, campo, max(lo, min(hi, int(getattr(self, campo)))))

        protegidas = 6
        capacidade_total = self.largura * self.altura - protegidas
        soma = sum(self.quantidades_minerios.values())
        if soma > capacidade_total:
            excesso = soma - capacidade_total
            for tipo in _CORTE_ORE:
                if excesso <= 0:
                    break
                campo = f"num_{tipo}"
                atual = int(getattr(self, campo))
                lo = self.min_minerio(tipo)
                reduzivel = atual - lo
                if reduzivel <= 0:
                    continue
                corta = min(excesso, reduzivel)
                setattr(self, campo, atual - corta)
                excesso -= corta

        capacidade = capacidade_total - sum(self.quantidades_minerios.values())
        total_obs = self.num_paredes + self.num_armadilhas
        if total_obs > capacidade:
            excesso = total_obs - capacidade
            reduz_arm = min(excesso, self.num_armadilhas)
            self.num_armadilhas -= reduz_arm
            excesso -= reduz_arm
            if excesso > 0:
                self.num_paredes = max(0, self.num_paredes - excesso)

    def ajustar(self, campo: str, delta: int) -> None:
        """Incrementa ou decrementa um campo e normaliza."""
        valor = getattr(self, campo, None)
        if valor is None:
            return
        setattr(self, campo, int(valor) + delta)
        self.normalizar()

"""
Configuração mutável de partida / torneio (editável na tela de Opções).

Os defaults espelham o enunciado do PP01; o usuário só altera se quiser.
"""

from __future__ import annotations

from dataclasses import dataclass

import config


@dataclass
class ConfigPartida:
    """Parâmetros de arena e torneio ajustáveis pela interface.

    Attributes:
        num_rounds: Quantidade de partidas no torneio (1 = partida única).
        num_paredes: Paredes intransponíveis na arena.
        num_armadilhas: Células com custo extra de bateria.
        custo_passo_armadilha: Gasto de bateria ao pisar em armadilha.
    """

    num_rounds: int = 1
    num_paredes: int = config.NUM_PAREDES
    num_armadilhas: int = config.NUM_ARMADILHAS
    custo_passo_armadilha: int = config.CUSTO_PASSO_ARMADILHA

    # Limites da UI
    MIN_ROUNDS: int = 1
    MAX_ROUNDS: int = 30
    MIN_PAREDES: int = 0
    MAX_PAREDES: int = 50
    MIN_ARMADILHAS: int = 0
    MAX_ARMADILHAS: int = 20
    MIN_DANO_ARMADILHA: int = 1
    MAX_DANO_ARMADILHA: int = 20

    def clonar(self) -> ConfigPartida:
        """Cria cópia independente dos valores atuais.

        Returns:
            Nova instância com os mesmos campos.
        """
        return ConfigPartida(
            num_rounds=self.num_rounds,
            num_paredes=self.num_paredes,
            num_armadilhas=self.num_armadilhas,
            custo_passo_armadilha=self.custo_passo_armadilha,
        )

    def restaurar_padroes(self) -> None:
        """Volta todos os campos aos defaults do enunciado."""
        self.num_rounds = 1
        self.num_paredes = config.NUM_PAREDES
        self.num_armadilhas = config.NUM_ARMADILHAS
        self.custo_passo_armadilha = config.CUSTO_PASSO_ARMADILHA

    def normalizar(self) -> None:
        """Aplica clamp e garante espaço livre na grade.

        Células protegidas (6) + minérios (12) + paredes + armadilhas
        não podem exceder 15×9 = 135.
        """
        self.num_rounds = max(self.MIN_ROUNDS, min(self.MAX_ROUNDS, self.num_rounds))
        self.num_paredes = max(self.MIN_PAREDES, min(self.MAX_PAREDES, self.num_paredes))
        self.num_armadilhas = max(
            self.MIN_ARMADILHAS, min(self.MAX_ARMADILHAS, self.num_armadilhas)
        )
        self.custo_passo_armadilha = max(
            self.MIN_DANO_ARMADILHA,
            min(self.MAX_DANO_ARMADILHA, self.custo_passo_armadilha),
        )

        protegidas = 6
        minerios = config.NUM_MINERIOS
        capacidade = (
            config.LARGURA_GRADE * config.ALTURA_GRADE - protegidas - minerios
        )
        total_obs = self.num_paredes + self.num_armadilhas
        if total_obs > capacidade:
            # Reduz armadilhas primeiro, depois paredes.
            excesso = total_obs - capacidade
            reduz_arm = min(excesso, self.num_armadilhas)
            self.num_armadilhas -= reduz_arm
            excesso -= reduz_arm
            if excesso > 0:
                self.num_paredes = max(0, self.num_paredes - excesso)

    def ajustar(self, campo: str, delta: int) -> None:
        """Incrementa ou decrementa um campo e normaliza.

        Args:
            campo: Nome do atributo a alterar.
            delta: Variação (+1 / -1 tipicamente).
        """
        valor = getattr(self, campo, None)
        if valor is None:
            return
        setattr(self, campo, int(valor) + delta)
        self.normalizar()

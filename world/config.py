"""
Constantes e parâmetros do Arena Bot (PP01).

Centraliza valores obrigatórios do enunciado para facilitar experimentos
e justificativas no relatório. Variações devem ser documentadas.
"""

from __future__ import annotations

from typing import Final

# --- Arena -----------------------------------------------------------------
LARGURA_GRADE: Final[int] = 15
ALTURA_GRADE: Final[int] = 9
NUM_PAREDES: Final[int] = 25
NUM_ARMADILHAS: Final[int] = 6
NUM_MINERIOS: Final[int] = 12

BASE_ALFA: Final[tuple[int, int]] = (0, 0)
BASE_BETA: Final[tuple[int, int]] = (LARGURA_GRADE - 1, ALTURA_GRADE - 1)

# Valores de pontuação por tipo de minério (Tabela 1 do enunciado).
VALORES_MINERIO: Final[dict[str, int]] = {
    "diamante": 100,
    "rubi": 80,
    "ouro": 50,
    "prata": 30,
    "bronze": 10,
}

# --- Agente / economia -----------------------------------------------------
BATERIA_INICIAL: Final[int] = 100
CUSTO_PASSO_NORMAL: Final[int] = 2
CUSTO_PASSO_ARMADILHA: Final[int] = 4
CAPACIDADE_CARGA: Final[int] = 3
BONUS_ENTREGA: Final[int] = 10
LIMIAR_BATERIA_SEGURA: Final[int] = 10

# Custo de aresta no grafo de busca A* (não confundir com gasto de bateria).
CUSTO_ARESTA_NORMAL: Final[int] = 1
CUSTO_ARESTA_ARMADILHA: Final[int] = 2

# --- Estratégia ------------------------------------------------------------
PROFUNDIDADE_MINIMAX: Final[int] = 4
PESO_VALOR_MINERIO: Final[float] = 1.0
PESO_VANTAGEM_DISTANCIA: Final[float] = 3.0

# --- Interface Pygame ------------------------------------------------------
TAMANHO_CELULA: Final[int] = 48
ALTURA_HUD: Final[int] = 118
ALTURA_AREA: Final[int] = 180
ALTURA_BARRA_JANELA: Final[int] = 32
FPS: Final[int] = 30
DELAY_TURNO_MS: Final[int] = 180

# Controles da janela (minimizar / maximizar / fechar)
COR_BTN_MIN: Final[tuple[int, int, int]] = (70, 90, 110)
COR_BTN_MAX: Final[tuple[int, int, int]] = (70, 110, 90)
COR_BTN_FECHAR: Final[tuple[int, int, int]] = (160, 60, 60)
COR_BTN_JANELA_HOVER: Final[tuple[int, int, int]] = (255, 255, 255)

# Paleta própria (não reutiliza assets do jogo de referência).
COR_FUNDO: Final[tuple[int, int, int]] = (14, 20, 28)
COR_FUNDO_TOPO: Final[tuple[int, int, int]] = (28, 42, 58)
COR_GRADE: Final[tuple[int, int, int]] = (42, 58, 74)
COR_CHAO: Final[tuple[int, int, int]] = (48, 64, 80)
COR_CHAO_ALT: Final[tuple[int, int, int]] = (54, 72, 90)
COR_PAREDE: Final[tuple[int, int, int]] = (32, 38, 48)
COR_PAREDE_LUZ: Final[tuple[int, int, int]] = (58, 66, 78)
COR_PAREDE_SOMBRA: Final[tuple[int, int, int]] = (18, 22, 28)
COR_ARMADILHA: Final[tuple[int, int, int]] = (160, 52, 52)
COR_ALFA: Final[tuple[int, int, int]] = (72, 168, 255)
COR_BETA: Final[tuple[int, int, int]] = (240, 96, 78)
COR_TEXTO: Final[tuple[int, int, int]] = (236, 242, 248)
COR_TEXTO_SUAVE: Final[tuple[int, int, int]] = (150, 168, 188)
COR_BOTAO: Final[tuple[int, int, int]] = (36, 92, 118)
COR_BOTAO_HOVER: Final[tuple[int, int, int]] = (52, 128, 160)
COR_PAINEL: Final[tuple[int, int, int]] = (22, 32, 44)
COR_BARRA_BG: Final[tuple[int, int, int]] = (30, 40, 52)
COR_BARRA_OK: Final[tuple[int, int, int]] = (72, 190, 120)
COR_BARRA_BAIXA: Final[tuple[int, int, int]] = (230, 160, 50)
COR_BARRA_CRITICA: Final[tuple[int, int, int]] = (220, 70, 70)

CORES_MINERIO: Final[dict[str, tuple[int, int, int]]] = {
    "diamante": (120, 220, 255),
    "rubi": (220, 60, 90),
    "ouro": (240, 200, 60),
    "prata": (190, 200, 210),
    "bronze": (180, 120, 70),
}

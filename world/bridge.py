"""Espelha a grade da cena na partida Arena Bot, gerencia modos (COM/P1/P2), rounds e turnos."""

from __future__ import annotations

import random
from enum import Enum

import world  # noqa: F401 — registra sys.path para config/core/ia

import config
from core.arena import Minerio
from core.config_partida import ConfigPartida
from core.partida import Partida, ResultadoPartida, criar_partida
from scene.catalog import CellKind
from scene.workshop import Workshop

RESULT_LABELS = {
    ResultadoPartida.VITORIA_ALFA: "VITORIA ALFA",
    ResultadoPartida.VITORIA_BETA: "VITORIA BETA",
    ResultadoPartida.EMPATE: "EMPATE",
    ResultadoPartida.EM_ANDAMENTO: "EM PARTIDA",
}


class GameMode(Enum):
    COM_VS_COM = "COM vs COM"
    P1_VS_COM = "P1 vs COM"
    P1_VS_P2 = "P1 vs P2"


class WorldBridge:
    def __init__(self) -> None:
        self.cfg: ConfigPartida = ConfigPartida()
        self.mode: GameMode = GameMode.COM_VS_COM
        self.starter: str = "Alfa"
        self.round_atual: int = 1
        self.vitorias_alfa: int = 0
        self.vitorias_beta: int = 0
        self.empates: int = 0

        self.partida: Partida | None = None
        self.running = False
        self.accum = 0.0
        self.turn_interval = 0.35  # segundos por turno visual
        self.last_result: ResultadoPartida | None = None
        self.last_seed: int = 0
        # Eventos disparados no último passo: lista de (quem, delta_bateria, pisou_armadilha, texto_evento)
        self.step_events: list[tuple[str, int, bool, str]] = []

    def reset_series(self) -> None:
        """Zera contadores da série de partidas (torneio)."""
        self.round_atual = 1
        self.vitorias_alfa = 0
        self.vitorias_beta = 0
        self.empates = 0
        self.last_result = None

    def has_next_round(self) -> bool:
        return self.round_atual < self.cfg.num_rounds

    def is_human_controlled(self, who: str) -> bool:
        if who == "Alfa":
            return self.mode in (GameMode.P1_VS_COM, GameMode.P1_VS_P2)
        return self.mode == GameMode.P1_VS_P2

    def whose_turn(self) -> str:
        if self.partida is None:
            return self.starter
        ag = self.partida.agente_da_vez()
        return "Alfa" if ag is self.partida.alfa else "Beta"

    def _next_seed(self, seed: int | None = None) -> int:
        if seed is not None:
            self.last_seed = int(seed)
            return self.last_seed
        candidate = random.randrange(1, 1_000_000)
        if candidate == self.last_seed:
            candidate = (candidate + 1) % 1_000_000
        self.last_seed = candidate
        return candidate

    def seed_workshop_preview(self, workshop: Workshop, seed: int | None = None) -> Partida:
        """Gera arena aleatória (paredes, armadilhas e minérios) respeitando self.cfg."""
        s = self._next_seed(seed)
        self.partida = criar_partida(seed=s, cfg=self.cfg)
        self.partida.definir_primeiro_jogador(self.starter)
        self.partida.alfa.posicao = self.partida.alfa.base
        self.partida.beta.posicao = self.partida.beta.base
        self.last_result = None
        self.running = False
        self.accum = 0.0
        self.step_events.clear()
        workshop.seed_from_arena(self.partida.arena)
        return self.partida

    def _sync_workshop_to_arena(self, workshop: Workshop, arena) -> None:
        """Sincroniza objetos da cena para a arena preservando tipos e valores de cada minério."""
        kinds = workshop.sync_walls_to_kinds()
        arena.paredes = set(kinds["paredes"])
        arena.armadilhas = set(kinds["armadilhas"]) - arena.paredes
        bases = {arena.base_alfa, arena.base_beta}
        new_minerios: dict[tuple[int, int], Minerio] = {}
        for cell in kinds["minerios"]:
            if cell in arena.paredes or cell in arena.armadilhas:
                continue
            if cell in bases:
                continue
            obj = workshop.occupancy.get(cell)
            if obj is not None and obj.ore_tipo is not None and obj.ore_valor is not None:
                new_minerios[cell] = Minerio(tipo=obj.ore_tipo, valor=int(obj.ore_valor))
            elif cell in arena.minerios:
                new_minerios[cell] = arena.minerios[cell]
            else:
                new_minerios[cell] = Minerio(tipo="ouro", valor=50)
        arena.minerios = new_minerios
        for base in bases:
            arena.paredes.discard(base)
            arena.armadilhas.discard(base)
            arena.minerios.pop(base, None)

    def start_from_workshop(
        self,
        workshop: Workshop,
        seed: int | None = None,
        *,
        new_random_map: bool = False,
    ) -> Partida:
        """Inicia ou reinicia partida; se new_random_map=True gera novo mapa aleatório."""
        if new_random_map or self.partida is None or self.last_result is not None:
            s = self._next_seed(seed)
            self.partida = criar_partida(seed=s, cfg=self.cfg)
            if new_random_map or not workshop.has_user_placed_objects():
                workshop.seed_from_arena(self.partida.arena)
            else:
                self._sync_workshop_to_arena(workshop, self.partida.arena)
        else:
            self._sync_workshop_to_arena(workshop, self.partida.arena)

        self.partida.definir_primeiro_jogador(self.starter)
        self.last_result = None
        self.partida.alfa.posicao = self.partida.alfa.base
        self.partida.beta.posicao = self.partida.beta.base
        self.running = True
        self.accum = 0.0
        self.step_events.clear()
        workshop.editing = False
        return self.partida

    def pause(self, workshop: Workshop) -> None:
        self.running = False
        workshop.editing = False
        workshop.cancel_ghost()

    def toggle(self, workshop: Workshop) -> None:
        if self.partida is None or self.last_result is not None:
            self.start_from_workshop(workshop, new_random_map=(self.last_result is not None))
            return
        if self.partida.turno == 0 and not self.running:
            self.start_from_workshop(workshop, new_random_map=False)
            return
        if self.running:
            self.pause(workshop)
        else:
            self._sync_workshop_to_arena(workshop, self.partida.arena)
            self.running = True
            workshop.editing = False

    def _finish_match(self, workshop: Workshop | None) -> None:
        if self.partida is None or self.last_result is not None:
            return
        self.running = False
        self.last_result = self.partida.resultado()
        if self.last_result == ResultadoPartida.VITORIA_ALFA:
            self.vitorias_alfa += 1
        elif self.last_result == ResultadoPartida.VITORIA_BETA:
            self.vitorias_beta += 1
        elif self.last_result == ResultadoPartida.EMPATE:
            self.empates += 1
        if workshop is not None:
            workshop.editing = False
            workshop.cancel_ghost()

    def step_human(
        self,
        who: str,
        dx: int,
        dz: int,
        workshop: Workshop | None = None,
    ) -> bool:
        """Executa o passo de um jogador humano (P1=Alfa em WASD, P2=Beta nas Setas)."""
        if not self.running or self.partida is None or self.last_result is not None:
            return False
        if not self.is_human_controlled(who):
            return False
        if self.whose_turn() != who:
            return False

        agente = self.partida.alfa if who == "Alfa" else self.partida.beta
        nx = agente.posicao[0] + dx
        nz = agente.posicao[1] + dz
        agente.ultimo_gasto_bateria = 0
        agente.pisou_armadilha = False
        agente.ultimo_evento = ""

        moved = agente.executar_passo_manual(
            self.partida.arena,
            (nx, nz),
            custo_armadilha=self.partida.cfg.custo_passo_armadilha,
        )
        if not moved:
            return False

        if agente.ultimo_gasto_bateria != 0 or agente.ultimo_evento:
            self.step_events.append(
                (
                    who,
                    int(agente.ultimo_gasto_bateria),
                    bool(agente.pisou_armadilha),
                    agente.ultimo_evento,
                )
            )

        self.partida.turno += 1
        if workshop is not None:
            self.mirror_minerios_to_scene(workshop)

        if self.partida.terminou():
            self._finish_match(workshop)
        else:
            # Pequeno intervalo antes da resposta da IA no modo P1 vs COM
            self.accum = 0.0
        return True

    def pop_step_events(self) -> list[tuple[str, int, bool, str]]:
        events = list(self.step_events)
        self.step_events.clear()
        return events

    def update(self, dt: float, workshop: Workshop | None = None) -> bool:
        """Avança turnos da IA. Retorna True se a partida acabou neste frame."""
        if not self.running or self.partida is None:
            return False
        if self.partida.terminou():
            self._finish_match(workshop)
            return True

        agente = self.partida.agente_da_vez()
        who = "Alfa" if agente is self.partida.alfa else "Beta"

        # Se for a vez de um jogador humano com bateria, aguarda o input do teclado
        if self.is_human_controlled(who):
            if agente.bateria <= 0:
                agente.ultimo_evento = "SEM BATERIA!"
                self.partida.turno += 1
                if self.partida.terminou():
                    self._finish_match(workshop)
                    return True
            return False

        ended = False
        self.accum += dt
        while self.accum >= self.turn_interval:
            self.accum -= self.turn_interval
            agente = self.partida.agente_da_vez()
            who = "Alfa" if agente is self.partida.alfa else "Beta"
            if self.is_human_controlled(who) and agente.bateria > 0:
                break

            prev_a = self.partida.alfa.posicao
            prev_b = self.partida.beta.posicao
            agente.ultimo_gasto_bateria = 0
            agente.pisou_armadilha = False
            agente.ultimo_evento = ""

            if not self.partida.executar_turno():
                self._finish_match(workshop)
                ended = True
                break

            if agente.ultimo_gasto_bateria != 0 or agente.ultimo_evento:
                self.step_events.append(
                    (
                        who,
                        int(agente.ultimo_gasto_bateria),
                        bool(agente.pisou_armadilha),
                        agente.ultimo_evento,
                    )
                )

            base_a = self.partida.alfa.base
            base_b = self.partida.beta.base
            arrived_alfa = prev_a != base_a and self.partida.alfa.posicao == base_a
            arrived_beta = prev_b != base_b and self.partida.beta.posicao == base_b
            if agente.pisou_armadilha:
                self.accum -= 0.28
                break
            if arrived_alfa or arrived_beta:
                self.accum -= 0.45
                break
        return ended

    def robot_cells(self) -> dict[str, tuple[int, int]]:
        if not self.partida:
            return {"Alfa": config.BASE_ALFA, "Beta": config.BASE_BETA}
        return {
            "Alfa": self.partida.alfa.posicao,
            "Beta": self.partida.beta.posicao,
        }

    def robot_paths(self) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
        if not self.partida:
            return [], []
        return list(self.partida.alfa.caminho), list(self.partida.beta.caminho)

    def result_label(self) -> str:
        if self.last_result is None:
            return "EM PARTIDA"
        return RESULT_LABELS.get(self.last_result, "FIM")

    def series_summary_label(self) -> str:
        if self.vitorias_alfa > self.vitorias_beta:
            return f"CAMPEAO DA SERIE: ALFA ({self.vitorias_alfa}x{self.vitorias_beta})"
        if self.vitorias_beta > self.vitorias_alfa:
            return f"CAMPEAO DA SERIE: BETA ({self.vitorias_beta}x{self.vitorias_alfa})"
        return f"SERIE EMPATADA ({self.vitorias_alfa}x{self.vitorias_beta})"

    def hud_line(self) -> str:
        """Placar / bateria / carga / resultado para o título da janela."""
        if self.partida is None:
            return "MENU"
        a, b = self.partida.alfa, self.partida.beta
        score = (
            f"[{self.mode.value} P{self.round_atual}/{self.cfg.num_rounds}] "
            f"A {a.pontuacao}pts bat{a.bateria}/{a.bateria_maxima} c{a.carga}/{config.CAPACIDADE_CARGA} | "
            f"B {b.pontuacao}pts bat{b.bateria}/{b.bateria_maxima} c{b.carga}/{config.CAPACIDADE_CARGA} | t{self.partida.turno}"
        )
        if self.last_result is not None:
            return f"FIM {self.result_label()} | {score}"
        if self.running:
            return f"SIM | {score}"
        return f"PRONTO/PAUSA | {score}"

    def mirror_minerios_to_scene(self, workshop: Workshop) -> None:
        """Atualiza malhas de minério na cena conforme a arena (coleta remove)."""
        if not self.partida:
            return
        keep: list = []
        for o in workshop.objects:
            if o.item.cell_kind != CellKind.MINERIO:
                keep.append(o)
                continue
            if o.cell in self.partida.arena.minerios:
                keep.append(o)
            else:
                workshop.occupancy.pop(o.cell, None)
        workshop.objects = keep

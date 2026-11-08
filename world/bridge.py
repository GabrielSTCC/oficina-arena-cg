"""Espelha a grade da cena na partida Arena Bot e avança turnos."""

from __future__ import annotations

import world  # noqa: F401 — registra sys.path para config/core/ia

import config
from core.arena import Minerio
from core.partida import Partida, ResultadoPartida, criar_partida
from scene.catalog import CellKind
from scene.workshop import Workshop

_RESULT_LABEL = {
    ResultadoPartida.VITORIA_ALFA: "vence Alfa",
    ResultadoPartida.VITORIA_BETA: "vence Beta",
    ResultadoPartida.EMPATE: "empate",
    ResultadoPartida.EM_ANDAMENTO: "…",
}


class WorldBridge:
    def __init__(self) -> None:
        self.partida: Partida | None = None
        self.running = False
        self.accum = 0.0
        self.turn_interval = 0.35  # segundos por turno visual
        self.last_result: ResultadoPartida | None = None

    def seed_workshop_preview(self, workshop: Workshop, seed: int = 42) -> None:
        """Gera arena IA e popula a cena (boot / preview antes do P)."""
        preview = criar_partida(seed=seed)
        workshop.seed_from_arena(preview.arena)

    def start_from_workshop(self, workshop: Workshop, seed: int = 42) -> Partida:
        """Cria partida; sincroniza catálogo↔arena (paredes/minérios/armadilhas)."""
        self.partida = criar_partida(seed=seed)
        self.last_result = None
        arena = self.partida.arena
        kinds = workshop.sync_walls_to_kinds()
        user_built = bool(kinds["paredes"] or kinds["minerios"] or kinds["armadilhas"])

        if user_built:
            arena.paredes = set(kinds["paredes"])
            arena.armadilhas = set(kinds["armadilhas"]) - arena.paredes
            arena.minerios = {
                p: m for p, m in arena.minerios.items() if p not in arena.paredes
            }
            for cell in kinds["minerios"]:
                if cell not in arena.paredes and cell not in {
                    config.BASE_ALFA,
                    config.BASE_BETA,
                }:
                    arena.minerios[cell] = Minerio(tipo="ouro", valor=50)
            # remove minérios em armadilha/parede inválidos
            arena.minerios = {
                p: m
                for p, m in arena.minerios.items()
                if p not in arena.paredes and p not in arena.armadilhas
            }
        else:
            # cena vazia de obstáculos: espelha a geração IA
            workshop.seed_from_arena(arena)

        arena.paredes.discard(config.BASE_ALFA)
        arena.paredes.discard(config.BASE_BETA)
        arena.armadilhas.discard(config.BASE_ALFA)
        arena.armadilhas.discard(config.BASE_BETA)
        arena.minerios.pop(config.BASE_ALFA, None)
        arena.minerios.pop(config.BASE_BETA, None)

        self.partida.alfa.posicao = config.BASE_ALFA
        self.partida.beta.posicao = config.BASE_BETA
        self.running = True
        self.accum = 0.0
        workshop.editing = False
        return self.partida

    def pause(self, workshop: Workshop) -> None:
        self.running = False
        workshop.editing = True

    def toggle(self, workshop: Workshop) -> None:
        if self.partida is None or self.last_result is not None:
            self.start_from_workshop(workshop)
            return
        if self.running:
            self.pause(workshop)
        else:
            self.running = True
            workshop.editing = False

    def update(self, dt: float, workshop: Workshop | None = None) -> bool:
        """Avança turnos. Retorna True se a partida acabou neste frame."""
        if not self.running or self.partida is None:
            return False
        ended = False
        self.accum += dt
        while self.accum >= self.turn_interval:
            self.accum -= self.turn_interval
            if not self.partida.executar_turno():
                self.running = False
                self.last_result = self.partida.resultado()
                if workshop is not None:
                    workshop.editing = True
                ended = True
                break
        return ended

    def robot_cells(self) -> dict[str, tuple[int, int]]:
        if not self.partida:
            return {"Alfa": config.BASE_ALFA, "Beta": config.BASE_BETA}
        return {
            "Alfa": self.partida.alfa.posicao,
            "Beta": self.partida.beta.posicao,
        }

    def hud_line(self) -> str:
        """Placar / bateria / carga / resultado para o título da janela."""
        if self.partida is None:
            return "EDIT"
        a, b = self.partida.alfa, self.partida.beta
        score = (
            f"A {a.pontuacao}pts bat{a.bateria} c{a.carga} | "
            f"B {b.pontuacao}pts bat{b.bateria} c{b.carga} | t{self.partida.turno}"
        )
        if self.last_result is not None:
            return f"FIM {_RESULT_LABEL[self.last_result]} | {score}"
        if self.running:
            return f"SIM | {score}"
        return f"PAUSE | {score}"

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

"""HUD 2D e Menus Interativos em OpenGL: Menu Inicial, Configurações, Modos, Moeda e Placar."""

from __future__ import annotations

import ctypes
from enum import Enum
from pathlib import Path

import glm
import numpy as np
from OpenGL.GL import (
    GL_ARRAY_BUFFER,
    GL_BLEND,
    GL_CLAMP_TO_EDGE,
    GL_DEPTH_TEST,
    GL_FLOAT,
    GL_LINEAR,
    GL_ONE_MINUS_SRC_ALPHA,
    GL_RGBA,
    GL_SRC_ALPHA,
    GL_STATIC_DRAW,
    GL_TEXTURE0,
    GL_TEXTURE_2D,
    GL_TEXTURE_MAG_FILTER,
    GL_TEXTURE_MIN_FILTER,
    GL_TEXTURE_WRAP_S,
    GL_TEXTURE_WRAP_T,
    GL_TRIANGLES,
    GL_UNSIGNED_BYTE,
    glActiveTexture,
    glBindBuffer,
    glBindTexture,
    glBindVertexArray,
    glBlendFunc,
    glBufferData,
    glDisable,
    glDrawArrays,
    glEnable,
    glEnableVertexAttribArray,
    glGenBuffers,
    glGenTextures,
    glGenVertexArrays,
    glTexImage2D,
    glTexParameteri,
    glTexSubImage2D,
    glVertexAttribPointer,
)
from PIL import Image, ImageDraw, ImageFont

from gfx.mesh_loader import EURO_COIN_GLTF
from gfx.shader import Shader
from scene.coin_actor import CoinActor
from scene.robot_actor import RobotActor
from world.bridge import GameMode, WorldBridge

# (rótulo, campo ConfigPartida, passo ±). Ordem do menu de Configurações.
CONFIG_ROWS: list[tuple[str, str, int]] = [
    ("Tamanho da Arena", "tamanho_idx", 1),
    ("Quantidade de Armadilhas", "num_armadilhas", 1),
    ("Dano da Armadilha", "custo_passo_armadilha", 1),
    ("Quantidade de Paredes", "num_paredes", 1),
    ("Diamantes (2 espacos)", "num_diamante", 1),
    ("Rubis", "num_rubi", 1),
    ("Ouro", "num_ouro", 1),
    ("Prata", "num_prata", 1),
    ("Bronze", "num_bronze", 1),
    ("Quantidade de Partidas", "num_rounds", 1),
    ("Quantidade da Vida (Bateria)", "bateria_inicial", 10),
]


class AppState(Enum):
    MENU_PRINCIPAL = "menu_principal"
    MENU_CONFIG = "menu_config"
    SELECAO_ROBO = "selecao_robo"
    MENU_MODO = "menu_modo"
    MOEDA_ESCOLHA = "moeda_escolha"
    MOEDA_GIRANDO = "moeda_girando"
    MOEDA_RESULTADO = "moeda_resultado"
    EM_JOGO = "em_jogo"
    VITORIA = "vitoria"


_FONT_PATHS = (
    "/usr/share/fonts/Adwaita/AdwaitaMono-Bold.ttf",
    "/usr/share/fonts/Adwaita/AdwaitaSans-Regular.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for p in _FONT_PATHS:
        if Path(p).is_file():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _load_coin_face_icons(size: int = 64) -> tuple[Image.Image | None, Image.Image | None]:
    """Recorta ícones circulares de Cara (Águia) e Coroa (1 Euro) da textura da moeda."""
    tex_path = EURO_COIN_GLTF.parent / "textures" / "material_0_baseColor.jpeg"
    if not tex_path.is_file():
        return None, None
    try:
        src = Image.open(tex_path).convert("RGBA")
        w, h = src.size
        # No atlas: topo-direito = 1 Euro (Coroa), baixo-direito = Águia (Cara)
        box_coroa = (int(w * 0.46), int(h * 0.005), int(w * 0.925), int(h * 0.455))
        box_cara = (int(w * 0.46), int(h * 0.450), int(w * 0.925), int(h * 0.900))
        coroa = src.crop(box_coroa).rotate(-90, expand=True).resize((size, size), Image.LANCZOS)
        cara = src.crop(box_cara).rotate(-90, expand=True).resize((size, size), Image.LANCZOS)

        mask = Image.new("L", (size, size), 0)
        mdraw = ImageDraw.Draw(mask)
        mdraw.ellipse([1, 1, size - 2, size - 2], fill=255)

        out_cara = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        out_cara.paste(cara, (0, 0), mask)
        out_coroa = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        out_coroa.paste(coroa, (0, 0), mask)
        return out_cara, out_coroa
    except Exception:
        return None, None


def _project_to_screen(
    world_pos: glm.vec3,
    view: glm.mat4,
    proj: glm.mat4,
    width: int,
    height: int,
) -> tuple[int, int] | None:
    clip = proj * view * glm.vec4(world_pos, 1.0)
    if clip.w <= 0.05:
        return None
    ndc_x = clip.x / clip.w
    ndc_y = clip.y / clip.w
    if not (-1.15 <= ndc_x <= 1.15 and -1.15 <= ndc_y <= 1.15):
        return None
    sx = int((ndc_x * 0.5 + 0.5) * width)
    sy = int((1.0 - (ndc_y * 0.5 + 0.5)) * height)
    return sx, sy


def _bat_color(ratio: float) -> tuple[int, int, int, int]:
    if ratio > 0.50:
        return (46, 218, 126, 255)
    if ratio > 0.24:
        return (245, 182, 42, 255)
    return (245, 62, 58, 255)


class HudOverlay:
    """Renderiza Menus (Principal, Configurações, Modos, Moeda) e HUD tático sobre a cena 3D."""

    def __init__(self, shader_dir: Path, width: int, height: int) -> None:
        self.width = max(1, width)
        self.height = max(1, height)
        self.shader = Shader(shader_dir / "fullscreen.vert", shader_dir / "hud.frag")
        self._vao = self._make_quad()
        self.tex_id = int(glGenTextures(1))
        self._font_hero = _load_font(26)
        self._font_h1 = _load_font(20)
        self._font_title = _load_font(15)
        self._font_score = _load_font(19)
        self._font_body = _load_font(13)
        self._font_small = _load_font(11)
        self._font_popup = _load_font(13)
        self._cara_icon, self._coroa_icon = _load_coin_face_icons(62)

        self.buttons: list[tuple[str, tuple[int, int, int, int]]] = []
        self.hover_action: str | None = None
        self.selected_idx: int = 0
        self.robo_nomes: list[str] = ["Robo 3", "Robo 5"]
        self.vitoria_is_alfa: bool = True
        self.vitoria_nome: str = ""
        self.window_maximized: bool = False
        self.volume: float = 0.8
        self.vol_bar_rect: tuple[int, int, int, int] | None = None
        self._dirty = True
        self._last_redraw = 0.0
        self._redraw_interval = 0.14
        self._last_state_sig: tuple | None = None
        self._alloc_texture(self.width, self.height)

    @staticmethod
    def _make_quad() -> int:
        verts = np.array(
            [
                -1.0, -1.0, 0.0, 0.0,
                 1.0, -1.0, 1.0, 0.0,
                 1.0,  1.0, 1.0, 1.0,
                -1.0, -1.0, 0.0, 0.0,
                 1.0,  1.0, 1.0, 1.0,
                -1.0,  1.0, 0.0, 1.0,
            ],
            dtype=np.float32,
        )
        vao = int(glGenVertexArrays(1))
        vbo = int(glGenBuffers(1))
        glBindVertexArray(vao)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, verts.nbytes, verts, GL_STATIC_DRAW)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, False, 16, None)
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, False, 16, ctypes.c_void_p(8))
        glBindVertexArray(0)
        return vao

    def _alloc_texture(self, w: int, h: int) -> None:
        glBindTexture(GL_TEXTURE_2D, self.tex_id)
        empty = np.zeros((h, w, 4), dtype=np.uint8)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, empty)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

    def resize(self, width: int, height: int) -> None:
        w, h = max(1, width), max(1, height)
        if w == self.width and h == self.height:
            return
        self.width = w
        self.height = h
        self._alloc_texture(w, h)
        self._dirty = True

    def mark_dirty(self) -> None:
        self._dirty = True

    def hit_test(self, mx: float, my: float) -> str | None:
        x, y = int(mx), int(my)
        for act, (x0, y0, x1, y1) in reversed(self.buttons):
            if x0 <= x <= x1 and y0 <= y <= y1:
                return act
        return None

    def update_hover(self, mx: float, my: float) -> None:
        h = self.hit_test(mx, my)
        if h != self.hover_action:
            self.hover_action = h
            self._dirty = True

    def _draw_button(
        self,
        draw: ImageDraw.ImageDraw,
        action_id: str,
        rect: tuple[int, int, int, int],
        label: str,
        *,
        sublabel: str | None = None,
        selected: bool = False,
        accent: tuple[int, int, int, int] = (58, 222, 255, 255),
        text_offset_x: int = 0,
    ) -> None:
        x0, y0, x1, y1 = rect
        self.buttons.append((action_id, rect))
        hovered = self.hover_action == action_id
        active = hovered or selected
        bg = (26, 48, 72, 238) if active else (16, 24, 38, 222)
        outline = accent if active else (75, 98, 130, 215)
        width = 3 if active else 2
        draw.rounded_rectangle(rect, radius=8, fill=bg, outline=outline, width=width)
        mx = (x0 + x1) // 2 + text_offset_x
        if sublabel:
            draw.text((mx, y0 + 16), label, font=self._font_h1, fill=(245, 250, 255, 255), anchor="ma")
            draw.text((mx, y0 + 44), sublabel, font=self._font_small, fill=(175, 198, 225, 240), anchor="ma")
        else:
            my = (y0 + y1) // 2
            draw.text((mx, my), label, font=self._font_title, fill=(245, 250, 255, 255), anchor="mm")

    @staticmethod
    def _window_controls_layout(width: int) -> tuple[int, int, int, int]:
        """Retorna (x0, y0, size, total_w) da faixa de ícones no canto superior direito."""
        size, gap, margin = 28, 6, 10
        total_w = 3 * size + 2 * gap
        x0 = width - margin - total_w
        return x0, margin, size, total_w

    def _draw_window_controls(self, draw: ImageDraw.ImageDraw) -> None:
        """Botões minimizar / maximizar / fechar no canto superior direito."""
        x0, y0, size, _total_w = self._window_controls_layout(self.width)
        gap = 6
        icons = ("win_min", "win_max", "win_close")
        stroke = (220, 228, 238, 255)
        for i, act in enumerate(icons):
            bx = x0 + i * (size + gap)
            rect = (bx, y0, bx + size, y0 + size)
            self.buttons.append((act, rect))
            hovered = self.hover_action == act
            bg = (40, 18, 22, 230) if (act == "win_close" and hovered) else (
                (32, 48, 70, 230) if hovered else (14, 20, 30, 200)
            )
            outline = (255, 90, 90, 255) if (act == "win_close" and hovered) else (
                (90, 200, 255, 230) if hovered else (70, 90, 120, 200)
            )
            draw.rounded_rectangle(rect, radius=6, fill=bg, outline=outline, width=2)
            cx, cy = bx + size // 2, y0 + size // 2
            if act == "win_min":
                draw.line([(cx - 6, cy), (cx + 6, cy)], fill=stroke, width=2)
            elif act == "win_max":
                if self.window_maximized:
                    # restore: dois quadrados sobrepostos
                    draw.rectangle([cx - 2, cy - 7, cx + 7, cy + 2], outline=stroke, width=2)
                    draw.rectangle([cx - 7, cy - 2, cx + 2, cy + 7], outline=stroke, width=2)
                else:
                    draw.rectangle([cx - 6, cy - 6, cx + 6, cy + 6], outline=stroke, width=2)
            else:
                draw.line([(cx - 5, cy - 5), (cx + 5, cy + 5)], fill=stroke, width=2)
                draw.line([(cx + 5, cy - 5), (cx - 5, cy + 5)], fill=stroke, width=2)

    # ------------------------------------------------------------------
    # Telas de Menu (Principal, Configurações, Modos e Moeda)
    # ------------------------------------------------------------------

    def _draw_menu_principal(self, draw: ImageDraw.ImageDraw) -> None:
        pw, ph = min(560, self.width - 40), 400
        x0 = (self.width - pw) // 2
        y0 = (self.height - ph) // 2
        draw.rounded_rectangle(
            [x0, y0, x0 + pw, y0 + ph],
            radius=14,
            fill=(10, 15, 25, 228),
            outline=(58, 222, 255, 240),
            width=2,
        )
        mx = x0 + pw // 2
        draw.text(
            (mx, y0 + 22),
            "OFICINA COSY DA",
            font=self._font_hero,
            fill=(58, 222, 255, 255),
            anchor="ma",
        )
        draw.text(
            (mx, y0 + 50),
            "ARENA DE MINERACAO",
            font=self._font_hero,
            fill=(58, 222, 255, 255),
            anchor="ma",
        )
        draw.text(
            (mx, y0 + 82),
            "COMPUTACAO GRAFICA  •  ARENA BOT",
            font=self._font_body,
            fill=(175, 195, 220, 240),
            anchor="ma",
        )

        items = [
            ("menu_iniciar", "INICIAR JOGO", (58, 222, 255, 255)),
            ("menu_config", "CONFIGURACOES", (255, 190, 64, 255)),
            ("menu_sair", "SAIR", (255, 92, 82, 255)),
        ]
        bw = pw - 72
        bh = 54
        bx = x0 + 36
        for i, (act, lbl, acc) in enumerate(items):
            by = y0 + 120 + i * 70
            self._draw_button(
                draw,
                act,
                (bx, by, bx + bw, by + bh),
                lbl,
                selected=(self.selected_idx % 3 == i),
                accent=acc,
            )

        draw.text(
            (mx, y0 + ph - 28),
            "Clique com o mouse ou use [↑/↓] + [Enter]",
            font=self._font_small,
            fill=(145, 165, 192, 230),
            anchor="ma",
        )
        self._draw_volume_control(draw)

    def _draw_volume_control(self, draw: ImageDraw.ImageDraw) -> None:
        """Slider de volume no canto inferior direito (menu inicial)."""
        panel_w, panel_h = 220, 56
        margin = 14
        x0 = self.width - margin - panel_w
        y0 = self.height - margin - panel_h
        draw.rounded_rectangle(
            [x0, y0, x0 + panel_w, y0 + panel_h],
            radius=8,
            fill=(12, 18, 28, 230),
            outline=(70, 100, 140, 220),
            width=2,
        )
        draw.text(
            (x0 + 10, y0 + 6),
            "VOLUME",
            font=self._font_small,
            fill=(160, 185, 215, 255),
        )
        pct = int(round(max(0.0, min(1.0, self.volume)) * 100))
        draw.text(
            (x0 + panel_w - 10, y0 + 6),
            f"{pct}%",
            font=self._font_small,
            fill=(255, 230, 120, 255),
            anchor="ra",
        )

        btn = 22
        by = y0 + 28
        self._draw_button(
            draw,
            "vol_down",
            (x0 + 8, by, x0 + 8 + btn, by + btn),
            "-",
            accent=(255, 140, 90, 255),
        )
        self._draw_button(
            draw,
            "vol_up",
            (x0 + panel_w - 8 - btn, by, x0 + panel_w - 8, by + btn),
            "+",
            accent=(80, 235, 145, 255),
        )

        bar_x0 = x0 + 8 + btn + 8
        bar_x1 = x0 + panel_w - 8 - btn - 8
        bar_y0 = by + 6
        bar_y1 = by + btn - 6
        self.vol_bar_rect = (bar_x0, bar_y0, bar_x1, bar_y1)
        self.buttons.append(("vol_bar", self.vol_bar_rect))
        draw.rounded_rectangle(
            [bar_x0, bar_y0, bar_x1, bar_y1],
            radius=4,
            fill=(28, 36, 50, 240),
            outline=(80, 100, 130, 220),
            width=1,
        )
        t = max(0.0, min(1.0, self.volume))
        fill_w = int(t * (bar_x1 - bar_x0 - 4))
        if fill_w > 0:
            draw.rounded_rectangle(
                [bar_x0 + 2, bar_y0 + 2, bar_x0 + 2 + fill_w, bar_y1 - 2],
                radius=3,
                fill=(58, 200, 255, 230),
            )
        knob_x = bar_x0 + int(t * (bar_x1 - bar_x0))
        knob_r = 6
        draw.ellipse(
            [knob_x - knob_r, (bar_y0 + bar_y1) // 2 - knob_r, knob_x + knob_r, (bar_y0 + bar_y1) // 2 + knob_r],
            fill=(245, 250, 255, 255),
            outline=(58, 222, 255, 255),
            width=2,
        )

    def volume_from_x(self, mx: float) -> float | None:
        """Converte coordenada X do mouse em volume 0–1 (barra do menu)."""
        if self.vol_bar_rect is None:
            return None
        x0, _y0, x1, _y1 = self.vol_bar_rect
        span = max(1, x1 - x0)
        return max(0.0, min(1.0, (float(mx) - x0) / span))

    def _config_value_str(self, cfg, campo: str) -> str:
        import config as world_config

        if campo == "tamanho_idx":
            return f"{cfg.largura}x{cfg.altura}"
        if campo == "custo_passo_armadilha":
            return f"-{cfg.custo_passo_armadilha} BAT"
        if campo == "bateria_inicial":
            return f"{cfg.bateria_inicial} (min {cfg.bateria_recomendada()})"
        valor = int(getattr(cfg, campo))
        if campo.startswith("num_") and campo[4:] in world_config.MIN_MINERIO:
            tipo = campo[4:]
            return f"{valor} (min {cfg.min_minerio(tipo)})"
        return str(valor)

    def _draw_menu_config(self, draw: ImageDraw.ImageDraw, bridge: WorldBridge) -> None:
        cfg = bridge.cfg
        n_rows = len(CONFIG_ROWS)
        n_opts = n_rows + 2
        header, footer = 56, 86
        row_step = max(30, min(42, (self.height - 24 - header - footer) // n_rows))
        row_h = row_step - 4
        ph = min(header + n_rows * row_step + footer, self.height - 16)
        pw = min(640, self.width - 28)
        x0 = (self.width - pw) // 2
        y0 = (self.height - ph) // 2
        draw.rounded_rectangle(
            [x0, y0, x0 + pw, y0 + ph],
            radius=14,
            fill=(10, 15, 25, 232),
            outline=(255, 190, 64, 240),
            width=2,
        )
        mx = x0 + pw // 2
        draw.text((mx, y0 + 16), "CONFIGURACOES DA PARTIDA", font=self._font_h1, fill=(255, 200, 75, 255), anchor="ma")
        draw.text(
            (mx, y0 + 38),
            "Arena, armadilhas, paredes, minerios, partidas e bateria",
            font=self._font_small,
            fill=(170, 188, 212, 240),
            anchor="ma",
        )

        rx0 = x0 + 26
        rw = pw - 52
        btn_h = max(24, row_h - 6)
        for i, (label, campo, passo) in enumerate(CONFIG_ROWS):
            ry = y0 + header + i * row_step
            sel = (self.selected_idx % n_opts) == i
            row_bg = (22, 34, 52, 230) if sel else (15, 22, 34, 210)
            row_out = (58, 222, 255, 230) if sel else (55, 72, 96, 190)
            draw.rounded_rectangle([rx0, ry, rx0 + rw, ry + row_h], radius=6, fill=row_bg, outline=row_out, width=2 if sel else 1)
            mid_y = ry + row_h // 2
            draw.text((rx0 + 12, mid_y), label, font=self._font_body, fill=(235, 242, 252, 255), anchor="lm")

            bx_inc = rx0 + rw - 44
            bx_val = rx0 + rw - 200
            bx_dec = rx0 + rw - 238
            by0 = ry + (row_h - btn_h) // 2
            self._draw_button(draw, f"cfg:{campo}:{-passo}", (bx_dec, by0, bx_dec + 32, by0 + btn_h), "-", accent=(255, 120, 80, 255))
            draw.rounded_rectangle([bx_val, by0, bx_val + 150, by0 + btn_h], radius=5, fill=(10, 14, 22, 240), outline=(80, 100, 130, 200))
            draw.text((bx_val + 75, mid_y), self._config_value_str(cfg, campo), font=self._font_title, fill=(255, 232, 135, 255), anchor="mm")
            self._draw_button(draw, f"cfg:{campo}:{passo}", (bx_inc, by0, bx_inc + 32, by0 + btn_h), "+", accent=(80, 235, 145, 255))

        by = y0 + ph - footer + 8
        bw = (rw - 16) // 2
        self._draw_button(
            draw,
            "cfg_padrao",
            (rx0, by, rx0 + bw, by + 40),
            "RESTAURAR PADROES",
            selected=(self.selected_idx % n_opts == n_rows),
            accent=(255, 185, 65, 255),
        )
        self._draw_button(
            draw,
            "cfg_voltar",
            (rx0 + bw + 16, by, rx0 + rw, by + 40),
            "VOLTAR AO MENU",
            selected=(self.selected_idx % n_opts == n_rows + 1),
            accent=(58, 222, 255, 255),
        )
        draw.text(
            (mx, y0 + ph - 14),
            "Setas [↑/↓] escolhem linha  •  [←/→] alteram valor  •  [ESC] Voltar",
            font=self._font_small,
            fill=(145, 165, 192, 230),
            anchor="ma",
        )

    def _draw_menu_robo(self, draw: ImageDraw.ImageDraw, nomes: list[str]) -> None:
        """Overlay da seleção: cartões clicáveis sob os modelos 3D."""
        mx = self.width // 2
        draw.text(
            (mx, 28),
            "ESCOLHA SEU ROBO",
            font=self._font_h1,
            fill=(255, 210, 80, 255),
            anchor="ma",
        )
        draw.text(
            (mx, 56),
            "O escolhido joga como Alfa  •  o outro e o adversario (Beta)",
            font=self._font_small,
            fill=(170, 190, 215, 240),
            anchor="ma",
        )
        n = max(1, len(nomes))
        card_w = min(220, self.width // 3)
        gap = 40
        total = n * card_w + (n - 1) * gap
        x0 = (self.width - total) // 2
        by = self.height - 150
        for i, nome in enumerate(nomes):
            cx = x0 + i * (card_w + gap)
            sel = (self.selected_idx % n) == i
            self._draw_button(
                draw,
                f"robo_sel:{i}",
                (cx, by, cx + card_w, by + 52),
                nome,
                selected=sel,
                accent=(58, 222, 255, 255) if i == 0 else (255, 148, 68, 255),
            )
        bw = min(280, self.width // 3)
        self._draw_button(
            draw,
            "robo_confirmar",
            (mx - bw - 10, self.height - 80, mx - 10, self.height - 36),
            "CONFIRMAR [Enter]",
            selected=False,
            accent=(82, 240, 148, 255),
        )
        self._draw_button(
            draw,
            "robo_voltar",
            (mx + 10, self.height - 80, mx + bw + 10, self.height - 36),
            "VOLTAR [ESC]",
            selected=False,
            accent=(180, 195, 215, 255),
        )

    def _draw_vitoria(
        self,
        draw: ImageDraw.ImageDraw,
        bridge: WorldBridge,
        winner_nome: str,
        *,
        is_alfa: bool = True,
    ) -> None:
        mx = self.width // 2
        who = "ALFA" if is_alfa else "BETA"
        col = (58, 222, 255, 255) if is_alfa else (255, 148, 68, 255)
        draw.rounded_rectangle(
            [mx - 260, 18, mx + 260, 110],
            radius=12,
            fill=(10, 15, 26, 230),
            outline=col,
            width=2,
        )
        draw.text((mx, 36), f"VENCEDOR: {who}", font=self._font_h1, fill=col, anchor="ma")
        draw.text(
            (mx, 68),
            f"{winner_nome}  •  Partida {bridge.round_atual}/{bridge.cfg.num_rounds}",
            font=self._font_title,
            fill=(255, 230, 140, 255),
            anchor="ma",
        )
        draw.text(
            (mx, 92),
            "[ENTER] continuar  •  [ESC] menu",
            font=self._font_small,
            fill=(170, 190, 215, 240),
            anchor="ma",
        )

    def _draw_menu_modo(self, draw: ImageDraw.ImageDraw) -> None:
        pw, ph = min(540, self.width - 36), 420
        x0 = (self.width - pw) // 2
        y0 = (self.height - ph) // 2
        draw.rounded_rectangle(
            [x0, y0, x0 + pw, y0 + ph],
            radius=14,
            fill=(10, 15, 25, 232),
            outline=(58, 222, 255, 240),
            width=2,
        )
        mx = x0 + pw // 2
        draw.text((mx, y0 + 24), "SELECIONE O MODO DE JOGO", font=self._font_h1, fill=(58, 222, 255, 255), anchor="ma")
        draw.text(
            (mx, y0 + 52),
            "Antes da partida, a moeda 3D decidira quem comeca!",
            font=self._font_small,
            fill=(175, 195, 220, 240),
            anchor="ma",
        )

        modes = [
            ("modo_com_com", "COM vs COM", "Robo vs Robo (IA Alfa vs IA Beta)", (58, 222, 255, 255)),
            ("modo_p1_com", "P1 vs COM", "Jogador 1 [WASD] vs IA Beta", (95, 240, 155, 255)),
            ("modo_p1_p2", "P1 vs P2", "P1 [WASD] vs P2 [Setas Direcionais ↑↓←→]", (255, 145, 62, 255)),
        ]
        bx = x0 + 30
        bw = pw - 60
        for i, (act, title, sub, acc) in enumerate(modes):
            by = y0 + 84 + i * 80
            self._draw_button(
                draw,
                act,
                (bx, by, bx + bw, by + 68),
                title,
                sublabel=sub,
                selected=(self.selected_idx % 4 == i),
                accent=acc,
            )

        by_back = y0 + ph - 72
        self._draw_button(
            draw,
            "modo_voltar",
            (bx, by_back, bx + bw, by_back + 44),
            "VOLTAR AO MENU PRINCIPAL [ESC]",
            selected=(self.selected_idx % 4 == 3),
            accent=(180, 195, 215, 255),
        )

    def _draw_moeda_overlay(
        self,
        draw: ImageDraw.ImageDraw,
        img: Image.Image,
        state: AppState,
        bridge: WorldBridge,
        coin: CoinActor,
    ) -> None:
        # Banner no topo (deixando o centro da tela livre para a moeda 3D!)
        bw = min(680, self.width - 28)
        bx0 = (self.width - bw) // 2
        by0 = 14
        bh = 86
        draw.rounded_rectangle(
            [bx0, by0, bx0 + bw, by0 + bh],
            radius=12,
            fill=(10, 16, 28, 226),
            outline=(255, 205, 75, 245),
            width=2,
        )
        mx = self.width // 2
        draw.text(
            (mx, by0 + 14),
            f"SORTEIO DA MOEDA 3D (1 EURO)  •  {bridge.mode.value} (Partida {bridge.round_atual}/{bridge.cfg.num_rounds})",
            font=self._font_title,
            fill=(255, 215, 90, 255),
            anchor="ma",
        )
        if state == AppState.MOEDA_ESCOLHA:
            draw.text(
                (mx, by0 + 42),
                "Escolha CARA (Aguia) ou COROA (1 Euro) para lancar a moeda:",
                font=self._font_body,
                fill=(235, 242, 252, 255),
                anchor="ma",
            )
            draw.text(
                (mx, by0 + 64),
                "O lado que cair define qual robo inicia a partida!",
                font=self._font_small,
                fill=(170, 190, 218, 240),
                anchor="ma",
            )
        elif state == AppState.MOEDA_GIRANDO:
            esc = coin.chosen_side.upper()
            draw.text(
                (mx, by0 + 46),
                f"Jogando a moeda... (Alfa escolheu {esc})",
                font=self._font_h1,
                fill=(95, 235, 255, 255),
                anchor="ma",
            )
        else:
            res = coin.result_side.upper()
            starter = coin.winner_starter.upper()
            col = (58, 222, 255, 255) if starter == "ALFA" else (255, 138, 58, 255)
            draw.text(
                (mx, by0 + 44),
                f"CAIU {res}! ROBO {starter} INICIA A PARTIDA!",
                font=self._font_h1,
                fill=col,
                anchor="ma",
            )

        # Painel inferior com os botões de escolha ou de iniciar partida
        pw = min(680, self.width - 28)
        px0 = (self.width - pw) // 2
        py0 = self.height - 132
        ph = 114
        draw.rounded_rectangle(
            [px0, py0, px0 + pw, py0 + ph],
            radius=12,
            fill=(10, 16, 28, 226),
            outline=(85, 110, 145, 225),
            width=2,
        )

        if state == AppState.MOEDA_ESCOLHA:
            cw = (pw - 42) // 2
            c1_rect = (px0 + 14, py0 + 14, px0 + 14 + cw, py0 + ph - 14)
            c2_rect = (px0 + 28 + cw, py0 + 14, px0 + pw - 14, py0 + ph - 14)
            self._draw_button(
                draw,
                "moeda_cara",
                c1_rect,
                "CARA (AGUIA)",
                sublabel="Escolher Cara [Tecla 1 / ←]",
                selected=(self.selected_idx % 2 == 0),
                accent=(58, 222, 255, 255),
                text_offset_x=28,
            )
            self._draw_button(
                draw,
                "moeda_coroa",
                c2_rect,
                "COROA (1 EURO)",
                sublabel="Escolher Coroa [Tecla 2 / →]",
                selected=(self.selected_idx % 2 == 1),
                accent=(255, 195, 68, 255),
                text_offset_x=28,
            )
            if self._cara_icon is not None:
                img.paste(self._cara_icon, (c1_rect[0] + 12, c1_rect[1] + 12), self._cara_icon)
            if self._coroa_icon is not None:
                img.paste(self._coroa_icon, (c2_rect[0] + 12, c2_rect[1] + 12), self._coroa_icon)
        elif state == AppState.MOEDA_GIRANDO:
            draw.text(
                (mx, py0 + ph // 2),
                "A moeda 3D esta girando no ar...",
                font=self._font_h1,
                fill=(235, 242, 252, 255),
                anchor="mm",
            )
        else:
            esc = coin.chosen_side.upper()
            res = coin.result_side.upper()
            starter = coin.winner_starter.upper()
            draw.text(
                (mx, py0 + 24),
                f"Escolha Alfa (P1): {esc}   •   Moeda caiu em: {res}   •   1o Turno: {starter}",
                font=self._font_body,
                fill=(230, 238, 250, 255),
                anchor="ma",
            )
            self._draw_button(
                draw,
                "moeda_iniciar",
                (px0 + 90, py0 + 52, px0 + pw - 90, py0 + ph - 14),
                f"INICIAR PARTIDA ({starter} COMECA) [Enter / Clique]",
                selected=True,
                accent=(82, 240, 148, 255),
            )

    # ------------------------------------------------------------------
    # HUD de Partida (Placar, Vida/Bateria, Carga máx 3, Dano e Fim de Jogo)
    # ------------------------------------------------------------------

    def _draw_agent_card(
        self,
        draw: ImageDraw.ImageDraw,
        x0: int,
        y0: int,
        w: int,
        h: int,
        *,
        title: str,
        accent: tuple[int, int, int, int],
        agente,
        actor: RobotActor,
        arena,
        is_turn: bool,
    ) -> None:
        is_trap_hit = actor.damage_timer > 0.0
        bg = (52, 14, 18, 228) if is_trap_hit else (11, 16, 26, 218)
        border = (255, 72, 62, 255) if is_trap_hit else (accent if is_turn else (68, 86, 112, 210))
        draw.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=8, fill=bg, outline=border, width=3 if is_turn else 2)

        estado_txt = agente.status_bc if agente is not None else "Pronto"
        pts = int(agente.pontuacao) if agente is not None else 0
        bat = int(agente.bateria) if agente is not None else 100
        bat_max = int(agente.bateria_maxima) if agente is not None else 100
        carga = int(agente.carga) if agente is not None else 0
        volta_val = agente.custo_retorno_base(arena) if (agente is not None and arena is not None) else 0.0
        volta = int(volta_val) if volta_val < 999 else 0

        # Linha 1: Nome do robô à esquerda e Placar alinhado à direita
        draw.text((x0 + 10, y0 + 7), title, font=self._font_title, fill=accent)
        score_str = f"{pts} PTS"
        draw.text((x0 + w - 10, y0 + 5), score_str, font=self._font_score, fill=(255, 238, 150, 255), anchor="ra")

        # Linha 2: Barra de vida/bateria + indicador de passo/dano
        bx0, by0 = x0 + 10, y0 + 32
        bw = max(110, min(160, w - 165))
        bh = 16
        draw.rounded_rectangle(
            [bx0, by0, bx0 + bw, by0 + bh],
            radius=4,
            fill=(26, 32, 44, 240),
            outline=(70, 82, 102, 220),
            width=1,
        )
        ratio = max(0.0, min(1.0, bat / max(1, bat_max)))
        fill_w = int(ratio * (bw - 4))
        if fill_w > 0:
            draw.rounded_rectangle(
                [bx0 + 2, by0 + 2, bx0 + 2 + fill_w, by0 + bh - 2],
                radius=3,
                fill=_bat_color(ratio),
            )
        draw.text(
            (bx0 + 6, by0 + 1),
            f"VIDA {bat:3d}/{bat_max}",
            font=self._font_small,
            fill=(245, 248, 255, 255),
        )

        # Badge de gasto do passo (-2 BAT ou -X ARMADILHA!)
        px = bx0 + bw + 8
        pw = max(90, x0 + w - px - 8)
        if actor.popup_timer > 0.0 and actor.last_delta_bat != 0:
            if actor.last_is_trap:
                p_txt = f"DANO {actor.last_delta_bat} BAT!"
                p_bg = (225, 38, 38, 245)
            elif actor.last_delta_bat < 0:
                p_txt = f"PASSO {actor.last_delta_bat} BAT"
                p_bg = (210, 135, 24, 235)
            else:
                p_txt = "VIDA 100%"
                p_bg = (28, 145, 78, 235)
            draw.rounded_rectangle([px, by0 - 1, px + pw, by0 + bh + 1], radius=4, fill=p_bg)
            draw.text((px + 6, by0 + 1), p_txt, font=self._font_small, fill=(255, 255, 255, 255))
        else:
            draw.text(
                (px + 2, by0 + 1),
                f"Volta: {volta} bat",
                font=self._font_small,
                fill=(170, 184, 205, 235),
            )

        # Linha 3: Slots de carga (máximo 3 minérios por rota) + status
        cy = y0 + 55
        draw.text((x0 + 10, cy), "CARGA:", font=self._font_body, fill=(210, 220, 235, 255))
        sx = x0 + 64
        for slot in range(3):
            filled = slot < carga
            s_fill = (250, 200, 58, 245) if filled else (30, 36, 48, 220)
            s_out = (255, 235, 130, 255) if filled else (85, 96, 115, 200)
            draw.rounded_rectangle(
                [sx + slot * 20, cy + 1, sx + slot * 20 + 15, cy + 15],
                radius=3,
                fill=s_fill,
                outline=s_out,
                width=1,
            )
        draw.text(
            (sx + 64, cy + 1),
            f"{carga}/3  [{estado_txt}]",
            font=self._font_small,
            fill=(230, 238, 250, 255),
        )

    def _draw_robot_floating_tag(
        self,
        draw: ImageDraw.ImageDraw,
        sx: int,
        sy: int,
        *,
        name: str,
        accent: tuple[int, int, int, int],
        agente,
        actor: RobotActor,
    ) -> None:
        bat = int(agente.bateria) if agente is not None else 100
        bat_max = int(agente.bateria_maxima) if agente is not None else 100
        carga = int(agente.carga) if agente is not None else 0
        tw, th = 132, 34
        x0 = max(6, min(self.width - tw - 6, sx - tw // 2))
        y0 = max(92, min(self.height - th - 6, sy - th))

        is_trap = actor.damage_timer > 0.0
        bg = (60, 14, 16, 224) if is_trap else (12, 18, 28, 210)
        outline = (255, 68, 58, 255) if is_trap else accent
        draw.rounded_rectangle([x0, y0, x0 + tw, y0 + th], radius=6, fill=bg, outline=outline, width=2)

        dots = "".join("●" if i < carga else "○" for i in range(3))
        draw.text((x0 + 7, y0 + 3), f"{name}  {dots} {carga}/3", font=self._font_small, fill=accent)

        # Mini barra de vida/bateria
        bx, by, bw, bh = x0 + 7, y0 + 19, tw - 14, 10
        draw.rectangle([bx, by, bx + bw, by + bh], fill=(28, 34, 46, 240), outline=(72, 82, 100, 220))
        ratio = max(0.0, min(1.0, bat / max(1, bat_max)))
        fw = int(ratio * (bw - 2))
        if fw > 0:
            draw.rectangle([bx + 1, by + 1, bx + 1 + fw, by + bh - 1], fill=_bat_color(ratio))
        draw.text((bx + 26, by - 2), f"{bat}/{bat_max}", font=self._font_small, fill=(255, 255, 255, 255))

        # Popup flutuante acima da etiqueta (gasto de bateria a cada passo / dano de armadilha)
        if actor.popup_timer > 0.0 and (actor.last_delta_bat != 0 or actor.last_event_text):
            py = max(90, y0 - 28)
            if actor.last_is_trap:
                label = f"DANO ARMADILHA {actor.last_delta_bat} BAT!"
                p_fill = (230, 32, 32, 248)
                p_out = (255, 210, 190, 255)
            elif actor.last_delta_bat < 0:
                extra = f" | {actor.last_event_text}" if (actor.last_event_text and "Passo" not in actor.last_event_text) else ""
                label = f"{actor.last_delta_bat} BAT{extra}"
                p_fill = (22, 34, 52, 238)
                p_out = (255, 195, 65, 245)
            else:
                label = actor.last_event_text
                p_fill = (20, 95, 58, 238)
                p_out = (120, 255, 175, 250)

            pw = max(92, len(label) * 8 + 16)
            px = max(6, min(self.width - pw - 6, sx - pw // 2))
            draw.rounded_rectangle([px, py, px + pw, py + 22], radius=5, fill=p_fill, outline=p_out, width=2)
            draw.text((px + 8, py + 3), label, font=self._font_popup, fill=(255, 255, 255, 255))

    def _draw_match_hud(
        self,
        draw: ImageDraw.ImageDraw,
        bridge: WorldBridge,
        actor_alfa: RobotActor,
        actor_beta: RobotActor,
        view: glm.mat4,
        proj: glm.mat4,
    ) -> None:
        partida = bridge.partida
        alfa = partida.alfa if partida is not None else None
        beta = partida.beta if partida is not None else None
        arena = partida.arena if partida is not None else None
        whose = bridge.whose_turn()

        alfa_tag = "P1 [WASD]" if bridge.mode != GameMode.COM_VS_COM else "COM"
        beta_tag = "P2 [SETAS]" if bridge.mode == GameMode.P1_VS_P2 else "COM"

        card_w = min(375, max(285, int(self.width * 0.34)))
        card_h = 78
        # Reserva a faixa dos ícones de janela à direita (não cobrir placar do Beta)
        _ix, _iy, _isz, win_w = self._window_controls_layout(self.width)
        beta_right_pad = win_w + 16
        self._draw_agent_card(
            draw,
            10,
            8,
            card_w,
            card_h,
            title=f"ALFA • {alfa_tag}",
            accent=(58, 222, 255, 255),
            agente=alfa,
            actor=actor_alfa,
            arena=arena,
            is_turn=(whose == "Alfa" and bridge.running),
        )
        self._draw_agent_card(
            draw,
            self.width - card_w - beta_right_pad,
            8,
            card_w,
            card_h,
            title=f"BETA • {beta_tag}",
            accent=(255, 128, 52, 255),
            agente=beta,
            actor=actor_beta,
            arena=arena,
            is_turn=(whose == "Beta" and bridge.running),
        )

        # Painel central: Modo, Partida X/N, Vez e Atalhos
        cx0 = card_w + 18
        cw = max(180, self.width - card_w - beta_right_pad - card_w - 28)
        cmid = cx0 + cw // 2
        draw.rounded_rectangle(
            [cx0, 8, cx0 + cw, 8 + card_h],
            radius=8,
            fill=(14, 20, 32, 218),
            outline=(90, 112, 145, 220),
            width=2,
        )
        turno = partida.turno if partida is not None else 0
        restantes = len(arena.minerios) if arena is not None else 0
        if bridge.last_result is not None:
            status = f"FIM: {bridge.result_label()}"
            s_col = (255, 225, 95, 255)
        elif bridge.running:
            if bridge.is_human_controlled(whose):
                tecla = "WASD" if whose == "Alfa" else "SETAS"
                status = f"VEZ DE {whose.upper()} [{tecla}]"
                s_col = (58, 222, 255, 255) if whose == "Alfa" else (255, 148, 68, 255)
            else:
                status = f"IA ({whose.upper()}) JOGANDO"
                s_col = (95, 245, 155, 255)
        else:
            status = "PAUSADO (P continua)"
            s_col = (140, 205, 255, 255)

        draw.text((cmid, 12), status, font=self._font_title, fill=s_col, anchor="ma")
        draw.text(
            (cmid, 35),
            f"Partida {bridge.round_atual}/{bridge.cfg.num_rounds} ({bridge.vitorias_alfa}x{bridge.vitorias_beta}) | Min: {restantes}",
            font=self._font_small,
            fill=(230, 236, 248, 255),
            anchor="ma",
        )
        draw.text(
            (cmid, 56),
            f"Turno {turno} | [P] Pausa [R] Novo [M] Menu",
            font=self._font_small,
            fill=(168, 184, 208, 240),
            anchor="ma",
        )

        # Etiquetas flutuantes sobre os robôs no espaço 3D -> 2D
        pos_a = _project_to_screen(
            actor_alfa._to + glm.vec3(0.0, 2.05, 0.0),
            view,
            proj,
            self.width,
            self.height,
        )
        if pos_a is not None:
            self._draw_robot_floating_tag(
                draw,
                pos_a[0],
                pos_a[1],
                name="ALFA",
                accent=(58, 222, 255, 255),
                agente=alfa,
                actor=actor_alfa,
            )

        pos_b = _project_to_screen(
            actor_beta._to + glm.vec3(0.0, 2.05, 0.0),
            view,
            proj,
            self.width,
            self.height,
        )
        if pos_b is not None:
            self._draw_robot_floating_tag(
                draw,
                pos_b[0],
                pos_b[1],
                name="BETA",
                accent=(255, 128, 52, 255),
                agente=beta,
                actor=actor_beta,
            )

        # Modal de fim de partida / rodada
        if bridge.last_result is not None:
            mw, mh = min(460, self.width - 40), 230
            mx0 = (self.width - mw) // 2
            my0 = (self.height - mh) // 2
            draw.rounded_rectangle(
                [mx0, my0, mx0 + mw, my0 + mh],
                radius=12,
                fill=(10, 15, 26, 235),
                outline=(255, 205, 75, 245),
                width=2,
            )
            mmx = mx0 + mw // 2
            draw.text((mmx, my0 + 20), f"FIM DA PARTIDA {bridge.round_atual}/{bridge.cfg.num_rounds}", font=self._font_title, fill=(180, 200, 225, 255), anchor="ma")
            draw.text((mmx, my0 + 48), bridge.result_label(), font=self._font_hero, fill=(255, 222, 88, 255), anchor="ma")
            pts_a = alfa.pontuacao if alfa else 0
            pts_b = beta.pontuacao if beta else 0
            draw.text(
                (mmx, my0 + 86),
                f"Placar: Alfa {pts_a} pts vs Beta {pts_b} pts  |  Serie: {bridge.vitorias_alfa}x{bridge.vitorias_beta}",
                font=self._font_body,
                fill=(235, 242, 252, 255),
                anchor="ma",
            )
            if bridge.has_next_round():
                self._draw_button(
                    draw,
                    "jogo_prox_round",
                    (mx0 + 28, my0 + 120, mx0 + mw - 28, my0 + 164),
                    f"PROXIMA PARTIDA ({bridge.round_atual + 1}/{bridge.cfg.num_rounds}) [Enter]",
                    selected=True,
                    accent=(82, 240, 148, 255),
                )
            else:
                draw.text((mmx, my0 + 112), bridge.series_summary_label(), font=self._font_title, fill=(95, 245, 165, 255), anchor="ma")
                self._draw_button(
                    draw,
                    "jogo_nova_serie",
                    (mx0 + 28, my0 + 136, mx0 + mw - 28, my0 + 174),
                    "JOGAR NOVAMENTE [R / Enter]",
                    selected=True,
                    accent=(58, 222, 255, 255),
                )
            self._draw_button(
                draw,
                "jogo_menu",
                (mx0 + 28, my0 + 180, mx0 + mw - 28, my0 + 218),
                "VOLTAR AO MENU PRINCIPAL [M / ESC]",
                accent=(200, 210, 228, 255),
            )

    def _render_hud_image(
        self,
        state: AppState,
        bridge: WorldBridge,
        actor_alfa: RobotActor,
        actor_beta: RobotActor,
        coin: CoinActor,
        view: glm.mat4,
        proj: glm.mat4,
    ) -> np.ndarray:
        self.buttons.clear()
        self.vol_bar_rect = None
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        if state == AppState.MENU_PRINCIPAL:
            self._draw_menu_principal(draw)
        elif state == AppState.MENU_CONFIG:
            self._draw_menu_config(draw, bridge)
        elif state == AppState.SELECAO_ROBO:
            nomes = [
                getattr(actor_alfa, "_sel_nome_0", "Robo 3"),
                getattr(actor_alfa, "_sel_nome_1", "Robo 5"),
            ]
            # application injeta nomes via hud.robo_nomes
            nomes = getattr(self, "robo_nomes", nomes)
            self._draw_menu_robo(draw, list(nomes))
        elif state == AppState.MENU_MODO:
            self._draw_menu_modo(draw)
        elif state in (AppState.MOEDA_ESCOLHA, AppState.MOEDA_GIRANDO, AppState.MOEDA_RESULTADO):
            self._draw_moeda_overlay(draw, img, state, bridge, coin)
        elif state == AppState.VITORIA:
            is_alfa = getattr(self, "vitoria_is_alfa", True)
            nome = getattr(self, "vitoria_nome", "")
            self._draw_vitoria(draw, bridge, nome, is_alfa=is_alfa)
        else:
            self._draw_match_hud(draw, bridge, actor_alfa, actor_beta, view, proj)

        self._draw_window_controls(draw)
        return np.asarray(img, dtype=np.uint8)

    def _compute_state_sig(
        self,
        state: AppState,
        bridge: WorldBridge,
        actor_alfa: RobotActor,
        actor_beta: RobotActor,
        coin: CoinActor,
        view: glm.mat4,
    ) -> tuple:
        if state != AppState.EM_JOGO:
            return (
                state,
                self.selected_idx,
                self.hover_action,
                self.window_maximized,
                round(self.volume, 2),
                bridge.mode,
                bridge.round_atual,
                bridge.cfg.tamanho_idx,
                bridge.cfg.num_armadilhas,
                bridge.cfg.custo_passo_armadilha,
                bridge.cfg.num_paredes,
                bridge.cfg.num_diamante,
                bridge.cfg.num_rubi,
                bridge.cfg.num_ouro,
                bridge.cfg.num_prata,
                bridge.cfg.num_bronze,
                bridge.cfg.num_rounds,
                bridge.cfg.bateria_inicial,
                coin.chosen_side,
                coin.result_side,
            )
        p = bridge.partida
        a = p.alfa if p is not None else None
        b = p.beta if p is not None else None
        cam_sig = (
            round(float(view[3][0]), 1),
            round(float(view[3][1]), 1),
            round(float(view[3][2]), 1),
            round(float(view[0][0]), 2),
        )
        return (
            state,
            self.hover_action,
            self.window_maximized,
            bridge.running,
            bridge.last_result,
            bridge.round_atual,
            p.turno if p is not None else 0,
            a.posicao if a is not None else None,
            b.posicao if b is not None else None,
            a.bateria if a is not None else 0,
            b.bateria if b is not None else 0,
            a.carga if a is not None else 0,
            b.carga if b is not None else 0,
            a.pontuacao if a is not None else 0,
            b.pontuacao if b is not None else 0,
            actor_alfa.popup_timer > 0.0,
            actor_beta.popup_timer > 0.0,
            actor_alfa.damage_timer > 0.0,
            actor_beta.damage_timer > 0.0,
            cam_sig,
        )

    def draw(
        self,
        now: float,
        state: AppState,
        bridge: WorldBridge,
        actor_alfa: RobotActor,
        actor_beta: RobotActor,
        coin: CoinActor,
        view: glm.mat4,
        proj: glm.mat4,
    ) -> None:
        sig = self._compute_state_sig(state, bridge, actor_alfa, actor_beta, coin, view)
        if self._dirty or sig != self._last_state_sig:
            self._dirty = False
            self._last_state_sig = sig
            self._last_redraw = now
            arr = self._render_hud_image(state, bridge, actor_alfa, actor_beta, coin, view, proj)
            glBindTexture(GL_TEXTURE_2D, self.tex_id)
            glTexSubImage2D(
                GL_TEXTURE_2D,
                0,
                0,
                0,
                self.width,
                self.height,
                GL_RGBA,
                GL_UNSIGNED_BYTE,
                arr,
            )

        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self.shader.use()
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.tex_id)
        self.shader.set_int("uHud", 0)
        glBindVertexArray(self._vao)
        glDrawArrays(GL_TRIANGLES, 0, 6)
        glBindVertexArray(0)
        glEnable(GL_DEPTH_TEST)
